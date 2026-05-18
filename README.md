# Unitree G1 23DOF Training Template

A practical motion-and-model playground for the Unitree G1 23DOF humanoid.

This repository collects retargeted motion datasets, ready-to-use trained policy artifacts, and conversion utilities for building, replaying, and organizing G1 23DOF locomotion and whole-body motion experiments. It is designed to be a friendly starting point when you want to go from motion files to robot-ready assets without rebuilding the whole asset pipeline from scratch.

## What Is Inside

- Retargeted motion datasets in `datasets/pkl`, `datasets/csv`, and `datasets/npz`.
- Curated available model bundles in `datasets/Available_Models`.
- Trained G1 23DOF model outputs in `models/g1_23dof`.
- Conversion scripts for `PKL -> CSV` and `CSV -> NPZ`.
- Git LFS tracking for large motion and policy artifacts.

The repository is intentionally asset-heavy. It is less of a tiny Python package and more of a motion library plus a training-output shelf: dances, kicks, punches, walks, jumps, run transitions, velocity control, and a few dramatic motion experiments with names that are hard not to like.

## Repository Layout

```text
.
|-- datasets/
|   |-- Available_Models/       # Packaged model/motion bundles for quick use
|   |-- csv/                    # CSV motion data and CSV conversion helpers
|   |-- npz/                    # Retargeted NPZ motion assets
|   `-- pkl/                    # Retargeted PKL motion assets
|-- models/
|   `-- g1_23dof/               # Trained policy/model artifacts by motion
|-- scripts/
|   |-- pkls_to_csv.py          # Batch export PKL motions to numeric CSV
|   `-- csv_to_npz.py           # Replay CSV motion and export simulation NPZ
|-- .gitattributes              # Git LFS rules for large binary artifacts
|-- .gitignore
|-- LICENSE
`-- README.md
```

## Available Model Bundles

The `datasets/Available_Models` directory contains packaged assets that are convenient to copy, inspect, or deploy in downstream workflows. Current bundles include:

- `Velocity`
- `Andria_Happy_v1_C3D`
- `Bruce_Lee_pose`
- `Charleston_dance`
- `Hooks_punch`
- `Horse-stance_punch`
- `Roundhouse_kick`
- `Side_kick`
- `run1_subject2`
- `jumps1_subject1`
- `C20_-__run_to_jump_to_walk_stageii`
- `daoma_23dof_gmr`
- `dahuajiao_even_23dof_modified`
- `huhuashizhe_23dof_omni`
- `Lucifer_23dof_new`
- `merged_motion__01_dance1_subject2_150_700_cont_mask_inter0`
- `merged_motion__03_fightAndSports1_subject4_150_300_cont_mask_inter0`

Most bundles combine some mix of:

- `.onnx` exported policy files
- `.pt` PyTorch checkpoints
- `.npz` motion assets
- `.pkl` source/retargeted motion data
- `.csv` numeric motion rows
- `params/*.yaml` environment and agent configuration files

## Motion Data Format

The CSV conversion flow expects each row to contain:

```text
root_trans_offset(3), root_rot_xyzw(4), dof(23)
```

That gives 30 numeric columns per frame:

- 3 root translation values
- 4 root quaternion values in `xyzw` order
- 23 joint position values for the G1 23DOF body

The `scripts/csv_to_npz.py` loader converts quaternions internally for simulation replay and computes interpolated velocities before exporting `.npz` motion files.

## Quick Start

Clone the repository with Git LFS enabled:

```bash
git lfs install
git clone https://github.com/awsdkk/Unitree_g1_23dof_Training_Template.git
cd Unitree_g1_23dof_Training_Template
git lfs pull
```

On Windows, long paths are strongly recommended because some motion names are descriptive enough to challenge the filesystem:

```bash
git config core.longpaths true
```

## Convert PKL Motions To CSV

Use `scripts/pkls_to_csv.py` to batch-convert PKL motion dictionaries into numeric CSV files accepted by the NPZ conversion step.

```bash
python scripts/pkls_to_csv.py \
  --input-root datasets/pkl \
  --output-root datasets/csv_npz_input
```

The script writes:

- one CSV per motion
- `manifest.csv` with source files, frame counts, FPS, and output paths
- `failed.csv` only when a source motion cannot be converted

It also includes compatibility helpers for Windows paths and older Joblib/Numpy pickle alignment behavior.

## Convert CSV Motions To NPZ

Use `scripts/csv_to_npz.py` to replay a CSV motion through the simulation stack and export a robot motion `.npz`.

Example:

```bash
python scripts/csv_to_npz.py \
  --robot g1_23dof \
  --input-file datasets/csv/example_motion.csv \
  --output-name example_motion \
  --input-fps 30 \
  --output-fps 50 \
  --device cuda:0
```

Optional rendering can be enabled with:

```bash
python scripts/csv_to_npz.py \
  --robot g1_23dof \
  --input-file datasets/csv/example_motion.csv \
  --output-name example_motion \
  --render True
```

The script supports:

- `g1_23dof` for the 23 DOF configuration
- `g1` for the 29 DOF configuration
- optional line ranges for slicing CSV motion clips
- interpolation from source FPS to simulation/output FPS
- export of joint positions, joint velocities, body pose, and body velocities

## Dependencies

The conversion scripts expect a Python environment with the simulation/training stack used by this project. At minimum, the scripts import:

- `numpy`
- `torch`
- `joblib`
- `tyro`
- `tqdm`
- `mjlab`
- project modules such as `src.tasks.tracking.config.g1_23dof`

In practice, use the environment where your Unitree G1 / MJLab training code already runs, then place this repository's assets and scripts alongside that workspace as needed.

## Git LFS Notes

Large binary assets are tracked with Git LFS:

```text
*.npz
*.pkl
*.pt
*.onnx
```

If a file looks tiny on GitHub but should be a model or motion asset, it is probably an LFS pointer. Run:

```bash
git lfs pull
```

To inspect LFS state:

```bash
git lfs status
```

## Suggested Workflow

1. Pick or add a source motion in `datasets/pkl`.
2. Convert it to CSV with `scripts/pkls_to_csv.py`.
3. Convert or replay CSV into simulation-ready NPZ with `scripts/csv_to_npz.py`.
4. Train or export policies in your G1 23DOF environment.
5. Store useful artifacts under `models/g1_23dof` or `datasets/Available_Models`.
6. Commit large files through Git LFS so the repository stays cloneable.

## Why This Repo Exists

Humanoid motion work can get messy fast: one folder for source motion, one folder for retargeting, another for simulation exports, another for policies, and a mysterious checkpoint called `final_final_really_final.pt`.

This template tries to make the shelf a little cleaner. Motions, model outputs, and conversion utilities live together with enough structure that future experiments can be found, reused, and compared.

## License

This repository includes a `LICENSE` file. Please review it before redistributing assets or using the repository in commercial projects.
