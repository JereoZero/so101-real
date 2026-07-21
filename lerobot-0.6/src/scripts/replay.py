#!/usr/bin/env python3
"""SO-101 data replay script (replay a recorded episode on the real robot).

Usage:
    unset PYTHONPATH && conda activate lerobot
    python src/scripts/replay.py \
        --dataset.repo_id=local/so101_grape_put_v1-1 \
        --dataset.root=/home/j/ws/so101/data/so101_grape_put_v1-1 \
        --dataset.episode=0

robot.type/port/id and fixed_joints are auto-loaded from src/configs/so101.yaml.
"""

import sys
from pathlib import Path

import yaml

from lerobot.scripts.lerobot_replay import main

# Load config from the project YAML and inject missing args into CLI.
_CONFIG_PATH = Path(__file__).resolve().parents[2] / "src/configs/so101.yaml"


def _inject_from_yaml() -> None:
    """Inject robot/fixed_joints args from so101.yaml if not on CLI."""
    if not _CONFIG_PATH.exists():
        return

    with open(_CONFIG_PATH) as f:
        _cfg = yaml.safe_load(f)

    def _has(prefix: str) -> bool:
        return any(arg.startswith(prefix) for arg in sys.argv[1:])

    _robot_cfg = _cfg.get("robot", {})

    if not _has("--robot.type="):
        sys.argv.append(f"--robot.type={_robot_cfg.get('type', 'so101_follower')}")
    if not _has("--robot.port="):
        sys.argv.append(f"--robot.port={_robot_cfg['port']}")
    if not _has("--robot.id="):
        sys.argv.append(f"--robot.id={_robot_cfg.get('id', 'j_follower')}")
    _fixed = _robot_cfg.get("fixed_joints", {})
    if _fixed and not _has("--robot.fixed_joints="):
        import json

        sys.argv.append(f"--robot.fixed_joints={json.dumps(_fixed)}")


if __name__ == "__main__":
    _inject_from_yaml()
    sys.argv[0] = "lerobot-replay"
    main()
