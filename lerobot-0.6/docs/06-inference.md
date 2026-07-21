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
| ACT / Diffusion | 快 | 默认 `sync` | 充足 |
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

### DAgger 人机回环（模型纠错迭代）

v0.6.0 的 `lerobot-rollout` 支持 DAgger 模式：模型执行时如果出错，人可以接管主臂纠正，纠正数据自动保存用于再训练。

```bash
python src/scripts/rollout.py \
  --strategy.type=dagger \
  --strategy.num_episodes=20 \
  --inference.type=rtc \
  --inference.rtc.execution_horizon=10 \
  --policy.path=/home/j/ws/so101/checkpoints/so101_smolvla_infer \
  --dataset.repo_id=local/so101_dagger_corrections \
  --dataset.single_task="put grape block in plate" \
  --dataset.push_to_hub=false
```

## DAgger 迭代训练方案（推荐）

> 当前项目已录制约 170+ 条演示数据，计划先达到 200 条后再开始第一次训练。训练完成并验证效果后，可通过 DAgger 迭代进一步提升成功率。

DAgger 的核心价值：模型在实际运行中暴露的失败模式，往往是最难通过静态演示数据覆盖的。让模型在这些失败场景下由人接管纠正，把纠正轨迹保存为新数据，再训练一次，通常比单纯堆数据更有效。

### 推荐迭代流程

```
阶段 1: 初始演示数据（当前）
  v1-1 ~ v1-N（计划 200 条）
        ↓
阶段 2: 第一次训练
  合并 → 训练 SmolVLA → 导出模型
        ↓
阶段 3: 真机推理测试
  用 episodic/base 策略跑 20~30 轮，记录失败模式
        ↓
阶段 4: DAgger 收集纠正数据
  针对失败场景，人接管主臂纠正，保存 30~50 条
        ↓
阶段 5: 合并数据并重新训练
  原数据 + DAgger 数据 → 从头训练 v1_dagger 模型
        ↓
阶段 6: 再次验证
  成功率达标则结束；否则重复阶段 3~5
```

### 方案 A：合并后从头重新训练（第一次 DAgger 推荐）

第一次引入 DAgger 数据时，建议把原数据和纠正数据合并后**从头训练**（加载 `smolvla_base_migrated`，而不是上次训好的 checkpoint）。这样可以避免旧模型的坏习惯被保留，数据分布也更均衡。

```bash
# 步骤 1：DAgger 收集（在基础模型上执行）
python src/scripts/rollout.py \
  --strategy.type=dagger \
  --strategy.num_episodes=30 \
  --inference.type=rtc \
  --inference.rtc.execution_horizon=10 \
  --policy.path=/home/j/ws/so101/checkpoints/so101_smolvla_infer_v1 \
  --dataset.repo_id=local/so101_grape_put_v1_dagger \
  --dataset.single_task="put grape block in plate" \
  --dataset.push_to_hub=false

# 步骤 2：合并原数据与 DAgger 数据
lerobot-edit-dataset \
  --operation.type=merge \
  --operation.repo_ids='["local/so101_grape_put_v1_merged","local/so101_grape_put_v1_dagger"]' \
  --operation.roots='["/home/j/ws/so101/data/so101_grape_put_v1_merged","/home/j/ws/so101/data/so101_grape_put_v1_dagger"]' \
  --new_repo_id=local/so101_grape_put_v1_merged_dagger \
  --new_root=/home/j/ws/so101/data/so101_grape_put_v1_merged_dagger

# 步骤 3：从头重新训练（加载 base，不是上次 checkpoint）
python src/scripts/train.py \
  --policy.path=/home/j/ws/so101/checkpoints/smolvla_base_migrated \
  --policy.load_vlm_weights=false \
  --dataset.repo_id=local/so101_grape_put_v1_merged_dagger \
  --dataset.root=/home/j/ws/so101/data/so101_grape_put_v1_merged_dagger \
  --dataset.streaming=false \
  --dataset.image_transforms.enable=true \
  --dataset.image_transforms.random_order=true \
  --output_dir=outputs/so101_smolvla_v1_dagger \
  --job_name=so101_smolvla_v1_dagger \
  --policy.device=cuda \
  --wandb.enable=false \
  --policy.push_to_hub=false \
  --steps=40000 \
  --batch_size=36 \
  --save_freq=2000 \
  --rename_map='{"observation.images.front": "observation.images.camera1",
    "observation.images.top": "observation.images.camera2"}'
```

### 方案 B：在训好的模型上 fine-tune（后续小修小补）

如果模型已经 90% 成功，只剩某个特定小场景失败，可以只收集该场景的 DAgger 数据，用低学习率在上次 checkpoint 上 fine-tune。

