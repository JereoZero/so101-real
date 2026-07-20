#!/usr/bin/env python3
"""SO-101 teleoperation with real-time follower angle logging.

This is a thin wrapper around LeRobot's `lerobot-teleoperate` that additionally
prints the follower's current joint positions to the terminal every control tick.
Use this script when you want to communicate specific follower angles during
teleoperation testing.

Usage:
    unset PYTHONPATH && conda activate lerobot
    python src/scripts/teleoperate_log.py \
        --teleop.type=so101_leader \
        --teleop.port=/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B3E121553-if00 \
        --teleop.id=j_leader \
        --robot.type=so101_follower \
        --robot.port=/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B3E121987-if00 \
        --robot.id=j_follower
"""

import logging
import sys
from dataclasses import asdict
from pprint import pformat

from lerobot.cameras.opencv import OpenCVCameraConfig  # noqa: F401
from lerobot.cameras.realsense import RealSenseCameraConfig  # noqa: F401
from lerobot.cameras.zmq import ZMQCameraConfig  # noqa: F401
from lerobot.configs import parser
from lerobot.processor import (
    RobotObservation,
    make_default_processors,
)
from lerobot.robots import (  # noqa: F401
    Robot,
    RobotConfig,
    bi_openarm_follower,
    bi_rebot_b601_follower,
    bi_so_follower,
    earthrover_mini_plus,
    hope_jr,
    koch_follower,
    make_robot_from_config,
    omx_follower,
    openarm_follower,
    reachy2,
    rebot_b601_follower,
    so_follower,
    unitree_g1 as unitree_g1_robot,
)
from lerobot.scripts.lerobot_teleoperate import TeleoperateConfig, teleop_loop
from lerobot.teleoperators import (  # noqa: F401
    Teleoperator,
    TeleoperatorConfig,
    bi_openarm_leader,
    bi_openarm_mini,
    bi_rebot_102_leader,
    bi_so_leader,
    gamepad,
    homunculus,
    keyboard,
    koch_leader,
    make_teleoperator_from_config,
    omx_leader,
    openarm_leader,
    openarm_mini,
    reachy2_teleoperator,
    rebot_102_leader,
    so_leader,
    unitree_g1,
)
from lerobot.utils.import_utils import register_third_party_plugins
from lerobot.utils.utils import init_logging


def log_observation(obs: RobotObservation) -> None:
    """Print joint positions from robot observation."""
    pos_items = [(k, v) for k, v in obs.items() if k.endswith(".pos")]
    if not pos_items:
        return
    print("\n--- Follower present positions (degrees) ---")
    for key, val in pos_items:
        motor = key.removesuffix(".pos")
        print(f"  {motor:<15} | {val:>8.2f}")
    sys.stdout.flush()


@parser.wrap()
def teleoperate_with_log(cfg: TeleoperateConfig):
    init_logging()
    logging.info(pformat(asdict(cfg)))

    teleop = make_teleoperator_from_config(cfg.teleop)
    robot = make_robot_from_config(cfg.robot)
    teleop_action_processor, robot_action_processor, robot_observation_processor = make_default_processors()

    teleop.connect()
    robot.connect()

    # Wrap the robot observation method so we can log angles in real time.
    original_get_observation = robot.get_observation

    def get_observation_and_log() -> RobotObservation:
        obs = original_get_observation()
        log_observation(obs)
        return obs

    robot.get_observation = get_observation_and_log

    try:
        teleop_loop(
            teleop=teleop,
            robot=robot,
            fps=cfg.fps,
            display_data=False,
            display_mode=cfg.display_mode,
            duration=cfg.teleop_time_s,
            teleop_action_processor=teleop_action_processor,
            robot_action_processor=robot_action_processor,
            robot_observation_processor=robot_observation_processor,
            display_compressed_images=False,
        )
    except KeyboardInterrupt:
        pass
    finally:
        teleop.disconnect()
        robot.disconnect()


def main():
    register_third_party_plugins()
    teleoperate_with_log()


if __name__ == "__main__":
    main()
