# 9. 模型训练

## 9.1 训练概述

本项目基于 SmolVLA 官方预训练模型（`lerobot/smolvla_base`）进行微调，不是从头训练。预训练模型已在大量数据上学习了基础的视觉-语言-动作映射，我们的微调只在小规模 SO101 数据集上做领域适配。

经历了多轮训练，逐步调整策略：

| 轮次 | 步数 | batch_size | save_freq | 说明 |
|------|------|------------|-----------|------|
| 第1轮 | 10000 | 8 | 1000 | 首次训练测试 |
| 第2轮 | 40000 | 8 | 2000 | 从零重训（因 resume bug） |
| 第3轮 | 40000 | **36** | 2000 | V3版，大 batch 加速训练 |

---

## 9.2 SmolVLA 不支持 --policy.dropout 参数

**现象**：训练时报 `unrecognized arguments: --policy.dropout=0.15`。

**原因**：SmolVLA 的配置类中并没有 `dropout` 字段，这个参数是 ACT 特有的。ACT 和 SmolVLA 的命令参数不完全相同。

**解决**：从 SmolVLA 训练命令中移除 `--policy.dropout` 参数。

---

## 9.3 预训练模型路径配置

SmolVLA 需要从 HuggingFace 的预训练模型开始微调。

**模型文件**：
- `model.safetensors`（906MB）
- `config.json`

**两个关键参数**：

```bash
--policy.path=/home/jer/ws/workspace/models/smolvla_base_migrated \
--policy.load_vlm_weights=false
```

**重要**：首次训练前必须先对预训练模型执行 migration：

```bash
python src/lerobot/processor/migrate_policy_normalization.py \
    --pretrained-path /home/jer/ws/workspace/models/smolvla_base
```

否则训练会因 normalizer 缺失而失败。迁移后使用 `_migrated` 后缀的路径。

---

## 9.4 Feature 不匹配：camera1/camera2 vs front/top

**现象**：训练时报 `Missing features: ['observation.images.camera1', 'observation.images.camera2']`。

**原因**：SmolVLA 预训练模型期望的摄像头名称是 `camera1`/`camera2`，而录制数据集使用的是 `front`/`top`。

**解决**：训练命令中添加 `--rename_map`：

```bash
--rename_map='{"observation.images.front": "observation.images.camera1", "observation.images.top": "observation.images.camera2"}'
```

---

## 9.5 Resume 训练时 Optimizer 配置缺失

**现象**：使用 `--resume=true` 继续训练时报：
```
ValueError: Optimizer config is required but not provided in TrainPipelineConfig
```

**原因**：这是 LeRobot 框架的一个 Bug：
1. 训练配置（checkpoint 中的 `train_config.json`）没有保存 optimizer 和 scheduler 的完整配置
2. `use_policy_training_preset=true` 时，只有在非 resume 模式下才会从 policy 自动获取 optimizer preset
3. resume 模式下代码逻辑没有正确加载 optimizer 配置

**尝试失败的方案**：
- `--resume=true` + `--use_policy_training_preset=true` → 失败
- `--resume=true` + `--use_policy_training_preset=false` + 手动指定 optimizer/scheduler 参数 → 失败（draccus 解析器有 bug，见 9.6）

**最终解决方案（绕过去）**：不使用 `--resume`，而是直接把 checkpoint 路径作为 `policy.path`，从头开始新一轮训练：

```bash
lerobot-train \
    --policy.path=/path/to/checkpoint/025000/pretrained_model \
    --steps=40000 \
    ...
```

这样虽然训练步数从 0 开始计数，但模型权重是从 checkpoint 继承的。**本项目第2轮训练就是通过这种方式执行的**。

---

## 9.6 命令行参数解析错误（draccus Bug）

**现象**：使用嵌套参数格式如 `--optimizer.lr=1e-4` `--scheduler.num_warmup_steps=1000` 时报：
```
TypeError: 'str' object does not support item assignment
```

**原因**：draccus（LeRobot 使用的命令行解析库）在处理嵌套参数时有问题。

**解决**：避免复杂的嵌套命令行参数，改用配置文件或 checkpoint 路径方式。

---

## 9.7 离线训练配置

