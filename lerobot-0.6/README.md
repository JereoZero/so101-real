# SO-101 真机项目

> 基于 LeRobot v0.6.0 + 幻尔 SO-101 双臂机械臂的模仿学习项目。
>
> 参考项目：[JereoZero/so101-real](https://github.com/JereoZero/so101-real)

## 项目简介

让 SO-101 机械臂学会自主完成"抓取紫色方块放入盘子"的任务。采用遥操作录制专家数据 → SmolVLA 模仿学习训练 → 语言指令驱动推理的完整流程。

| 项目 | 内容 |
|------|------|
| 任务 | `"put grape block in plate"`（紫色方块 → 白盘子） |
| 硬件 | 幻尔 SO-101 双臂 + 前置/顶部双摄像头 |
| 算法 | SmolVLA（500M VLM backbone + 模仿学习） |
| 框架 | LeRobot **v0.6.0** |
| GPU | NVIDIA RTX 5070 12GB |
| 训练数据 | 199 条 / 52,010 frames（v1-1 ~ v1-20 合并） |

## LeRobot v0.6.0 新特性与本项目的应用

本项目基于 LeRobot v0.6.0，相比参考项目使用的 v0.5.1 有诸多变化。以下是关键差异及本项目如何适配：

### 核心变化

| 类别 | v0.5.1 | v0.6.0 | 本项目适配 |
|------|--------|--------|-----------|
| 真机推理 | `lerobot-eval` | **`lerobot-rollout`** | 使用 `src/scripts/rollout.py` 包装，支持 DAgger/RTC/连续录制 |
| 数据录制 | `repo_id` 原样保存 | **`repo_id` 自动追加时间戳** | 用 `--dataset.root` 指定存储路径，不受时间戳影响 |
| 多数据集训练 | `--dataset.repo_id='["a","b"]'` | **已禁用**（`NotImplementedError`） | 使用 `lerobot-edit-dataset --operation.type=merge` 物理合并 |
| 数据回放 | `lerobot-record --replay` | **`lerobot-replay`** 独立命令 | 使用 `src/scripts/replay.py` 包装 |
| DAgger | 需要自行实现 | **原生支持** | 计划用于人机回环纠错，生成 v2 数据 |
| RTC 推理 | 无 | **`--inference.type=rtc`** | SmolVLA 推理速度慢，需 RTC 实时 chunk 推理 |
| 视频解码 | 默认 `torchcodec` | 默认 `torchcodec`（有兼容问题） | 改用 **`--dataset.video_backend=pyav`** |
| 参数命名 | `--output_dir` | 移除，用 `--output_dir` 仍可 | 训练命名方案：`so101_smolvla_v{version}-{group}` |
| 评估频率 | `eval_freq` | **`env_eval_freq`** | 真机任务设为 `0`（不做仿真评估） |
| 策略命名 | `sac` | **`gaussian_actor`** | - |
| 最小 PyTorch | 2.x | **2.7+** | 当前环境 PyTorch 2.10 |

### 视频解码后端问题（重要）

v0.6.0 默认使用 `torchcodec` 作为视频解码后端，但在当前环境（Ubuntu 22.04 + conda）中因 `libstdc++` CXXABI 版本不兼容（需要 `CXXABI_1.3.15`，系统仅 `1.3.13`），导致训练卡在 0% 不动。

**解决方案**：所有训练命令必须加 `--dataset.video_backend=pyav`，使用 PyAV 后端替代。

```bash
# 错误：默认 torchcodec 会卡住
--dataset.video_backend=torchcodec  # ← 不要用

# 正确：使用 pyav
--dataset.video_backend=pyav  # ← 必须加这个
```

> 详见 [07-troubleshooting.md](docs/07-troubleshooting.md) 第 13 节。

### 数据合并方式变化

v0.5.x 可以在训练时直接传多个 `repo_id`：

```bash
# v0.5.x 方式（v0.6.0 已不可用）
--dataset.repo_id='["local/dataset_a","local/dataset_b"]'
```

v0.6.0 必须先用 `lerobot-edit-dataset` 物理合并：

```bash
# v0.6.0 方式：先合并，再训练
lerobot-edit-dataset \
  --operation.type=merge \
  --operation.repo_ids='["local/dataset_a","local/dataset_b"]' \
  --operation.roots='["/path/to/a","/path/to/b"]' \
  --new_repo_id=local/dataset_merged \
  --new_root=/path/to/dataset_merged

# 训练时用单个 repo_id
--dataset.repo_id=local/dataset_merged
```

## 目录结构

```
/home/j/ws/so101/
├── apply_patches.py          # 自动把 SO-101 patch 应用到 LeRobot 源码
├── README.md                 # 本文件
├── docs/                     # 详细操作步骤文档
│   ├── README.md
│   ├── 01-hardware-setup.md
│   ├── 02-calibration.md
│   ├── 03-teleoperation.md
│   ├── 04-recording.md
│   ├── 05-training.md
│   ├── 06-inference.md
│   └── 07-troubleshooting.md
├── patches/                  # 补丁相关说明（实际 patch 逻辑在 apply_patches.py）
├── src/
│   ├── configs/
│   │   ├── so101.yaml        # SO-101 自定义配置（gitignore，含设备 ID）
│   │   └── so101.yaml.example  # 配置模板（上传用，不含真实 ID）
│   ├── scripts/
│   │   ├── teleoperate.py    # 遥操作测试
│   │   ├── record.py         # 数据录制（自动从 yaml 加载端口/相机/固定关节）
│   │   ├── train.py          # 训练
│   │   ├── replay.py         # 数据回放验证
│   │   ├── rollout.py        # 真机推理/部署（lerobot-rollout 包装）
│   │   ├── eval.py           # 仿真评估（lerobot-eval 包装）
│   │   ├── check_data.py     # 数据质量检查
│   │   ├── eval_stats.py     # 成功率统计
│   │   └── merge_v1.py       # v1 数据集合并
│   └── utils/
│       └── __init__.py
├── data/                     # 录制数据集（gitignore）
├── outputs/                  # 训练输出（gitignore）
└── checkpoints/              # 模型检查点（gitignore）
```

## 环境准备

```bash
unset PYTHONPATH
conda activate lerobot
cd /home/j/ws/so101
```

LeRobot 源码位于 `/home/j/ws/repos/lerobot`，已通过 `pip install -e /home/j/ws/repos/lerobot` 以 editable 模式安装到当前环境。

## 应用 SO-101 Patch

```bash
cd /home/j/ws/so101
python apply_patches.py
```

这会修改 `/home/j/ws/repos/lerobot` 中的以下文件：

| 文件 | 修改内容 |
|------|----------|
| `config_so_follower.py` | 新增 `fixed_joints` 字段，恢复 v0.5.1 固定关节能力 |
| `so_follower.py` | `wrist_roll` 参与校准；范围裁剪到 `[0, 4095]`；`send_action` 中覆盖 `fixed_joints`；夹爪扭矩改为 100% |
| `so_leader.py` | `wrist_roll` 参与校准；范围裁剪到 `[0, 4095]`；适配 v0.6.0 电机列表类型 |
| `lerobot_record.py` | 修复复位阶段 teleop 控制失效；**录制时记录从臂实际执行的 action（含 fixed_joints 覆盖），而非主臂原始 action** |
| `feetech.py` | `enable_torque` / `disable_torque` 增加通信失败容错，避免单电机失败导致整体流程崩溃 |

> 由于使用 editable 安装，patch 后无需重新安装。

## 常用命令

### 1. 查找串口

```bash
lerobot-find-port
```

### 2. 遥操作测试

```bash
python src/scripts/teleoperate.py
```

> `fixed_joints`、端口、摄像头等配置已写入 `src/configs/so101.yaml`，脚本启动时自动加载。

### 3. 录制数据

```bash
python src/scripts/record.py \
  --display_data=true \
  --dataset.repo_id=local/so101_grape_put_v1-1 \
  --dataset.root=/home/j/ws/so101/data/so101_grape_put_v1-1 \
  --dataset.push_to_hub=false \
  --dataset.num_episodes=10 \
  --dataset.single_task="put grape block in plate" \
  --dataset.episode_time_s=60 \
  --dataset.reset_time_s=9999
```

> 端口、摄像头、fixed_joints 从 `so101.yaml` 自动加载，只需指定 `--dataset.*` 参数。
> v0.6.0 会自动在 `repo_id` 后追加时间戳，但数据仍保存到 `--dataset.root` 指定的路径。

### 4. 训练 SmolVLA

```bash
HF_HUB_OFFLINE=1 python src/scripts/train.py \
  --policy.path=checkpoints/smolvla_base_migrated \
  --policy.use_amp=true \
  --policy.n_obs_steps=4 \
  --dataset.repo_id=local/so101_grape_put_v1_merged \
  --dataset.root=data/so101_grape_put_v1_merged \
  --dataset.video_backend=pyav \
  --dataset.image_transforms.enable=true \
  --output_dir=outputs/so101_smolvla_v1-1 \
  --steps=10000 \
  --batch_size=36 \
  --save_freq=2000 \
  --env_eval_freq=0 \
  --rename_map='{"observation.images.front": "observation.images.camera1",
    "observation.images.top": "observation.images.camera2"}'
```

> ⚠️ **必须加 `--dataset.video_backend=pyav`**，否则 torchcodec CXXABI 不兼容导致训练卡住。
> 训练采用分阶段命名：`v1-1`（0→10k）→ `v1-2`（10k→20k resume）→ `v1-3`（20k→30k resume）。

### 5. 推理

```bash
python src/scripts/rollout.py \
  --strategy.type=base \
  --policy.path=outputs/so101_smolvla_v1-1/checkpoints/010000/pretrained_model \
  --task="put grape block in plate" \
  --duration=60
```

> 慢速 VLA 模型建议加 `--inference.type=rtc` 启用实时 chunk 推理。

## 训练方案

### 命名规则

| 训练名 | 数据版本 | 训练轮次 | 步数范围 |
|--------|---------|---------|---------|
| `so101_smolvla_v1-1` | v1 | 第 1 版 | 0 → 10,000 |
| `so101_smolvla_v1-2` | v1 | 第 2 版（续训） | 10,000 → 20,000 |
| `so101_smolvla_v1-3` | v1 | 第 3 版（续训） | 20,000 → 30,000 |
| `so101_smolvla_v2-1` | v2（含 DAgger） | 第 1 版（从头训） | 0 → N |

### 分阶段训练

使用 `--resume=true` + `--config_path` 从 checkpoint 续训：

```bash
# 从 v1-1 续训到 v1-2
HF_HUB_OFFLINE=1 python src/scripts/train.py \
  --resume=true \
  --config_path=outputs/so101_smolvla_v1-1/checkpoints/010000/train_config.json \
  --steps=20000
```

> `--steps` 是**总步数**而非增量步数。从 10k 续到 20k 应设 `--steps=20000`。

### DAgger 迭代流程（计划中）

1. 部署 v1 模型进行推理
2. 模型出错时人类接管纠正（DAgger 人机回环）
3. 纠正数据作为 v2 版数据集
4. 合并 v1 + v2 数据，从头训练 `v2-1`

## 下一步

详细操作步骤见 [docs/README.md](docs/README.md)：

1. [硬件连接与上电](docs/01-hardware-setup.md)
2. [机械臂校准](docs/02-calibration.md)
3. [遥操作测试](docs/03-teleoperation.md)
4. [数据录制](docs/04-recording.md)
5. [模型训练](docs/05-training.md)
6. [推理部署](docs/06-inference.md)
7. [常见问题排查](docs/07-troubleshooting.md)

---

## AI 新会话接手指南

> 新开一个 AI 对话框时，让它读这个 README + `docs/` 下的文档就能接手。以下是最关键的信息。

### 1. 环境

```bash
unset PYTHONPATH          # 必须！否则会加载 ros2 环境的 PYTHONPATH 污染
conda activate lerobot    # LeRobot v0.6.0 装在 lerobot 这个 conda 环境里
cd /home/j/ws/so101
```

- LeRobot 源码：`/home/j/ws/repos/lerobot`，editable 安装（`pip install -e`）
- 用户是 **Mac 远程 SSH 连 Ubuntu 主机**，Ubuntu 本机有 HTTP 代理（端口见本地环境配置）
- 多 conda 环境：`ros2_humble`、`lerobot`、`isaac`，切换时注意 PYTHONPATH 污染

### 2. 核心决策（本项目的特殊点）

| 决策 | 内容 |
|------|------|
| LeRobot 版本 | **v0.6.0**（参考项目是 v0.5.1，命令/参数不兼容） |
| 任务 | `"put grape block in plate"`（紫色方块 -> 白盘子） |
| 目标物体 | 仅紫色方块，无干扰物（简化版） |
| wrist_roll | 固定 `-27.82°`，从 `src/configs/so101.yaml` 自动加载 |
| 数据命名 | `v{version}-{group}`，如 `v1-1`（第1版第1组，每组10条） |
| 训练命名 | `so101_smolvla_v{version}-{group}`，同数据命名规则 |
| SmolVLA 格式 | 录制用 `front`/`top`，训练时 `--rename_map` 映射到 `camera1`/`camera2` |
| 已下载模型 | `checkpoints/smolvla_base_migrated`（迁移后的官方 SmolVLA 预训练） |
| 视频后端 | 必须用 `--dataset.video_backend=pyav`，torchcodec 有 CXXABI 兼容问题 |

### 3. 已应用的 Patch（必须知道）

`apply_patches.py` 修改了 `/home/j/ws/repos/lerobot` 源码：
- `config_so_follower.py`：新增 `fixed_joints` 字段
- `so_follower.py`：`wrist_roll` 校准 + 范围裁剪 `[0,4095]` + `send_action` 覆盖 fixed_joints + 夹爪扭矩 100%
- `so_leader.py`：同上适配
- `lerobot_record.py`：修复复位阶段 teleop 控制失效 + 录制时记录从臂实际 action
- `feetech.py`：通信失败容错

> 如果源码被 `git checkout` 或重装覆盖，需要重新 `python apply_patches.py`

### 4. 关键坑点

1. **PYTHONPATH 污染**：切换 conda 环境后必须 `unset PYTHONPATH`，否则 import 混乱
2. **fixed_joints 不生效**：CLI 传 `--robot.fixed_joints=` 可能被 draccus 解析失败，已改为从 yaml 自动加载
3. **录制必须加 `--teleop.*`**：否则复位阶段从臂不跟随（已通过 yaml 自动加载解决）
4. **v0.6.0 时间戳**：`repo_id` 自动追加时间戳，训练用实际生成的名字或 `--dataset.root`
5. **SmolVLA 相机键名**：必须是 `observation.images.camera1`/`camera2`，录制用 `front`/`top` 需 rename_map
6. **torchcodec 卡死**：必须用 `--dataset.video_backend=pyav`，详见 [07-troubleshooting.md](docs/07-troubleshooting.md)
7. **多数据集已禁用**：v0.6.0 不支持列表式多数据集，必须先用 `lerobot-edit-dataset --operation.type=merge` 合并
8. **断网/代理**：GitHub 访问慢时配置本机 HTTP 代理，或使用镜像 `ghfast.top`

### 5. 当前进度

- [x] 硬件连接、校准、遥操作（wrist_roll 锁定 -27.82°）
- [x] 录制/训练/推理流程设计完成
- [x] 数据录制完成：v1-1 ~ v1-20 共 **199 条** / 52,010 frames
- [x] 数据合并完成：`so101_grape_put_v1_merged`
- [x] torchcodec 问题已解决（改用 `--dataset.video_backend=pyav`）
- [x] 1000 步测试训练通过（batch=36 显存 ~10.1GB）
- [x] 训练命名方案：`v1-1`（0→10k）→ `v1-2`（10k→20k）→ `v1-3`（20k→30k）
- [ ] **正式训练 SmolVLA v1-1**（batch=36, 10k 步, ~3h）
- [ ] 推理部署 + 成功率验证
- [ ] DAgger 迭代（如需，生成 v2 数据重新训练）

### 6. 新会话第一句话建议

> "读 `/home/j/ws/so101/README.md` 和 `docs/` 下所有文档，特别是 AI 接手指南章节，然后告诉我当前进度和下一步该做什么。"
