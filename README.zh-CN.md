# Axon Creative Agent

[English](README.md) · [简体中文](README.zh-CN.md)

![Axon Creative Agent——Codex 编排 Skills、工具与算力](docs/assets/axon-creative-agent-hero.webp)

> **DIRECT —— Codex 负责导演，ComfyUI 负责执行，云端 GPU 负责生成。**

Codex 在用户电脑上充当创意总助手：选择并解释经过梳理的工作流、协助准备 ComfyUI、
把参考素材发送到云端 GPU、等待生成，再把结果带回本地检查。首版聚焦带同步立体声
音频的 MiniMax H3 视频。

本项目不是 GPU 云平台、托管 ComfyUI 服务、安装器或生产 Web UI；它不会自动下载
模型，也不会把 ComfyUI 暴露到公网。

## 核心流程

```text
用户本地电脑                         云端 RTX 5090
Codex 创意总助手
  → 理解创意需求
  → 选择 UI/API 工作流
  → 通过 SSH 上传参考素材       ───→  ComfyUI 生成
  → 下载并检查结果              ←───  视频 + 运行清单
```

UI JSON 用于第一次跑通和理解工作流；确认它能在 ComfyUI 运行后，再用对应 API JSON
完成可重复自动化。

## 第一次运行：把工作流拖进 ComfyUI

先在用户电脑克隆仓库，并一次性安装 CLI：

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

1. 让 Codex 根据需求选择 T2V、I2V 或 R2V。默认推荐展示 RTX 5090 的
   `accelerated`，它需要 H3 Turbo 和 Sol-Attn。
2. 输出准确的工作流和依赖：

```bash
axon-creative inspect minimax-h3-t2v --variant accelerated
```

3. 通过 SSH 隧道访问云端 ComfyUI，把输出的 `workflow.ui.json` 直接拖进页面。

```bash
ssh -N -L 8188:127.0.0.1:8188 axon-5090
```

保持隧道运行，在本地浏览器打开 `http://127.0.0.1:8188`。

使用仓库自带的 I2V/R2V 样例时，先把 `docs/assets/axon-signal-reference.png`
复制到 `ComfyUI/input/`；也可以在 `LoadImage` 节点中选择自己的图片。

4. 根据 ComfyUI Manager 提示安装缺失自定义节点；缺少核心节点时先更新 ComfyUI。
   把 `inspect` 列出的每个模型放入对应 `ComfyUI/models/<目录>`。
5. 重启 ComfyUI、重新载入 JSON，先生成 5–10 秒测试片，再进入自动化。

[工作流索引](docs/workflows.md)直接链接全部九份可拖拽 JSON。如果 ComfyUI 没有给出
模型提示，以 Manifest/`inspect` 的文件名、目录和下载链接为准。

## 一次性配置云端

云端主机使用 Linux，并通过 `~/.ssh/config` 中的 alias 访问。在云端克隆相同提交、
创建 `.venv`、安装本项目，并让 ComfyUI 只监听云端回环地址 `127.0.0.1:8188`。

```bash
ssh axon-5090
git clone https://github.com/bg-vc/axon-creative-agent.git /workspace/axon-creative-agent
cd /workspace/axon-creative-agent
python3.11 -m venv .venv
.venv/bin/python -m pip install -e .
```

在用户本地电脑保存 Profile 并测试 SSH：

```bash
axon-creative cloud init --profile cloud5090 --ssh-host axon-5090 \
  --remote-repo /workspace/axon-creative-agent \
  --comfy-input-dir /workspace/ComfyUI/input

axon-creative cloud doctor --profile cloud5090 \
  --workflow-id minimax-h3-t2v --variant accelerated
```

被 Git 忽略的 `.axon-creative/profiles.toml` 只保存 SSH alias 和云端路径；密码与私钥
仍由系统 SSH 管理。`cloud doctor` 检查所选工作流需要的 SSH、仓库版本、云端目录、
ComfyUI、节点和模型。它只报告问题，不自动安装，也不会静默切换模型。

## 由本地 Codex 发起生成

```bash
axon-creative cloud run --profile cloud5090 \
  minimax-h3-t2v --variant accelerated \
  --prompt-file prompts/axon-signal-t2v.txt --seed 20260812

axon-creative cloud run --profile cloud5090 \
  minimax-h3-i2v --variant accelerated \
  --input first-frame=docs/assets/axon-signal-reference.png --seed 20260812

axon-creative cloud run --profile cloud5090 \
  minimax-h3-r2v --variant accelerated \
  --input picture=docs/assets/axon-signal-reference.png \
  --input video=/private/path/motion.mp4 \
  --input audio=/private/path/voice.wav
```

命令只上传本次运行的素材，在云端调用同一个 API 执行器，再把包含视频和 Manifest 的
`runs/<run-id>/` 下载回本地。下载成功后清理临时上传；运行成功后同时清理复制到
ComfyUI 的输入。失败也会在本地生成带有明确原因的运行清单。

## 工作流与变体

| 工作流 | 用途 | 输入 |
| --- | --- | --- |
| `minimax-h3-t2v` | 从创意需求直接生成镜头 | 提示词 |
| `minimax-h3-i2v` | 保持主体或构图一致性 | 首帧图片 |
| `minimax-h3-r2v` | 参考身份、运动、镜头或声音 | 图片；视频/音频可选 |

| 变体 | 配置 | 用途 |
| --- | --- | --- |
| `official` | `res_multistep`，20 步 | 质量与速度基线 |
| `turbo` | H3 Turbo，8 步 | 加速采样 |
| `accelerated` | H3 Turbo + Sol-Attn，8 步 | 实验性 RTX 5090 路径 |

每种模式/变体都有 `workflow.ui.json`、`workflow.api.json` 和共享 Manifest；自动验证
保证三者的模型名称和加速节点保持一致。

## 如实做性能基准

**状态：基准协议已完成，尚未发布 RTX 5090 实测结果。** 先补齐
`benchmarks/rtx5090.json` 中的云服务商、实例类型、系统、驱动、CUDA、PyTorch 和
提交占位值，再在云端运行：

```bash
axon-creative benchmark --suite benchmarks/rtx5090.json
```

每个工作流/变体先预热一次，再正式运行三次。发布时同时给出中位数/最小值/最大值、
准确环境、显存峰值和同帧质量对比；占位数据未清理时 CLI 会拒绝运行。

## 边界、许可与扩展

- 仓库代码和原创工作流改造使用 Apache-2.0。
- ComfyUI 模板使用 MIT；模型和 LoRA 保留各自条款。
- Sol-Attn 属于实验性能力且仓库当前未声明许可证；本项目只提供链接，不分发其代码。
- SSH 主机密钥校验保持开启。不要公开 ComfyUI，也不要提交模型、私人素材、生成媒体、
  Profile 或密钥。
- 新的生图、音频、视频或 3D 能力必须提供 UI/API JSON、Manifest、版权安全样例、
  依赖链接和测试，不在执行器中增加模型分支。FLUX.3 发布、许可和实测前不列为已支持。

本地 GPU 仍可通过 `axon-creative run` 兼容运行，但文档以云端 GPU 为主路径。详见
[THIRD_PARTY.md](THIRD_PARTY.md)、[SECURITY.md](SECURITY.md) 和
[发布文案草稿](docs/launch-posts.md)。
