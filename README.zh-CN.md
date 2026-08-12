# Axon Creative Agent

[English](README.md) · [简体中文](README.zh-CN.md)

![Axon Signal——原创且版权安全的参考帧](docs/assets/axon-signal-reference.png)

> **DIRECT —— Codex 负责导演，ComfyUI 负责执行，本地 GPU 负责生成。**

Axon Creative Agent 是一个小而克制、本地优先的开源工作区，把创意需求
转成可复现的 ComfyUI 运行。Codex 检查参考素材、选择带版本的工作流、解释本次
运行、提交本地 ComfyUI，并核验生成媒体。首版聚焦 RTX 5090 上带原生同步立体声
音频的 MiniMax H3 视频。

固定基准没有跑完之前不发布性能数字；模型权重、私有输入和生成视频都不进入仓库。

## 是什么 / 不是什么

它是：

- 一个仓库级 Codex Skill 和小型 Python 3.11+ 执行器；
- 三条经过梳理的 H3 工作流：文生视频、首帧图生视频、多模态参考生视频；
- 三种可比较变体：`official`、`turbo`、实验性的 `accelerated`；
- 一套未来生图、音频、视频或 3D Skill 都能采用的 Manifest 契约。

它不是：

- ComfyUI/CUDA/模型安装器、托管服务、任务队列或生产 Web UI；
- Axon Imagine 的替代品；后者是完全独立的消费产品；
- “所有显卡或系统都能达到 5090 数据”的承诺；
- FLUX.3 集成。只有官方发布、许可明确、实现并实测后才加入。

## DIRECT 如何工作

```text
创意需求
   ↓
Codex Skill——检查参考素材、选择并解释工作流
   ↓
Manifest——映射提示词、种子、素材、依赖与输出
   ↓
ComfyUI 本地 API——校验、排队、执行、返回历史
   ↓
RTX 5090——本地生成
   ↓
视频 + 立体声音频 + 被 Git 忽略的运行清单
```

执行器使用 `/system_stats`、`/object_info`、`/models/*`、`/upload/image`、
`/prompt`、`/history/{prompt_id}` 和 `/view`。除非显式加入
`--allow-remote`，否则拒绝非本机回环地址。

## 三条 MiniMax H3 工作流

| 工作流 | 使用场景 | 必需输入 |
| --- | --- | --- |
| `minimax-h3-t2v` | 从结构化创意需求直接生成镜头 | 提示词 |
| `minimax-h3-i2v` | 从首帧保持构图或主体一致性 | 图片 |
| `minimax-h3-r2v` | 分别用参考控制身份、风格、运动、镜头或声音 | 图片；视频/音频可选 |

每条工作流都有可拖入 ComfyUI 的 `workflow.ui.json`、执行器提交的
`workflow.api.json` 和 `manifest.json`。三个变体含义明确：

| 变体 | 采样器 | 步数 | Sol-Attn | 用途 |
| --- | --- | ---: | --- | --- |
| `official` | `res_multistep` | 20 | 否 | 质量与速度基线 |
| `turbo` | H3 Turbo | 8 | 否 | 加速采样 |
| `accelerated` | H3 Turbo | 8 | 是 | 实验性 RTX 5090 加速路径 |

公开示例 “Axon Signal” 是本仓库原创角色和环境，替代研发阶段使用现有角色的私有提示词。

## Windows 三步启动

前置条件：RTX 5090、兼容当前驱动/CUDA 的 PyTorch、ComfyUI 0.30.0+、
Git、Python 3.11+，以及用于生成后检查的 FFmpeg。

1. 按上游说明安装 ComfyUI 和两个可选加速节点。模型放进 `doctor` 输出的
   目录；执行器绝不自动下载权重。
2. 在 PowerShell 运行：

```powershell
git clone https://github.com/bg-vc/axon-creative-agent.git
cd axon-creative-agent
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
$env:COMFYUI_INPUT_DIR = "C:\ComfyUI_windows_portable\ComfyUI\input"
axon-creative doctor
```

3. 先生成 5–10 秒测试片，再跑完整基准。