由于目标机器网络不通，训练必须离线进行：

```bash
HF_HUB_OFFLINE=1 lerobot-train \
    --policy.path=/本地/模型/路径 \
    --dataset.repo_id=local/数据集名 \
    --dataset.root=/本地/数据集/路径 \
    --dataset.streaming=false \
    --policy.push_to_hub=false \
    --wandb.enable=false \
    ...
```

关键参数：
- `HF_HUB_OFFLINE=1`：环境变量，禁止 HuggingFace Hub 联网
- `--dataset.repo_id=local/xxx`：本地数据集标识
- `--dataset.root=/本地路径`：数据集本地路径
- `--dataset.streaming=false`：不从网络流式加载
- `--wandb.enable=false`：禁用 wandb 在线日志

---

## 9.8 OpenCV/numpy 版本冲突

**现象**：训练或回放数据时报：
```
AttributeError: module 'numpy' has no attribute 'ndarray'
```

**原因**：conda 安装的 opencv 与 pip 安装的 opencv-python-headless 产生库冲突，叠加 numpy 版本不兼容（LeRobot 要求 `numpy>=2.0.0,<2.3.0`）。

**一键修复**：

```bash
conda uninstall -y opencv && pip install opencv-python-headless==4.10.0.84 && pip install "numpy<2.3.0,>=2.0.0"
```

**修复后必须重新打开终端**，确保环境变量生效。

**背景**：LeRobot 的 `pyproject.toml` 明确要求 `numpy>=2.0.0,<2.3.0`，上限是因为 `opencv-python-headless` 的兼容性。

---

## 9.9 训练速度参考

本项目硬件 RTX 5070 12GB：
- batch_size=8 时约 **3.3 step/s**，40000 步约 3.3 小时
- batch_size=36 时约 **1.0 step/s**（单步计算量大但总收敛更快），40000 步约 11 小时
- 25000 步（batch_size=8）约 2.1 小时
- 10000 步（batch_size=8）约 50 分钟

---

## 9.10 第1轮训练（10000步）

```bash
HF_HUB_OFFLINE=1 lerobot-train \
    --policy.path=/home/jer/ws/workspace/models/smolvla_base_migrated \
    --policy.load_vlm_weights=false \
    --dataset.repo_id=local/smolvla210 \
    --dataset.root=/home/jer/ws/workspace/datasets/smolvla210 \
    --dataset.streaming=false \
    --output_dir=/home/jer/ws/workspace/models/smolvla_model/smolvla210/ \
    --job_name=so101_3color_smolvla210 \
    --policy.device=cuda \
    --wandb.enable=false \
    --policy.push_to_hub=false \
    --steps=10000 \
    --batch_size=8 \
    --save_freq=1000 \
    --rename_map='{"observation.images.front": "observation.images.camera1", "observation.images.top": "observation.images.camera2"}'
```

### 第1轮检查点

| 步数 | 路径 |
|------|------|
| 10000 | `checkpoints/010000` |
| 12000 | `checkpoints/012000` |
| 14000 | `checkpoints/014000` |
| 16000 | `checkpoints/016000` |
| 18000 | `checkpoints/018000` |
| 20000 | `checkpoints/020000` |
| 22000 | `checkpoints/022000` |
| 24000 | `checkpoints/024000` |
| 25000 | `checkpoints/025000` |

---

## 9.11 第2轮训练（40000步，从零重训）

由于 resume bug 无法继续训练，决定从 zero checkpoint 开始重训到 40000 步：

```bash
HF_HUB_OFFLINE=1 lerobot-train \
    --policy.path=/home/jer/ws/workspace/models/smolvla_base_migrated \
    --policy.load_vlm_weights=false \
    --dataset.repo_id=local/smolvla210 \
    --dataset.root=/home/jer/ws/workspace/datasets/smolvla210 \
    --dataset.streaming=false \
    --output_dir=/home/jer/ws/workspace/models/smolvla_model/smolvla210_40000/ \
    --job_name=so101_3color_smolvla210 \
    --policy.device=cuda \
    --wandb.enable=false \
    --policy.push_to_hub=false \
    --steps=40000 \
    --batch_size=8 \
    --save_freq=2000 \
    --rename_map='{"observation.images.front": "observation.images.camera1", "observation.images.top": "observation.images.camera2"}'
```

---

## 9.12 第3轮训练（V3版，40000步，batch_size=36）

使用更大 batch size 加速收敛：

```bash
HF_HUB_OFFLINE=1 lerobot-train \
    --policy.path=/home/jer/ws/workspace/models/smolvla_base_migrated \
    --policy.load_vlm_weights=false \
    --policy.use_amp=true \
    --policy.n_obs_steps=4 \
    --dataset.repo_id=local/smolvla210 \
    --dataset.root=/home/jer/ws/workspace/datasets/smolvla210 \
    --dataset.streaming=false \
    --dataset.image_transforms.enable=true \
    --dataset.image_transforms.random_order=true \
    --output_dir=/home/jer/ws/workspace/models/smolvla_v3_run2/ \
    --job_name=so101_3color_smolvla_v3 \
    --policy.device=cuda \
    --wandb.enable=false \
    --policy.push_to_hub=false \
    --steps=40000 \
    --batch_size=36 \
    --save_freq=2000 \
    --rename_map='{"observation.images.front": "observation.images.camera1", "observation.images.top": "observation.images.camera2"}'
```

**V3 与之前版本的差异**：

| 参数 | V1/V2 | V3 | 说明 |
|------|-------|-----|------|
| batch_size | 8 | **36** | 大幅提升，加速收敛 |
| use_amp | 关闭 | **开启 (bfloat16)** | 混合精度训练，节省显存 |
| n_obs_steps | 1 | **4** | 连续4帧历史信息，增强时序感知 |
| image_transforms | 关闭 | **开启** | 轻量图像增强，提升泛化 |
| steps | 10000/40000 | 40000 | 相同 |
| save_freq | 1000/2000 | 2000 | 相同 |

### 9.12.1 V3 图像增强详情

V3 使用"轻量"图像增强策略，只开启亮度和对比度变换，关闭颜色/几何增强：

| 变换 | V1/V2 | V3 | 范围 |
|------|-------|-----|------|
| brightness | 关闭 | **开启** | ±10% (0.9, 1.1) |
| contrast | 关闭 | **开启** | ±10% (0.9, 1.1) |
| saturation | 关闭 | 关闭 | — |
| hue | 关闭 | 关闭 | — |
| sharpness | 关闭 | 关闭 | — |
| affine (旋转/平移) | 关闭 | 关闭 | — |

设计思路：增强太强会干扰学习，太弱则起不到泛化效果。±10% 是经过权衡的轻量选择。

### 9.12.2 优化器与学习率调度

训练使用的 optimizer 和 scheduler 配置（从预训练模型继承）：

- **优化器**: AdamW
- **初始学习率**: 1e-4 (0.0001)
- **Weight decay**: 1e-10
- **Gradient clip**: 10.0
- **Scheduler**: cosine_decay_with_warmup
- **Warmup 步数**: 1000
- **衰减总步数**: 30000
- **学习率范围**: 1e-4 (peak) → 2.5e-6 (final)

### 9.12.3 V2 测试结果参考

在切换到 V3 之前，V2 模型（batch_size=8, 40000步）各 checkpoint 的测试表现：

| 步数 | 表现 |
|------|------|
| 10000 | 基础可用 |
| 26000 | 非常一般 |
| 28000 | ✓ **最佳**（比 32000 好很多） |
| 32000 | 一般 |

### 9.12.4 训练步数选择经验

训练过程中会每隔 `save_freq` 步保存一个 checkpoint，不同步数的模型效果差异很大。不要默认使用最后一步的版本。

经过对比测试，本项目效果最好的是 18000 步的 checkpoint，而不是步数更多的版本。建议在推理测试时多对比几个不同步数的 checkpoint，从中选出效果最好的。

| 步数 | 效果 |
|------|------|
| 10000 | 基础可用 |
| 18000 | ✓ **最佳** |
| 26000 | 非常一般 |
| 28000 | 较好但不如 18000 |
| 32000 | 一般 |
| 40000 | 不一定比中期好 |

> **结论**：更多步数不代表更好效果，务必对比多个 checkpoint 再选择。

