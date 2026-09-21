# ForgeCode 完整使用说明书

适用范围：本仓库 V0–V5，以及后续加入的 `forge` 交互终端与历史浏览功能。
推荐环境：Linux 或 WSL，Python 3.10 及以上，Git。命令执行使用 POSIX 进程组，原生 Windows 未作为受支持环境验证。

## 目录

1. [选择入口](#1-选择入口)
2. [安装与虚拟环境](#2-安装与虚拟环境)
3. [首次启动和工作目录](#3-首次启动和工作目录)
4. [配置接口与模型](#4-配置接口与模型)
5. [交互命令全集](#5-交互命令全集)
6. [一次完整的交互任务](#6-一次完整的交互任务)
7. [历史与恢复](#7-历史与恢复)
8. [隔离模式](#8-隔离模式)
9. [旧版本与测试](#9-旧版本与测试)
10. [评测](#10-评测)
11. [本地数据](#11-本地数据)
12. [故障排查](#12-故障排查)
13. [能力边界](#13-能力边界)

## 1. 选择入口

| 入口 | 用途 | 修改位置 | 验证要求 |
|---|---|---|---|
| `forge` | 连续对话、菜单配置、历史记录 | 指定目录本身 | `/verify` 可选 |
| `forgecode` | 单次、可恢复的隔离编码任务 | `.forgecode/worktrees/<thread>` | 新任务必须传 `--verify` |
| `forgecode-eval` | 批量基准与消融 | 临时测试仓库 | 独立验收器评分 |
| `python -m v0.cli` | 学习只读原始 Agent | 不编辑源码 | 无编码验收 |

初次使用推荐 `forge`。正式演示隔离与可靠执行时使用 `forgecode`。
这两个入口共享大部分核心实现，但不是同一个会话数据库，也不是同一种工作目录策略。

## 2. 安装与虚拟环境

### 2.1 已经使用本机现有项目

在 WSL 终端执行：

```bash
cd /mnt/e/files/project-for-codexinwsl2/forgecode-agent
source .venv/bin/activate
forge
```

激活仅修改当前终端的 PATH，不是全局安装。激活后可 `cd` 到任意目录再运行 `forge`。
新终端需要重新激活；`deactivate` 退出虚拟环境。

也可不激活，直接使用绝对路径：

```bash
/mnt/e/files/project-for-codexinwsl2/forgecode-agent/.venv/bin/forge --repo /path/to/project
```

### 2.2 在另一台 Linux / WSL 机器安装

```bash
git clone https://github.com/yxccai/forgecode-agent.git
cd forgecode-agent
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install -e .
python -m unittest discover -s tests -v
forge --help
```

`requirements.lock` 固定已验证的依赖版本；`-e .` 表示可编辑安装，源码修改后不需要复制到 site-packages。
增加或改变控制台入口、依赖、包配置后需要重新运行 `pip install -e .`。
`venv` 不可直接跨机器搬迁；复制项目后应在目标机器重新创建。

## 3. 首次启动和工作目录

```bash
forge --repo "/path/with spaces/project"
```

不传 `--repo` 就使用当前 shell 目录。启动时打印目标目录、模型和会话 ID。
历史和配置均以这个目录为基础。仅在提示词里说“去另一个目录”不会改变工具的根目录。
目前没有 `/cd`；切换项目应 `/exit` 后重新启动。

没有模型配置也能进入界面。输入 `/api` 后再完成配置即可。
交互模式允许脏目录；请知道自己有哪些未提交改动，它不会自动替你提交或回滚。
主流程面向 Git 仓库；普通目录可做部分读写，但 diff、自动完成记录等 Git 能力不保证可用。

`forge` 启动参数：

| 参数 | 含义 |
|---|---|
| `--repo PATH` | 工作目录 |
| `--config PATH` | 指定交互配置文件 |
| `--windows-env` | 明确从 Windows 读取三个 FORGECODE 变量 |
| `--session ID` | 打开指定历史会话 |
| `--sessions` | 启动时打开历史选择菜单 |

`forge` 没有 `--model` 等单次入口参数，进入后使用 `/model`、`/effort`。

## 4. 配置接口与模型

### 4.1 会话内配置

输入 `/api`，按编号选择：Base URL、API key、Model、Reasoning effort。
例如 Base URL 为 `https://provider.example/v1`，程序在后面拼接 `/chat/completions`。
不要把完整 `/chat/completions` 地址当作 Base URL，否则可能重复拼接路径。

Key 使用隐藏输入，不显示在终端；配置文件仍是本地明文 JSON，不是加密密钥库。
菜单中的“Return without saving”表示改动只在当前进程生效，**不是撤销改动**。
“Save and return”或 `/save` 才会写入文件。

默认保存位置是目标仓库的 `.forgecode/config.local.json`。传了 `--config` 则保存到指定路径。
`/model` 尝试请求 `/models` 列表（需要已有 Key）；接口不支持时可以直接输入模型 ID。
模型列表最多展示 100 项；型号不存在或不支持工具调用，通常会在发起任务时由提供商报错。

`/effort` 提供 `default`、`none`、`minimal`、`low`、`medium`、`high`、`xhigh`。
它们不是每个提供商都支持。`default` 表示不发送 reasoning_effort，交给提供商决定。
推理强度不是温度参数，也不意味着终端会显示模型的隐藏思维链。

### 4.2 配置优先级

| 情形 | 优先级 |
|---|---|
| `forgecode`、V0–V3 CLI | 命令行覆盖 > FORGECODE 环境变量 > OPENAI 环境变量 > JSON > 默认值 |
| `forge` 选定本地配置 | 该 JSON 中存在的字段覆盖环境变量；缺失字段仍可取环境值 |
| `forge` 会话内修改 | 立即覆盖当前进程配置；保存后影响下次启动 |

交互入口优先选择 `--config`，其次目标目录 `.forgecode/config.local.json`；没有这些文件时，
加载器还会检查启动目录中的 `config.local.json`，然后尝试环境变量。
因此“配置文件改了却没生效”要先确认使用的是哪个入口、哪个工作目录。

### 4.3 Windows 环境变量

支持读取 Windows 用户/机器/进程中的 `FORGECODE_API_KEY`、`FORGECODE_BASE_URL`、`FORGECODE_MODEL`。
`forge` 在没有本地配置与模型环境变量时会自动尝试读取；也可显式传 `--windows-env`。
当前桥接只读取这三个变量，推理强度请在菜单或 WSL 环境中设置。
Windows 变量不一定自动出现在 WSL shell 中，这就是桥接存在的原因。

### 4.4 不通过菜单配置

```bash
forgecode configure
forgecode --config config.local.json --repo /path/to/repo \
  --model your-model --reasoning-effort high \
  --verify 'python3 -m unittest discover' '修复测试失败'
```

JSON 字段有 `base_url`、`api_key`、`model`、`reasoning_effort`、`max_steps`、`timeout`。
默认超时 90 秒、最大模型步数 20。不要把真实 Key 写入 Git 或分享配置文件。

## 5. 交互命令全集

| 命令 | 行为 |
|---|---|
| 普通文本 | 启动一轮任务或继续追问 |
| `/help` | 显示命令列表 |
| `/api`、`/config` | 打开 API 设置菜单 |
| `/model` 或 `/model ID` | 菜单选择或直接切换模型 |
| `/effort` 或 `/effort LEVEL` | 菜单选择或直接切换强度 |
| `/url` 或 `/url URL` | 输入或直接更换地址 |
| `/key` | 隐藏输入新密钥 |
| `/save` | 保存模型配置，不保存一个新的任务 |
| `/verify COMMAND` | 设置后续新一轮任务的可信验证命令 |
| `/verify off` | 关闭后续新一轮任务的自动验证 |
| `/status` | 会话 ID、模型、强度和当前验证命令，不显示 Key |
| `/sessions` | 浏览并切换当前目录的历史会话 |
| `/history` | 当前会话的用户/助手消息 |
| `/history all` | 另包含工具请求、结果、运行时反馈 |
| `/resume` | 从持久化中断点继续当前任务 |
| `/new` | 新会话 ID、清空当前对话历史，不删除旧记录或文件改动 |
| `/exit`、`/quit` | 退出 |

模型配置是当前进程级设置，切换历史会话不会恢复该会话当时的模型/Key。
验证命令从被恢复会话的状态加载。`/new` 保留当前进程的模型配置和验证命令。
修改 `/verify` 不会改写一个已经中断任务的验证契约；`/resume` 使用其 checkpoint 中的命令。
当前使用普通单行输入，不提供多行编辑器、自动补全或方向键选择菜单。

## 6. 一次完整的交互任务

```text
forge> /verify python3 -m unittest discover -s tests
forge> 阅读相关源码，修复空输入导致的异常，补充回归测试。
...
Approve? [y/N] y
...
forge> 解释刚才修改的原因，并列出验证结果。
forge> /history
forge> /exit
```

审批中会展示编辑的 path/old/new，或命令的 argv/cwd。
输入 `y` 才允许；空输入、`n` 等均拒绝。拒绝会成为观察反馈，模型可以换方案。
`/verify` 是你预先授权的测试命令，基线和最终验证不会再逐次询问。
测试命令也能执行代码，不应把未知下载脚本当作可信验证命令。

自动验证会先运行基线，再让模型工作；模型没有待执行工具时，运行最终验证。
失败后反馈给模型修复，最多受步数、工具预算和修复次数共同约束。
交互模式不做额外的 Plan 模型调用，但仍复用 V3 的仓库线索和记忆。

| 状态 | 含义 |
|---|---|
| `answered` | 模型本轮不再请求工具；未证明代码正确 |
| `verified` | 指定验证命令退出零且未超时 |
| `verification_failed` | 验证未通过，修复次数或预算不足 |
| `budget_exhausted` | 模型步骤或工具次数等预算耗尽 |
| `running` | 尚在执行或等待恢复；列表状态不能单独判断是否等待审批 |

终端 Thinking 动画表示等待请求；正文是真实流式片段。观察到的片段不是模型内部推理的完整记录。

## 7. 历史与恢复

```bash
forge --repo /path/to/project --sessions
forge --repo /path/to/project --session 82c08580905a
```

会话列表每页 10 项，按更新时间由近到远排列。输入编号或 ID 恢复；`n/p` 翻页，`0` 取消。
默认历史每页 8 条消息；`n/p` 翻页，`q` 返回。恢复时自动显示最近 8 条可见消息。
默认隐藏工具和系统注入的说明，完整排查用 `/history all`，它仍不展示 system prompt。
“Messages”是可见对话消息数，不是 tool calls 数或模型 token 数。
没有提交过任务的空会话不会出现在历史列表。

运行中按 Ctrl+C：当前请求停止，终端保留；随后 `/resume`、`/new` 或 `/exit`。
恢复待审批任务仍会询问审批，不会因为你查看历史就执行命令。
浏览历史不调用模型；不同工作目录的历史不统一合并。
会话 ID 不是全局云账号记录，它只有配合原目录中的数据库才有意义。

预算耗尽的任务不支持交互重置预算后原地继续，当前界面会要求 `/new`。
移动整个仓库后 checkpoint 的绝对根路径可能不匹配，需要新会话；当前没有路径迁移工具。

## 8. 隔离模式

先把目标仓库正常提交，保证干净，再执行：

```bash
forgecode --windows-env --repo /path/to/repo --thread demo \
  --verify 'python3 -m unittest discover -s tests' \
  '修复测试失败，说明实际修改和验证结果'
```

新任务不接受脏仓库，因为 worktree 从 HEAD 创建，不包含你的未提交改动。
不要为了让命令运行而盲目清理自己的文件，应自行检查并提交/暂存需要保留的改动。
V4/V5 的线程 ID 限制为 1–80 个字母、数字、下划线或连字符。

常用参数：

| 参数 | 默认/含义 |
|---|---|
| `--thread ID` | 不传则自动生成 |
| `--resume` | 继续该线程，需要 `--thread` |
| `--verify 'COMMAND'` | 新任务必需；使用参数数组，不经过 shell |
| `--max-steps N` | 默认 20，计划也消耗模型步数 |
| `--max-calls N` | 默认 60，工具调用次数 |
| `--max-tokens N` | 默认 0 不启用；提供商 usage 驱动的软预算 |
| `--max-repairs N` | 默认 3，最终验证失败后的修复轮次 |
| `--no-planning` | 禁用独立计划调用 |
| `--no-repo-context` | 禁用自动仓库大纲和符号工具 |
| `--no-memory` | 禁用记忆检索和工具 |
| `--config`、`--base-url`、`--model`、`--reasoning-effort` | 模型配置 |

恢复命令：

```bash
forgecode --windows-env --repo /path/to/repo --thread demo --resume
```

保持与创建任务相同的功能开关；预算与验证命令来自 checkpoint，不靠恢复参数重置。
`--verify 'pytest && ruff check .'` 不会解释 `&&`。多个步骤应写成自己的可信脚本并运行该脚本。
独立 worktree 不复制原目录的 `.venv`；需要时将验证命令指向虚拟环境 Python 的绝对路径。

完成后检查：

```bash
git -C /path/to/repo/.forgecode/worktrees/demo diff
git -C /path/to/repo apply --check /path/to/repo/.forgecode/tasks/demo.patch
```

确认后可自行 `git apply`，这里不会替你自动合并、提交或推送。
补丁导出包含跟踪文件的变动及允许的新文件；内部文件、部分符号链接等不导出。
检查新文件也可用 `git status --short`，仅看 `git diff` 看不到全部未跟踪文件内容。
worktree 默认保留，清理前确认所需修改已保存；使用 Git 的 worktree 管理命令，不直接删 Git 元数据。

## 9. 旧版本与测试

所有命令在源码根目录并激活 `.venv` 后运行：

```bash
python -m unittest discover -s tests -v
python -m unittest discover -s tests -p 'test_v2.py' -v
python -m v0.cli --config config.local.json --repo . '解释 Agent 循环并引用源码'
```

V0 只读；V1–V3 直接编辑目录；V2/V3 支持 `--pause-after-tool` 与 `--thread ID --resume`。
旧版本 CLI 不支持当前所有菜单和 Windows 参数；请用各自 `--help` 或 WSL 环境变量/JSON。
真实模型脚本包括 `validate_live.py`、`validate_coding.py`、`validate_state.py`、
`validate_repository.py`、`validate_reliable.py`。它们会使用 API；脚本各自参数以源码或 `--help` 为准。
部分脚本固定从 Windows 读取测试配置，不能把它们误当成通用 CLI。

## 10. 评测

```bash
forgecode-eval --suite smoke --config /path/to/config.local.json --out .forgecode/eval-smoke
forgecode-eval --suite matrix --windows-env --workers 3 --out .forgecode/eval-new
python -m v5.report .forgecode/eval-new --output docs/my-report.md
```

`smoke` 为一个任务；`full` 为 20 个任务；`matrix` 为 20 个完整配置任务和 20 个消融任务。
`--repeats` 指定重复次数，`--workers` 范围 1–4，`--variant` 只执行所选配置。
消融任务只在 matrix 中安排，不能期待 `--suite full --variant no_memory` 自动创建消融任务。
输出目录相同且 manifest 匹配时跳过已记录任务，包括已记录失败；重新实验应使用新目录。
报告 JSON 固定写入输出 Markdown 所在目录的 `evaluation-v5.json`，注意别覆盖之前要保留的结果。
本地真实轨迹不会默认提交 Git，公开报告只含配置标识与指标。
评测会消耗 API token，完整方法与结果见 [V5 指南](tutorials/V5.md)。

## 11. 本地数据

| 路径（相对目标仓库） | 内容 |
|---|---|
| `.forgecode/config.local.json` | 交互模型配置，可能含明文 Key |
| `.forgecode/interactive.sqlite` | forge 多轮会话、checkpoint、待审批状态 |
| `.forgecode/state.sqlite` | V2/V3 单次任务状态 |
| `.forgecode/state-v4.sqlite` | V4/V5 单次隔离任务状态 |
| `.forgecode/memory.sqlite` | 跨任务知识笔记，不等于完整对话 |
| `.forgecode/traces/*.jsonl` | 追加事件轨迹，可含源码和输出 |
| `.forgecode/worktrees/` | 隔离工作区 |
| `.forgecode/tasks/` | worktree 清单与补丁 |
| `.forgecode/evaluation*/` | 本地评测输出，具体目录由 --out 决定 |

本项目 `.gitignore` 排除了 `.forgecode`；对别的仓库，不应假设它已自动配置忽略规则。
你需要检查自己的 `.gitignore`，不要把密钥、源码轨迹或 worktree 意外提交。
备份 SQLite 最稳妥的方式是先退出相关进程，再备份数据库和需要保留的工作区。

## 12. 故障排查

| 现象 | 先检查什么 |
|---|---|
| `forge: command not found` | 激活正确 `.venv`；`command -v forge`；重装 `pip install -e .` |
| `No module named ...` | 当前 `python` 与安装依赖的 pip 是否属于同一虚拟环境 |
| `401` / 请求失败 | `/api` 的 Key 与 Base URL；注意接口错误可能仅显示异常类型 |
| `404` | URL 是否重复了 `/v1` 或 `/chat/completions`；模型 ID 是否正确 |
| 模型列表不可用 | 不一定不能聊天；直接 `/model 模型ID` |
| 强度不支持 | `/effort default`，查提供商支持值 |
| 没有工具调用 | 模型是否支持 Chat Completions tool calling，不只是文本生成 |
| Windows 配置没读到 | WSL 能否运行 powershell.exe；变量是否保存到用户或机器环境 |
| 终端没有动画 | 重定向/非 TTY 时会降级为普通流式文本 |
| 历史空白 | 是否选了原工作目录；空会话不会存入列表 |
| 不能新任务 | 待完成节点需要 `/resume`，或 `/new` 开新会话 |
| 测试始终失败 | 测试命令 cwd、依赖、实际失败输出；不要只看模型“已修复” |
| 编辑匹配失败 | old 必须与当前文件唯一精确匹配，重新读文件再尝试 |
| Token 计数缺失 | 提供商未返回 usage，不能把缺失当作零成本 |
| worktree 拒绝创建 | Git 根目录是否正确、有无 HEAD、是否有未提交变动 |
| 原目录出现变动 | 是否使用了直接写目录的 forge/V1–V3，而非 forgecode 隔离入口 |

## 13. 能力边界

worktree、路径检查、审批均不是操作系统安全沙箱。已批准的 Python/测试命令拥有当前用户权限。
工具只支持有限大小的文本；单文件读取上限 500 KB、每次最多 200 行，工具结果会截断。
精确替换不支持专用删除/重命名工具。Python AST 才有符号提取，其它语言以词法线索为主。
检索分词偏英文标识符，中文任务最好同时给出文件名、函数名或异常文本。
命令超时默认 30 秒；大量输出会写临时文件，并非严格磁盘配额控制。
checkpoint 不保证外部副作用恰好执行一次；同一线程不要由多个进程同时操作。
`verified` 只证明给定命令成功，可能受测试不足、测试篡改或零测试发现影响；关键修改应人工审核。

下一步：[零基础学习入口](tutorials/README.md)。
