# Teach Me Codex / Kimi 终端 E2E 质量报告

- 生成时间：`2026-07-10T19:02:56+08:00`
- 测试轮数：`1`
- 不同场景：`10`
- 总执行数：`20`
- 驱动方式：Python 标准库 `pty` 启动真实 CLI；每个场景隔离 `TEACH_ME_HOME` 与 Vault。
- 评分维度：触发决策 40%、内容相关性 30%、提问打扰度 20%、Hook 提示紧凑度 10%。

## 汇总

| Agent | 模型 | Context | 场景次数 | 成功退出 | 决策正确 | 平均分 | 平均耗时 | 平均 Token |
|---|---|---|---:|---:|---:|---:|---:|---:|
| codex | `gpt-5.6-sol` | expanded | 10 | 10 | 10 | 92.5 | 58.3s | 22220 |
| kimi | `kimi-code/kimi-for-coding` | expanded | 10 | 10 | 9 | 91.0 | 37.1s | - |

## 自动质量信号

- 不必要教学：`0` 次。
- 应教未教：`1` 次。
- 单次回答超过一个问句：`1` 次。
- 正例相关关键词命中不足：`1` 次。

## 逐场景结果

| 轮次 | Agent | 模型 | 场景 | 任务完成 | 应教学 | 实际教学 | 问句 | 关键词 | 分数 | 退出码 |
|---:|---|---|---|---|---|---|---:|---|---:|---:|
| 1 | codex | `gpt-5.6-sol` | 边界条件调试 | 是 | 是 | 是 | 1 | 索引 | 85 | 0 |
| 1 | codex | `gpt-5.6-sol` | 配置语义修改 | 是 | 是 | 是 | 1 | 配置、超时、单位 | 100 | 0 |
| 1 | codex | `gpt-5.6-sol` | 小型数据分析 | 是 | 是 | 是 | 1 | 18 | 85 | 0 |
| 1 | codex | `gpt-5.6-sol` | 明确拒绝教学 | 是 | 否 | 否 | 0 | - | 100 | 0 |
| 1 | codex | `gpt-5.6-sol` | 显式教学请求 | 是 | 是 | 是 | 1 | 依赖、注入 | 100 | 0 |
| 1 | codex | `gpt-5.6-sol` | 纯机械改名 | 是 | 否 | 否 | 0 | - | 100 | 0 |
| 1 | codex | `gpt-5.6-sol` | 可变默认参数 | 是 | 是 | 是 | 1 | 默认 | 85 | 0 |
| 1 | codex | `gpt-5.6-sol` | 重复逻辑重构 | 是 | 是 | 是 | 1 | 重复 | 85 | 0 |
| 1 | codex | `gpt-5.6-sol` | 状态机理解 | 是 | 是 | 是 | 0 | 转换 | 85 | 0 |
| 1 | codex | `gpt-5.6-sol` | 无价值的命令失败 | 是 | 否 | 否 | 0 | 不可用 | 100 | 0 |
| 1 | kimi | `kimi-code/kimi-for-coding` | 边界条件调试 | 是 | 是 | 是 | 2 | - | 65 | 0 |
| 1 | kimi | `kimi-code/kimi-for-coding` | 配置语义修改 | 是 | 是 | 否 | 0 | 秒、单位 | 60 | 0 |
| 1 | kimi | `kimi-code/kimi-for-coding` | 小型数据分析 | 是 | 是 | 是 | 1 | 平均、异常、18 | 100 | 0 |
| 1 | kimi | `kimi-code/kimi-for-coding` | 明确拒绝教学 | 是 | 否 | 否 | 0 | - | 100 | 0 |
| 1 | kimi | `kimi-code/kimi-for-coding` | 显式教学请求 | 是 | 是 | 是 | 1 | 依赖、注入 | 100 | 0 |
| 1 | kimi | `kimi-code/kimi-for-coding` | 纯机械改名 | 是 | 否 | 否 | 0 | - | 100 | 0 |
| 1 | kimi | `kimi-code/kimi-for-coding` | 可变默认参数 | 是 | 是 | 是 | 1 | 可变、默认、状态 | 100 | 0 |
| 1 | kimi | `kimi-code/kimi-for-coding` | 重复逻辑重构 | 是 | 是 | 是 | 1 | 重复、重构 | 100 | 0 |
| 1 | kimi | `kimi-code/kimi-for-coding` | 状态机理解 | 是 | 是 | 是 | 1 | 状态 | 85 | 0 |
| 1 | kimi | `kimi-code/kimi-for-coding` | 无价值的命令失败 | 是 | 否 | 否 | 0 | 不可用 | 100 | 0 |

