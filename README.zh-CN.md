# Axon Creative Agent

[English](README.md) · [简体中文](README.zh-CN.md)

![Axon Signal——原创且版权安全的参考帧](docs/assets/axon-signal-reference.png)

> **DIRECT —— Codex 负责导演，ComfyUI 负责执行，本地 GPU 负责生成。**

把创意需求交给 Codex。它选择经过梳理的工作流、解释本次运行、检查本地环境，
再让 ComfyUI 在你的 GPU 上生成。首版聚焦带同步立体声音频的 MiniMax H3 视频。

这是本地工作流项目，不是 ComfyUI 安装器、云服务或生产 Web UI。它不会自动下载
模型、把 ComfyUI 暴露到公网，也不会在完成可复现基准前发布性能结论。

## 核心流程

```text
1. 理解需求    Codex 阅读提示词和参考素材
       ↓
2. 选择方案    Skill 选择 Manifest 和运行变体
       ↓
3. 本地生成    ComfyUI 执行，本地 GPU 生成
       ↓
4. 检查结果    执行器核验媒体并记录本次运行
```

Manifest 是 Codex 与 ComfyUI 之间的小型契约，负责映射提示词、种子、输入、依赖、
工作流和输出。未来生图、音频、视频或 3D 工作流可以复用它，无需修改执行器。

## 三条 MiniMax H3 工作流

| 工作流 | 用途 | 输入 |
| --- | --- | --- |
| `minimax-h3-t2v` | 从创意需求直接生成镜头 | 提示词 |
| `minimax-h3-i2v` | 保持主体或构图一致性 | 首帧图片 |
| `minimax-h3-r2v` | 参考身份、运动、镜头或声音 | 图片；视频/音频可选 |

每条工作流都提供可编辑的 `workflow.ui.json`、可执行的 `workflow.api.json` 和
`manifest.json`。

| 变体 | 配置 | 用途 |
| --- | --- | --- |
| `official` | `res_multistep`，20 步 | 质量与速度基线 |
| `turbo` | H3 Turbo，8 步 | 加速采样 |
| `accelerated` | H3 Turbo + Sol-Attn，8 步 | 实验性 RTX 5090 路径 |

## 三步运行

前置条件：Python 3.11+、ComfyUI 0.30.0+、FFmpeg、兼容的 NVIDIA 环境，以及
Manifest 声明的模型和节点。ComfyUI 应监听 `127.0.0.1:8188`。

**第一步：准备 ComfyUI。** 按上游说明安装 ComfyUI，把 H3 权重放入相应模型目录；
只有使用对应变体时才安装 Turbo 和 Sol-Attn。本仓库提供依赖链接，不代替安装器。

**第二步：安装并检查。**

Linux：

```bash
git clone https://github.com/bg-vc/axon-creative-agent.git
cd axon-creative-agent
python3.11 -m venv .venv && source .venv/bin/activate
python -m pip install -e .
export COMFYUI_INPUT_DIR=/opt/ComfyUI/input
axon-creative doctor --variant accelerated
```

Windows PowerShell：

```powershell
git clone https://github.com/bg-vc/axon-creative-agent.git
cd axon-creative-agent
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
$env:COMFYUI_INPUT_DIR = "C:\ComfyUI_windows_portable\ComfyUI\input"
axon-creative doctor --variant accelerated
```

**第三步：先生成一条短片。**

```bash
axon-creative run minimax-h3-t2v --variant accelerated \
  --prompt-file prompts/axon-signal-t2v.txt --seed 20260812

axon-creative run minimax-h3-i2v --variant accelerated \
  --input first-frame=docs/assets/axon-signal-reference.png --seed 20260812

axon-creative run minimax-h3-r2v --variant accelerated \
  --input picture=docs/assets/axon-signal-reference.png \
  --input video=/private/path/motion.mp4 \
  --input audio=/private/path/voice.wav
```

先做 5–10 秒测试。每次运行都会写入被 Git 忽略的
`runs/<run-id>/manifest.json`，记录工作流哈希、种子、耗时、输出、媒体检查和错误。
手动使用 ComfyUI 时，先把参考图复制到它的 input 目录，再加载 UI 工作流。

## 如实做性能基准

**状态：基准协议已完成，尚未发布 RTX 5090 实测结果。**

先补齐 `benchmarks/rtx5090.json` 中所有 `FILL_AFTER_MEASUREMENT`，再运行：

```bash
axon-creative benchmark --suite benchmarks/rtx5090.json
```

每个工作流和变体先预热一次，再正式运行三次。发布时同时给出中位数/最小值/最大值、
准确系统版本、显存峰值和同帧质量对比。环境信息仍是占位值时，CLI 会拒绝执行基准。

## 增加新工作流或 Skill

新增一个包含 `manifest.json` 和 UI/API 工作流的目录，声明全部输入和依赖，并补充
公开样例与测试。不要在执行器中增加模型判断。仓库 Skill 位于
`.agents/skills/run-creative-workflows/SKILL.md`，也遵循“理解、选择、生成、检查”四步。

## 边界、许可与安全

- 仓库代码和原创工作流改造使用 Apache-2.0。
- ComfyUI 模板使用 MIT；模型权重与 LoRA 保留各自条款。
- Sol-Attn 仍属实验性且仓库没有声明许可证；本项目只提供链接，不分发其代码。
- 非本机 ComfyUI 必须显式使用 `--allow-remote`，优先选择 SSH 隧道。不要提交权重、
  私人参考素材、生成媒体或密钥。
- FLUX.3 只有在官方发布、工作流、许可审查和实测全部完成后才会列为已支持。

详见 [THIRD_PARTY.md](THIRD_PARTY.md)、[SECURITY.md](SECURITY.md) 和
[发布文案草稿](docs/launch-posts.md)。私有研发录屏 `0812.mov` 明确不进入本仓库。
