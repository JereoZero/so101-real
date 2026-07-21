# 8. 数据录制

## 8.1 录制命令中必须加 --teleop 参数

**现象**：录制时，每条 episode 之间的复位阶段，从臂（follower）完全不跟随主臂（leader）移动。只能眼睁睁看着从臂保持上一 episode 结束时的位置，无法手动控制复位。

**原因**：录制命令 `lerobot-record` 中没有加 `--teleop` 参数。没有 teleop，系统不知道有遥操作设备，复位阶段自然无法跟随。

**解决**：录制命令**必须**包含以下三个参数：

```bash
--teleop.type=so101_leader \
--teleop.port=/dev/ttySO101_LEADER \
--teleop.id=j_leader \
```

完整录制命令模板：

```bash
sudo chmod 666 /dev/ttySO101_FOLLOWER /dev/ttySO101_LEADER

lerobot-record \
    --robot.type=so101_follower \
    --robot.port=/dev/ttySO101_FOLLOWER \
    --robot.id=j_follower \
    --robot.fixed_joints="{wrist_roll: -67.74}" \
    --robot.cameras="{front: {type: opencv, index_or_path: 2, fps: 30, width: 640, height: 480, fourcc: YUYV}, top: {type: opencv, index_or_path: 0, fps: 30, width: 640, height: 480, fourcc: MJPG}}" \
    --teleop.type=so101_leader \
    --teleop.port=/dev/ttySO101_LEADER \
    --teleop.id=j_leader \
    --display_data=true \
    --dataset.repo_id=jer/数据集名称 \
    --dataset.push_to_hub=false \
    --dataset.num_episodes=10 \
    --dataset.single_task="put small green block in plate" \
    --dataset.episode_time_s=20 \
    --dataset.reset_time_s=9999
```

---

## 8.2 episode_time_s 和 reset_time_s 的设置策略

**推荐配置**：
- `--dataset.episode_time_s=20`：给 20 秒的录制时间（足够长），通过按键手动结束
- `--dataset.reset_time_s=9999`：复位阶段设置超长时间（9999秒），实现完全手动控制

**为什么用 9999**：设置为极大值后，复位阶段不会自动超时，你有充足时间手动调整场景（摆方块、换干扰物等），准备好后按键继续。

### 8.2.1 参数演变历史

录制参数不是一开始就定好的，经历了多轮迭代才找到最佳配置：

| 阶段 | episode_time_s | reset_time_s | single_task |
|------|---------------|-------------|-------------|
| **最初** | 10 | 5 | `Put small block in plate`（通用） |
| **中期** | 20 | 9999 | `put small green block in plate`（分颜色） |
| **最终** | 20 | 9999 | 分颜色指令（绿/葡萄紫/橙） |

**演变原因**：
- `episode_time_s` 从 10 秒延长到 20 秒：10 秒太短，动作做不完就自动超时切断了
- `reset_time_s` 从 5 秒改为 9999 秒：自动复位时间太短，来不及重新摆放方块和盘子，改为完全手动控制
- 任务指令从通用改为分颜色：SmolVLA 推理时需要根据指令判断抓哪个颜色，通用指令无法区分

---

## 8.3 手动控制键位与必要性

录制过程中可以使用键盘控制录制流程：

| 按键 | 功能 |
|------|------|
| **→ 右箭头** | 结束当前阶段（结束录制进入复位 / 结束复位开始录制） |
| **← 左箭头** | 放弃当前 episode，**重新录制这一条** |
| **ESC** | 完全停止整个录制过程 |

### 为什么必须手动控制

设置 `reset_time_s=9999` 实现完全手动控制，背后有两个关键原因：

**1. 不能让模型学到"停止"**

如果录制时间自动截止（比如设 20 秒自动切），机械臂会在动作完成后的等待阶段继续记录静止状态。这意味着训练数据里会包含大量"机械臂停在原地不动"的帧——模型会学到"做完动作后停一会儿"这个行为。这在推理时会导致机械臂莫名其妙地暂停。

正确的做法是：动作一做完就立即按键结束当前 episode，让数据只包含有效动作序列，没有冗余的静止帧。

**2. 自动复位容易手忙脚乱**

如果复位阶段设置过短（比如 5 秒），每次 reset 都要在倒计时内完成：摆放方块、调整盘子位置、把主臂移到合适初始位置……时间一紧张，容易：
- 场景没摆好就自动开始了，产出废数据
- 手忙脚乱中碰到正在运动的机械臂，有安全风险
- 主臂还没回到初始位置就开始录制，导致开头几帧关节角度异常

设 9999 秒后，你有充足时间从容摆好场景、调整好主臂位置，准备好了再按键开始。

**完全手动控制工作流**：
1. 启动录制 → 系统进入复位阶段（无限等待）
2. 从容摆好场景、调好主臂位置 → 按 **→** 开始录制
3. 动作完成 → 立即按 **→** 结束录制，回到复位阶段
4. 调整场景 → 准备好后按 **→** 开始下一条
5. 想停止按 **ESC**

---

## 8.4 任务难点与数据增强策略

### 物理尺寸约束

