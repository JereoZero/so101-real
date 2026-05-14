# 5. SO101 机械臂硬件

## 5.1 电机 ID 错误排查全过程

**现象**：只连接了 6 个电机，但用脚本扫描时发现：
- ID 6 有时能识别到，有时识别不到（不稳定）
- ID 3 始终扫描不到
- 总共只能找到 5 个稳定的电机

**排查过程**：尝试了多种排查手段都没找到原因，最终采用最直接的方法——**逐个物理拔线**：

1. 先把机械臂上 6 个电机一一编号，确认各自对应的 ID
2. 逐个拔掉电机连接线，每次拔一个后重新扫描，观察哪个 ID 消失了
3. 发现：拔掉物理位置为 ID 3 的电机后，ID 6 变得完全识别不到了
4. 而 ID 3 本来就从没出现过——**说明物理 ID 3 的电机被错误编程成了 ID 6**

**根因**：电机#3（elbow_flex 关节）出厂时或之前被误写成了 ID 6，导致总线上有两个 ID 6（一个正确的一个错误的），产生了冲突。两个 ID 6 竞争总线，导致识别不稳定。

**解决**：用 SDK 将错误的 ID 6 写回正确的 ID 3，断电重启后验证。

```python
bus = FeetechMotorsBus('/dev/ttyACM0', test_motors)
bus.connect()
bus.write('ID', 6, 3)   # 把错误的 ID=6 写回正确的 ID=3
bus.disconnect()
```

**核心教训**：电机 ID 冲突导致的不稳定识别很难靠软件排查，物理拔线逐一定位是最可靠的。

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

## 5.6 校准失败

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

## 5.7 测试从臂连接

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