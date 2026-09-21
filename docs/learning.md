# 从 V0 到 V5 的学习路线

需要零基础逐函数解析、练习与面试问答，请从 [详细源码课程](tutorials/README.md) 开始。
日常操作见 [完整使用手册](USER_MANUAL.md)。本文保留为简短路线图。

建议每版先看核心、再看验证脚本，最后看 UI。终端效果不是 Agent 决策逻辑的一部分。

| 版本 | 核心入口 | 要回答的问题 | 实际证据 |
|---|---|---|---|
| V0 | v0/agent.py | 模型如何请求工具、工具结果如何回传？ | 分片 SSE、本地文件读取、真实模型引用源码 |
| V1 | v1/tools.py | 编辑失败、命令失败如何反馈给模型？ | 实际修改、运行测试、查看 diff |
| V2 | v2/agent.py | 为什么需要图、状态和 checkpoint？ | 两个独立进程暂停与恢复 |
| V3 | v3/repository.py | 哪些源码需要进入上下文？ | 102 文件索引中模型只读取 2 个目标文件 |
| V4 | v4/agent.py | 谁决定任务完成，谁允许执行命令？ | 验证失败回到修复、持久审批、worktree |
| V5 | v5/evaluate.py | 机制增加复杂度后是否实际有收益？ | 配对消融、独立验收与真实 token 数据 |

## 不应混用的概念

| 概念 | 项目中的具体对象 | 生命周期 |
|---|---|---|
| Context | context() 选择后发送给模型的消息 | 一次模型请求 |
| State | messages、plan、pending、cursor、预算计数 | 一个任务线程 |
| Checkpoint | state.sqlite 中节点执行后的快照 | 可跨进程恢复 |
| Memory | memory.sqlite 中来源可追踪的笔记 | 跨任务，但需要验证新鲜度 |

## 适合讲清楚的取舍

1. V0 不用 Agent 工厂，显式看到协议；V1 只复用消息、工具与模型适配。
2. V2 引入 LangGraph 是为了控制流与恢复，而不是仅为了多用一个框架。
3. V3 先用路径、词法、AST；没有证据支持向量数据库时不引入。
4. V4 的 worktree 不等于安全沙箱，checkpoint 不等于工具副作用 exactly-once。
5. 验证命令退出零不等于绝对正确。V5 额外提供独立用例和重构结构约束。
6. 小任务上的额外计划可能只有开销。负结果应公开，而不是换任务直到看起来有收益。

## 重现路径

先运行 `python -m unittest discover -s tests -v`，覆盖确定性机制。
再设置自己的接口配置，运行 `forgecode-eval --suite smoke --config config.local.json`。
查看 `.forgecode/evaluation/traces/` 的 JSONL，依次对照模型调用、工具结果、验证结果与最终指标。
真实 API 输出有随机性；重新运行的结果不必与已提交报告完全一致。

历史源码保留在版本目录；公共配置与 UI 由最新版共享。Git 中每版的独立提交保存当时完整快照，
用于对照演进，不要求安装多套依赖让所有旧版本同时长期兼容。
