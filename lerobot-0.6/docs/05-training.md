# 05. 模型训练

> 参考项目：[JereoZero/so101-real](https://github.com/JereoZero/so101-real)  
> 参考项目文档：[06-model-training.md](https://github.com/JereoZero/so101-real/blob/main/%E9%A1%B9%E7%9B%AE%E6%B5%81%E7%A8%8B/06-model-training.md)

## 前置条件

- 已完成 [04-recording.md](04-recording.md)
- 数据集已录制完成并经过回放验证
- 任务：`"put grape block in plate"`（紫色方块 -> 盘子）
- 数据集：`local/so101_grape_put_v{version}-{group}`（详见录制文档命名规则）
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
  --dataset.repo_id=local/so101_grape_put_v0-1 \
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

### 2. 数据集合并（多组数据）

> ⚠️ **v0.6.0 重要变化**：v0.5.x 支持的 `--dataset.repo_id='["a","b","c"]'` 列表式多数据集合并**已被禁用**（源码 `factory.py` 中 `MultiLeRobotDataset` 被 `raise NotImplementedError` 屏蔽）。必须先用 `lerobot-edit-dataset --operation.type=merge` 物理合并为一个数据集，再训练。

合并 v1 版的多组数据（如 v1-1 ~ v1-5 共 50 条）：

```bash
unset PYTHONPATH
conda activate lerobot
cd /home/j/ws/so101

lerobot-edit-dataset \
  --operation.type=merge \
  --operation.repo_ids='["local/so101_grape_put_v1-1","local/so101_grape_put_v1-2","local/so101_grape_put_v1-3","local/so101_grape_put_v1-4","local/so101_grape_put_v1-5"]' \
  --operation.roots='["/home/j/ws/so101/data/so101_grape_put_v1-1","/home/j/ws/so101/data/so101_grape_put_v1-2","/home/j/ws/so101/data/so101_grape_put_v1-3","/home/j/ws/so101/data/so101_grape_put_v1-4","/home/j/ws/so101/data/so101_grape_put_v1-5"]' \
  --new_repo_id=local/so101_grape_put_v1_merged \
  --new_root=/home/j/ws/so101/data/so101_grape_put_v1_merged
```

合并后产出完整的新数据集（视频拼接 + parquet 合并 + stats 重算），训练时直接用单个 `repo_id`。

> **注意**：`repo_ids` 和 `roots` 列表长度必须一致，顺序对应。合并后可用 `lerobot-edit-dataset --operation.type=info --repo_id=local/so101_grape_put_v1_merged --root=...` 查看合并结果。

### 3. 训练命令

```bash
unset PYTHONPATH
conda activate lerobot
cd /home/j/ws/so101

HF_HUB_OFFLINE=1 python src/scripts/train.py \
  --policy.path=/home/j/ws/so101/checkpoints/smolvla_base_migrated \
  --policy.load_vlm_weights=false \
  --policy.use_amp=true \
  --policy.n_obs_steps=4 \
  --dataset.repo_id=local/so101_grape_put_v1_merged \
  --dataset.root=/home/j/ws/so101/data/so101_grape_put_v1_merged \
  --dataset.streaming=false \
  --dataset.video_backend=pyav \
  --dataset.eval_split=0.1 \
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
  --env_eval_freq=0 \
  --rename_map='{"observation.images.front": "observation.images.camera1",
    "observation.images.top": "observation.images.camera2"}'
```

> **指定数据集的两种方式**：
> 1. **单数据集 + root 路径**（推荐）：`--dataset.repo_id=local/xxx --dataset.root=/path/to/xxx`
> 2. **单数据集仅 repo_id**：`--dataset.repo_id=local/xxx`（从 `$HF_LEROBOT_HOME/repo_id` 查找）
>
> v0.6.0 录制时会在 `repo_id` 后自动追加时间戳，但通过 `--dataset.root` 指定路径不受影响。
>
> ⚠️ **多数据集合并**：v0.6.0 不再支持 `--dataset.repo_id='["a","b"]'` 列表方式。请先用 `lerobot-edit-dataset --operation.type=merge` 物理合并（见上方"数据集合并"小节）。

### 4. 1000 步显存/流程测试命令

在正式跑 40k 步之前，建议先用 1000 步小测试确认：
1. 显存是否够用
2. 训练流程能正常启动
3. checkpoint 能正常保存

```bash
unset PYTHONPATH
conda activate lerobot
cd /home/j/ws/so101

HF_HUB_OFFLINE=1 python src/scripts/train.py \
  --policy.path=/home/j/ws/so101/checkpoints/smolvla_base_migrated \
  --policy.load_vlm_weights=false \
  --policy.use_amp=true \
  --policy.n_obs_steps=4 \
  --dataset.repo_id=local/so101_grape_put_v1_merged \
  --dataset.root=/home/j/ws/so101/data/so101_grape_put_v1_merged \
  --dataset.streaming=false \
  --dataset.video_backend=pyav \
  --dataset.image_transforms.enable=true \
  --dataset.image_transforms.random_order=true \
  --output_dir=outputs/so101_smolvla_test \
  --job_name=so101_smolvla_test \
  --policy.device=cuda \
  --wandb.enable=false \
  --policy.push_to_hub=false \
  --steps=1000 \
  --batch_size=36 \
  --save_freq=500 \
  --env_eval_freq=0 \
  --rename_map='{"observation.images.front": "observation.images.camera1",
    "observation.images.top": "observation.images.camera2"}'
```

> 训练过程中可用 `nvidia-smi` 观察显存占用。RTX 5070 12GB 配合 `use_amp=true` + `batch_size=36` 通常能跑。如果 OOM，把 `batch_size` 降到 16 或 8。

### 关键参数说明

| 参数 | 默认值 | 参考值 | 说明 |
|------|--------|--------|------|
| `HF_HUB_OFFLINE=1` | - | 环境变量 | 离线模式，禁止 HuggingFace 联网 |
| `--policy.path` | - | 本地路径 | 从迁移后的预训练模型加载 |
| `--policy.load_vlm_weights` | false | false | 不重新加载 VLM 权重 |
| `--policy.use_amp` | false | true | bfloat16 混合精度，节省显存+加速 |
| `--policy.n_obs_steps` | 1 | 4 | 连续 4 帧历史信息 |
| `--policy.chunk_size` | 50 | 50 | 输出动作 chunk 长度 |
| `--policy.device` | - | cuda | 训练设备 |
| `--dataset.streaming` | false | false | 不从网络流式加载 |
| `--dataset.eval_split` | 0 | 0.1 | 留出 10% episodes 做验证 loss |
| `--dataset.image_transforms.enable` | false | true | 开启图像增强 |
| `--dataset.image_transforms.random_order` | false | true | 随机顺序应用增强 |
| `--wandb.enable` | - | false | 禁用 wandb 在线日志 |
| `--policy.push_to_hub` | - | false | 不推送到 HF Hub |
| `--rename_map` | - | front→camera1, top→camera2 | 数据集 front/top → SmolVLA camera1/camera2 |
| `--steps` | 100000 | 40000 | 总训练步数 |
| `--batch_size` | 8 | 36 | 每步 batch size |
| `--save_freq` | 20000 | 2000 | 每 N 步保存 checkpoint |
| `--env_eval_freq` | 20000 | **0** | 仿真环境评估频率，真机任务必须设为 0 |
| `--dataset.video_backend` | torchcodec | **pyav** | 视频解码后端。torchcodec 需 FFmpeg 动态库，当前环境因 CXXABI 版本不兼容无法加载，**必须用 pyav** |
| `--log_freq` | 200 | 200 | 每 N 步打印 log |

> 显存不足时可将 `--batch_size` 降至 16/8。如果 `use_amp=true` 仍 OOM，可尝试 `--policy.n_obs_steps=2` 或 `--policy.compile_model=false`。

### 输出目录

`--output_dir=outputs/so101_smolvla` 是相对于 `cwd=/home/j/ws/so101` 的路径，所以实际输出在：

```text
/home/j/ws/so101/outputs/so101_smolvla/
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

训练前确保 `/home/j/ws/so101/outputs/` 目录存在（当前已存在 `.gitkeep`）。

## 训练监控

训练日志会输出到 `outputs/<run_name>/` 目录。可通过以下方式监控：

```bash
# 查看训练日志
tail -f outputs/so101_smolvla/train.log

# TensorBoard（如果启用）
tensorboard --logdir=outputs/so101_smolvla
```

## 断点续训（分阶段训练）

LeRobot v0.6.0 原生支持从 checkpoint 断点续训。你可以先训 10k 步看效果，满意后再从 10k 继续训到 20k、40k。

### 原理

每次 `--save_freq` 步会保存 checkpoint，包含：
- 模型权重（`pretrained_model/`）
- 优化器状态（`training_state/`）
- 训练配置（`train_config.json`）
- 采样器状态（确保数据顺序续接）

用 `--resume=true` + `--config_path` 指向 checkpoint 的 `train_config.json` 即可从断点继续。

### 分阶段训练流程

### 训练命名规则

采用与数据集一致的 `v{version}-{group}` 格式：

```
outputs/so101_smolvla_v{version}-{group}
```

| 含义 | 说明 |
|------|------|
| `version` | 对应数据版本号，表示用的是哪版数据训练的 |
| `group` | 同版本数据的第几次训练，从 1 开始 |

| 训练名 | 说明 |
|--------|------|
| `so101_smolvla_v1-1` | 用 v1 数据训练，第 1 版模型（0→10k 步） |
| `so101_smolvla_v1-2` | 用 v1 数据训练，第 2 版模型（从 v1-1 续训 10k→20k） |
| `so101_smolvla_v1-3` | 用 v1 数据训练，第 3 版模型（从 v1-2 续训 20k→30k） |
| `so101_smolvla_v2-1` | 用 v2 数据（含 DAgger 等）重新训练，第 1 版 |

> 注意：v1-2 是 v1-1 的续训（`--resume=true`），不是从头训练。v2-1 是用新数据从头训练。

### 分阶段训练计划

| 阶段 | 训练名 | 步数范围 | 续训方式 | 预计耗时 |
|------|--------|---------|---------|---------|
| **第 1 阶段** | `v1-1` | 0 → 10,000 | 从头训练 | ~3h |
| **第 2 阶段** | `v1-2` | 10,000 → 20,000 | resume from v1-1 | ~3h |
| **第 3 阶段** | `v1-3` | 20,000 → 30,000 | resume from v1-2 | ~3h |

> 最多训到 30k 步。之后考虑用 DAgger 生成新数据，可能以 v2 版本重新训练。

**第 1 阶段：训练 v1-1（0→10k 步）**

```bash
cd /home/j/ws/so101
unset PYTHONPATH
conda activate lerobot

HF_HUB_OFFLINE=1 python src/scripts/train.py \
  --policy.path=/home/j/ws/so101/checkpoints/smolvla_base_migrated \
  --policy.load_vlm_weights=false \
  --policy.use_amp=true \
  --policy.n_obs_steps=4 \
  --dataset.repo_id=local/so101_grape_put_v1_merged \
  --dataset.root=/home/j/ws/so101/data/so101_grape_put_v1_merged \
  --dataset.streaming=false \
  --dataset.video_backend=pyav \
  --dataset.image_transforms.enable=true \
  --dataset.image_transforms.random_order=true \
  --output_dir=outputs/so101_smolvla_v1-1 \
  --job_name=so101_smolvla_v1-1 \
  --policy.device=cuda \
  --wandb.enable=false \
  --policy.push_to_hub=false \
  --steps=10000 \
  --batch_size=36 \
  --save_freq=2000 \
  --env_eval_freq=0 \
  --log_freq=10 \
  --rename_map='{"observation.images.front": "observation.images.camera1",
    "observation.images.top": "observation.images.camera2"}'
```

> 预计耗时：~3 小时（batch=36, ~1.06 s/step）

**第 1 阶段完成后**：产出 checkpoint 在 `outputs/so101_smolvla_v1-1/checkpoints/010000/`。可先导出做推理测试，看效果决定是否继续。

**第 2 阶段：训练 v1-2（10k→20k 步，从 v1-1 续训）**

```bash
HF_HUB_OFFLINE=1 python src/scripts/train.py \
  --resume=true \
  --config_path=outputs/so101_smolvla_v1-1/checkpoints/010000/train_config.json \
  --steps=20000
```

> 续训时 output_dir 会自动从 config 继承（即 `outputs/so101_smolvla_v1-1/`），新 checkpoint 仍保存在同一目录下。

**第 3 阶段：训练 v1-3（20k→30k 步，从 v1-2 续训）**

```bash
HF_HUB_OFFLINE=1 python src/scripts/train.py \
  --resume=true \
  --config_path=outputs/so101_smolvla_v1-1/checkpoints/020000/train_config.json \
  --steps=30000
```

### 关键注意事项

| 事项 | 说明 |
|------|------|
| `--steps` 是总步数 | 从 10k 续到 20k 应设 `--steps=20000`，不是 `--steps=10000` |
| `--config_path` 必须指向 `train_config.json` | 不是 `model.safetensors` 或目录 |
| `batch_size` 保持一致 | 续训时改 batch_size 会导致数据顺序偏移（有警告但不致命） |
| 可在任意 checkpoint 续训 | 不一定是 `last/`，可以是 `010000/`、`020000/` 等 |
| 先推理再决定 | 每个阶段完成后可以先测推理效果，满意再继续训 |

### 时间参考（batch=36, RTX 5070）

| 阶段 | 训练名 | 步数 | 累计步数 | 预计耗时 | 累计耗时 |
|------|--------|------|---------|---------|---------|
| 第 1 阶段 | `v1-1` | 0 → 10,000 | 10k | ~3h | ~3h |
| 第 2 阶段 | `v1-2` | 10,000 → 20,000 | 20k | ~3h | ~6h |
| 第 3 阶段 | `v1-3` | 20,000 → 30,000 | 30k | ~3h | ~9h |

> 最多训到 30k 步。之后如效果仍不满意，考虑用 DAgger 收集纠正数据生成 v2 版数据集，从头重新训练 `v2-1`。

## 训练产出

```text
outputs/so101_smolvla_v1-1/
├── checkpoints/
│   ├── 002000/
│   │   └── pretrained_model/
│   ├── 004000/
│   │   └── pretrained_model/
│   └── 010000/
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
    --dataset.repo_id=local/so101_grape_put_v0-1 \
    --policy.type=act \
    --output_dir=outputs/so101_act
  ```

- 用同一数据集训练 **SmolVLA**（需要把 `front/top` 映射到 `camera1/camera2`）：
  ```bash
  python src/scripts/train.py \
    --dataset.repo_id=local/so101_grape_put_v0-1 \
    --policy.type=smolvla \
    --policy.path=/home/j/ws/so101/checkpoints/smolvla_base_migrated \
    --rename_map='{"observation.images.front": "observation.images.camera1",
      "observation.images.top": "observation.images.camera2"}' \
    --output_dir=outputs/so101_smolvla
  ```

- 合并多组数据训练（如 v1 版 5 组共 50 条）：
  ```bash
  # 第 1 步：物理合并多个数据集
  lerobot-edit-dataset \
    --operation.type=merge \
    --operation.repo_ids='["local/so101_grape_put_v1-1","local/so101_grape_put_v1-2","local/so101_grape_put_v1-3","local/so101_grape_put_v1-4","local/so101_grape_put_v1-5"]' \
    --operation.roots='["/home/j/ws/so101/data/so101_grape_put_v1-1","/home/j/ws/so101/data/so101_grape_put_v1-2","/home/j/ws/so101/data/so101_grape_put_v1-3","/home/j/ws/so101/data/so101_grape_put_v1-4","/home/j/ws/so101/data/so101_grape_put_v1-5"]' \
    --new_repo_id=local/so101_grape_put_v1_merged \
    --new_root=/home/j/ws/so101/data/so101_grape_put_v1_merged

  # 第 2 步：用合并后的单个数据集训练
  python src/scripts/train.py \
    --dataset.repo_id=local/so101_grape_put_v1_merged \
    --dataset.root=/home/j/ws/so101/data/so101_grape_put_v1_merged \
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
