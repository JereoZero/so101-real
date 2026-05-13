# 5. SO101 机械臂硬件

## 5.1 电机 ID 冲突/识别错误

**现象**：只连接了 6 个电机，但扫描发现 ID 不对（如 ID=3 被识别为 ID=6，或者只检测到 ID=1,2,6 缺少 3,4,5）。

**原因**：电机出厂 ID 可能有误，或者被人为修改过。Feetech 电机支持软件修改 ID。

**排查**：先用脚本扫描所有电机 ID：

```python
from lerobot.motors.feetech import FeetechMotorsBus
from lerobot.motors import Motor, MotorNormMode

test_motors = {
    1: Motor(1, 'sts3215', MotorNormMode.DEGREES),
    2: Motor(2, 'sts3215', MotorNormMode.DEGREES),
    3: Motor(3, 'sts3215', MotorNormMode.DEGREES),
    4: Motor(4, 'sts3215', MotorNormMode.DEGREES),
    5: Motor(5, 'sts3215', MotorNormMode.DEGREES),
    6: Motor(6, 'sts3215', MotorNormMode.RANGE_0_100),
}

bus = FeetechMotorsBus('/dev/ttyACM0', test_motors)
bus.connect()

print('扫描电机 ID 1-6...')
for motor_id in range(1, 7):
    try:
        bus.write('Torque_Enable', motor_id, 0)
        print(f'  ID {motor_id}: 存在')
    except Exception as e:
        print(f'  ID {motor_id}: 不存在')

bus.disconnect()
```

**修复**：用 Python 重新设置电机 ID：

```python
bus = FeetechMotorsBus('/dev/ttyACM0', test_motors)
bus.connect()
bus.write('ID', 6, 3)   # 把 ID=6 改回 ID=3
bus.disconnect()
```

**重要**：修改 ID 后需要断电重启才能生效。

---

## 5.2 SO101 关节配置

| ID | 名称 | 功能 | 模式 |
|----|------|------|------|
| 1 | shoulder_pan | 肩膀水平旋转 | DEGREES |
| 2 | shoulder_lift | 肩膀升降 | DEGREES |
| 3 | elbow_flex | 肘部弯曲 | DEGREES |
| 4 | wrist_flex | 腕部弯曲 | DEGREES |
| 5 | wrist_roll | 腕部旋转（360°全向） | DEGREES |
| 6 | gripper | 夹爪 | RANGE_0_100（百分比） |

---

## 5.3 夹爪（gripper）无法张开

**现象**：1-5 号关节正常，但 6 号夹爪张不开，或者张开幅度很小。

**原因**：LeRobot 官方代码 `so_follower.py` 中夹爪的扭矩限制为 50%（`Max_Torque_Limit=500, Protection_Current=250`），扭矩不足导致夹爪无力。

**解决**：修改源码将扭矩改为 100%。详见 [07-source-modifications.md](./07-source-modifications.md) 第 7.2 节。

---

## 5.4 串口权限问题

**现象**：`Permission denied: '/dev/ttyACM0'` 或 `/dev/ttySO101_FOLLOWER`。

**两种解决方案**：

**临时方案（每次开机都要执行，最简单）**：
```bash
sudo chmod 666 /dev/ttySO101_LEADER /dev/ttySO101_FOLLOWER
```

**永久方案（推荐，一劳永逸）**：
```bash
sudo usermod -a -G dialout jer
# 需要重新登录生效
```

---

## 5.5 udev 固定设备名

**现象**：USB 口换位置后，`/dev/ttyACM0` 和 `/dev/ttyACM1` 的对应关系变了，不知道哪个是主臂哪个是从臂。

**解决**：使用 udev 规则根据设备唯一序列号创建固定符号链接。

创建 `/etc/udev/rules.d/99-so101.rules`：

```
SUBSYSTEM=="tty", ENV{ID_SERIAL_SHORT}=="5B3E121553", SYMLINK+="ttySO101_LEADER"
SUBSYSTEM=="tty", ENV{ID_SERIAL_SHORT}=="5B3E121987", SYMLINK+="ttySO101_FOLLOWER"
```

然后：

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

之后统一使用固定名称：
- 主臂：`/dev/ttySO101_LEADER`
- 从臂：`/dev/ttySO101_FOLLOWER`

如何找到序列号：

```bash
ls -l /dev/serial/by-id/
```

**注意**：序列号是唯一的，不会因为 USB 口或电脑变化而改变。

---

## 5.6 爪子马达红灯问题

**现象**：
- 遥控爪子时，某些角度会导致马达亮红灯
- 红灯后暂时还能遥控
- 但退出程序后再进入（遥控/录制/推理），会找不到马达
- 必须断电重启才能恢复

**可能原因**：
1. **角度超限**：爪子转动角度超过安全范围，触发硬件保护
2. **电流过大**：某些角度阻力大，导致电流超标
3. **CAN 总线异常**：红灯后 CAN 总线陷入异常状态

**临时解决方案**：
- 操作时注意爪子角度不要太大
- 一旦发现红灯，立即将爪子回到中间位置再退出程序
- 避免在红灯状态下退出程序（否则下次连不上）

---

## 5.7 校准失败

**现象**：校准过程中某一步失败，某个电机无响应，或者校准后关节读数异常。

**排查**：
1. 检查电机连接，确保所有 6 个电机都能通信（用 5.1 节的扫描脚本）
2. 检查电机 ID 是否正确
3. 断电重启后重新校准

**校准步骤**（每次断电重连必须执行）：
1. 移动机械臂到中间位置，按 Enter
2. 依次移动每个关节到最大范围，按 Enter
3. 完成后自动保存校准文件

**校准命令**：

```bash
# 校准主臂
lerobot-calibrate \
    --teleop.type=so101_leader \
    --teleop.port=/dev/ttySO101_LEADER \
    --teleop.id=j_leader

# 校准从臂
lerobot-calibrate \
    --robot.type=so101_follower \
    --robot.port=/dev/ttySO101_FOLLOWER \
    --robot.id=j_follower
```

**校准文件位置**：
- 主臂：`~/.cache/huggingface/lerobot/calibration/teleoperators/so101_leader/j_leader.json`
- 从臂：`~/.cache/huggingface/lerobot/calibration/robots/so_follower/j_follower.json`

---

## 5.8 测试从臂连接

校准后可用脚本快速验证连接：

```python
from lerobot.robots import so_follower

config = so_follower.SOFollowerRobotConfig(port='/dev/ttySO101_FOLLOWER')
robot = so_follower.SO101Follower(config)
robot.connect(calibrate=False)
print('连接成功')
print('读取关节位置...')
print(robot.get_joint_positions())
robot.disconnect()
```