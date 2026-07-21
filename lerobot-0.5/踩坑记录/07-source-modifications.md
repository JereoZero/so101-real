# 7. LeRobot 源码修改

> 源码路径：`/home/jer/ws/workspace/projects/lerobot/src/lerobot/`

## 7.1 修改 wrist_roll 关节校准流程

**问题**：原版 LeRobot 中 `wrist_roll`（腕部旋转关节）被硬编码为 360° 范围（0-4095），跳过校准。但用户需要精确校准。

**修改文件**：
- `robots/so_follower/so_follower.py` → `calibrate()` 方法
- `teleoperators/so_leader/so_leader.py` → `calibrate()` 方法

**修改前**：
```python
full_turn_motor = "wrist_roll"
unknown_range_motors = [motor for motor in self.bus.motors if motor != full_turn_motor]
# ...只校准其他5个关节，wrist_roll 固定 0-4095
```

**修改后**：
```python
# 所有6个关节都参与校准
range_mins, range_maxes = self.bus.record_ranges_of_motion(self.bus.motors)
```

---

## 7.2 修改夹爪扭矩限制（从 50% 到 100%）

**修改文件**：`robots/so_follower/so_follower.py` → `configure_motors()` 方法

**修改前**：
```python
if motor == "gripper":
    self.bus.write("Max_Torque_Limit", motor, 500)   # 50%
    self.bus.write("Protection_Current", motor, 250)  # 50%
```

**修改后**：
```python
if motor == "gripper":
    self.bus.write("Max_Torque_Limit", motor, 1000)  # 100%
    self.bus.write("Protection_Current", motor, 500)  # 100%
```

> Feetech STS3215 电机 Max_Torque_Limit 范围 0-1000，对应 0%-100%。

---

## 7.3 添加电机通信错误处理

**问题**：某个电机通信失败会导致整个校准/控制流程崩溃。

**修改文件**：`motors/feetech/feetech.py`、`motors/motors_bus.py` 中关键的读写操作处。

**修改内容**：对关键读写添加 try-except：

```python
try:
    self.bus.write("Torque_Enable", motor, TorqueMode.ENABLED.value)
except Exception:
    pass  # 跳过失败的电机，不阻断整体流程
```

---

## 7.4 修复录制时复位阶段 teleop 不能控制从臂

**问题**：录制过程中按右箭头进入复位阶段（reset）后，从臂不跟随主臂移动。导致无法手动调整从臂位置来准备下一条录制。

**原因**：`lerobot_record.py` 中使用了 `isinstance(teleop, Teleoperator)` 来判断是否有 teleop，在某些情况下类型检查失败，走到了 else 分支输出警告并跳过动作发送。

**修改文件**：`scripts/lerobot_record.py` 约第 371 行。

**修改前**：
```python
elif policy is None and isinstance(teleop, Teleoperator):
    act = teleop.get_action()
```

**修改后**：
```python
elif policy is None and teleop is not None:
    act = teleop.get_action()
```

**这是整个项目中最关键的源码修复之一**。没有这个修复，录制体验极差——每条录制完都要等从臂自己跳回，无法手动调整准备下一条。

---

## 7.5 注意事项

- LeRobot 0.5.x 通过 `pip install -e .` 安装，修改源码后无需重新安装
- 修改文件后建议重启 Python 进程确保生效
- 如果通过 PyPI 安装（非 -e 模式），修改 `site-packages` 下的对应文件

## 7.6 验证修改是否生效

修改源码后，通过遥操作验证所有功能：

```bash
lerobot-teleoperate \
    --teleop.type=so101_leader \
    --teleop.port=/dev/ttySO101_LEADER \
    --teleop.id=j_leader \
    --robot.type=so101_follower \
    --robot.port=/dev/ttySO101_FOLLOWER \
    --robot.id=j_follower
```

应确认：
- 所有 6 个关节（含 wrist_roll 和 gripper）都能正常控制
- 夹爪能完全张开