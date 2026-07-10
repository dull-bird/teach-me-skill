# Teach Me Codex / Kimi 终端 E2E 质量报告

- 生成时间：`2026-07-10T19:20:56+08:00`
- 测试轮数：`1`
- 不同场景：`10`
- 总执行数：`20`
- 驱动方式：Python 标准库 `pty` 启动真实 CLI；每个场景隔离 `TEACH_ME_HOME` 与 Vault。
- 评分维度：触发决策 40%、内容相关性 30%、提问打扰度 20%、Hook 提示紧凑度 10%。

## 汇总

| Agent | 模型 | Context | 场景次数 | 成功退出 | 决策正确 | 平均分 | 平均耗时 | 平均 Token |
|---|---|---|---:|---:|---:|---:|---:|---:|
| codex | `gpt-5.6-sol` | short | 10 | 10 | 10 | 94.0 | 55.0s | 21959 |
| kimi | `kimi-code/kimi-for-coding` | short | 10 | 10 | 10 | 97.0 | 34.6s | - |

## 自动质量信号

- 不必要教学：`0` 次。
- 应教未教：`0` 次。
- 单次回答超过一个问句：`0` 次。
- 正例相关关键词命中不足：`1` 次。

## 逐场景结果

| 轮次 | Agent | 模型 | 场景 | 任务完成 | 应教学 | 实际教学 | 问句 | 关键词 | 分数 | 退出码 |
|---:|---|---|---|---|---|---|---:|---|---:|---:|
| 1 | codex | `gpt-5.6-sol` | 边界条件调试 | 是 | 是 | 是 | 0 | 解析 | 85 | 0 |
| 1 | codex | `gpt-5.6-sol` | 配置语义修改 | 是 | 是 | 是 | 0 | 配置、秒、单位 | 100 | 0 |
| 1 | codex | `gpt-5.6-sol` | 小型数据分析 | 是 | 是 | 是 | 0 | 平均、18 | 100 | 0 |
| 1 | codex | `gpt-5.6-sol` | 明确拒绝教学 | 是 | 否 | 否 | 0 | - | 100 | 0 |
| 1 | codex | `gpt-5.6-sol` | 显式教学请求 | 是 | 是 | 是 | 0 | - | 70 | 0 |
| 1 | codex | `gpt-5.6-sol` | 纯机械改名 | 是 | 否 | 否 | 0 | - | 100 | 0 |
| 1 | codex | `gpt-5.6-sol` | 可变默认参数 | 是 | 是 | 是 | 0 | 默认、状态 | 100 | 0 |
| 1 | codex | `gpt-5.6-sol` | 重复逻辑重构 | 是 | 是 | 是 | 0 | 单一 | 85 | 0 |
| 1 | codex | `gpt-5.6-sol` | 状态机理解 | 是 | 是 | 是 | 0 | 状态、转换 | 100 | 0 |
| 1 | codex | `gpt-5.6-sol` | 无价值的命令失败 | 是 | 否 | 否 | 0 | 不可用 | 100 | 0 |
| 1 | kimi | `kimi-code/kimi-for-coding` | 边界条件调试 | 是 | 是 | 是 | 0 | 索引 | 85 | 0 |
| 1 | kimi | `kimi-code/kimi-for-coding` | 配置语义修改 | 是 | 是 | 是 | 0 | 配置、单位 | 100 | 0 |
| 1 | kimi | `kimi-code/kimi-for-coding` | 小型数据分析 | 是 | 是 | 是 | 1 | 平均、18 | 100 | 0 |
| 1 | kimi | `kimi-code/kimi-for-coding` | 明确拒绝教学 | 是 | 否 | 否 | 0 | - | 100 | 0 |
| 1 | kimi | `kimi-code/kimi-for-coding` | 显式教学请求 | 是 | 是 | 是 | 0 | 依赖、注入 | 100 | 0 |
| 1 | kimi | `kimi-code/kimi-for-coding` | 纯机械改名 | 是 | 否 | 否 | 0 | - | 100 | 0 |
| 1 | kimi | `kimi-code/kimi-for-coding` | 可变默认参数 | 是 | 是 | 是 | 0 | 可变、默认、共享 | 100 | 0 |
| 1 | kimi | `kimi-code/kimi-for-coding` | 重复逻辑重构 | 是 | 是 | 是 | 0 | 重复 | 85 | 0 |
| 1 | kimi | `kimi-code/kimi-for-coding` | 状态机理解 | 是 | 是 | 是 | 1 | 状态、转换 | 100 | 0 |
| 1 | kimi | `kimi-code/kimi-for-coding` | 无价值的命令失败 | 是 | 否 | 否 | 0 | 不可用 | 100 | 0 |

