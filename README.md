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

Teach Me 通过 hooks 观察你这一轮到底做了什么，而不是只看你说的话：

1. **Prompt hook** 识别工作/学习场景，或“教我”“复盘”“为什么”这类显式学习意图。
2. **Tool hooks** 记录实际发生的证据：文件编辑、测试运行、构建、类型检查、报错、验证结果、配置改动、数据处理、媒体操作、浏览搜索等。
3. **Stop hook** 在阶段结束时给证据打分。信号弱就安静，信号强才请求一次短复盘。
4. **Skill rubric** 决定写什么：默认只抓 1-3 个高价值点——能迁移的概念、隐藏机制、决策理由、可复用思路、工作地图、未来风险。
5. **本地 runtime** 把内容写入 Obsidian vault，同时更新你的知识树、掌握度、学习画像和复习计划。

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

### 三个技能

| 技能 | 作用 | 典型说法 |
| --- | --- | --- |
| **Teach Me** | 工作时收集证据，阶段边界触发复盘，写笔记 | “复盘一下刚才的调试” |
| **Teach Me Check** | 检查安装状态、vault 内容、学习画像、用户与风格 | “帮我检查 Teach Me 状态” |
| **Teach Me Recap** | 用间隔重复 + 主动回忆复习已记录知识 | “帮我复习一下” |

### AI 的教学个性，由你塑造

你可以告诉 Teach Me 你喜欢怎么被教：

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

之后 Teach Me 会按这个风格解释、提问、反馈，而不是套用默认模板。

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

### 对话风格

你可以自定义 Teach Me 的说话风格和教学人格：

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
```

更自然的方式是直接说：

- “帮我检查 Teach Me 状态”
- “复盘一下刚才的调试”
- “帮我复习一下”
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

```bash
python3 ~/.codex/skills/teach-me/scripts/teach_me.py configure --language auto
```

第一次写笔记前， Teach Me 会让你确认：

- vault 路径
- 笔记语言
- 是否启用 Git sync

### 可选 Git sync

Git sync 是可选项。提供远端仓库后， Teach Me 可以在 `assess`、`capture`、`style` 之后自动 commit、pull --rebase、push。

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

### Hook 支持

| Agent | 主要事件 | 行为 |
| --- | --- | --- |
| Claude Code | `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `Stop` | 注入上下文、记录工具证据、Stop 阶段请求短复盘 |
| Codex | `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `Stop` | 同上，并把 `~/.teach_me_skill` 加入 writable root |
| Kimi Code CLI | prompt/tool/stop hooks | 复用 `~/.agents/skills/teach-me`，按支持事件记录证据 |
| OpenClaw | `message:received`, `agent:bootstrap` | 注入 bootstrap context；真正的 final-review 需要插件层支持 |

### 开发测试（普通用户可跳过）

```bash
python3 -m unittest -v tests.test_teach_me_hook
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

Teach Me uses hooks to observe what you actually did this turn, not just what you typed:

1. **Prompt hook** detects work/learn scenarios, or explicit learning intent like “teach me”, “review”, or “why”.
2. **Tool hooks** record evidence: file edits, test runs, builds, type checks, errors, verification results, configuration changes, data processing, media operations, and browsing/search.
3. **Stop hook** scores the evidence at the end of a phase. If the signal is weak, it stays quiet; if strong, it asks for one short review.
4. **Skill rubric** decides what to keep: by default only 1-3 high-value items—transferable concepts, hidden mechanisms, decision rationales, reusable reasoning, workflow maps, and future risks.
5. **Local runtime** writes everything into an Obsidian vault and updates your knowledge tree, mastery, learner portrait, and review schedule.

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

### The three skills

| Skill | Purpose | Typical prompt |
| --- | --- | --- |
| **Teach Me** | Collects evidence while you work, triggers reviews at phase boundaries, writes notes | “Review the debugging we just did” |
| **Teach Me Check** | Checks installation status, vault contents, learner portrait, users, and style | “Check my Teach Me status” |
| **Teach Me Recap** | Reviews captured knowledge with spaced repetition and active recall | “Help me review” |

### Shape the AI's teaching personality

You can tell Teach Me how you like to be taught:

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

After that, Teach Me explains, asks, and responds in that style instead of using a default template.

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

### Conversation style

Customize how Teach Me speaks and what persona it adopts:

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
```

Or just speak naturally:

- “Check my Teach Me status”
- “Review the debugging we just did”
- “Help me review”
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

```bash
python3 ~/.codex/skills/teach-me/scripts/teach_me.py configure --language auto
```

Before writing the first note, Teach Me asks you to confirm:

- vault path
- note language
- whether to enable Git sync

### Optional Git sync

Git sync is opt-in. With a remote repository, Teach Me can automatically commit, pull --rebase, and push after `assess`, `capture`, and `style`.

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

### Hook support

| Agent | Main events | Behavior |
| --- | --- | --- |
| Claude Code | `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `Stop` | Inject context, record tool evidence, request a short Stop review |
| Codex | `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `Stop` | Same, plus adds `~/.teach_me_skill` as a writable root |
| Kimi Code CLI | prompt/tool/stop hooks | Reuses `~/.agents/skills/teach-me` and records evidence through supported events |
| OpenClaw | `message:received`, `agent:bootstrap` | Injects bootstrap context; true final-review behavior needs plugin support |

### Developer tests (users can skip)

```bash
python3 -m unittest -v tests.test_teach_me_hook
```

## License

MIT
