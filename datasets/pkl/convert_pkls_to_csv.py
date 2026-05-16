#!/usr/bin/env python
"""Export PKL motions as numeric CSV files accepted by scripts/csv_to_npz.py.

Each output row is:
  root_trans_offset(3), root_rot_xyzw(4), dof(23)

The output intentionally has no header because csv_to_npz.py reads files with
np.loadtxt(delimiter=",").
"""

from __future__ import annotations

import argparse
import csv
import inspect
import sys
from pathlib import Path
import pathlib

import joblib
import numpy as np


def patch_pathlib_for_windows() -> None:
    if sys.platform.startswith("win"):
        pathlib.PosixPath = pathlib.WindowsPath


def patch_old_joblib_alignment() -> None:
    import joblib.numpy_pickle as numpy_pickle
    from joblib.numpy_pickle import _read_bytes

    try:
        source = inspect.getsource(numpy_pickle.NumpyArrayWrapper.read_array)
    except (OSError, TypeError):
        source = ""

    if "numpy_array_alignment_bytes" in source:
        return
    if getattr(numpy_pickle.NumpyArrayWrapper.read_array, "_g1_alignment_patch", False):
        return

    original_read_array = numpy_pickle.NumpyArrayWrapper.read_array

    def read_array_with_alignment(self, unpickler):
        if hasattr(self, "numpy_array_alignment_bytes"):
            pad_len = _read_bytes(
                unpickler.file_handle, 1, "alignment padding length"
            )[0]
            if pad_len:
                _read_bytes(unpickler.file_handle, pad_len, "alignment padding")
        return original_read_array(self, unpickler)

    read_array_with_alignment._g1_alignment_patch = True
    numpy_pickle.NumpyArrayWrapper.read_array = read_array_with_alignment


def load_motion_file(path: Path) -> dict:
    patch_pathlib_for_windows()
    patch_old_joblib_alignment()
    data = joblib.load(path)
    if not isinstance(data, dict):
        raise TypeError(f"Expected dict, got {type(data).__name__}")
    return data


def scalar(value, default=30):
    if value is None:
        return default
    arr = np.asarray(value)
    if arr.ndim == 0:
        return arr.item()
    return default


def sanitize_name(name: str) -> str:
    safe = []
    for char in name:
        if char.isalnum() or char in ("-", "_", "."):
            safe.append(char)
        else:
            safe.append("_")
    result = "".join(safe).strip("._")
    return result or "motion"


def motion_to_matrix(motion: dict) -> np.ndarray:
    required = ("root_trans_offset", "root_rot", "dof")
    missing = [key for key in required if key not in motion]
    if missing:
        raise KeyError(f"Missing required fields: {missing}")

    root_pos = np.asarray(motion["root_trans_offset"], dtype=np.float32)
    root_rot = np.asarray(motion["root_rot"], dtype=np.float32)
    dof = np.asarray(motion["dof"], dtype=np.float32)

    if root_pos.ndim != 2 or root_pos.shape[1] != 3:
        raise ValueError(f"root_trans_offset must have shape (T, 3), got {root_pos.shape}")
    if root_rot.ndim != 2 or root_rot.shape[1] != 4:
        raise ValueError(f"root_rot must have shape (T, 4), got {root_rot.shape}")
    if dof.ndim != 2 or dof.shape[1] != 23:
        raise ValueError(f"dof must have shape (T, 23), got {dof.shape}")
    if not (root_pos.shape[0] == root_rot.shape[0] == dof.shape[0]):
        raise ValueError(
            "Frame count mismatch: "
            f"root_trans_offset={root_pos.shape[0]}, "
            f"root_rot={root_rot.shape[0]}, dof={dof.shape[0]}"
        )

    return np.concatenate([root_pos, root_rot, dof], axis=1)


def output_stem(source_path: Path, motion_key, motion_index: int, motion_count: int) -> str:
    stem = source_path.stem
    if motion_count == 1:
        return stem

    key_stem = sanitize_name(Path(str(motion_key)).stem)
    return f"{stem}__{motion_index:02d}_{key_stem}"


def convert_all(input_root: Path, output_root: Path) -> tuple[int, int, int]:
    pkl_files = sorted(
        path for path in input_root.rglob("*.pkl") if output_root not in path.parents
    )
    output_root.mkdir(parents=True, exist_ok=True)

    manifest_path = output_root / "manifest.csv"
    failed_path = output_root / "failed.csv"
    manifest_rows = []
    failed_rows = []

    for pkl_path in pkl_files:
        try:
            data = load_motion_file(pkl_path)
            motion_count = len(data)
            for motion_index, (motion_key, motion) in enumerate(data.items()):
                matrix = motion_to_matrix(motion)
                rel_parent = pkl_path.relative_to(input_root).parent
                csv_name = output_stem(pkl_path, motion_key, motion_index, motion_count) + ".csv"
                csv_path = output_root / rel_parent / csv_name
                csv_path.parent.mkdir(parents=True, exist_ok=True)

                np.savetxt(csv_path, matrix, delimiter=",", fmt="%.9g")
                fps = scalar(motion.get("fps"), 30)
                manifest_rows.append(
                    {
                        "source_file": str(pkl_path.relative_to(input_root)),
                        "csv_file": str(csv_path.relative_to(input_root)),
                        "motion_index": motion_index,
                        "motion_key": str(motion_key),
                        "frames": matrix.shape[0],
                        "fps": fps,
                        "columns": matrix.shape[1],
                    }
                )
                print(f"converted {pkl_path} [{motion_index}] -> {csv_path}")
        except Exception as exc:  # noqa: BLE001 - keep batch conversion moving.
            failed_rows.append(
                {
                    "source_file": str(pkl_path.relative_to(input_root)),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            print(f"failed {pkl_path}: {type(exc).__name__}: {exc}", file=sys.stderr)

    with manifest_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "source_file",
                "csv_file",
                "motion_index",
                "motion_key",
                "frames",
                "fps",
                "columns",
            ],
        )
        writer.writeheader()
        writer.writerows(manifest_rows)

    if failed_rows:
        with failed_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["source_file", "error"])
            writer.writeheader()
            writer.writerows(failed_rows)
    elif failed_path.exists():
        failed_path.unlink()

    return len(pkl_files), len(manifest_rows), len(failed_rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert G1 23DOF PKL files to csv_to_npz.py input CSV files."
    )
    parser.add_argument(
        "--input-root",
        type=Path,
        default=Path("."),
        help="Root directory containing original PKL files.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("csv_npz_input"),
        help="Directory where numeric CSV files will be written.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_root = args.input_root.resolve()
    output_root = args.output_root
    if not output_root.is_absolute():
        output_root = input_root / output_root

    total_files, total_motions, failed = convert_all(input_root, output_root)
    print(
        f"Done. PKL files: {total_files}, CSV motions: {total_motions}, failed: {failed}"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
