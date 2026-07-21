#!/usr/bin/env python3
"""Merge v1-1 ~ v1-20 into a single dataset."""

import json
import subprocess


def main() -> None:
    roots = [f"/home/j/ws/so101/data/so101_grape_put_v1-{i}" for i in range(1, 21)]
    repo_ids = [f"local/so101_grape_put_v1-{i}" for i in range(1, 21)]
    output_dir = "/home/j/ws/so101/data/so101_grape_put_v1_merged"

    cmd = [
        "lerobot-edit-dataset",
        "--operation.type=merge",
        f"--operation.repo_ids={json.dumps(repo_ids)}",
        f"--operation.roots={json.dumps(roots)}",
        "--new_repo_id=local/so101_grape_put_v1_merged",
        f"--new_root={output_dir}",
    ]
    print("Command:", " ".join(cmd))
    print("\n开始合并...")
    subprocess.run(cmd, check=True)
    print("合并完成")


if __name__ == "__main__":
    main()
