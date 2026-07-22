# 06. 推理部署

> 参考项目：[JereoZero/so101-real](https://github.com/JereoZero/so101-real)  
> 参考项目文档：[07-model-inference.md](https://github.com/JereoZero/so101-real/blob/main/%E9%A1%B9%E7%9B%AE%E6%B5%81%E7%A8%8B/07-model-inference.md)

## 前置条件

- 已完成 [05-training.md](05-training.md)
- 模型已训练完成
- 机械臂已连接并上电（与录制时同一环境最佳）

## 模型导出

训练生成的 checkpoint 目录结构为 `checkpoints/{step}/pretrained_model/`。LeRobot 推理时期望目标目录根层级包含模型文件，因此需要先"去壳"复制：

```bash
# 例如使用 40000 步的 checkpoint
mkdir -p /home/j/ws/so101/checkpoints/so101_smolvla_infer
cp -r outputs/so101_smolvla/checkpoints/040000/pretrained_model/* \
  /home/j/ws/so101/checkpoints/so101_smolvla_infer/
```

**注意**：不能保留 `pretrained_model/` 这层目录，否则推理时会报 `FileNotFoundError`。

## 真机推理（v0.6.0 推荐：`lerobot-rollout`）

LeRobot v0.6.0 新增了专门的真机部署 CLI `lerobot-rollout`，本项目已包装为 [`src/scripts/rollout.py`](../../src/scripts/rollout.py)。它替代了 v0.5.x 常用的 `lerobot-eval` 真机推理方式，支持自主运行、DAgger 人机回环、连续录制等多种策略。

### 基础自主推理

```bash
cd /home/j/ws/so101
unset PYTHONPATH
conda activate lerobot

python src/scripts/rollout.py \
  --strategy.type=base \
  --policy.path=/home/j/ws/so101/checkpoints/so101_smolvla_infer \
  --task="put grape block in plate" \
  --duration=60 \
  --display_data=false
```

> **端口/摄像头/固定关节自动加载**：`rollout.py` 会自动从 `src/configs/so101.yaml` 读取 `--robot.*`、`--teleop.*`、`--robot.cameras`、`--robot.fixed_joints`，无需手动传参。

### 按模型类型选择推理方式

| 模型 | 推理速度 | 建议配置 | 5070 显存 |
|------|---------|---------|----------|
| ACT | 快 | 默认 `sync` | 充足 |
| SmolVLA | 较慢 | 建议 `rtc` | 刚好 |
| Pi0 / Pi0.5 / EO1 | 很慢 | 必须 `rtc`，但 12GB 可能仍吃紧 | 不足 |

### 慢速 VLA 使用 RTC 推理

SmolVLA、Pi0、Pi0.5 等模型推理较慢，建议开启 Real-Time Chunking：

```bash
python src/scripts/rollout.py \
  --strategy.type=base \
  --inference.type=rtc \
  --inference.rtc.execution_horizon=10 \
  --policy.path=/home/j/ws/so101/checkpoints/so101_smolvla_infer \
  --task="put grape block in plate" \
  --duration=60
```

### 关键参数说明

| 参数 | 参考值 | 说明 |
|------|--------|------|
| `--strategy.type` | base | 自主运行；可选 sentry/highlight/dagger/episodic |
| `--inference.type` | sync / rtc | sync 为每控制周期调用一次策略；rtc 为慢速 VLA 实时 chunk 推理 |
| `--policy.path` | 导出后的模型目录 | 必须去掉 `pretrained_model/` 外壳 |
| `--task` | 语言指令 | 模型据此确定抓取哪种颜色的方块 |
| `--duration` | 60 / 300 | 推理时长（秒），0 表示无限运行 |
| `--display_data` | false | 推理时不预览，减少开销 |
| `--fps` | 30 | 控制频率 |

> **DAgger 已评估**：20k 模型实测 25 组成功率 84%（21/25），实际体验稳定，无需 DAgger 迭代纠错。

## 颜色切换

当前任务仅训练紫色方块，语言指令为 `"put grape block in plate"`。

如果后续扩展到多色训练，可通过 `--task` 切换目标颜色（必须与训练数据中的语言指令一致）：

```bash
# 紫色（当前）
--task="put grape block in plate"

# 绿色（扩展时）
--task="put green block in plate"

# 橙色（扩展时）
--task="put orange block in plate"
```

> 颜色名称必须与训练数据中 `--dataset.single_task` 设置的值完全一致。

## 兼容说明：v0.5.x 的 `lerobot-eval` 方式

v0.5.x 常用的真机推理命令形如：

```bash
lerobot-eval \
  --robot.type=so101_follower \
  --policy.path=... \
  --dataset.repo_id=local/eval_xxx \
  ...
```

在 v0.6.0 中，`lerobot-eval` 主要用于**仿真 benchmark 评估**（LIBERO-plus、RoboTwin 2.0 等），而真机部署推荐使用 `lerobot-rollout`。如果某些脚本或教程仍使用 `lerobot-eval` 接真机，建议替换为 `lerobot-rollout`。

## 验证推理

- [ ] 机械臂能自动完成抓放任务
- [ ] 对物体位置、颜色变化有一定泛化能力
- [ ] 失败时能安全停止（按 `Ctrl+C`）

## 模型验证与成功率统计

训练完成后，需要量化评估模型在真实任务上的表现。本项目的验证方案使用 `episodic` 策略**自动运行指定组数，每组 30 秒**，人工在每轮结束后标记成功/失败。

### 方案概述

| 方法 | 说明 | 适用场景 |
|------|------|---------|
| 自动多轮运行 | 用 `lerobot-rollout` 的 `episodic` 策略自动运行 N 组，每组固定时长 | 快速生成大量测试 episode |
| 手动成功标记 | 每轮结束后人工判断成功/失败，记录统计 | 真机任务，无自动成功检测 |

**评估配置**：每组推理 30 秒 + 复位 15 秒，共 25 组，全程约 19 分钟。直接在终端运行即可，无需守候。

### 自动运行多轮（episodic 策略）

v0.6.0 的 `lerobot-rollout` 支持 `--strategy.type=episodic` 自动连续运行多轮，每轮之间自动复位：

```bash
python src/scripts/rollout.py \
  --strategy.type=episodic \
  --dataset.num_episodes=20 \
  --dataset.episode_time_s=30 \
  --dataset.reset_time_s=15 \
  --inference.type=rtc \
  --inference.rtc.execution_horizon=10 \
  --policy.path=/home/j/ws/so101/checkpoints/so101_smolvla_infer \
  --task="put grape block in plate" \
  --dataset.repo_id=local/rollout_so101_eval \
  --dataset.single_task="put grape block in plate" \
  --dataset.push_to_hub=false
```

> `episodic` 策略会自动在每轮结束后进入复位阶段，等待环境重置后继续下一轮，直到完成 `--dataset.num_episodes` 指定的轮数。

### 手动成功标记与统计

由于真机抓取任务没有自动成功检测（如物体位置传感器），需要人工观察并记录：

#### 评估结果（v1-2，20k 步，2026-07-22）

```
模型: so101_smolvla_v1-2 (20k 步)  日期: 2026-07-22  测试轮数: 25

| 轮次 | 成功 | 备注 |
|------|------|------|
| 1-21 | ✓    | 21 次成功 |
| 22   | ✗    | 未能抓起 |
| 23   | ✗    | 未能抓起 |
| 24   | ✗    | 未能抓起 |
| 25   | ✗    | 已抓起但夹爪未松开 |

成功率: 21/25 = 84%
结论: 模型稳定，无需 DAgger 迭代纠错
```

#### 记录表模板

```
模型: so101_smolvla_v0  日期: 2026-07-22  测试轮数: 20

| 轮次 | 初始位置 | 成功 | 备注 |
|------|---------|------|------|
| 1    | 中心    | ✓    |      |
| 2    | 左偏    | ✗    | 方块未抓稳 |
| 3    | 右偏    | ✓    |      |
| ...  |         |      |      |
| 20   | 边缘    | ✓    |      |

成功率: 17/20 = 85%
```

#### 成功判定标准

- **成功**：紫色方块被抓起并放入白色盘子内，且方块在盘子中心区域内
- **失败**：
  - 方块未被抓起（夹爪空抓）
  - 方块掉出盘子
  - 方块推到盘子边缘但未入内
  - 动作超时未完成

#### 统计维度

建议从以下维度统计，找出模型弱点：

| 维度 | 分类 | 目的 |
|------|------|------|
| 初始位置 | 中心/左偏/右偏/边缘 | 测试位置泛化 |
| 光照 | 正常/强光/暗光 | 测试光照鲁棒性 |
| 盘子距离 | 近/中/远 | 测试操作范围 |
| 干扰 | 无/有 | 测试抗干扰（后期加入） |

### 验证脚本（可选）

可以写一个简单脚本自动统计手动记录的成功次数：

```python
# src/scripts/eval_stats.py
import sys

# 从命令行读取成功标记，如: python eval_stats.py s s f s s ...
marks = sys.argv[1:]
total = len(marks)
success = sum(1 for m in marks if m.lower() in ("s", "1", "y", "✓"))
print(f"总轮数: {total}")
print(f"成功: {success}")
print(f"成功率: {success / total * 100:.1f}%")
```

使用：
```bash
python src/scripts/eval_stats.py s s f s s s f s s s
# 输出: 总轮数: 10, 成功: 8, 成功率: 80.0%
```

## 迭代优化

当前 20k 模型（v1-2）已满足需求（84% 成功率），无需进一步优化。如果后续需要改进：

1. 增加数据多样性重新训练
2. 尝试不同策略（ACT 等）
3. 增加训练步数或调整固定关节角度

## 安全提示

推理时从臂会自主运动，请确保：

- 周围没有易碎物品和人员
- 从臂活动范围内没有障碍物
- 随时可以按 `Ctrl+C` 停止
- 首次推理时建议降低 `--duration`，先观察几轮

---

## 快速推理命令（手动操作用）

> 训练完成后直接复制粘贴即可运行。

### 前置检查

```bash
# 1. 确认机械臂已上电、USB 已连接
ls /dev/serial/by-id/

# 2. 确认摄像头正常
ls /dev/v4l/by-id/

# 3. 进入项目目录
cd /home/j/ws/so101
```

### 单条推理（测试用）

**10,000 步模型（v1-1）**：

```bash
PYTHONPATH= HF_HUB_OFFLINE=1 /home/j/miniconda3/envs/lerobot/bin/python -u src/scripts/rollout.py \
  --strategy.type=base \
  --inference.type=rtc \
  --inference.rtc.execution_horizon=10 \
  --policy.path=outputs/so101_smolvla_v1-1/checkpoints/010000/pretrained_model \
  --policy.empty_cameras=1 \
  --task="put grape block in plate" \
  --duration=300 \
  --rename_map='{"observation.images.front": "observation.images.camera1", "observation.images.top": "observation.images.camera2"}'
```

**20,000 步模型（v1-2）**：

```bash
PYTHONPATH= HF_HUB_OFFLINE=1 /home/j/miniconda3/envs/lerobot/bin/python -u src/scripts/rollout.py \
  --strategy.type=base \
  --inference.type=rtc \
  --inference.rtc.execution_horizon=10 \
  --policy.path=outputs/so101_smolvla_v1-1/checkpoints/020000/pretrained_model \
  --policy.empty_cameras=1 \
  --task="put grape block in plate" \
  --duration=300 \
  --rename_map='{"observation.images.front": "observation.images.camera1", "observation.images.top": "observation.images.camera2"}'
```

### 25 组正式评估（推荐）

每组 30 秒，自动复位，共 25 组。直接复制粘贴到终端运行即可。

> **注意**：`episodic` 策略会记录数据到本地（作为评估记录），但不会上传到 Hub。

**20,000 步模型（v1-2）**：

```bash
cd /home/j/ws/so101 && PYTHONPATH= HF_HUB_OFFLINE=1 /home/j/miniconda3/envs/lerobot/bin/python -u src/scripts/rollout.py \
  --strategy.type=episodic \
  --dataset.num_episodes=25 \
  --dataset.episode_time_s=30 \
  --dataset.reset_time_s=15 \
  --dataset.repo_id=local/rollout_so101_eval_20k \
  --dataset.single_task="put grape block in plate" \
  --dataset.push_to_hub=false \
  --inference.type=rtc \
  --inference.rtc.execution_horizon=10 \
  --policy.path=outputs/so101_smolvla_v1-1/checkpoints/020000/pretrained_model \
  --policy.empty_cameras=1 \
  --task="put grape block in plate" \
  --rename_map='{"observation.images.front": "observation.images.camera1", "observation.images.top": "observation.images.camera2"}'
```

**18,000 步模型（对比用）**：

```bash
cd /home/j/ws/so101 && PYTHONPATH= HF_HUB_OFFLINE=1 /home/j/miniconda3/envs/lerobot/bin/python -u src/scripts/rollout.py \
  --strategy.type=episodic \
  --dataset.num_episodes=25 \
  --dataset.episode_time_s=30 \
  --dataset.reset_time_s=15 \
  --dataset.repo_id=local/rollout_so101_eval_18k \
  --dataset.single_task="put grape block in plate" \
  --dataset.push_to_hub=false \
  --inference.type=rtc \
  --inference.rtc.execution_horizon=10 \
  --policy.path=outputs/so101_smolvla_v1-1/checkpoints/018000/pretrained_model \
  --policy.empty_cameras=1 \
  --task="put grape block in plate" \
  --rename_map='{"observation.images.front": "observation.images.camera1", "observation.images.top": "observation.images.camera2"}'
```

### 关键参数说明

| 参数 | 必须设置 | 说明 |
|------|---------|------|
| `HF_HUB_OFFLINE=1` | ✅ 必须 | 离线模式，避免卡在联网下载 |
| `--policy.empty_cameras=1` | ✅ 必须 | 声明有 1 个空相机（你只有 2 个，模型期望 3 个） |
| `--rename_map` | ✅ 必须 | front→camera1, top→camera2 |
| `--inference.type=rtc` | ✅ 必须 | SmolVLA 必须用 RTC 模式 |
| `--dataset.episode_time_s` | 可调 | 每组推理时长（秒），30=半分钟 |
| `--dataset.reset_time_s` | 可调 | 每组间复位时长（秒），15 秒 |
| `--dataset.num_episodes` | 可调 | 总组数，25 组 |

### 常见问题

**卡在 "Loading policy" 不动**：加上 `HF_HUB_OFFLINE=1`

**报错 "Visual feature mismatch"**：加上 `--policy.empty_cameras=1` 和 `--rename_map`

**报错 "Could not connect on port"**：机械臂未上电或 USB 未插，先 `ls /dev/serial/by-id/` 确认