```bash
python src/scripts/train.py \
  --policy.path=outputs/so101_smolvla_v1/checkpoints/last/pretrained_model \
  --dataset.repo_id=local/so101_grape_put_v1_dagger_small \
  --dataset.root=/home/j/ws/so101/data/so101_grape_put_v1_dagger_small \
  --output_dir=outputs/so101_smolvla_v1_finetune \
  --steps=5000 \
  --batch_size=8 \
  --lr=1e-5 \
  --save_freq=1000 \
  --rename_map='{"observation.images.front": "observation.images.camera1",
    "observation.images.top": "observation.images.camera2"}'
```

**fine-tune 的缺点**：
- 容易过拟合 DAgger 数据（样本少且分布偏）
- 可能遗忘原来的成功经验
- 只推荐用于"小修小补"，第一次 DAgger 迭代用方案 A

### DAgger 数据量与合并比例建议

| 原数据量 | DAgger 建议量 | 合并后总量 | 说明 |
|---------|-------------|-----------|------|
| 200 条 | 30~50 条 | 230~250 条 | 第一次迭代 |
| 250 条 | 20~30 条 | 270~280 条 | 后续小迭代 |

- DAgger 数据虽然少，但都是"失败场景 + 正确纠正"，信息密度高
- 合并后默认 equal weight，不需要额外加权
- 如果想提高 DAgger 数据采样概率，可以：
  - 多收集一些（占比 15~20%）
  - 或将 DAgger 数据集复制多份后合并

### DAgger 操作要点

1. **观察失败模式**：先在 `base`/`episodic` 模式下跑 20~30 轮，记录常见失败（如方块在左侧够不到、夹爪角度不对等）
2. **针对性收集**：DAgger 时故意制造这些失败场景，让模型出错，然后接管主臂纠正
3. **纠正要完整**：接管后要把整个正确轨迹做完，不只是修正一步
4. **覆盖多样性**：同一类失败场景多收集几次（不同位置、光照）
5. **夹爪冷却**：DAgger 也是真机运行，注意夹爪电机过热问题

### DAgger 与 RA-BC 的对比

| 方案 | 是否需要 reward model | 实施难度 | 适用阶段 | 推荐度 |
|------|---------------------|---------|---------|--------|
| **DAgger + 重新训练** | 不需要 | 中 | 第一次迭代 | ⭐⭐⭐⭐⭐ |
| **DAgger + fine-tune** | 不需要 | 低 | 小修小补 | ⭐⭐⭐ |
| **RA-BC + SARM** | 需要训练 SARM reward model | 高 | 有充足资源时 | ⭐⭐ |

DAgger 对当前项目是最实用的选择。

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

训练完成后，需要量化评估模型在真实任务上的表现。本项目的验证方案分为**自动运行多轮**和**手动标记成功**两部分。

### 方案概述

| 方法 | 说明 | 适用场景 |
|------|------|---------|
| 自动多轮运行 | 用 `lerobot-rollout` 的 `episodic` 策略自动运行 N 轮 | 快速生成大量测试 episode |
| 手动成功标记 | 每轮结束后人工判断成功/失败，记录统计 | 真机任务，无自动成功检测 |

### 自动运行多轮（episodic 策略）

v0.6.0 的 `lerobot-rollout` 支持 `--strategy.type=episodic` + `--strategy.num_episodes=N` 自动连续运行多轮，每轮之间自动复位：

```bash
python src/scripts/rollout.py \
  --strategy.type=episodic \
  --strategy.num_episodes=20 \
  --inference.type=rtc \
  --inference.rtc.execution_horizon=10 \
  --policy.path=/home/j/ws/so101/checkpoints/so101_smolvla_infer \
  --task="put grape block in plate" \
  --dataset.repo_id=local/so101_eval_grape \
  --dataset.single_task="put grape block in plate" \
  --dataset.push_to_hub=false
```

> `episodic` 策略会自动在每轮结束后进入复位阶段，等待环境重置后继续下一轮，直到完成 `--strategy.num_episodes` 指定的轮数。

### 手动成功标记与统计

由于真机抓取任务没有自动成功检测（如物体位置传感器），需要人工观察并记录：

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

如果效果不佳：

1. 增加数据多样性
2. 使用 DAgger 收集失败场景的人为纠正数据
3. 尝试不同策略（Diffusion / SmolVLA）
4. 增加训练步数或调整固定关节角度

## 安全提示

推理时从臂会自主运动，请确保：

- 周围没有易碎物品和人员
- 从臂活动范围内没有障碍物
- 随时可以按 `Ctrl+C` 停止
- 首次推理时建议降低 `--duration`，先观察几轮
