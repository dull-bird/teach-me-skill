# Teach Me Codex / Kimi 终端 E2E 质量报告

- 生成时间：`2026-07-10T18:58:33+08:00`
- 测试轮数：`1`
- 不同场景：`10`
- 总执行数：`20`
- 驱动方式：Python 标准库 `pty` 启动真实 CLI；每个场景隔离 `TEACH_ME_HOME` 与 Vault。
- 评分维度：触发决策 40%、内容相关性 30%、提问打扰度 20%、Hook 提示紧凑度 10%。

## 汇总

| Agent | 模型 | Context | 场景次数 | 成功退出 | 决策正确 | 平均分 | 平均耗时 | 平均 Token |
|---|---|---|---:|---:|---:|---:|---:|---:|
| codex | `gpt-5.6-sol` | short | 10 | 10 | 10 | 94.0 | 65.4s | 24499 |
| kimi | `kimi-code/kimi-for-coding` | short | 10 | 10 | 9 | 89.0 | 28.9s | - |

## 自动质量信号

- 不必要教学：`0` 次。
- 应教未教：`1` 次。
- 单次回答超过一个问句：`2` 次。
- 正例相关关键词命中不足：`2` 次。

## 逐场景结果

| 轮次 | Agent | 模型 | 场景 | 任务完成 | 应教学 | 实际教学 | 问句 | 关键词 | 分数 | 退出码 |
|---:|---|---|---|---|---|---|---:|---|---:|---:|
| 1 | codex | `gpt-5.6-sol` | 边界条件调试 | 是 | 是 | 是 | 1 | 索引 | 85 | 0 |
| 1 | codex | `gpt-5.6-sol` | 配置语义修改 | 是 | 是 | 是 | 1 | 配置、单位 | 100 | 0 |
| 1 | codex | `gpt-5.6-sol` | 小型数据分析 | 是 | 是 | 是 | 0 | - | 70 | 0 |
| 1 | codex | `gpt-5.6-sol` | 明确拒绝教学 | 是 | 否 | 否 | 0 | - | 100 | 0 |
| 1 | codex | `gpt-5.6-sol` | 显式教学请求 | 是 | 是 | 是 | 1 | 依赖、注入 | 100 | 0 |
| 1 | codex | `gpt-5.6-sol` | 纯机械改名 | 是 | 否 | 否 | 0 | - | 100 | 0 |
| 1 | codex | `gpt-5.6-sol` | 可变默认参数 | 是 | 是 | 是 | 1 | 默认、共享 | 100 | 0 |
| 1 | codex | `gpt-5.6-sol` | 重复逻辑重构 | 是 | 是 | 是 | 1 | 重构 | 85 | 0 |
| 1 | codex | `gpt-5.6-sol` | 状态机理解 | 是 | 是 | 是 | 1 | 状态、转换 | 100 | 0 |
| 1 | codex | `gpt-5.6-sol` | 无价值的命令失败 | 是 | 否 | 否 | 0 | 不可用 | 100 | 0 |
| 1 | kimi | `kimi-code/kimi-for-coding` | 边界条件调试 | 是 | 是 | 是 | 1 | 索引 | 85 | 0 |
| 1 | kimi | `kimi-code/kimi-for-coding` | 配置语义修改 | 是 | 是 | 否 | 0 | - | 30 | 0 |
| 1 | kimi | `kimi-code/kimi-for-coding` | 小型数据分析 | 是 | 是 | 是 | 1 | 平均、异常、18 | 100 | 0 |
| 1 | kimi | `kimi-code/kimi-for-coding` | 明确拒绝教学 | 是 | 否 | 否 | 0 | - | 100 | 0 |
| 1 | kimi | `kimi-code/kimi-for-coding` | 显式教学请求 | 是 | 是 | 是 | 2 | 依赖、注入 | 95 | 0 |
| 1 | kimi | `kimi-code/kimi-for-coding` | 纯机械改名 | 是 | 否 | 否 | 0 | - | 100 | 0 |
| 1 | kimi | `kimi-code/kimi-for-coding` | 可变默认参数 | 是 | 是 | 是 | 2 | 可变、默认、共享、状态 | 95 | 0 |
| 1 | kimi | `kimi-code/kimi-for-coding` | 重复逻辑重构 | 是 | 是 | 是 | 1 | 重复 | 85 | 0 |
| 1 | kimi | `kimi-code/kimi-for-coding` | 状态机理解 | 是 | 是 | 是 | 1 | 状态、转换 | 100 | 0 |
| 1 | kimi | `kimi-code/kimi-for-coding` | 无价值的命令失败 | 是 | 否 | 否 | 0 | 不可用 | 100 | 0 |