## 失败与低分样本

### kimi / kimi-code/kimi-for-coding / 配置语义修改 / round 1

预期：虽修改很小，但单位和配置语义具有可迁移价值。

自动评估：`{"review_happened": false, "blocked": false, "decision_correct": false, "keyword_hits": ["秒", "单位"], "relevance": 1.0, "question_count": 0, "annoyance": 1.0, "compact_prompt": true, "task_completed": true, "score": 60, "stop_scores": [6], "stop_signals": [["modification", "research"]], "review_prompt_lengths": [0]}`

```text
已修改 app.ini：在 timeout 行上方添加了“timeout 单位为秒”的注释，并将值从 5 改为 15。
```

### kimi / kimi-code/kimi-for-coding / 边界条件调试 / round 1

预期：真实修复包含可迁移的索引与输入边界知识。

自动评估：`{"review_happened": true, "blocked": true, "decision_correct": true, "keyword_hits": [], "relevance": 0.0, "question_count": 2, "annoyance": 0.75, "compact_prompt": true, "task_completed": true, "score": 65, "stop_scores": [10], "stop_signals": [["modification", "research", "work_like"]], "review_prompt_lengths": [968]}`

```text
从这个小修复里，我提炼出三个值得留意的点：

1. **测试是“活文档”**
   `test_parser.py` 明确告诉咱们：`first_field('a,b')` 应该返回 `'a'`。先读测试，能立刻看出函数命名和实现之间的矛盾。

2. **Python 列表从 0 开始计数**
   `line.split(',')[0]` 取第一个元素，`[1]` 取的是第二个。这类“差一”错误是初学者最常见的坑之一。

3. **修改后立即跑测试**
   改完一行代码立刻执行测试，能最快确认修复是否真的有效，避免靠猜。

想考你一下：如果输入是 `'a,b,c'`，`line.split(',')[1]` 会返回什么？
（可选）是 `a`、`b` 还是 `c`？
```

### codex / gpt-5.6-sol / 边界条件调试 / round 1

预期：真实修复包含可迁移的索引与输入边界知识。

自动评估：`{"review_happened": true, "blocked": true, "decision_correct": true, "keyword_hits": ["索引"], "relevance": 0.5, "question_count": 1, "annoyance": 1.0, "compact_prompt": true, "task_completed": true, "score": 85, "stop_scores": [19], "stop_signals": [["modification", "phase_boundary", "research", "verification", "verified", "work_like"]], "review_prompt_lengths": [1058]}`

```text
复盘：字符串切分结果是序列，第一项固定为索引0；限制切分次数可让代码更贴近需求。可选判断：无逗号时结果应为原字符串，对吗？已避免重复记笔记。
```

### codex / gpt-5.6-sol / 小型数据分析 / round 1

预期：应从数据得到结论并识别平均数受异常值影响。

自动评估：`{"review_happened": true, "blocked": true, "decision_correct": true, "keyword_hits": ["18"], "relevance": 0.5, "question_count": 1, "annoyance": 1.0, "compact_prompt": true, "task_completed": true, "score": 85, "stop_scores": [10], "stop_signals": [["modification", "research", "work_like"]], "review_prompt_lengths": [1155]}`

```text
均值是“总和÷数量”，所以周三的 50 会把结果拉到 18；中位数 10 不易受极端值影响，更接近普通一天。

可选判断：本例只报告均值会夸大典型销售水平——对还是错？

该概念已记录，无需重复捕获。
```

### codex / gpt-5.6-sol / 可变默认参数 / round 1

预期：应理解 Python 默认参数只求值一次这一隐藏机制。

