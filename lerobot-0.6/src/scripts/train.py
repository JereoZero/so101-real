#!/usr/bin/env python3
"""SO-101 training script.

Usage:
    unset PYTHONPATH && conda activate lerobot
    python src/scripts/train.py \
        --dataset.repo_id=local/so101_pick_place \
        --policy.type=act \
        --output_dir=outputs/so101_act
"""

import sys

from lerobot.scripts.lerobot_train import main

if __name__ == "__main__":
    sys.argv[0] = "lerobot-train"
    main()
