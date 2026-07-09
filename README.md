<p align="center">
  <img src="docs/assets/seedling_1f331_once.webp" alt="Teach Me logo" width="96" height="96">
</p>

<h1 align="center">Teach Me</h1>

<p align="center">
  把开发过程变成学习资产<br>
  Turn development work into learning assets
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

Teach Me 是一个面向开发学习的 Agent Skill。它支持 Claude Code、Codex、OpenClaw、Kimi Code CLI，把有价值的开发过程沉淀成本地 Obsidian 笔记、知识树、掌握度记录和复习问题。

它不是“每执行一个命令就讲课”的工具。Teach Me 的目标是让 agent 正常把事做完，同时在合适的阶段边界留下一点真正能迁移的知识：概念、算法思路、架构关系、数据流、易错点和未来可能造成 bug 的理解缺口。

### 它现在怎么工作

1. **Prompt hook 注入上下文**

   当用户明确说“教我”“复盘”“讲原理”，或提示词明显是开发、调试、重构、测试、构建等场景时，hook 会注入一段紧凑的 Teach Me context。它告诉 agent：可以使用 Teach Me，但不要打断正常实现。

2. **Tool hooks 收集证据**

   `PreToolUse`、`PostToolUse`、`PostToolUseFailure` 会记录这一轮真正发生了什么：文件编辑、测试、构建、类型检查、报错、验证结果等。它们不会直接写学习笔记，只是形成轻量 evidence。

3. **Stop hook 做阶段边界判断**

   在一轮回复结束前，Stop hook 会给这些 evidence 打分。信号弱时保持安静；信号足够强时，只请求一次短 Teach Me review。这样即使用户一开始没有说“教我”，只要 agent 实际完成了一段有学习价值的开发工作，也能触发复盘。

4. **Skill rubric 决定写不写**

   真正要不要写笔记，由 skill 在阶段边界判断。默认只捕获 1-3 个高价值点，优先选择能迁移到以后项目里的概念、隐藏机制、设计取舍、算法思路、项目地图和 bug 风险。

5. **Runtime 负责落盘**

   `scripts/teach_me.py` 负责配置、写入 Obsidian vault、更新知识树、记录掌握度、生成复习字段、可选 Git sync。hook 不直接改笔记内容。

### Learner model

Teach Me 会维护一个逐步生长的用户知识模型。遇到新领域时，agent 应该先画一条 prerequisite ladder，例如：

```text
proxy -> proxy node -> subscription provider -> config.yaml -> proxy group -> selector -> url-test -> fallback
```

然后根据对话判断哪些概念是 `unknown`、`seen`、`explained`、`practiced`、`transferable` 或 `confident`。如果只是学到了用户哪里不懂，可以用 `assess` 更新知识树，不一定写完整笔记。

Teach Me 也会主动收集轻量反馈。默认是可跳过的选择题或判断题，偶尔用简答题。用户不回答时，不会被当作“已经理解”。

### Vault 输出

默认 vault 路径：

```text
~/.teach_me_skill/vault
```

目录结构：

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

可读笔记是普通 Markdown。机器状态放在 `.teach-me/`。默认不会同步到远端。

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

第一次写学习笔记前，Teach Me 应该先让用户确认：

- vault 路径
- 笔记语言
- 是否启用 Git sync

### 可选 Git sync

Git sync 是可选项。提供远端仓库后，Teach Me 可以在 `assess`、`capture`、`style` 之后自动 commit、pull --rebase、push。

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

### 测试

```bash
python3 -m unittest -v tests.test_teach_me_hook
```

---

## English

Teach Me is an Agent Skill for development learning. It works with Claude Code, Codex, OpenClaw, and Kimi Code CLI, turning meaningful development work into local Obsidian notes, a knowledge tree, mastery records, and review prompts.

It is not a tool that explains every command. The point is to let the agent work normally, then preserve the few things that are worth learning from: concepts, algorithmic ideas, architecture relationships, data flow, hidden mechanisms, bug risks, and project maps.

### How it works now

1. **Prompt hook injects context**

   When the user explicitly asks for teaching, review, or first-principles explanation, or when the prompt is clearly about coding, debugging, refactoring, testing, or building, the hook injects compact Teach Me context. It tells the agent Teach Me is available without interrupting implementation.

2. **Tool hooks collect evidence**

   `PreToolUse`, `PostToolUse`, and `PostToolUseFailure` record what actually happened in the turn: file edits, tests, builds, type checks, errors, and verification results. These events do not write learning notes directly. They only become lightweight evidence.

3. **Stop hook scores the boundary**

   Before the final answer, the Stop hook scores the collected evidence. If the signal is weak, it stays silent. If the signal is strong enough, it requests exactly one short Teach Me review pass. This means useful learning can be captured even when the original prompt did not say “teach me.”

4. **The skill rubric decides what to keep**

   The skill decides whether the phase deserves durable notes. By default it captures only 1-3 high-value items: transferable concepts, hidden complexity, design tradeoffs, algorithmic ideas, project maps, and future bug risks.

5. **The runtime writes state**

   `scripts/teach_me.py` owns configuration, Obsidian vault writes, knowledge-tree updates, mastery state, review fields, event logs, and optional Git sync. Hooks provide context and evidence; the runtime performs deterministic file operations.

### Learner model

Teach Me keeps a growing learner model. When a new domain appears, the agent should sketch a prerequisite ladder, for example:

```text
proxy -> proxy node -> subscription provider -> config.yaml -> proxy group -> selector -> url-test -> fallback
```

Then it estimates whether each concept is `unknown`, `seen`, `explained`, `practiced`, `transferable`, or `confident`. If the useful discovery is only about the user's current understanding, the agent can run `assess` to update the knowledge tree without writing a full note.

Teach Me also asks small optional feedback probes. Most are multiple-choice or true/false checks; short-answer questions are occasional. If the user skips the probe, Teach Me keeps moving and does not treat silence as mastery.

### Vault output

Default vault path:

```text
~/.teach_me_skill/vault
```

Directory shape:

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

Readable notes are ordinary Markdown. Machine state lives under `.teach-me/`. Nothing is pushed remotely by default.

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

Before writing the first learning note, Teach Me should ask the user to confirm:

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

### Tests

```bash
python3 -m unittest -v tests.test_teach_me_hook
```

## License

MIT