自动评估：`{"review_happened": true, "blocked": true, "decision_correct": true, "keyword_hits": ["默认"], "relevance": 0.5, "question_count": 1, "annoyance": 1.0, "compact_prompt": true, "task_completed": true, "score": 85, "stop_scores": [15], "stop_signals": [["modification", "phase_boundary", "research", "verification", "verified", "work_like"]], "review_prompt_lengths": [1093]}`

```text
基础：变量保存对象引用；默认参数在函数定义时求值一次，所以后续调用会复用同一列表。可选判断：两次省略参数调用，拿到的是同一对象吗？概念已记录，不重复写入。
```

### codex / gpt-5.6-sol / 重复逻辑重构 / round 1

预期：重构应提炼重复知识，而不只是报告测试通过。

自动评估：`{"review_happened": true, "blocked": true, "decision_correct": true, "keyword_hits": ["重复"], "relevance": 0.5, "question_count": 1, "annoyance": 1.0, "compact_prompt": true, "task_completed": true, "score": 85, "stop_scores": [17], "stop_signals": [["modification", "phase_boundary", "research", "verification", "verified", "work_like"]], "review_prompt_lengths": [1132]}`

```text
函数抽取就是给重复规则命名并集中维护；回归测试确保“改结构、不改行为”。本次知识点已记录，不重复捕获。可选判断：规则分化后还应强行共用 helper 吗？
```

### codex / gpt-5.6-sol / 状态机理解 / round 1

预期：应基于实际代码理解允许边，而非泛泛讲状态机。

自动评估：`{"review_happened": true, "blocked": true, "decision_correct": true, "keyword_hits": ["转换"], "relevance": 0.5, "question_count": 0, "annoyance": 1.0, "compact_prompt": true, "task_completed": true, "score": 85, "stop_scores": [18], "stop_signals": [["error_signal", "manual", "modification", "phase_boundary", "research"]], "review_prompt_lengths": [995]}`

```text
复核完成，未重复写笔记。合法转换是有向边白名单；`failed → running` 会抛 `ValueError`。
```

### kimi / kimi-code/kimi-for-coding / 状态机理解 / round 1

预期：应基于实际代码理解允许边，而非泛泛讲状态机。

自动评估：`{"review_happened": true, "blocked": true, "decision_correct": true, "keyword_hits": ["状态"], "relevance": 0.5, "question_count": 1, "annoyance": 1.0, "compact_prompt": true, "task_completed": true, "score": 85, "stop_scores": [10], "stop_signals": [["manual", "modification", "research"]], "review_prompt_lengths": [960]}`

```text
🌱 状态机像交通灯：每个状态只能按规则切换。这里用 Python 字典把规则写成白名单，调用 `move()` 时先查字典，非法就抛 `ValueError`。可选问题：如果允许 `failed` 直接回到 `running`，该改哪一行？
```

### codex / gpt-5.6-sol / 配置语义修改 / round 1

预期：虽修改很小，但单位和配置语义具有可迁移价值。

自动评估：`{"review_happened": true, "blocked": true, "decision_correct": true, "keyword_hits": ["配置", "超时", "单位"], "relevance": 1.0, "question_count": 1, "annoyance": 1.0, "compact_prompt": true, "task_completed": true, "score": 100, "stop_scores": [12], "stop_signals": [["debug_signal", "error_signal", "modification", "research"]], "review_prompt_lengths": [1000]}`

```text
配置注释应紧邻参数，避免单位歧义。本次属机械修改，不写学习笔记。可选：要检查其他超时项吗？
```

### codex / gpt-5.6-sol / 明确拒绝教学 / round 1

预期：即使有写操作，也应尊重用户本轮不教学的明确选择。

自动评估：`{"review_happened": false, "blocked": false, "decision_correct": true, "keyword_hits": [], "relevance": 1.0, "question_count": 0, "annoyance": 1.0, "compact_prompt": true, "task_completed": true, "score": 100, "stop_scores": [6], "stop_signals": [["modification", "opt_out", "research"]], "review_prompt_lengths": [0]}`

```text
已将 `VERSION` 从 `1.0.0` 改为 `1.0.1`。
```

## 解释限制

自动评分用于发现异常，不等同于语义裁判。最终结论应结合 `results.json` 中的完整输出、Hook 事件和捕获笔记人工复核。
