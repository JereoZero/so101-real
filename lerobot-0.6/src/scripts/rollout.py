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
        --robot.type=so101_follower \
        --robot.port=/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B3E121987-if00 \
        --robot.id=j_follower \
        --task="put small green block in plate" \
        --duration=60

For slow VLAs (SmolVLA, Pi0, Pi0.5), add:
    --inference.type=rtc \
    --inference.rtc.execution_horizon=10

For DAgger-style human corrections, use:
    --strategy.type=dagger \
    --teleop.type=so101_leader \
    --teleop.port=/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B3E121553-if00 \
    --dataset.repo_id=local/so101_dagger_corrections
"""

import sys

from lerobot.scripts.lerobot_rollout import main

if __name__ == "__main__":
    sys.argv[0] = "lerobot-rollout"
    main()
