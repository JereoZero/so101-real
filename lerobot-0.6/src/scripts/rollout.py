#!/usr/bin/env python3
"""SO-101 policy rollout / real-robot evaluation script.

This is a thin wrapper around LeRobot v0.6.0's `lerobot-rollout` CLI,
which is the dedicated deployment engine for running trained policies
on physical robots.

Usage:
    unset PYTHONPATH && conda activate lerobot
    python src/scripts/rollout.py \
        --strategy.type=base \
        --policy.path=outputs/so101_smolvla/checkpoints/last/pretrained_model \
        --task="put grape block in plate" \
        --duration=60

For slow VLAs (SmolVLA, Pi0, Pi0.5), add:
    --inference.type=rtc \
    --inference.rtc.execution_horizon=10

For DAgger-style human corrections, use:
    --strategy.type=dagger \
    --dataset.repo_id=local/so101_dagger_corrections

Note:
    Robot port, cameras, fixed_joints, and teleop config are auto-loaded
    from ``src/configs/so101.yaml`` (no need to pass manually).
"""

import sys
from pathlib import Path

import yaml

from lerobot.scripts.lerobot_rollout import main

# Load config from the project YAML and inject missing args into CLI.
_CONFIG_PATH = Path(__file__).resolve().parents[2] / "src/configs/so101.yaml"


def _inject_from_yaml() -> None:
    """Inject robot/teleop/cameras/fixed_joints args from so101.yaml if not on CLI."""
    if not _CONFIG_PATH.exists():
        return

    with open(_CONFIG_PATH) as f:
        _cfg = yaml.safe_load(f)

    def _has(prefix: str) -> bool:
        return any(arg.startswith(prefix) for arg in sys.argv[1:])

    _robot_cfg = _cfg.get("robot", {})
    _teleop_cfg = _cfg.get("teleop", {})
    _cameras_cfg = _cfg.get("cameras", {})

    # Robot
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

    # Cameras
    if not _has("--robot.cameras=") and _cameras_cfg:
        import json

        sys.argv.append(f"--robot.cameras={json.dumps(_cameras_cfg)}")

    # Teleop
    if not _has("--teleop.type="):
        sys.argv.append(f"--teleop.type={_teleop_cfg.get('type', 'so101_leader')}")
    if not _has("--teleop.port="):
        sys.argv.append(f"--teleop.port={_teleop_cfg['port']}")
    if not _has("--teleop.id="):
        sys.argv.append(f"--teleop.id={_teleop_cfg.get('id', 'j_leader')}")


if __name__ == "__main__":
    _inject_from_yaml()
    sys.argv[0] = "lerobot-rollout"
    main()
