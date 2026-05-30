#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Export a trained .pt checkpoint from unitree_rl_mjlab to a deployable policy.onnx.

Target ONNX:
    input : obs
    output: actions

Usage examples:

1) Velocity policy, G1 23DoF:
python tools/export_pt_to_policy_onnx.py \
  --task Unitree-G1-23Dof-Flat \
  --checkpoint logs/rsl_rl/g1_23dof_velocity/xxxx/model_89500.pt \
  --output deploy/robots/g1_23dof/config/policy/velocity/v0/exported/policy.onnx \
  --device cpu

2) Tracking / mimic policy, G1 23DoF:
python tools/export_pt_to_policy_onnx.py \
  --task Unitree-G1-23Dof-Tracking-No-State-Estimation \
  --checkpoint logs/rsl_rl/g1_tracking/xxxx/model_89500.pt \
  --motion_file src/assets/motions/g1/dance1_subject2.npz \
  --output deploy/robots/g1_23dof/config/policy/mimic/dance1_subject2/exported/policy.onnx \
  --device cpu
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path
import sys

import torch

from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import MjlabOnPolicyRunner, RslRlVecEnvWrapper
from mjlab.tasks.registry import load_env_cfg, load_rl_cfg, load_runner_cls
from mjlab.utils.torch import configure_torch_backends

# Register tasks.
# These imports are required inside the unitree_rl_mjlab repository.
import mjlab.tasks  # noqa: F401
import src.tasks    # noqa: F401


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert unitree_rl_mjlab .pt checkpoint to deployable obs->actions policy.onnx."
    )
    parser.add_argument(
        "--task",
        required=True,
        help="Task id, e.g. Unitree-G1-23Dof-Flat or Unitree-G1-23Dof-Tracking-No-State-Estimation.",
    )
    parser.add_argument(
        "--checkpoint",
        required=True,
        help="Path to model_xxx.pt.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output ONNX path. Recommended: deploy/.../exported/policy.onnx",
    )
    parser.add_argument(
        "--motion_file",
        default=None,
        help="Required/recommended for tracking or mimic tasks, e.g. src/assets/motions/g1/dance1_subject2.npz.",
    )
    parser.add_argument(
        "--device",
        default="cpu",
        help="Use cpu for deploy export. cuda:0 also works if your environment supports it.",
    )
    parser.add_argument(
        "--num_envs",
        type=int,
        default=1,
        help="Number of envs used only to build the env for export. Keep 1.",
    )
    parser.add_argument(
        "--no_check",
        action="store_true",
        help="Skip lightweight ONNX input/output name check.",
    )
    return parser.parse_args()


def set_motion_file_if_needed(env_cfg, motion_file: str | None) -> None:
    """Patch motion_file into tracking/mimic env config when the task has a motion command."""
    if motion_file is None:
        return

    motion_path = Path(motion_file)
    if not motion_path.exists():
        raise FileNotFoundError(f"motion_file not found: {motion_path}")

    if hasattr(env_cfg, "commands") and "motion" in env_cfg.commands:
        env_cfg.commands["motion"].motion_file = str(motion_path)
        print(f"[INFO] Using motion_file: {motion_path}")
    else:
        print("[WARN] --motion_file was provided, but this task has no 'motion' command. Ignored.")


def check_onnx_io(onnx_path: Path) -> None:
    """Check that exported ONNX is the deployable obs -> actions policy."""
    try:
        import onnx
    except Exception:
        print("[WARN] Python package 'onnx' not installed; skipped ONNX IO check.")
        return

    model = onnx.load(str(onnx_path))
    inputs = [x.name for x in model.graph.input]
    outputs = [x.name for x in model.graph.output]

    print(f"[INFO] ONNX inputs : {inputs}")
    print(f"[INFO] ONNX outputs: {outputs}")

    if inputs != ["obs"] or outputs != ["actions"]:
        raise RuntimeError(
            "Exported ONNX is not the expected deploy policy.\n"
            f"Expected inputs ['obs'] and outputs ['actions'], got inputs {inputs}, outputs {outputs}.\n"
            "Do not use a motion ONNX with inputs like ['obs', 'time_step'] for the default robot deploy code."
        )


def main() -> None:
    args = parse_args()
    configure_torch_backends()

    checkpoint = Path(args.checkpoint).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    output_dir = output.parent

    if not checkpoint.exists():
        raise FileNotFoundError(f"checkpoint not found: {checkpoint}")

    if output.name != "policy.onnx":
        print(
            f"[WARN] Output file name is '{output.name}', but robot deploy code expects 'policy.onnx'."
        )

    output_dir.mkdir(parents=True, exist_ok=True)

    device = args.device
    if device.startswith("cuda") and not torch.cuda.is_available():
        print("[WARN] CUDA requested but unavailable. Falling back to cpu.")
        device = "cpu"

    print(f"[INFO] task      : {args.task}")
    print(f"[INFO] checkpoint: {checkpoint}")
    print(f"[INFO] output    : {output}")
    print(f"[INFO] device    : {device}")

    # Same config loading pattern as scripts/play.py.
    env_cfg = load_env_cfg(args.task, play=True)
    agent_cfg = load_rl_cfg(args.task)

    # Export does not need thousands of parallel envs.
    if hasattr(env_cfg, "scene") and hasattr(env_cfg.scene, "num_envs"):
        env_cfg.scene.num_envs = args.num_envs

    set_motion_file_if_needed(env_cfg, args.motion_file)

    env = None
    try:
        env = ManagerBasedRlEnv(cfg=env_cfg, device=device)
        env = RslRlVecEnvWrapper(env, clip_actions=agent_cfg.clip_actions)

        runner_cls = load_runner_cls(args.task) or MjlabOnPolicyRunner
        runner = runner_cls(env, asdict(agent_cfg), device=device)

        # Load only actor weights, because deployment only needs the policy.
        runner.load(
            str(checkpoint),
            load_cfg={"actor": True},
            strict=True,
            map_location=device,
        )

        # IMPORTANT:
        # This exports the plain deployable policy:
        #   input  = obs
        #   output = actions
        # It intentionally does NOT call tracking runner's save() or export_motion_policy_to_onnx().
        runner.export_policy_to_onnx(str(output_dir), "policy.onnx")

        exported = output_dir / "policy.onnx"
        if exported != output:
            exported.replace(output)

        if not args.no_check:
            check_onnx_io(output)

        print(f"[OK] Exported deployable policy.onnx: {output}")

    finally:
        if env is not None:
            # RslRlVecEnvWrapper forwards close() to underlying env in this repo's play flow.
            try:
                env.close()
            except Exception:
                pass


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise
