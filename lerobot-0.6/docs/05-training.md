# 05. 模型训练

> 参考项目：[JereoZero/so101-real](https://github.com/JereoZero/so101-real)  
> 参考项目文档：[06-model-training.md](https://github.com/JereoZero/so101-real/blob/main/%E9%A1%B9%E7%9B%AE%E6%B5%81%E7%A8%8B/06-model-training.md)

## 前置条件

- 已完成 [04-recording.md](04-recording.md)
- 数据集已录制完成并经过回放验证
- 已确认训练机器网络状态（是否离线）

## 推荐策略

| 策略 | 适用场景 | 显存需求（训练） | 说明 |
|------|---------|-----------------|------|
| **ACT** | 快速验证、简单任务 | ~2-4 GB | 非 VLM，训练最快，效果上限较低 |
| **Diffusion** | 生成式策略、中等复杂度任务 | ~4-8 GB | 效果较好，对数据多样性要求高 |
| **SmolVLA** | 语言指令、多任务/泛化 | ~8-12 GB | 参考项目最终使用，VLM  backbone 仅 500M，5070 可跑 |
| **Evo1** | 新出的轻量 VLA | ~10-12 GB | v0.6 新增，基于 InternVL3-1B，可关注但生态尚少 |
| **Pi0 / Pi0.5** | 通用 VLA | >16 GB | 效果强但 5070 12GB 训练和推理都吃力，不推荐 |
| **EO1 / Groot / MolmoAct2** | 大参数 VLA | >16 GB | 3B+ 参数，12GB 显存不够，不推荐 |

参考项目最终使用 **SmolVLA**。下面分别给出 ACT、Diffusion 和 SmolVLA 的训练示例。

## ACT 训练示例

```bash
cd /home/j/ws/so101
unset PYTHONPATH
conda activate lerobot

python src/scripts/train.py \
  --dataset.repo_id=local/so101_pick_place \
  --policy.type=act \
  --policy.dim_model=512 \
  --policy.n_layers=6 \
  --policy.n_heads=8 \
  --policy.dim_feedforward=2048 \
  --policy.chunk_size=100 \
  --policy.n_action_steps=10 \
  --training.batch_size=64 \
  --training.num_workers=4 \
  --training.lr=1e-4 \
  --training.num_epochs=3000 \
  --output_dir=outputs/so101_act
```

## Diffusion 训练示例

Diffusion Policy 是效果与速度兼顾的选择，适合 5070：

```bash
unset PYTHONPATH
conda activate lerobot
cd /home/j/ws/so101

python src/scripts/train.py \
  --dataset.repo_id=local/so101_pick_place_20260720_123456 \
  --policy.type=diffusion \
  --policy.n_obs_steps=2 \
  --policy.horizon=64 \
  --policy.n_action_steps=32 \
  --policy.vision_backbone=resnet18 \
  --policy.down_dims=[512,1024,2048] \
  --policy.num_train_timesteps=100 \
  --training.batch_size=32 \
  --training.num_workers=4 \
  --training.lr=1e-4 \
  --training.num_epochs=3000 \
  --output_dir=outputs/so101_diffusion
```

> 如果显存吃紧，可把 `down_dims` 改为 `[256,512,1024]` 或 `batch_size` 降到 16。

## SmolVLA 训练示例

### 1. 预训练模型准备

当前环境已通过 **HF-Mirror** 下载并迁移好 SmolVLA 预训练模型：

- 原始权重：`/home/j/ws/so101/checkpoints/smolvla_base/`（约 873MB）
- 迁移后权重（可直接训练）：`/home/j/ws/so101/checkpoints/smolvla_base_migrated/`（约 1.7GB）

> 迁移时会自动下载 VLM backbone `HuggingFaceTB/SmolVLM2-500M-Video-Instruct`（约 2GB），已使用镜像 `https://hf-mirror.com` 完成下载。

如果后续需要重新准备（例如换机器），步骤如下：

```bash
unset PYTHONPATH
conda activate lerobot

# 1. 确保已安装 SmolVLA 依赖
python -m pip install -e '/home/j/ws/repos/lerobot[smolvla]'

# 2. 下载预训练权重（使用 HF-Mirror）
HF_ENDPOINT=https://hf-mirror.com python - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id="lerobot/smolvla_base",
    local_dir="/home/j/ws/so101/checkpoints/smolvla_base",
)
PY

# 3. 执行迁移脚本
cd /home/j/ws/repos/lerobot
HF_ENDPOINT=https://hf-mirror.com python src/lerobot/processor/migrate_policy_normalization.py \
  --pretrained-path /home/j/ws/so101/checkpoints/smolvla_base
```

迁移后路径：`/home/j/ws/so101/checkpoints/smolvla_base_migrated/`

### 2. 训练命令

```bash
unset PYTHONPATH
conda activate lerobot
cd /home/j/ws/so101

HF_HUB_OFFLINE=1 python src/scripts/train.py \
  --policy.path=/home/j/ws/so101/checkpoints/smolvla_base_migrated \
  --policy.load_vlm_weights=false \
  --policy.use_amp=true \
  --policy.n_obs_steps=4 \
  --dataset.repo_id=local/so101_pick_place_20260720_123456 \
  --dataset.streaming=false \
  --dataset.image_transforms.enable=true \
  --dataset.image_transforms.random_order=true \
  --output_dir=outputs/so101_smolvla \
  --job_name=so101_smolvla \
  --policy.device=cuda \
  --wandb.enable=false \
  --policy.push_to_hub=false \
  --steps=40000 \
  --batch_size=36 \
  --save_freq=2000 \
  --rename_map='{"observation.images.front": "observation.images.camera1",
    "observation.images.top": "observation.images.camera2"}'
```

> **注意 `dataset.repo_id`**：v0.6.0 录制时会在你给的 `repo_id` 后自动追加时间戳（如 `local/so101_pick_place_20260720_123456`）。训练时必须使用这个**实际生成的 repo_id**，而不是录制命令里写的原始名字。你可以在录制结束的日志中找到它，或者用 `ls /home/j/ws/so101/data/so101_pick_place` / `ls ~/.cache/huggingface/lerobot/local/` 查看。

### 关键参数说明

| 参数 | 参考值 | 说明 |
|------|--------|------|
| `HF_HUB_OFFLINE=1` | 环境变量 | 离线模式，禁止 HuggingFace 联网 |
| `--policy.path` | 本地路径 | 从迁移后的预训练模型加载 |
| `--policy.load_vlm_weights` | false | 不重新加载 VLM 权重 |
| `--policy.use_amp` | true | bfloat16 混合精度训练，节省显存 |
| `--policy.n_obs_steps` | 4 | 连续 4 帧历史信息 |
| `--dataset.streaming` | false | 不从网络流式加载 |
| `--dataset.image_transforms` | true | 轻量图像增强，提升泛化 |
| `--wandb.enable` | false | 禁用 wandb 在线日志 |
| `--rename_map` | front→camera1, top→camera2 | 数据集用 front/top，SmolVLA 预训练模型期望 camera1/camera2 |
| `--batch_size` | 36 | 大 batch 加速收敛（RTX 5070 12GB 可尝试） |
| `--save_freq` | 2000 | 每 2000 步保存 checkpoint |

> 显存不足时可将 `--batch_size` 降至 8-16，并关闭 `use_amp=false`。

## 训练监控

训练日志会输出到 `outputs/<run_name>/` 目录。可通过以下方式监控：

```bash
# 查看训练日志
tail -f outputs/so101_smolvla/train.log

# TensorBoard（如果启用）
tensorboard --logdir=outputs/so101_smolvla
```

## 训练产出

```text
outputs/so101_smolvla/
├── checkpoints/
│   ├── 002000/
│   │   └── pretrained_model/
│   ├── 004000/
│   │   └── pretrained_model/
│   └── last/
│       └── pretrained_model/
├── train.log
└── ...
```

## 数据集格式与 v0.6 兼容性

### 录制数据能在 v0.6 直接训练吗？

**可以**。LeRobot v0.6.0 的数据集底层格式仍是 `LeRobotDataset`（视频/parquet + metadata），v0.6 主要变化是内部元数据类从旧字典换成了类型化的 `DatasetInfo`，并统一用语言列替代了旧版的 `subtask_index`。只要你在 v0.6 环境里用 `lerobot-record` 录制、用 `lerobot-train` 训练，格式完全兼容，不需要额外转换。

### v0.5.x 录制的数据能迁移到 v0.6 吗？

v0.6 自带了 `convert_dataset_v21_to_v30.py` 转换脚本，可以把旧版数据集升级到 v0.6 格式：

```bash
cd /home/j/ws/repos/lerobot
python src/lerobot/scripts/convert_dataset_v21_to_v30.py \
  --input_dir /path/to/old_dataset \
  --output_dir /path/to/new_dataset
```

> 本项目建议直接在 v0.6 里重新录制，避免跨版本迁移的潜在字段不一致。

### 可用的现成 SO-101 数据集

LeRobot v0.6 官方示例里提到了一个 SO-101 数据集：`lerobot/svla_so101_pickplace`。如果你的网络可访问 HuggingFace，可以直接用它做预训练或对比实验：

```bash
python src/scripts/train.py \
  --dataset.repo_id=lerobot/svla_so101_pickplace \
  --policy.type=act \
  --output_dir=outputs/svla_so101_act
```

### 同一个数据集能同时训练 SmolVLA 和 ACT/Diffusion 吗？

**可以。** LeRobot 的数据集是策略无关的，只要包含 `observation.images.*`、`observation.state` 和 `action` 就行。不同策略的主要差别是对**图像键名**的约定：

| 策略 | 对相机键名的要求 | 是否需要 `rename_map` |
|------|-----------------|---------------------|
| **ACT / Diffusion** | 自动识别所有 `observation.images.*` | 不需要 |
| **SmolVLA** | 预训练模型期望 `camera1`、`camera2`... | 需要 |

例如：

- 用同一数据集训练 **ACT**（直接用原始键名 `front/top`）：
  ```bash
  python src/scripts/train.py \
    --dataset.repo_id=local/so101_pick_place_20260720_123456 \
    --policy.type=act \
    --output_dir=outputs/so101_act
  ```

- 用同一数据集训练 **SmolVLA**（需要把 `front/top` 映射到 `camera1/camera2`）：
  ```bash
  python src/scripts/train.py \
    --dataset.repo_id=local/so101_pick_place_20260720_123456 \
    --policy.type=smolvla \
    --policy.path=/home/j/ws/so101/checkpoints/smolvla_base_migrated \
    --rename_map='{"observation.images.front": "observation.images.camera1",
      "observation.images.top": "observation.images.camera2"}' \
    --output_dir=outputs/so101_smolvla
  ```

> 语言指令列（`--dataset.single_task`）对 ACT/Diffusion 不是必需，它们只学动作；对 SmolVLA 是重要输入。

## 常见问题

### Q1: 训练时报 `FileNotFoundError` 找不到模型文件

- 检查 `--policy.path` 是否指向迁移后的目录
- 确认 `pretrained_model/` 内部的文件在目标目录根层级（见 [06-inference.md](06-inference.md) 导出说明）

### Q2: 显存不足

- 降低 `--batch_size`
- 开启 `--policy.use_amp=true`
- 降低输入图像分辨率（需同步调整录制配置）

### Q3: loss 不下降

- 检查数据质量，回放确认动作与图像对应正确
- 增加数据多样性
- 调整学习率

## 下一步

训练完成后，进入 [06-inference.md](06-inference.md) 进行推理部署。
