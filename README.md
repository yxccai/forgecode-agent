# ForgeCode Agent

用于学习 Agent 原理与面试演示的终端 Coding Agent。按 `PROJECT_PLAN.md` 逐版开发，源码保留在 `v0/` 到 `v5/`。

当前已实现 **V0**，尚未宣称完成后续版本。

## 安装与运行

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
export OPENAI_BASE_URL=https://your-provider.example/v1
export OPENAI_API_KEY=your-key
export OPENAI_MODEL=your-model
forgecode --repo . '解释 Agent 循环，并引用源码位置'
```

支持 `--base-url`、`--model`、`--reasoning-effort`、`--max-steps`，每次运行可切换。
运行 `forgecode configure` 可交互配置第三方接口，密钥输入不会回显。
也可用 `forgecode configure path/to/config.local.json` 维护不同配置文件。
支持 `FORGECODE_BASE_URL`、`FORGECODE_API_KEY`、`FORGECODE_MODEL`、`FORGECODE_REASONING_EFFORT`，
同名配置优先于 `OPENAI_*` 环境变量。
推理强度原样传给接口，例如 `low`、`medium`、`high`，具体支持值取决于提供商。
不设置则不发送该字段。Key 使用环境变量或被 Git 忽略的本地 JSON 配置，避免写入命令历史。
`--config config.local.json` 可读取 `base_url`、`api_key`、`model`、`reasoning_effort`。
优先级为命令行 > 环境变量 > 配置文件 > 默认值。

终端等待动画表示正在等待模型，不伪造或展示隐藏思维链。正文逐片流式输出。
`forgecode/ui.py` 负责显示；`v0/agent.py` 只产生事件，不依赖 UI。
轨迹位于目标仓库 `.forgecode/traces/`，可能包含源码和工具结果，请勿公开敏感轨迹。

## 学习顺序

1. `v0/tools.py`：工具 schema、路径边界、有限输出和错误反馈。
2. `v0/model.py`：OpenAI Chat Completions SSE、工具参数分片合并。
3. `v0/agent.py`：messages -> model -> tools -> observations -> model。
4. `forgecode/trace.py` 与 `forgecode/ui.py`：同一事件分别用于记录和渲染。

## 验证

```bash
python -m unittest discover -s tests -v
```

测试启动本地 HTTP SSE 服务并实际读取临时仓库，覆盖工具调用参数分片、工具结果回传、流式正文、路径越界和步数预算。
该测试验证运行机制，**不代表真实模型任务成功率**。真实提供商验证和后续版本进展记录在 `docs/`。
