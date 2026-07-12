<p align="center">
  <img src="docs/assets/seedling_1f331_once.webp" alt="Teach Me logo" width="96" height="96">
</p>

<h1 align="center">Teach Me</h1>

<p align="center">
  做事，顺便学明白<br>
  Learn by doing, with your tools
</p>

<p align="center">
  <a href="https://dull-bird.github.io/teach-me-skill/">中文官网</a>
  ·
  <a href="https://dull-bird.github.io/teach-me-skill/en/">English site</a>
  ·
  <a href="#中文">中文</a>
  ·
  <a href="#english">English</a>
</p>

---

## 中文

**Teach Me：做事，顺便学明白。**

它是一套 Agent Skill，支持 Claude Code、Codex、OpenClaw、Kimi Code CLI。在你写代码、调试、重构、测试，或者处理数据、整理文档、剪辑媒体、调试配置、研究问题的过程中，Teach Me 自动识别值得学习的瞬间，把关键概念、隐藏机制、决策理由整理成你的本地知识库。

它还会慢慢画出你的学习画像：你喜欢怎么被教、哪些概念已经掌握、哪些前置知识还模糊。AI 的教学个性可以由你塑造，复习和教学都会围绕你来进行。

### 解决的痛点

AI 帮你执行越来越快，但很多人发现：三天后就忘了当时为什么这么做。因为：

- 为什么这里要这样设计？忘了。
- 这个 bug 为什么出现？忘了。
- 这个做法能搬到下一个任务吗？不敢动。

Teach Me 在阶段边界帮你整理真正值得留下的东西，让你能复习、能迁移、能独立做事。

### 具体怎么做

我把“你明确想学什么”和“这一轮实际做了什么”分开处理：

1. **直接调用 skill**：你说“教我”“为什么”“复盘”时，Teach Me 负责解释；你说“考考我”时，Teach Me Exam 先询问范围、题型和时长。它们都不是 hook。
2. **Tool hooks**：`PreToolUse`、`PostToolUse` 和失败事件记录实际证据：文件编辑、测试运行、构建、类型检查、报错、验证结果、配置改动、数据处理、媒体操作、浏览搜索等。
3. **Stop hook**：在阶段结束时给工具证据打分。信号弱就安静，信号强才请求一次短复盘；它不会自动开考。
4. **目标级汇总**：一个 goal 进行中时，Stop 不重复打断教学，只积累证据；goal 完成时输出一段连贯的项目知识总结和恰好 5 个知识点。
5. **教学输出**：每次真正的 Teach Me 教学都以 `🌱 [领域：…]` 开头；有项目时还会标出 `[项目：…]`。领域可为 AI、数据库、数学、物理、软件工程、产品设计或通用。
6. **本地 runtime**：把内容写入 Obsidian vault，同时更新知识树、掌握度、学习画像和复习计划。项目优先按路径保存稳定 ID，改名不会切断历史关联。

### 你会得到什么

一个本地 vault，默认在 `~/.teach_me_skill/vault`：

```text
vault/
├── 00_Index.md                 # 总索引
├── 01_Knowledge_Graph.md       # 知识图谱
├── 02_Concepts/                # 概念笔记
├── 03_Algorithmic_Ideas/       # 算法思想
├── 04_Project_Maps/            # 项目地图
├── 05_Socratic_Questions/      # 苏格拉底问题
├── 06_Reviews/                 # 复盘记录
├── 07_Learning_Profile/
│   └── Knowledge_Tree.md       # 知识树
└── .teach-me/
    ├── learning-state.json     # 掌握度、复习计划
    ├── style-profile.json      # 学习风格偏好
    └── events.jsonl            # 事件日志
```

所有可读笔记都是普通 Markdown。机器状态放在 `.teach-me/`，包括你的学习画像（知识树、掌握度、风格偏好）。默认本地保存，不会推送到远端。

### 四个技能

