#!/usr/bin/env python3
"""Apply SO-101 specific patches to LeRobot source in /home/j/ws/repos/lerobot.

These patches are based on the original so101-real project modifications.
See: https://github.com/JereoZero/so101-real
"""

from pathlib import Path

REPOS = Path("/home/j/ws/repos/lerobot")


def patch_file(rel_path: str, old: str, new: str, description: str) -> None:
    fpath = REPOS / rel_path
    if not fpath.exists():
        raise FileNotFoundError(f"{fpath} not found. Is LeRobot cloned to {REPOS}?")

    text = fpath.read_text(encoding="utf-8")

    if old not in text:
        if new in text:
            print(f"[SKIP] Already patched: {rel_path} ({description})")
            return
        raise ValueError(f"[FAIL] Pattern not found in {rel_path}. The source may have changed.")

    text = text.replace(old, new, 1)
    fpath.write_text(text, encoding="utf-8")
    print(f"[OK] Patched: {rel_path} ({description})")


def main() -> None:
    # 1. so_follower: calibrate wrist_roll instead of hard-coding 0-4095
    patch_file(
        "src/lerobot/robots/so_follower/so_follower.py",
        old='''        # Attempt to call record_ranges_of_motion with a reduced motor set when appropriate.
        full_turn_motor = "wrist_roll"
        unknown_range_motors = [motor for motor in self.bus.motors if motor != full_turn_motor]
        print(
            f"Move all joints except '{full_turn_motor}' sequentially through their "
            "entire ranges of motion.\\nRecording positions. Press ENTER to stop..."
        )
        range_mins, range_maxes = self.bus.record_ranges_of_motion(unknown_range_motors)
        range_mins[full_turn_motor] = 0
        range_maxes[full_turn_motor] = 4095''',
        new='''        # SO-101 patch: calibrate all 6 joints including wrist_roll for precise range measurement.
        print(
            "Move all joints sequentially through their entire ranges of motion.\\n"
            "Recording positions. Press ENTER to stop..."
        )
        range_mins, range_maxes = self.bus.record_ranges_of_motion(list(self.bus.motors.keys()))''',
        description="calibrate wrist_roll",
    )

    # 2. so_follower: increase gripper torque to 100%
    patch_file(
        "src/lerobot/robots/so_follower/so_follower.py",
        old='''                if motor == "gripper":
                    self.bus.write("Max_Torque_Limit", motor, 500)  # 50% of max torque to avoid burnout
                    self.bus.write("Protection_Current", motor, 250)  # 50% of max current to avoid burnout
                    self.bus.write("Overload_Torque", motor, 25)  # 25% torque when overloaded''',
        new='''                if motor == "gripper":
                    self.bus.write("Max_Torque_Limit", motor, 1000)  # 100% of max torque
                    self.bus.write("Protection_Current", motor, 500)  # 100% of max current
                    self.bus.write("Overload_Torque", motor, 50)  # 50% torque when overloaded''',
        description="gripper torque 100%",
    )

    # 3. so_leader: calibrate wrist_roll instead of hard-coding 0-4095
    patch_file(
        "src/lerobot/teleoperators/so_leader/so_leader.py",
        old='''        full_turn_motor = "wrist_roll"
        unknown_range_motors = [motor for motor in self.bus.motors if motor != full_turn_motor]
        print(
            f"Move all joints except '{full_turn_motor}' sequentially through their "
            "entire ranges of motion.\\nRecording positions. Press ENTER to stop..."
        )
        range_mins, range_maxes = self.bus.record_ranges_of_motion(unknown_range_motors)
        range_mins[full_turn_motor] = 0
        range_maxes[full_turn_motor] = 4095''',
        new='''        # SO-101 patch: calibrate all joints including wrist_roll.
        print(
            "Move all joints sequentially through their entire ranges of motion.\\n"
            "Recording positions. Press ENTER to stop..."
        )
        range_mins, range_maxes = self.bus.record_ranges_of_motion(list(self.bus.motors.keys()))''',
        description="calibrate wrist_roll",
    )

    # 4. so_follower: clip wrist_roll range to valid [0, 4095]
    patch_file(
        "src/lerobot/robots/so_follower/so_follower.py",
        old='''        self.calibration = {}
        for motor, m in self.bus.motors.items():
            self.calibration[motor] = MotorCalibration(
                id=m.id,
                drive_mode=0,
                homing_offset=homing_offsets[motor],
                range_min=range_mins[motor],
                range_max=range_maxes[motor],
            )''',
        new='''        self.calibration = {}
        for motor, m in self.bus.motors.items():
            range_min = range_mins[motor]
            range_max = range_maxes[motor]
            # SO-101: wrist_roll is a full-turn motor; clip to valid [0, 4095] to avoid
            # negative position limits after wrap-around.
            if motor == "wrist_roll":
                range_min = max(0, min(4095, range_min))
                range_max = max(0, min(4095, range_max))
            self.calibration[motor] = MotorCalibration(
                id=m.id,
                drive_mode=0,
                homing_offset=homing_offsets[motor],
                range_min=range_min,
                range_max=range_max,
            )''',
        description="clip wrist_roll range",
    )

    # 5. so_leader: clip wrist_roll range to valid [0, 4095]
    patch_file(
        "src/lerobot/teleoperators/so_leader/so_leader.py",
        old='''        self.calibration = {}
        for motor, m in self.bus.motors.items():
            self.calibration[motor] = MotorCalibration(
                id=m.id,
                drive_mode=0,
                homing_offset=homing_offsets[motor],
                range_min=range_mins[motor],
                range_max=range_maxes[motor],
            )''',
        new='''        self.calibration = {}
        for motor, m in self.bus.motors.items():
            range_min = range_mins[motor]
            range_max = range_maxes[motor]
            # SO-101: wrist_roll is a full-turn motor; clip to valid [0, 4095] to avoid
            # negative position limits after wrap-around.
            if motor == "wrist_roll":
                range_min = max(0, min(4095, range_min))
                range_max = max(0, min(4095, range_max))
            self.calibration[motor] = MotorCalibration(
                id=m.id,
                drive_mode=0,
                homing_offset=homing_offsets[motor],
                range_min=range_min,
                range_max=range_max,
            )''',
        description="clip wrist_roll range",
    )

    # 6. config_so_follower: add fixed_joints field (v0.5.1 compatibility)
    patch_file(
        "src/lerobot/robots/so_follower/config_so_follower.py",
        old='''    # Set to `True` for backward compatibility with previous policies/dataset
    use_degrees: bool = True


@RobotConfig.register_subclass("so101_follower")''',
        new='''    # Set to `True` for backward compatibility with previous policies/dataset
    use_degrees: bool = True

    # Fixed joint target positions (in degrees when use_degrees=True).
    # Used to override policy outputs for specific joints, e.g. to keep wrist_roll at a fixed angle.
    fixed_joints: dict[str, float] = field(default_factory=dict)


@RobotConfig.register_subclass("so101_follower")''',
        description="add fixed_joints config",
    )

    # 7. so_follower: override fixed joints in send_action
    patch_file(
        "src/lerobot/robots/so_follower/so_follower.py",
        old='''        goal_pos = {key.removesuffix(".pos"): val for key, val in action.items() if key.endswith(".pos")}

        # Cap goal position when too far away from present position.''',
        new='''        goal_pos = {key.removesuffix(".pos"): val for key, val in action.items() if key.endswith(".pos")}

        # Override fixed joints (e.g. wrist_roll) with configured constant targets.
        for motor, fixed_val in self.config.fixed_joints.items():
            if motor in goal_pos:
                goal_pos[motor] = fixed_val

        # Cap goal position when too far away from present position.''',
        description="override fixed joints in send_action",
    )

    # 8. lerobot_record: fix teleop check during reset phase
    patch_file(
        "src/lerobot/scripts/lerobot_record.py",
        old='''        if isinstance(teleop, Teleoperator):''',
        new='''        if teleop is not None:''',
        description="teleop reset fix",
    )

    # 9. feetech: tolerate motor communication failures during torque enable/disable
    patch_file(
        "src/lerobot/motors/feetech/feetech.py",
        old='''    def enable_torque(self, motors: int | str | list[str] | None = None, num_retry: int = 0) -> None:
        for motor in self._get_motors_list(motors):
            self.write("Torque_Enable", motor, TorqueMode.ENABLED.value, num_retry=num_retry)
            self.write("Lock", motor, 1, num_retry=num_retry)''',
        new='''    def enable_torque(self, motors: int | str | list[str] | None = None, num_retry: int = 0) -> None:
        for motor in self._get_motors_list(motors):
            try:
                self.write("Torque_Enable", motor, TorqueMode.ENABLED.value, num_retry=num_retry)
                self.write("Lock", motor, 1, num_retry=num_retry)
            except Exception as e:
                logger.warning(f"Failed to enable torque for motor '{motor}': {e}")''',
        description="tolerate torque enable errors",
    )

    patch_file(
        "src/lerobot/motors/feetech/feetech.py",
        old='''    def disable_torque(self, motors: int | str | list[str] | None = None, num_retry: int = 0) -> None:
        for motor in self._get_motors_list(motors):
            self.write("Torque_Enable", motor, TorqueMode.DISABLED.value, num_retry=num_retry)
            self.write("Lock", motor, 0, num_retry=num_retry)''',
        new='''    def disable_torque(self, motors: int | str | list[str] | None = None, num_retry: int = 0) -> None:
        for motor in self._get_motors_list(motors):
            try:
                self.write("Torque_Enable", motor, TorqueMode.DISABLED.value, num_retry=num_retry)
                self.write("Lock", motor, 0, num_retry=num_retry)
            except Exception as e:
                logger.warning(f"Failed to disable torque for motor '{motor}': {e}")''',
        description="tolerate torque disable errors",
    )

    print("\nAll patches applied. You can reinstall with:")
    print("  unset PYTHONPATH && conda activate lerobot")
    print("  pip install -e /home/j/ws/repos/lerobot --no-deps")


if __name__ == "__main__":
    main()