## 失败与低分样本

### codex / gpt-5.6-sol / 显式教学请求 / round 1

预期：显式请求必须教学，并从弱前提开始且最多问一个问题。

自动评估：`{"review_happened": true, "blocked": true, "decision_correct": true, "keyword_hits": [], "relevance": 0.0, "question_count": 0, "annoyance": 1.0, "compact_prompt": true, "task_completed": true, "score": 70, "stop_scores": [6], "stop_signals": [["manual", "phase_boundary"]], "review_prompt_lengths": [634]}`

```text
这里保存的是对同一个 `repository` 对象的引用，并没有复制对象。外部传入哪个 repository，`find()` 就会调用那个对象的 `get()`。
```

### codex / gpt-5.6-sol / 边界条件调试 / round 1

预期：真实修复包含可迁移的索引与输入边界知识。

自动评估：`{"review_happened": true, "blocked": true, "decision_correct": true, "keyword_hits": ["解析"], "relevance": 0.5, "question_count": 0, "annoyance": 1.0, "compact_prompt": true, "task_completed": true, "score": 85, "stop_scores": [17], "stop_signals": [["modification", "phase_boundary", "research", "verification", "verified", "work_like"]], "review_prompt_lengths": [1055]}`

```text
`split(',', 1)[0]`只解析首个分隔符，兼容无逗号及多字段输入。已记录“有限分割提取前缀字段”。
```

### codex / gpt-5.6-sol / 重复逻辑重构 / round 1

预期：重构应提炼重复知识，而不只是报告测试通过。

自动评估：`{"review_happened": true, "blocked": true, "decision_correct": true, "keyword_hits": ["单一"], "relevance": 0.5, "question_count": 0, "annoyance": 1.0, "compact_prompt": true, "task_completed": true, "score": 85, "stop_scores": [15], "stop_signals": [["modification", "phase_boundary", "research", "verification", "verified", "work_like"]], "review_prompt_lengths": [1003]}`

```text
折扣规则集中为单一事实来源，避免多入口修改不同步；公开接口保持不变。已沉淀对应学习笔记。
```

### kimi / kimi-code/kimi-for-coding / 边界条件调试 / round 1

预期：真实修复包含可迁移的索引与输入边界知识。

自动评估：`{"review_happened": true, "blocked": true, "decision_correct": true, "keyword_hits": ["索引"], "relevance": 0.5, "question_count": 0, "annoyance": 1.0, "compact_prompt": true, "task_completed": true, "score": 85, "stop_scores": [10], "stop_signals": [["modification", "research", "work_like"]], "review_prompt_lengths": [1219]}`

```text
🌱 核心点：Python 的索引从 0 开始，所以 `"a,b".split(",")[0]` 才是第一个字段 `"a"`，而 `[1]` 会拿到第二个。已把这条记进 vault：[[Python 零基索引]]。
```

### kimi / kimi-code/kimi-for-coding / 重复逻辑重构 / round 1

预期：重构应提炼重复知识，而不只是报告测试通过。