| 技能 | 作用 | 典型说法 |
| --- | --- | --- |
| **Teach Me** | 工作时收集证据，阶段边界触发复盘，写笔记 | “复盘一下刚才的调试” |
| **Teach Me Check** | 检查安装状态、vault 内容、学习画像、用户与风格 | “帮我检查 Teach Me 状态” |
| **Teach Me Recap** | 用间隔重复 + 主动回忆复习已记录知识 | “帮我复习一下” |
| **Teach Me Exam** | 从学习画像生成自适应测验和考试 | “考考我” |

### AI 的教学个性，由你塑造

你可以告诉 Teach Me 你喜欢怎么被教，之后它会按这个风格解释、提问、反馈，而不是套用默认模板：

```bash
python3 ~/.codex/skills/teach-me/scripts/teach_me.py style \
  --speaking-style "friendly coach" \
  --teach-me-persona "a curious peer who explains simply and asks one short question"
```

或用 Check skill：

```bash
python3 ~/.codex/skills/check/scripts/check_me.py style \
  --set speaking_style "concise mentor"
```

### 它也在绘制你的学习画像

随着你使用和复盘，Teach Me 会记录：

- 你接触过哪些概念，掌握到什么程度
- 哪些前置知识还模糊
- 你喜欢类比、代码示例，还是直接讲原理
- 哪些问题该在什么时候复习

这些画像完全存在你的本地 vault 里，用来让教学和复习越来越贴合你。

### 多用户

Teach Me 支持为不同用户创建独立 vault，适合共用机器或希望把个人学习内容隔离的场景。

```bash
# 添加用户
python3 ~/.codex/skills/teach-me/scripts/teach_me.py configure \
  --add-user alice --name Alice --github alice

# 切换当前用户
python3 ~/.codex/skills/teach-me/scripts/teach_me.py switch-user alice

# 或者用 Check skill 管理用户
python3 ~/.codex/skills/check/scripts/check_me.py profile --add alice --name Alice
python3 ~/.codex/skills/check/scripts/check_me.py profile --switch alice
```

用户解析顺序：hook payload 中的 `user_id` → 环境变量 `TEACH_ME_USER` → git config 中已存在的 GitHub 用户 → `config.current_user`。

### 适合谁

- **刚入门的人**：跟着真实项目学，每一步都留下理解痕迹。
- **不想被 AI 绑架的人**：把 AI 的输出变成自己的知识。
- **长期维护项目的人**：把架构决策、易错点、隐式依赖记下来，避免重复踩坑。
- **想建立个人知识体系的人**：每个项目都是课程，vault 是你的教材。

### 快速开始

```bash
# 1. 安装
git clone https://github.com/dull-bird/teach-me-skill.git
cd teach-me-skill
./install.sh

# 2. 按你的 agent 装 hook
./codex/install-hook.sh      # 或 claude-code, kimi, openclaw

# 3. 配置
python3 ~/.codex/skills/teach-me/scripts/teach_me.py configure --language auto

# 4. 正常写代码； Teach Me 会在合适时机请求复盘
```

之后：

```bash
# 检查状态
python3 ~/.codex/skills/check/scripts/check_me.py report

# 复习
python3 ~/.codex/skills/recap/scripts/recap.py next

# 考试 / 测验
python3 ~/.codex/skills/exam/scripts/exam.py plan --time 15
```

更自然的方式是直接说：

- “帮我检查 Teach Me 状态”
- “复盘一下刚才的调试”
- “帮我复习一下”
- “考考我”
- “导入我的 Obsidian vault：`/path/to/vault`”
- “关闭所有 Teach Me 钩子” / “打开所有 Teach Me 钩子”
- “把 vault 改到 ~/Documents/Teach-Me”

### 安装

```bash
git clone https://github.com/dull-bird/teach-me-skill.git
cd teach-me-skill
./install.sh
```

按你使用的 agent 安装 hook：

