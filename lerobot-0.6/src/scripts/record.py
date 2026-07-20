#!/usr/bin/env python3
"""SO-101 data recording script.

Usage:
    unset PYTHONPATH && conda activate lerobot
    python src/scripts/record.py \
        --robot.type=so101_follower \
        --robot.port=/dev/ttySO101_FOLLOWER \
        --teleop.type=so101_leader \
        --teleop.port=/dev/ttySO101_LEADER \
        --dataset.repo_id=local/so101_pick_place \
        --dataset.root=/home/j/ws/so101/data/so101_pick_place

Note:
    LeRobot v0.6.0 automatically appends a timestamp to ``dataset.repo_id``
    (e.g. ``local/so101_pick_place_20260720_123456``). Use the stamped
    repo_id when training, or set ``--dataset.root`` to a stable local path.
"""

import sys

from lerobot.scripts.lerobot_record import main

if __name__ == "__main__":
    sys.argv[0] = "lerobot-record"
    main()
