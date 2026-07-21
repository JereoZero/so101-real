#!/usr/bin/env python3
"""SO-101 dataset quality checker.

Quickly validate a recorded dataset: episodes, frames, wrist_roll lock,
gripper range, camera videos, and action/state ranges.

Usage:
    unset PYTHONPATH && conda activate lerobot
    python src/scripts/check_data.py data/so101_grape_put_v1-5
    # or with repo_id:
    python src/scripts/check_data.py --repo_id=local/so101_grape_put_v1-5 \
        --root=/home/j/ws/so101/data/so101_grape_put_v1-5
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd


# Joint names in order (SO-101 6-DOF)
JOINT_NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]

# Expected fixed wrist_roll value (from so101.yaml)
EXPECTED_WRIST_ROLL = -27.82


def find_parquet_files(data_dir: Path) -> list[Path]:
    """Find all parquet files under data/chunk-*/."""
    parquets = sorted(data_dir.glob("data/chunk-*/file-*.parquet"))
    if not parquets:
        parquets = sorted(data_dir.rglob("*.parquet"))
    return parquets


def find_video_files(data_dir: Path) -> dict[str, list[Path]]:
    """Find video files grouped by camera key."""
    videos: dict[str, list[Path]] = {}
    for v in sorted(data_dir.rglob("*.mp4")):
        # Determine camera key from path (videos/camera_key/...)
        rel = v.relative_to(data_dir)
        parts = rel.parts
        if "videos" in parts:
            idx = parts.index("videos")
            if idx + 1 < len(parts):
                cam_key = parts[idx + 1]
                videos.setdefault(cam_key, []).append(v)
        else:
            videos.setdefault("unknown", []).append(v)
    return videos


def check_dataset(data_dir: Path) -> bool:
    """Run all quality checks on a dataset. Returns True if all pass."""
    print(f"\n{'=' * 60}")
    print(f"  数据集质量检查: {data_dir.name}")
    print(f"  路径: {data_dir}")
    print(f"{'=' * 60}\n")

    all_ok = True

    # 1. Check parquet files exist
    parquets = find_parquet_files(data_dir)
    if not parquets:
        print("[FAIL] 未找到 parquet 文件！")
        return False
    print(f"[OK] Parquet 文件数: {len(parquets)}")

    # 2. Load and concatenate all parquet data
    try:
        dfs = []
        for f in parquets:
            try:
                dfs.append(pd.read_parquet(f))
            except Exception as e:
                print(f"[FAIL] 读取 parquet 文件失败: {f}")
                print(f"       错误: {e}")
                print(f"       文件大小: {f.stat().st_size / 1024:.0f} KB")
                print(f"       可能原因: 录制中断导致文件不完整")
                all_ok = False
                return all_ok
        df = pd.concat(dfs, ignore_index=True)
    except Exception as e:
        print(f"[FAIL] 合并 parquet 数据失败: {e}")
        all_ok = False
        return all_ok
    total_frames = len(df)
    n_episodes = df["episode_index"].nunique() if "episode_index" in df.columns else 0
    print(f"[OK] 总 frames: {total_frames}")
    print(f"[OK] 总 episodes: {n_episodes}")
    print(f"     平均每 episode frames: {total_frames / max(n_episodes, 1):.0f}")

    # 3. Check action columns
    if "action" not in df.columns:
        print("[FAIL] 数据集缺少 'action' 列！")
        all_ok = False
    else:
        actions = np.stack(df["action"].values)
        print(f"\n--- Action 关节范围 (度) ---")
        for i, name in enumerate(JOINT_NAMES):
            if i < actions.shape[1]:
                col = actions[:, i]
                lo, hi = col.min(), col.max()
                uniq = np.unique(np.round(col, 2))
                status = "OK"
                if name == "wrist_roll":
                    # Should be fixed at EXPECTED_WRIST_ROLL
                    if len(uniq) == 1 and abs(uniq[0] - EXPECTED_WRIST_ROLL) < 0.1:
                        status = f"锁定 ✅ ({uniq[0]:.2f}°)"
                    else:
                        status = f"未锁定 ❌ (期望 {EXPECTED_WRIST_ROLL}°, 实际 {uniq})"
                        all_ok = False
                elif name == "gripper":
                    if hi - lo < 5:
                        status = "范围太小 ⚠️ (可能夹爪没动)"
                    else:
                        status = "正常"
                print(f"  {name:<15} | min={lo:>8.2f}  max={hi:>8.2f}  unique={len(uniq):>5}  {status}")

    # 4. Check observation.state
    if "observation.state" in df.columns:
        states = np.stack(df["observation.state"].values)
        print(f"\n--- Observation.state 范围 (度) ---")
        for i, name in enumerate(JOINT_NAMES):
            if i < states.shape[1]:
                col = states[:, i]
                lo, hi = col.min(), col.max()
                print(f"  {name:<15} | min={lo:>8.2f}  max={hi:>8.2f}")

    # 5. Check videos
    videos = find_video_files(data_dir)
    print(f"\n--- 视频文件 ---")
    if not videos:
        print("[FAIL] 未找到视频文件！")
        all_ok = False
    else:
        for cam_key, vfiles in videos.items():
            print(f"  {cam_key}: {len(vfiles)} 个视频文件")
    if videos:
        print("[OK] 视频文件存在")

    # 6. Check task field
    if "task_index" in df.columns:
        tasks = df["task_index"].unique()
        print(f"\n--- 任务 ---")
        print(f"  task_index 唯一值: {tasks}")

    # Summary
    print(f"\n{'=' * 60}")
    if all_ok:
        print(f"  ✅ 全部检查通过！{n_episodes} episodes / {total_frames} frames")
    else:
        print(f"  ❌ 存在问题，请检查上方标记为 FAIL 的项")
    print(f"{'=' * 60}\n")

    return all_ok


def main():
    parser = argparse.ArgumentParser(description="SO-101 dataset quality checker")
    parser.add_argument("path", nargs="?", type=Path, help="Dataset directory path")
    parser.add_argument("--repo_id", type=str, help="Dataset repo_id (alternative to path)")
    parser.add_argument("--root", type=Path, help="Dataset root path (used with --repo_id)")
    args = parser.parse_args()

    if args.path:
        data_dir = args.path
    elif args.repo_id and args.root:
        data_dir = args.root
    elif args.repo_id:
        data_dir = Path.home() / ".cache/huggingface/lerobot" / args.repo_id
    else:
        parser.print_help()
        sys.exit(1)

    if not data_dir.exists():
        print(f"错误: 目录不存在 {data_dir}")
        sys.exit(1)

    ok = check_dataset(data_dir)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