```bash
./claude-code/install-hook.sh
./codex/install-hook.sh
./openclaw/install-hook.sh
./kimi/install-hook.sh
```

### 首次配置

不用记命令，直接对你的 agent 说：

> “帮我初始化 Teach Me，语言用自动。”

agent 会运行：

```bash
python3 ~/.codex/skills/teach-me/scripts/teach_me.py configure --language auto
```

第一次写笔记前，Teach Me 会让你确认：

- vault 路径（默认 `~/.teach_me_skill/vault`）
- 笔记语言
- 是否启用 Git sync

想换 vault 位置：

> “把 Teach Me vault 放到 ~/Documents/Teach-Me-Vault。”

### 导入已有知识

你可以把已有的资料或整个 Obsidian vault 导入知识库：

```bash
# 导入 PDF / URL / Markdown / EPUB / Word
python3 ~/.codex/skills/teach-me/scripts/teach_me.py import --source pdf --path /path/to/file.pdf --project "Book Name"

# 导入整个 Obsidian vault（自动跳过 .teach-me / .obsidian / 系统生成笔记）
python3 ~/.codex/skills/teach-me/scripts/teach_me.py import --source obsidian --path /path/to/obsidian/vault --project "My Obsidian"
```

导入后，AI 会先简要介绍材料内容，询问你的掌握程度；如果你已经很熟悉，可以直接发起测验。

### 开关 hooks

临时关闭或重新开启所有 agent 的 Teach Me hooks：

```bash
python3 ~/.codex/skills/teach-me/scripts/teach_me.py hooks --disable
python3 ~/.codex/skills/teach-me/scripts/teach_me.py hooks --enable
```

### Vault 格式迁移

如果 Teach Me 更新了 vault 内部格式，运行迁移命令对齐旧数据：

```bash
python3 ~/.codex/skills/teach-me/scripts/teach_me.py vault-version
python3 ~/.codex/skills/teach-me/scripts/teach_me.py migrate --dry-run
python3 ~/.codex/skills/teach-me/scripts/teach_me.py migrate
```

### 可选 Git sync

想跨设备接着学，给 vault 配一个 Git remote：

> “开启 Git sync，远程仓库用 git@github.com:user/teach-me-vault.git，写入后自动同步。”

agent 会运行：

```bash
python3 ~/.codex/skills/teach-me/scripts/teach_me.py configure \
  --language auto \
  --git-remote git@github.com:user/teach-me-vault.git \
  --auto-sync
```

手动同步：

```bash
python3 ~/.codex/skills/teach-me/scripts/teach_me.py sync
```

如果只想要本地版本历史，不提供远端也可以：

```bash
python3 ~/.codex/skills/teach-me/scripts/teach_me.py configure \
  --language auto \
  --enable-git-sync
```

### 目标级汇总与 quiet window

一个 `Stop` 只说明 agent 的一次输出结束，并不说明 feature、排查或小项目已经完成。长任务里可能发生很多次 Stop；若每次都教学，重要的脉络会被连续的小提示冲散。目标级汇总把“收集证据”和“交付解释”分成两个边界：中途安静积累，真正完成时再给一张能看懂全貌的知识地图。

| 时机 | runtime / hook 做什么 | 用户会看到什么 |
| --- | --- | --- |
| goal 开始 | agent 运行 `goal start`，把稳定 goal ID、项目路径、领域和可选 quiet window 写入本地 `goal_sessions` | 不教学、不打断 |
| 正常工作 | Tool hooks 继续把编辑、测试、构建、错误和验证写入 `events.jsonl` | 不教学、不把命令当知识 |
| 目标仍活跃时的 Stop | Stop hook 记录 `defer_goal_end`，跳过普通阶段微复盘 | 不重复刷出小课堂 |
| goal 完成 | agent 运行 `goal complete`；runtime 从该 goal 开始以来的证据重建完整上下文 | 一段连贯总结 + **恰好 5 个**知识点 |
| 用户补救 | “**帮我总结上面的工作**”会运行 `goal summary --recent --force` | 汇总近期尚未处理的工作 |