自动评估：`{"review_happened": true, "blocked": true, "decision_correct": true, "keyword_hits": ["重复"], "relevance": 0.5, "question_count": 0, "annoyance": 1.0, "compact_prompt": true, "task_completed": true, "score": 85, "stop_scores": [14], "stop_signals": [["modification", "research", "verification", "work_like"]], "review_prompt_lengths": [935]}`

```text
核心做法：把两处完全相同的折扣规则抽到 `_apply_discount` 里，阈值或折扣率只需改一处，避免漏改。已记入 vault：[[消除重复：提取公共折扣函数]]。
```

### codex / gpt-5.6-sol / 配置语义修改 / round 1

预期：虽修改很小，但单位和配置语义具有可迁移价值。

自动评估：`{"review_happened": true, "blocked": true, "decision_correct": true, "keyword_hits": ["配置", "秒", "单位"], "relevance": 1.0, "question_count": 0, "annoyance": 1.0, "compact_prompt": true, "task_completed": true, "score": 100, "stop_scores": [8], "stop_signals": [["debug_signal", "error_signal", "modification"]], "review_prompt_lengths": [802]}`

```text
配置项注明单位可消除数值语义歧义，避免误把秒当成毫秒。此次改动简单，无需沉淀笔记。
```

### codex / gpt-5.6-sol / 小型数据分析 / round 1

预期：应从数据得到结论并识别平均数受异常值影响。

自动评估：`{"review_happened": true, "blocked": true, "decision_correct": true, "keyword_hits": ["平均", "18"], "relevance": 1.0, "question_count": 0, "annoyance": 1.0, "compact_prompt": true, "task_completed": true, "score": 100, "stop_scores": [12], "stop_signals": [["modification", "phase_boundary", "research", "work_like"]], "review_prompt_lengths": [1046]}`

```text
平均数会被极端值拉动：周三的 50 将均值推至 18，而其余四天均值仅 10。已记录该概念。
```

### codex / gpt-5.6-sol / 明确拒绝教学 / round 1

预期：即使有写操作，也应尊重用户本轮不教学的明确选择。

自动评估：`{"review_happened": false, "blocked": false, "decision_correct": true, "keyword_hits": [], "relevance": 1.0, "question_count": 0, "annoyance": 1.0, "compact_prompt": true, "task_completed": true, "score": 100, "stop_scores": [8], "stop_signals": [["modification", "opt_out", "research"]], "review_prompt_lengths": [0]}`

```text
已将 [VERSION](<E2E_TMP>/round-1/codex/gpt-5.6-sol/explicit_opt_out/work/VERSION) 从 `1.0.0` 改为 `1.0.1`。
```

### codex / gpt-5.6-sol / 纯机械改名 / round 1

预期：没有值得教学的机制，触发回顾会显得啰嗦。

自动评估：`{"review_happened": false, "blocked": false, "decision_correct": true, "keyword_hits": [], "relevance": 1.0, "question_count": 0, "annoyance": 1.0, "compact_prompt": true, "task_completed": true, "score": 100, "stop_scores": [8], "stop_signals": [["modification", "opt_out", "research"]], "review_prompt_lengths": [0]}`

```text
README.md 标题已改为 Sample。
```

### codex / gpt-5.6-sol / 可变默认参数 / round 1

预期：应理解 Python 默认参数只求值一次这一隐藏机制。

自动评估：`{"review_happened": true, "blocked": true, "decision_correct": true, "keyword_hits": ["默认", "状态"], "relevance": 1.0, "question_count": 0, "annoyance": 1.0, "compact_prompt": true, "task_completed": true, "score": 100, "stop_scores": [19], "stop_signals": [["modification", "phase_boundary", "research", "verification", "verified", "work_like"]], "review_prompt_lengths": [1040]}`

```text
Python 参数传递的是对象引用：默认列表只创建一次，原地修改会让后续调用看到旧状态；`None` 哨兵可确保每次新建列表。
```

## 解释限制

自动评分用于发现异常，不等同于语义裁判。最终结论应结合 `results.json` 中的完整输出、Hook 事件和捕获笔记人工复核。
