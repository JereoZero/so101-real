#!/usr/bin/env python3
"""SO-101 teleoperation test script.

Usage:
    unset PYTHONPATH && conda activate lerobot
    python src/scripts/teleoperate.py \
        --teleop.type=so101_leader \
        --teleop.port=/dev/ttySO101_LEADER \
        --robot.type=so101_follower \
        --robot.port=/dev/ttySO101_FOLLOWER
"""

import sys

# Delegate to LeRobot's built-in teleoperation entry point.
from lerobot.scripts.lerobot_teleoperate import main

if __name__ == "__main__":
    sys.argv[0] = "lerobot-teleoperate"
    main()
