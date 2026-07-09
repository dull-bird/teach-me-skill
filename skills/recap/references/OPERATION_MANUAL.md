# Teach Me Recap 操作手册

Teach Me Recap 是你的间隔重复复习助手。它从 Teach Me vault 中读取你记录过的概念、算法思想和项目地图，按 SM-2 算法安排复习，并用“主动回忆 + 苏格拉底提问”帮你巩固知识。

---

## 1. 复习理念

### 1.1 间隔重复（Spaced Repetition）

你记得越牢，下次复习的间隔就越长；如果忘了，间隔会缩短。

- `again`（完全想不起来）→ 明天再复习
- `hard`（费劲才想起来）→ 小幅度延长
- `good`（正常想起）→ 标准 SM-2 延长
- `easy`（太简单）→ 更大幅度延长

### 1.2 主动回忆（Active Recall）

复习时，脚本会先给你标题和提示，但不展示完整笔记。你要先尝试自己解释，再揭晓答案。这比反复阅读更有效。

### 1.3 苏格拉底提问

如果知识树节点有 `probes`（探测题）、`gaps`（缺口）或 `prerequisites`（前置依赖），Recap 会优先用它们作为提示，帮你建立联系、发现盲点。

---

## 2. 命令速查

```bash
# 查看今天到期复习项
python3 ~/.codex/skills/recap/scripts/recap.py due

# 开始一道复习题
python3 ~/.codex/skills/recap/scripts/recap.py next

# 记录复习结果（again / hard / good / easy）
python3 ~/.codex/skills/recap/scripts/recap.py rate "概念名称" good

# 查看复习统计
python3 ~/.codex/skills/recap/scripts/recap.py stats

# 查看本手册
python3 ~/.codex/skills/recap/scripts/recap.py manual
```

所有命令都支持 `--json` 输出结构化数据。

---

## 3. 自然语言用法

直接对 agent 说：

- “帮我复习一下”
- “今天该复习什么？”
- “考考我”
- “把 `Canvas 小游戏中的实体状态机` 标为 easy”
- “我最近学了什么？”
- “哪些概念最薄弱？”

agent 会调用 `recap.py` 并把你的回答转化为评分。

---

## 4. 复习流程示例

**用户**：帮我复习一下

**agent**（运行 `recap.py next`）：

```text
## 复习题

**PDF4QT page tree mutation**（concept）

思考题：True or false: 裁剪 PDF 页面通常只是设置 CropBox，不一定删除被裁剪区域的原始内容。

先不要看笔记，试着自己解释这个概念。
```

**用户**：我记得这是说页面级编辑如果只修改后端，Qt 主视图无法自然 undo/apply/save……

**agent**（运行 `recap.py rate "PDF4QT page tree mutation" good`）：

```text
已标记 PDF4QT page tree mutation 为 good。下次复习：2026-07-20（间隔 6 天）。
```

---

## 5. 数据存在哪里

Recap 只读取和修改：

```text
~/.teach_me_skill/vault/.teach-me/learning-state.json
```

具体字段：

- `concepts.<name>.score` — 最近一次的评分
- `concepts.<name>.mastery` — 掌握度（unknown / seen / practiced / confident）
- `concepts.<name>.next_review` — 下次复习日期
- `concepts.<name>.review_interval_days` — 当前间隔天数
- `concepts.<name>.ease` — SM-2 ease factor
- `concepts.<name>.repetitions` — 连续成功次数
- `concepts.<name>.review_history` — 复习历史

它也会读取 vault 中的实际笔记文件作为提示来源。

---

## 6. 常见问题

### Q: 为什么今天没有到期复习项？

A: 说明所有已记录项的 `next_review` 都在未来。你可以：

1. 让 agent 用 `recap.py next` 手动复习薄弱项；
2. 继续学新东西，等它们自然到期。

### Q: 我标错了，能改吗？

A: 可以。重新运行 `recap.py rate "概念" <正确评分>` 即可覆盖最近一次结果和下次复习时间。

### Q: 评分标准是什么？

A:

| 评分 | 含义 | 下次间隔 |
| --- | --- | --- |
| again / 0 | 完全没想起或错了 | 1 天 |
| hard / 3 | 费劲但想起来了 | 小幅延长 |
| good / 4 | 正常想起 | 标准延长 |
| easy / 5 | 秒答 | 大幅延长 |

### Q: 怎么增加新的复习项？

A: 继续正常写代码、调试、学习。当 Teach Me 认为某个概念值得记录时，它会在 `capture` 时写入 `learning-state.json`。Recap 会自动识别这些项。

### Q: 复习时不想看提示，只想看标题？

A: 对 agent 说“直接考我，不要给提示”。agent 可以运行 `recap.py next --json` 后只展示标题。

---

## 7. 设计原则

- **只读/写 learning-state.json**：不创建额外数据库。
- **零依赖**：仅使用 Python 标准库。
- **不伪造历史**：只在用户真实复习后写入 `review_history`。
- **友好而非焦虑**：忘了就是“间隔缩短”，不是失败。