| 物品 | 尺寸 | 特点 |
|------|------|------|
| 小方块 | **3.5cm** 边长 | 体积小，对抓取精度要求高 |
| 盘子 | **8.5cm** 直径 | 盘子小，放置目标区域狭窄 |

盘子直径只有方块边长的约 2.4 倍，意味着机器人必须以较高精度将方块放入盘子，容错空间很小。这是本项目的一个核心难点。

### 随机放置（非定点操作）

盘子和方块在每次录制时都**随机摆放在桌面上**，不是固定的预设位置。这意味着：

- 机器人需要根据视觉信息动态定位目标
- 每次的抓取路径不完全相同
- 对模型的泛化能力提出了更高要求

### 环境光照控制与数据增强

为了让数据既有一致性又有多样性，录制时使用了"拉窗帘"策略：

| 光照条件 | 窗帘状态 | 目的 |
|----------|----------|------|
| 标准光照 | 窗帘完全拉上 | 保证基础数据的环境光一致性 |
| 增强光照 | 部分拉开窗帘 | 引入自然光变化，增加数据多样性 |
| 增强光照 | 改变灯光角度 | 制造不同方向的阴影和反光 |

通过这种方式，模型既能在标准环境下稳定工作，又对光照变化有一定鲁棒性。

---

## 8.5 录制迭代：v1→v6 的教训

录制过程不是一蹴而就的。以绿色方块 only 为例，经历了 **6 个版本**才得到可用的数据：

| 版本 | 结果 | 问题 |
|------|------|------|
| v1 | ❌ | 首次尝试，动作不流畅 |
| v2 | ❌ | 夹爪角度不对，抓不住 |
| v3 | ❌ | 光照不一致 |
| v4 | ❌ | 复位阶段从臂不跟随（此时还没加 teleop 参数） |
| v5 | ❌ | wrist_roll 角度不合适，抓取方向歪 |
| v6 | ✅ | 最终可用版本 |

**教训**：
- 前几条录制几乎必定是废的，不要指望一次成功
- 每次录制前确认参数正确（teleop、fixed_joints、摄像头 fourcc）
- 录制完一条后立即回放检查（用 `lerobot-replay`）确认质量
- 数据集命名要带版本号（v1, v2...），方便追溯

---

## 8.6 数据集已存在（FileExistsError）

**现象**：重复录制时报 `FileExistsError`，因为上次录的数据集还在缓存目录。

**解决**：

```bash
# 删除缓存中的旧数据
rm -rf /home/jer/.cache/huggingface/lerobot/jer/数据集名称

# 或者更换 repo_id（如 v1 → v2）
```

---

## 8.7 wrist_roll 固定关节的作用

录制和推理时都需要固定 `wrist_roll` 关节（手腕旋转），否则抓取方向会飘：

```bash
--robot.fixed_joints="{wrist_roll: -67.74}"
```

如何确定角度值：
1. 先不带 fixed_joints 运行遥操作 `lerobot-teleoperate`
2. 手动把 wrist_roll 转到合适的抓取角度
3. 看终端打印的关节角度（norm 值）
4. 把这个值填到 fixed_joints 里

---

## 8.8 双摄像头命名与训练时的冲突

录制时使用 `front` 和 `top` 作为摄像头名称（自然语义），但 SmolVLA 模型期望 `camera1` 和 `camera2`。这会导致训练时 Feature 不匹配。

**录制命令中的名字**（人类可读）：
```bash
--robot.cameras="{front: ..., top: ...}"
```

**训练时的映射**（用 rename_map 解决）：
```bash
--rename_map='{"observation.images.front": "observation.images.camera1", "observation.images.top": "observation.images.camera2"}'
```

---

## 8.9 录制前必须校准

每次断电重连后，必须重新校准主臂和从臂：

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

校准文件存储在：
- `~/.cache/huggingface/lerobot/calibration/teleoperators/so101_leader/j_leader.json`
- `~/.cache/huggingface/lerobot/calibration/robots/so_follower/j_follower.json`

---

## 8.10 任务指令（single_task）的重要性

`--dataset.single_task` 不仅用于元数据标注，SmolVLA 推理时会根据此指令判断抓哪个颜色的方块。

三色指令：

| 颜色 | 指令 |
|------|------|
| 绿色 | `put small green block in plate` |
| 葡萄紫 | `put small grape block in plate` |
| 橙色 | `put small orange block in plate` |

---

## 8.11 数据回放检查（lerobot-replay）

录制完成后应该立即回放确认质量：

```bash
sudo chmod 666 /dev/ttySO101_FOLLOWER

lerobot-replay \
    --robot.type=so101_follower \
    --robot.port=/dev/ttySO101_FOLLOWER \
    --robot.id=j_follower \
    --dataset.repo_id=jer/so101_3color_green_only_v6 \
    --dataset.episode=0
```

也可以用可视化方式查看（不驱动机械臂）：

```bash
python -m lerobot.scripts.lerobot_dataset_viz \
    --repo-id jer/so101_3color_green_only_v6 \
    --episode-index 0 \
    --mode local
```

---

## 8.12 数据集整理流程

录制完成后，数据需要从缓存复制到正式目录，再合并成训练集：

