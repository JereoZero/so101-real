#!/usr/bin/env python3
"""SO-101 data recording script.

Usage:
    unset PYTHONPATH && conda activate lerobot
    python src/scripts/record.py \
        --dataset.repo_id=local/so101_grape_put_v1-1 \
        --dataset.root=/home/j/ws/so101/data/so101_grape_put_v1-1 \
        --dataset.num_episodes=10 \
        --dataset.single_task="put grape block in plate" \
        --dataset.episode_time_s=60 \
        --dataset.reset_time_s=9999

Note:
    - Robot port, cameras, fixed_joints, and teleop config are auto-loaded
      from ``src/configs/so101.yaml`` (no need to pass manually).
    - LeRobot v0.6.0 appends a timestamp to ``dataset.repo_id``, but ``--dataset.root`` is
      used as the actual storage path, so data lands in the specified ``data/`` directory.
    - If ``--dataset.root`` already exists, this script auto-suffixes it with ``_retryN``
      to avoid a FileExistsError from LeRobot's mkdir(exist_ok=False).
"""

import sys
from pathlib import Path

import yaml

from lerobot.scripts.lerobot_record import main

# Load config from the project YAML and inject missing args into CLI.
_CONFIG_PATH = Path(__file__).resolve().parents[2] / "src/configs/so101.yaml"


def _inject_from_yaml() -> None:
    """Inject robot/teleop/camera/fixed_joints args from so101.yaml if not on CLI.

    This lets you run `python src/scripts/record.py` with only --dataset.* args,
    without copy-pasting device IDs from the config.
    """
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

    # Teleop
    if not _has("--teleop.type="):
        sys.argv.append(f"--teleop.type={_teleop_cfg.get('type', 'so101_leader')}")
    if not _has("--teleop.port="):
        sys.argv.append(f"--teleop.port={_teleop_cfg['port']}")
    if not _has("--teleop.id="):
        sys.argv.append(f"--teleop.id={_teleop_cfg.get('id', 'j_leader')}")

    # Cameras
    if not _has("--robot.cameras=") and _cameras_cfg:
        import json

        sys.argv.append(f"--robot.cameras={json.dumps(_cameras_cfg)}")


def _avoid_root_collision(argv: list[str]) -> None:
    """Handle --dataset.root collision with LeRobot's mkdir(exist_ok=False).

    - If the existing dir is empty (e.g. a previous run that recorded nothing),
      just remove it and reuse the same path (no _retryN suffix).
    - If it has real data, auto-suffix with _retryN to avoid overwriting.
    """
    for i, arg in enumerate(argv):
        if arg.startswith("--dataset.root="):
            root = Path(arg.split("=", 1)[1])
            if root.exists():
                # Check if dir is effectively empty (no parquet/videos/episodes)
                has_data = any(root.rglob("*.parquet")) or any(
                    p for p in root.iterdir() if p.name != "meta"
                )
                if not has_data:
                    import shutil

                    shutil.rmtree(root)
                    print(f"  [info] 检测到空目录 {root}，已清理并复用")
                else:
                    n = 1
                    while (root.parent / f"{root.name}_retry{n}").exists():
                        n += 1
                    new_root = root.parent / f"{root.name}_retry{n}"
                    argv[i] = f"--dataset.root={new_root}"
                    print(f"  [warn] {root} 已有数据，自动改用: {new_root}")
            return


if __name__ == "__main__":
    _inject_from_yaml()
    _avoid_root_collision(sys.argv)
    sys.argv[0] = "lerobot-record"

    # Print control key hints to the terminal for the user.
    print("\n" + "=" * 60)
    print("   SO-101 录制控制快捷键")
    print("=" * 60)
    print("   → 右箭头 / n : 开始/结束录制本条 episode")
    print("   ← 左箭头 / r : 放弃当前 episode，重新录制")
    print("   ESC / q     : 完全停止录制")
    print("-" * 60)
    print("   提示：")
    print("   - 每条 episode 最长 60 秒，可手动提前结束")
    print("   - 复位阶段可继续用主臂控制从臂摆场景")
    print("   - 操作失误按 左箭头 重录本条")
    print("=" * 60 + "\n")
    sys.stdout.flush()

    main()