完成时，runtime 返回给 agent 一份写作契约：以 `🌱 [领域：…] [项目：…]` 开头，先写 **一段** 连贯的项目知识总结，再写 **恰好 5 个**相互关联、可迁移的知识点。那一段要解释机制、决策和取舍如何彼此关联，而不是复述“运行了什么命令”。hook 本身不生成教学文字；agent 仍要检查实际代码、文档和对话，不能补造证据里没有的事实。

`summary_checkpoints` 只用于手动或 quiet-window 的“近期未总结”范围。它不会缩短最终的 `goal complete`：即使中途已经因为 quiet window 做过一次小结，完成 goal 时仍会回看整个目标周期，避免最终总结丢掉前半段的设计理由。

可选的 `--quiet-window-minutes 15` 是兜底，不是计时器：连续工作期间它只积累；15 分钟过去后，只有遇到**下一次 Stop**才会请求一次汇总。它不会后台弹窗、不会强行打断，也不会自行启动考试。goal 完成总是绕过等待，直接进入完整总结；默认值为 `0`，即关闭这个兜底。

典型调用如下；通常由 Teach Me skill 在可见 goal 的开始和完成边界执行：

```bash
# 开始积累一个项目目标
python3 ~/.codex/skills/teach-me/scripts/teach_me.py goal start \
  --id parser-refactor \
  --project-name "Parser refactor" \
  --project-path /absolute/path/to/repo \
  --knowledge-domain 软件工程 \
  --quiet-window-minutes 15

# 在完成边界取得完整总结提示
python3 ~/.codex/skills/teach-me/scripts/teach_me.py goal complete --id parser-refactor

# 已停止工作但漏掉自动总结时
python3 ~/.codex/skills/teach-me/scripts/teach_me.py goal summary --recent --force
```

### Hook 支持

| Agent | 主要事件 | 行为 |
| --- | --- | --- |
| Claude Code | `PreToolUse`, `PostToolUse`, `Stop` | 记录工具证据；普通 Stop 只在证据足够时请求短复盘，活跃 goal 则延后到目标汇总 |
| Codex | `PreToolUse`, `PostToolUse`, `Stop` | 同上，并把 `~/.teach_me_skill` 加入 writable root |
| Kimi Code CLI | tool/stop hooks | 复用 `~/.agents/skills/teach-me`，按支持事件记录证据；goal 会话同样避免重复 Stop 教学 |
| OpenClaw | `message:received`, `agent:bootstrap` | 注入 bootstrap context；真正的 final-review 需要插件层支持 |

### 开发测试（普通用户可跳过）

```bash
python3 -m unittest -v tests.test_teach_me_hook tests.test_goal_summary
```

---

## English

**Teach Me: Learn by doing, with your tools.**

It is a set of Agent Skills for Claude Code, Codex, OpenClaw, and Kimi Code CLI. As you code, debug, refactor, and test — or work with data, media, documents, configuration, and research — Teach Me spots the moments worth learning from and turns key concepts, hidden mechanisms, and decision rationales into a local knowledge base.

It also builds a growing learner portrait: how you like to be taught, which concepts you have mastered, and which prerequisites are still fuzzy. The AI's teaching personality is shaped by you, and reviews and explanations are centered on you.

### Pain points it solves

AI executes faster than ever, but many people find they cannot reproduce or adapt what they did three days later. Because:

- Why was it designed this way? Forgotten.
- Why did that bug appear? Forgotten.
- Can I reuse this approach in the next task? Afraid to touch it.

Teach Me helps you organize what is actually worth keeping at phase boundaries, so you can review it, transfer it, and independently do the work later.

### How it works

I keep explicit learning intent separate from evidence of actual work:

1. **Skills are explicit**: “teach me”, “why”, and “review” invoke Teach Me; “quiz me” invokes Teach Me Exam, which asks for scope, format, and time before planning anything. Neither is a hook.
2. **Tool hooks**: `PreToolUse`, `PostToolUse`, and failure events record real evidence: edits, tests, builds, checks, errors, verification, configuration, data work, media work, and research.
3. **Stop hook**: scores that evidence at a phase boundary. It stays quiet for weak signals, asks for one short review for strong ones, and never starts an exam.
4. **Goal-level summary**: while one goal is active, Stop defers repeated teaching and keeps accumulating evidence; at completion, the agent writes one connected project paragraph and exactly 5 knowledge points.
5. **Teaching output**: every actual Teach Me lesson starts with `🌱 [领域：…]`, followed by `[项目：…]` when a project is known. Domains include AI, databases, mathematics, physics, software engineering, product design, and general knowledge.
6. **Local runtime**: writes the vault, updates mastery and review data, and keeps project history linked by a stable path-derived ID even when its display name changes.

### What you get

A local vault, default at `~/.teach_me_skill/vault`:

```text
vault/
├── 00_Index.md
├── 01_Knowledge_Graph.md
├── 02_Concepts/
├── 03_Algorithmic_Ideas/
├── 04_Project_Maps/
├── 05_Socratic_Questions/
├── 06_Reviews/
├── 07_Learning_Profile/
│   └── Knowledge_Tree.md
└── .teach-me/
    ├── learning-state.json
    ├── style-profile.json
    └── events.jsonl
```

Readable notes are plain Markdown. Machine state lives under `.teach-me/`, including your learner portrait (knowledge tree, mastery, style preferences). Local by default; nothing is pushed remotely unless you enable Git sync.

### The four skills

| Skill | Purpose | Typical prompt |
| --- | --- | --- |
| **Teach Me** | Collects evidence while you work, triggers reviews at phase boundaries, writes notes | “Review the debugging we just did” |
| **Teach Me Check** | Checks installation status, vault contents, learner portrait, users, and style | “Check my Teach Me status” |
| **Teach Me Recap** | Reviews captured knowledge with spaced repetition and active recall | “Help me review” |
| **Teach Me Exam** | Generates adaptive quizzes and exams from your learner portrait | “Quiz me” |

### Shape the AI's teaching personality

You can tell Teach Me how you like to be taught. After that, it explains, asks, and responds in that style instead of using a default template:

```bash
python3 ~/.codex/skills/teach-me/scripts/teach_me.py style \
  --speaking-style "friendly coach" \
  --teach-me-persona "a curious peer who explains simply and asks one short question"
```

Or use the Check skill:

```bash
python3 ~/.codex/skills/check/scripts/check_me.py style \
  --set speaking_style "concise mentor"
```

### It draws your learner portrait

As you work and review, Teach Me records:

- Which concepts you have encountered and how well you know them
- Which prerequisites are still fuzzy
- Whether you prefer analogies, concrete examples, or first-principles explanations
- Which items should be reviewed and when

This portrait is stored entirely in your local vault and is used to make teaching and review increasingly personal.

### Multiple users

Teach Me supports separate vaults per user, useful for shared machines or anyone who wants to keep their learning content isolated.

```bash
# Add a user
python3 ~/.codex/skills/teach-me/scripts/teach_me.py configure \
  --add-user alice --name Alice --github alice

# Switch active user
python3 ~/.codex/skills/teach-me/scripts/teach_me.py switch-user alice

# Or use the Check skill
python3 ~/.codex/skills/check/scripts/check_me.py profile --add alice --name Alice
python3 ~/.codex/skills/check/scripts/check_me.py profile --switch alice
```

User resolution order: `user_id` from the hook payload → `TEACH_ME_USER` environment variable → an existing GitHub user matching git config → `config.current_user`.

### Who it is for

