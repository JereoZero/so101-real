# 6. 模型训练

## 预训练模型准备

由于训练机器网络不通，需手动准备：

1. 在能上网的机器访问 HuggingFace，下载 `lerobot/smolvla_base`
   - 文件：`model.safetensors`（906MB）+ `config.json`
2. U 盘拷贝到训练机器 `/home/jer/ws/workspace/models/smolvla_base/`
3. 执行模型迁移（migrate），补齐 normalizer 信息：

```bash
cd ~/workspace/projects/lerobot
python src/lerobot/processor/migrate_policy_normalization.py \
    --pretrained-path /home/jer/ws/workspace/models/smolvla_base
```

迁移后路径：`/home/jer/ws/workspace/models/smolvla_base_migrated/`

## 训练命令（最终 V3 版本）

下面是本项目最终使用的训练命令。V3 相比之前版本新增了混合精度、多帧输入和图像增强。

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
    --rename_map='{"observation.images.front": "observation.images.camera1",
      "observation.images.top": "observation.images.camera2"}'
```

### 关键配置说明

| 参数 | 值 | 说明 |
|------|-----|------|
| `HF_HUB_OFFLINE=1` | 环境变量 | 离线模式，禁止 HuggingFace 联网 |
| `--policy.path` | 本地路径 | 从本地迁移后的预训练模型加载 |
| `--policy.load_vlm_weights` | false | VLM 权重不加载（从预训练继承） |
| `--policy.use_amp` | true | bfloat16 混合精度训练 |
| `--policy.n_obs_steps` | 4 | 连续 4 帧历史信息 |
| `--dataset.streaming` | false | 不从网络流式加载数据集 |
| `--dataset.image_transforms` | true | 轻量图像增强 |
| `--wandb.enable` | false | 禁用 wandb 在线日志 |
| `--rename_map` | front→camera1, top→camera2 | 数据集用 front/top，模型期望 camera1/camera2 |
| `--batch_size` | 36 | 大 batch 加速收敛 |
| `--save_freq` | 2000 | 每 2000 步保存一个 checkpoint |

## 三轮训练过程

训练不是一次完成的，经历了三轮迭代：

| 轮次 | 输出目录 | 步数 | batch_size | save_freq | 说明 |
|------|----------|------|------------|-----------|------|
| 第1轮 | `smolvla210` | 10000→25000 | 8 | 1000 | 首次训练验证流程 |
| 第2轮 | `smolvla210_40000` | 40000 | 8 | 2000 | 从头训练到 40000 步 |
| 第3轮 | `smolvla_v3_run2` | 40000 | **36** | 2000 | V3 版，大 batch 加速收敛 |

### 第1轮（验证流程）

初始步数设为 10000 步，目的是快速验证训练流程没问题。验证通过后继续训练到 25000 步。此轮 checkpoint 保存频率为每 1000 步。

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
    --rename_map='{"observation.images.front": "observation.images.camera1",
      "observation.images.top": "observation.images.camera2"}'
```

生成的检查点：
```
checkpoints/010000, 012000, 014000, 016000, 018000,
checkpoints/020000, 022000, 024000, 025000
```

### 第2轮（从零重训 40000 步）

由于 LeRobot 框架的 resume 功能存在 Bug（checkpoint 未保存 optimizer 配置），无法从 25000 步继续训练到 40000 步。解决方式是：不使用 `--resume`，而是从头开始新一轮训练，目标 40000 步，__save_freq 改为 2000__。

### 第3轮（V3，大 batch）

在第2轮基础上优化，batch_size 从 8 大幅提升到 36。大 batch 虽单步计算量增大但收敛更快：

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
    --rename_map='{"observation.images.front": "observation.images.camera1",
      "observation.images.top": "observation.images.camera2"}'
```

训练速度：
- batch_size=8：~3.3 step/s，40000 步约 3.3 小时
- batch_size=36：~1.0 step/s，40000 步约 11 小时（RTX 5070 12GB 满载）

V3 相比 V1/V2 的主要增强：
- `use_amp=true`：开启 bfloat16 混合精度，节省显存
- `n_obs_steps=4`：使用连续 4 帧历史信息，增强时序感知
- `image_transforms.enable=true`：轻量图像增强（亮度/对比度 ±10%），提升泛化能力
- `batch_size=36`：大 batch 加速收敛

## 训练产出

| 用途 | 模型路径 | 来源 |
|------|----------|------|
| V1/V2 推理 | `smolvla210/checkpoints/025000` | 第1轮 |
| 重训参考 | `smolvla210_40000/checkpoints/040000` | 第2轮 |
| V3 推理 | `smolvla_v3_run2/checkpoints/040000` | 第3轮 |

## 数据与模型的命名映射

由于录制数据集使用 `front` / `top` 作为摄像头名称，而 SmolVLA 预训练模型期望 `camera1` / `camera2`，训练时通过 `--rename_map` 做映射。这是本项目中数据与模型之间的关键适配点。