## 失败与低分样本

### kimi / kimi-code/kimi-for-coding / 配置语义修改 / round 1

预期：虽修改很小，但单位和配置语义具有可迁移价值。

自动评估：`{"review_happened": false, "blocked": false, "decision_correct": false, "keyword_hits": [], "relevance": 0.0, "question_count": 0, "annoyance": 1.0, "compact_prompt": true, "task_completed": true, "score": 30, "stop_scores": [6], "stop_signals": [["modification", "research"]], "review_prompt_lengths": [0]}`

```text
已完成修改。
```

### codex / gpt-5.6-sol / 小型数据分析 / round 1

预期：应从数据得到结论并识别平均数受异常值影响。

自动评估：`{"review_happened": true, "blocked": true, "decision_correct": true, "keyword_hits": [], "relevance": 0.0, "question_count": 0, "annoyance": 1.0, "compact_prompt": true, "task_completed": true, "score": 70, "stop_scores": [15], "stop_signals": [["modification", "phase_boundary", "research", "verified", "work_like"]], "review_prompt_lengths": [950]}`

```text
复盘完成：极端值会拉高均值，中位数更能代表多数天的典型水平。该概念已记录，无需重复写入。
```

### codex / gpt-5.6-sol / 边界条件调试 / round 1

预期：真实修复包含可迁移的索引与输入边界知识。

自动评估：`{"review_happened": true, "blocked": true, "decision_correct": true, "keyword_hits": ["索引"], "relevance": 0.5, "question_count": 1, "annoyance": 1.0, "compact_prompt": true, "task_completed": true, "score": 85, "stop_scores": [27], "stop_signals": [["modification", "phase_boundary", "research", "verification", "verified", "work_like"]], "review_prompt_lengths": [1011]}`

```text
字符串分割后首字段在索引0；`split(',',1)`无逗号也不会越界。测试应覆盖正常与退化输入。可选判断：`a,b,c`返回`a`，对吗？要点已记录。
```

### codex / gpt-5.6-sol / 重复逻辑重构 / round 1

预期：重构应提炼重复知识，而不只是报告测试通过。

自动评估：`{"review_happened": true, "blocked": true, "decision_correct": true, "keyword_hits": ["重构"], "relevance": 0.5, "question_count": 1, "annoyance": 1.0, "compact_prompt": true, "task_completed": true, "score": 85, "stop_scores": [28], "stop_signals": [["modification", "phase_boundary", "research", "verification", "verified", "work_like"]], "review_prompt_lengths": [1029]}`

```text
已记录“行为保持型重构”：测试只保护已覆盖行为，不代表所有边界无误。可选判断：现有测试足以覆盖阈值 100 吗？
```

### kimi / kimi-code/kimi-for-coding / 边界条件调试 / round 1

预期：真实修复包含可迁移的索引与输入边界知识。

自动评估：`{"review_happened": true, "blocked": true, "decision_correct": true, "keyword_hits": ["索引"], "relevance": 0.5, "question_count": 1, "annoyance": 1.0, "compact_prompt": true, "task_completed": true, "score": 85, "stop_scores": [14], "stop_signals": [["modification", "research", "verification", "work_like"]], "review_prompt_lengths": [780]}`

```text
🌱 修复这个 bug 的关键是：**“第一个字段”在 Python 里对应索引 `0`，不是 `1`**。`line.split(',')[0]` 才是 `a`，`[1]` 其实是第二个字段。测试就像一份小合同，告诉我们函数应该返回什么。

小问题（可选）：`['a', 'b', 'c']` 里索引 `1` 对应的是第几个元素？可以跳过。

已记入 vault：`[[零基索引与字段提取]]`。
```

### kimi / kimi-code/kimi-for-coding / 重复逻辑重构 / round 1

预期：重构应提炼重复知识，而不只是报告测试通过。

自动评估：`{"review_happened": true, "blocked": true, "decision_correct": true, "keyword_hits": ["重复"], "relevance": 0.5, "question_count": 1, "annoyance": 1.0, "compact_prompt": true, "task_completed": true, "score": 85, "stop_scores": [15], "stop_signals": [["modification", "research", "tool_use", "verification", "work_like"]], "review_prompt_lengths": [806]}`