```
1. 原始缓存
   ~/.cache/huggingface/lerobot/jer/so101_3color_green_only_v6/
                              ↓ 复制
2. 分类目录
   /home/jer/ws/workspace/datasets/so101_3color_put_into_plate/train/green/only_green/
                              ↓ 合并
3. 训练集
   smolvla90/   ← 90 条 baseline（3色 × 3场景 × 10条）
   smolvla210/  ← 90 条 baseline + 120 条增强数据
```

---

## 8.13 数据量完整清单

### 第一批（baseline）：各场景各颜色 10 条，共 90 条

| 颜色 | only | +1干扰 | +2干扰 |
|------|------|--------|--------|
| 绿色 | v6（最终版） | v2 | v2/v3 |
| 葡萄紫 | v1 | v1 | v1 |
| 橙色 | v1 | v1 | v1 |

### 第二批（增强数据）：额外录制，共 120 条

- 每色增加 **40 条**（20 only + 20 干扰），包含更多光照变化和随机放置
- 部分场景增加到 20 episodes（如橙色 +1干扰 round2 录了 20 条）

#### 橙色 round2 录制示例（20 条，num_episodes=20）

```bash
sudo chmod 666 /dev/ttySO101_FOLLOWER /dev/ttySO101_LEADER

lerobot-record \
    --robot.type=so101_follower \
    --robot.port=/dev/ttySO101_FOLLOWER \
    --robot.id=j_follower \
    --robot.fixed_joints="{wrist_roll: -67.74}" \
    --robot.cameras="{front: {type: opencv, index_or_path: 2, fps: 30, width: 640, height: 480, fourcc: YUYV}, top: {type: opencv, index_or_path: 0, fps: 30, width: 640, height: 480, fourcc: MJPG}}" \
    --teleop.type=so101_leader \
    --teleop.port=/dev/ttySO101_LEADER \
    --teleop.id=j_leader \
    --display_data=true \
    --dataset.repo_id=jer/so101_3color_orange_round2_plus1_v1 \
    --dataset.push_to_hub=false \
    --dataset.num_episodes=20 \
    --dataset.single_task="put small orange block in plate" \
    --dataset.episode_time_s=20 \
    --dataset.reset_time_s=9999
```

### 总计：210 条（每色约 70 条）

---

## 8.14 数据集命名规范

- 绿色 only：`jer/so101_3color_green_only_v6`
- 绿色 +1：`jer/so101_3color_green_plus1_v2`
- 绿色 +2：`jer/so101_3color_green_plus2_v3`
- 葡萄紫 only：`jer/so101_3color_grape_only_v1`
- 葡萄紫 +1：`jer/so101_3color_grape_plus1_v1`
- 葡萄紫 +2：`jer/so101_3color_grape_plus2_v1`
- 橙色 only：`jer/so101_3color_orange_only_v1`
- 橙色 +1：`jer/so101_3color_orange_plus1_v1`
- 橙色 +2：`jer/so101_3color_orange_plus2_v1`

> **注意**：录制时是按颜色分组录的（每个 repo_id 只对应一种颜色+一个场景），但训练时会把所有颜色和场景的数据**合并成统一的训练集**。例如 `smolvla210` 包含了绿色、葡萄紫、橙色三种颜色在 only / +1干扰 / +2干扰 下的所有数据。合并后的训练集不再区分颜色来源，模型通过 `single_task` 语言指令来区分当前该抓哪个颜色。

---

## 8.15 数据集质量检查清单

录制完成后，对照以下检查清单逐项确认数据质量：

| 类别 | 检查项 | 本项目状态 |
|------|--------|-----------|
| 📷 图像 | 至少 2 个摄像头视角 | ✅ front + top |
| 📷 图像 | 摄像头稳定不抖动 | ✅ |
| 📷 图像 | 中性光照（不偏黄/蓝） | ⚠️ 通过拉窗帘控制 |
| 📷 图像 | 一致的曝光和对焦 | ✅ |
| 📷 图像 | 主臂不在画面中 | ✅ |
| 📷 图像 | 只有从臂和物体在移动 | ✅ |
| 📷 图像 | 静态/干净背景 | ⚠️ 需注意桌面杂物 |
| 📷 图像 | 分辨率 ≥ 480p | ✅ 640x480 |
| ⚙️ 协议 | 正确的机器人类型 | ✅ so101_follower |
| ⚙️ 协议 | 摄像头 ~30 FPS | ✅ |
| ⚙️ 协议 | 删除 episode 后更新元数据 | ⚠️ 手动处理 |
| 🏷️ 命名 | 标准命名 `front`/`top` | ✅ |
| 🏷️ 命名 | 不使用设备特定名称 | ✅ |
| 📝 标注 | 精确描述机器人任务 | ✅ 25-50字符 |
| 📝 标注 | 任务指令针对不同颜色 | ✅ 三个独立指令 |

**重点关注**：
- 光照一致性是最大的难点，需要用窗帘严格控制环境光
- 背景杂物会影响模型注意力，录制前清理桌面
- 如果删除了某个 episode，需要更新 `meta/info.json` 中的元数据