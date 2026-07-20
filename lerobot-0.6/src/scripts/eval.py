#!/usr/bin/env python3
"""SO-101 evaluation / inference script.

Usage:
    unset PYTHONPATH && conda activate lerobot
    python src/scripts/eval.py \
        --env.type=push_t \
        --policy.path=outputs/so101_act/checkpoints/last/pretrained_model
"""

import sys

from lerobot.scripts.lerobot_eval import main

if __name__ == "__main__":
    sys.argv[0] = "lerobot-eval"
    main()