```text
🌱 刚才的改动核心是 **DRY 原则**：同一段折扣逻辑只在 `_discount` 里保留一份，需要时调用它。这样未来改规则（比如门槛从 100 变 150）只需改一处，也不容易漏掉某个分支。

小检查（可选）：如果以后要把折扣门槛从 100 改成 150，现在的代码需要改几个地方？

已记录到 vault：[[DRY 原则：消除重复代码]]。
```

### kimi / kimi-code/kimi-for-coding / 显式教学请求 / round 1

预期：显式请求必须教学，并从弱前提开始且最多问一个问题。

自动评估：`{"review_happened": true, "blocked": true, "decision_correct": true, "keyword_hits": ["依赖", "注入"], "relevance": 1.0, "question_count": 2, "annoyance": 0.75, "compact_prompt": true, "task_completed": true, "score": 95, "stop_scores": [6], "stop_signals": [["manual", "research"]], "review_prompt_lengths": [513]}`

```text
🌱 核心点再强调一下：`Service` 真正依赖的不是某个具体的 `repository` 对象，而是“能按 key 取值”这个**行为约定**。只要传入的对象有 `.get(key)` 方法，代码就能工作——这让你以后换数据库、写单元测试时都不用改 `Service`。

一个可选小检查：下面哪种做法最符合依赖注入的思想？

A. `Service` 内部直接 `self.repository = {"a": 1}`
B. 调用方创建 `repo = {...}`，然后 `Service(repo)`
C. `Service` 在 `find()` 里自己 `import` 一个数据库客户端

你选 B。能说说 A 和 C 主要问题在哪吗？（可跳过）

我顺手把这点记进了 vault：`[[构造函数依赖注入]]`。
```

### kimi / kimi-code/kimi-for-coding / 可变默认参数 / round 1

预期：应理解 Python 默认参数只求值一次这一隐藏机制。

自动评估：`{"review_happened": true, "blocked": true, "decision_correct": true, "keyword_hits": ["可变", "默认", "共享", "状态"], "relevance": 1.0, "question_count": 2, "annoyance": 0.75, "compact_prompt": true, "task_completed": true, "score": 95, "stop_scores": [14], "stop_signals": [["modification", "research", "verification", "work_like"]], "review_prompt_lengths": [780]}`

```text
🌱 这次改动的核心知识点：Python 的默认参数只在函数定义时求值一次。如果默认值是列表这类可变对象，所有调用会共享同一个列表，导致状态泄漏。正确做法是用 `items=None`，在函数体里再创建新列表。

小检查（可选）：`def add(item, items=None): items.append(item)` 这样写还会有问题吗？为什么？

已记到 vault：`[[Python 可变默认参数]]`。
```

### codex / gpt-5.6-sol / 配置语义修改 / round 1

预期：虽修改很小，但单位和配置语义具有可迁移价值。

自动评估：`{"review_happened": true, "blocked": true, "decision_correct": true, "keyword_hits": ["配置", "单位"], "relevance": 1.0, "question_count": 1, "annoyance": 1.0, "compact_prompt": true, "task_completed": true, "score": 100, "stop_scores": [10], "stop_signals": [["debug_signal", "error_signal", "modification", "research"]], "review_prompt_lengths": [739]}`

```text
配置值不自带单位，紧邻注释可消除歧义。可选判断：注释越近越易维护，对吗？本次未建笔记。
```

### codex / gpt-5.6-sol / 明确拒绝教学 / round 1

预期：即使有写操作，也应尊重用户本轮不教学的明确选择。

自动评估：`{"review_happened": false, "blocked": false, "decision_correct": true, "keyword_hits": [], "relevance": 1.0, "question_count": 0, "annoyance": 1.0, "compact_prompt": true, "task_completed": true, "score": 100, "stop_scores": [12], "stop_signals": [["modification", "opt_out", "verification"]], "review_prompt_lengths": [0]}`

```text
已将 [VERSION](<E2E_TMP>/round-1/codex/gpt-5.6-sol/explicit_opt_out/work/VERSION) 从 `1.0.0` 改为 `1.0.1`。
```

## 解释限制

自动评分用于发现异常，不等同于语义裁判。最终结论应结合 `results.json` 中的完整输出、Hook 事件和捕获笔记人工复核。