- **Beginners**: Learn by working on real projects; every step leaves a trace of understanding.
- **People who want AI acceleration without dependency**: Turn AI output into your own knowledge.
- **Long-term maintainers**: Record architectural decisions, pitfalls, and implicit dependencies so you do not step on the same rake twice.
- **People building a personal knowledge system**: Every project becomes a course; the vault is your textbook.

### Quick start

```bash
# 1. Install
git clone https://github.com/dull-bird/teach-me-skill.git
cd teach-me-skill
./install.sh

# 2. Register hooks for your agent
./codex/install-hook.sh      # or claude-code, kimi, openclaw

# 3. Configure
python3 ~/.codex/skills/teach-me/scripts/teach_me.py configure --language auto

# 4. Code as usual; Teach Me asks for a review when it matters
```

After that:

```bash
# Check status
python3 ~/.codex/skills/check/scripts/check_me.py report

# Review
python3 ~/.codex/skills/recap/scripts/recap.py next

# Quiz / exam
python3 ~/.codex/skills/exam/scripts/exam.py plan --time 15
```

Or just speak naturally:

- “Check my Teach Me status”
- “Review the debugging we just did”
- “Help me review”
- “Quiz me”
- “Import my Obsidian vault: `/path/to/vault`”
- “Disable all Teach Me hooks” / “Enable all Teach Me hooks”
- “Move my vault to ~/Documents/Teach-Me”

### Install

```bash
git clone https://github.com/dull-bird/teach-me-skill.git
cd teach-me-skill
./install.sh
```

Install hooks for the agent you use:

```bash
./claude-code/install-hook.sh
./codex/install-hook.sh
./openclaw/install-hook.sh
./kimi/install-hook.sh
```

### First configuration

No need to memorize commands. Just tell your agent:

> “Initialize Teach Me for me, language auto.”

The agent will run:

```bash
python3 ~/.codex/skills/teach-me/scripts/teach_me.py configure --language auto
```

Before writing the first note, Teach Me asks you to confirm:

- vault path (default `~/.teach_me_skill/vault`)
- note language
- whether to enable Git sync

To use a custom vault path:

> “Put my Teach Me vault in ~/Documents/Teach-Me-Vault.”

### Import existing knowledge

You can import existing material or an entire Obsidian vault into your knowledge base:

```bash
# Import PDF / URL / Markdown / EPUB / Word
python3 ~/.codex/skills/teach-me/scripts/teach_me.py import --source pdf --path /path/to/file.pdf --project "Book Name"

# Import an entire Obsidian vault (skips .teach-me / .obsidian / system-generated notes)
python3 ~/.codex/skills/teach-me/scripts/teach_me.py import --source obsidian --path /path/to/obsidian/vault --project "My Obsidian"
```

After importing, the AI will summarize the material, ask how familiar you are with it, and offer a quiz if you already know it well.

### Toggle hooks

Temporarily disable or re-enable Teach Me hooks across all agents:

```bash
python3 ~/.codex/skills/teach-me/scripts/teach_me.py hooks --disable
python3 ~/.codex/skills/teach-me/scripts/teach_me.py hooks --enable
```

### Vault migration

If Teach Me changes its internal vault format, run the migration command to align existing vaults:

```bash
python3 ~/.codex/skills/teach-me/scripts/teach_me.py vault-version
python3 ~/.codex/skills/teach-me/scripts/teach_me.py migrate --dry-run
python3 ~/.codex/skills/teach-me/scripts/teach_me.py migrate
```

### Optional Git sync

To keep learning across devices, give the vault a Git remote:

> “Enable Git sync with remote git@github.com:user/teach-me-vault.git and auto-sync after writes.”

The agent will run:

```bash
python3 ~/.codex/skills/teach-me/scripts/teach_me.py configure \
  --language auto \
  --git-remote git@github.com:user/teach-me-vault.git \
  --auto-sync
```

Manual sync:

```bash
python3 ~/.codex/skills/teach-me/scripts/teach_me.py sync
```

Local-only version history is also possible:

```bash
python3 ~/.codex/skills/teach-me/scripts/teach_me.py configure \
  --language auto \
  --enable-git-sync
```

### Goal-level summaries and the quiet window

A `Stop` only means that one agent response ended; it does not mean that a feature, investigation, or small project is complete. A long task can contain many Stops. Teaching at every one turns a connected explanation into a stream of small interruptions, so goal-level summaries separate evidence collection from explanation delivery: accumulate quietly during the goal, then produce one map of the work at its real boundary.

| Moment | What the runtime / hook does | What the user sees |
| --- | --- | --- |
| Goal starts | The agent runs `goal start` and stores a stable goal ID, project path, domain, and optional quiet window in local `goal_sessions` | No lesson and no interruption |
| Normal work | Tool hooks continue recording edits, tests, builds, errors, and verification in `events.jsonl` | No lesson; commands are not treated as knowledge |
| Stop while the goal is active | The Stop hook records `defer_goal_end` and skips the normal phase micro-review | No repeated mini-lessons |
| Goal completes | The agent runs `goal complete`; the runtime rebuilds context from evidence since the goal began | One connected paragraph + **exactly 5** knowledge points |
| Manual recovery | “**帮我总结上面的工作**” / “summarize the work above” runs `goal summary --recent --force` | A summary of recent unsummarized work |

At completion, the runtime gives the agent a writing contract: begin with `🌱 [领域：…] [项目：…]`, write **one** coherent project paragraph, then write **exactly 5** distinct, connected, transferable knowledge points. The paragraph explains how mechanisms, decisions, and tradeoffs fit together; it is not a recital of commands. The hook never fabricates teaching text. The agent still checks the real code, documents, and conversation and must not invent facts absent from that evidence.

`summary_checkpoints` only scope manual or quiet-window requests to recent unsummarized evidence. They never shorten the final `goal complete`: even if a quiet-window fallback already produced an interim summary, completion reconsiders the full goal period so the final explanation does not lose the earlier design rationale.

`--quiet-window-minutes 15` is an opt-in fallback, not a timer. It accumulates during continuous work and may request a summary only at the **next Stop** after 15 minutes. There is no scheduler, popup, forced interruption, or automatic exam. Goal completion bypasses the wait; `0` (the default) disables the fallback.

Typical calls are below; the Teach Me skill normally runs them at a visible goal's start and completion boundaries:

```bash
# Start accumulating one project-sized goal
python3 ~/.codex/skills/teach-me/scripts/teach_me.py goal start \
  --id parser-refactor \
  --project-name "Parser refactor" \
  --project-path /absolute/path/to/repo \
  --knowledge-domain 软件工程 \
  --quiet-window-minutes 15

# Get the complete summary prompt at the completion boundary
python3 ~/.codex/skills/teach-me/scripts/teach_me.py goal complete --id parser-refactor

# Recover a missed automatic summary after work stopped
python3 ~/.codex/skills/teach-me/scripts/teach_me.py goal summary --recent --force
```

### Hook support

| Agent | Main events | Behavior |
| --- | --- | --- |
| Claude Code | `PreToolUse`, `PostToolUse`, `Stop` | Records tool evidence; normal Stop requests a short review only for strong evidence, while an active goal defers to its final summary |
| Codex | `PreToolUse`, `PostToolUse`, `Stop` | Same, plus adds `~/.teach_me_skill` as a writable root |
| Kimi Code CLI | tool/stop hooks | Reuses `~/.agents/skills/teach-me`, records supported evidence, and defers repeated reviews inside a goal |
| OpenClaw | `message:received`, `agent:bootstrap` | Injects bootstrap context; true final-review behavior needs plugin support |

### Developer tests (users can skip)

```bash
python3 -m unittest -v tests.test_teach_me_hook tests.test_goal_summary
```

## License

MIT