## Linux 三步启动

依赖相同。项目维护 Linux CLI 兼容性，但性能表始终绑定实际产生数据的系统。

```bash
git clone https://github.com/bg-vc/axon-creative-agent.git
cd axon-creative-agent
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
export COMFYUI_INPUT_DIR=/opt/ComfyUI/input
axon-creative doctor
```

ComfyUI 应保持监听 `127.0.0.1:8188`。需要远程使用时优先建立 SSH 隧道。

## 完整命令

```bash
axon-creative workflows
axon-creative doctor

axon-creative run minimax-h3-t2v --variant accelerated \
  --prompt-file prompts/axon-signal-t2v.txt --seed 20260812

axon-creative run minimax-h3-i2v --variant accelerated \
  --input first-frame=docs/assets/axon-signal-reference.png --seed 20260812

axon-creative run minimax-h3-r2v --variant accelerated \
  --input picture=docs/assets/axon-signal-reference.png \
  --input video=/private/path/motion.mp4 \
  --input audio=/private/path/voice.wav
```

每次运行都会写入 `runs/<run-id>/manifest.json`，记录工作流哈希、种子、耗时、
输出哈希、媒体元数据与失败信息。`runs/` 已被 Git 忽略。
CLI 属于仓库级工具：请在克隆目录中运行，或把 `AXON_CREATIVE_ROOT` 指向克隆目录。

## RTX 5090 性能基准

**状态：协议已完成；本仓库尚未产生实测结果。**

基准固定提示词、参考素材、种子、分辨率、帧数和输出；每个工作流/变体先预热一次，
再正式运行三次，最后在被忽略的 `runs/benchmarks/` 下生成 JSON 和 Markdown。
运行前必须补齐真实系统、驱动、CUDA、PyTorch 和节点提交：

```bash
axon-creative benchmark --suite benchmarks/rtx5090.json
```

发布数据时同时给出中位数/最小值/最大值、首次 Triton 编译、热启动端到端耗时、
显存峰值与同帧质量检查。证据出现前，“约二十分钟降到几分钟”只是私人观察，
不是项目对外宣称。

## 增加 Creative Skill

不要为每个模型修改执行器。新增目录：

```text
workflows/<family>/<mode>/
├── manifest.json
├── official/workflow.ui.json
├── official/workflow.api.json
├── turbo/workflow.ui.json
└── turbo/workflow.api.json
```

使用 schema version `1`，声明提示词/种子/素材映射、依赖和输出，提供版权安全输入，
并增加验证测试。独立的仓库 Skill 可以复用同一 CLI 契约。当前 Codex Skill 位于
`.agents/skills/run-creative-workflows/`，符合仓库级 Skills 目录约定。

## 依赖、许可与安全

- 仓库代码、Manifest 和原创工作流改造：Apache-2.0。
- ComfyUI 官方模板：MIT，并保留来源说明。
- MiniMax H3 权重和 Turbo LoRA 各有自己的条款；“开放权重”不等于无限制商用。
- H3 Turbo 自定义节点：Apache-2.0。
- Sol-Attn 集成仍属实验性且仓库当前没有声明许可证，本项目只提供链接，不分发其代码。
- 不提交个人参考素材、权重、密钥、输出或绝对本地路径；发布前人工检查生成媒体。

详见 [THIRD_PARTY.md](THIRD_PARTY.md) 和 [SECURITY.md](SECURITY.md)。

## 非目标与路线图

项目刻意不做安装器、模型管理器、Web UI、云账号、计费、Kubernetes 或远程 GPU
调度。新增能力必须提交可运行 Manifest、实测工作流和明确许可证。生图——可能包括
未来官方发布的 FLUX 版本——在这些证据出现后加入；音频和 3D 同样遵循该门槛。

## 发布说明

> Codex writes code. Here it directs a 5090.

首发视频将使用三条 Axon Signal 工作流制作 25–40 秒原创对比片，并作为 GitHub
Release 资产上传。私有研发录屏 `0812.mov` 明确排除。中英文 X 文案草稿见
[docs/launch-posts.md](docs/launch-posts.md)。
