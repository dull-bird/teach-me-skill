# Teach Me Check 操作手册

Teach Me Check 是一个只读诊断技能，用来回答“Teach Me 装好了吗？”、“我的学习记录在哪里？”、“怎么改配置？”这类问题。它不会修改你的 vault 或配置，除非你又额外发出了明确指令。

---

## 1. 它能做什么

运行一次检查，你会看到：

| 检查项 | 说明 |
| --- | --- |
| 安装状态 | 哪些 agent（Claude Code / Codex / Kimi / OpenClaw）已经注册了 Teach Me hook |
| 当前用户 | 当前生效的用户 ID、名称、GitHub |
| 配置项 | vault 路径、笔记语言、每阶段最多笔记数、是否完成首次配置 |
| Vault 内容 | 概念、算法思想、项目地图、苏格拉底问题、复盘、知识树节点、事件总数等 |
| 学习画像 | 风格偏好、掌握度分布、薄弱项 |
| 最近活动 | 最近 200 条事件里各类型的数量（prompt、tool、capture、assessment 等） |
| Git sync | 是否开启、远程仓库、分支、本地仓库是否初始化、是否有未提交改动 |
| 下一步建议 | 用自然语言即可发起的后续操作 |

---

## 2. 怎么用

### 让 agent 帮你检查

直接对 agent 说：

```text
帮我检查一下 Teach Me 的状态
```

agent 会运行：

```bash
python3 ~/.codex/skills/check/scripts/check_me.py report
```

然后用自然语言把结果告诉你。

### 获取结构化数据

如果你自己想看原始数据：

```bash
python3 ~/.codex/skills/check/scripts/check_me.py report --json
```

### 查看操作手册

```bash
python3 ~/.codex/skills/check/scripts/check_me.py manual
```

---

## 3. 常用自然语言指令

检查完后，你可以继续用自然语言让 agent 帮你调整。下面是一些例子：

### 修改配置

- “把 Teach Me vault 改到 `~/Documents/Teach-Me`”
- “把笔记语言改成英文” / “把笔记语言改成中文” / “让笔记语言跟随系统自动”
- “把每阶段最多笔记数改成 5”

对应命令（agent 内部会执行）：

```bash
python3 ~/.codex/skills/teach-me/scripts/teach_me.py configure \
  --vault ~/Documents/Teach-Me \
  --language auto
```

### Git sync

直接说：

- “开启 Git sync 到 `git@github.com:user/teach-me-vault.git`，写入后自动同步。”
- “开启自动同步。”
- “关闭 Git sync。”
- “立刻同步一次 vault。”

对应命令：

```bash
python3 ~/.codex/skills/teach-me/scripts/teach_me.py configure \
  --git-remote git@github.com:user/teach-me-vault.git \
  --auto-sync

python3 ~/.codex/skills/teach-me/scripts/teach_me.py sync
```

### 查看记录

- “给我看看最近的学习记录”
- “最近记录了哪些概念？”
- “帮我整理一下知识图谱”

agent 会读取 `vault/.teach-me/events.jsonl`、`learning-state.json` 和 `01_Knowledge_Graph.md` 后回答你。

---

## 4. 文件位置

```text
~/.teach_me_skill/
├── config.json                 # 全局配置
└── vault/                      # Obsidian vault（路径可配置）
    ├── .teach-me/
    │   ├── learning-state.json # 概念、知识树、评估记录
    │   ├── style-profile.json  # 笔记风格偏好
    │   └── events.jsonl        # 运行事件日志
    ├── 00_Index.md
    ├── 01_Knowledge_Graph.md
    ├── 02_Concepts/
    ├── 03_Algorithmic_Ideas/
    ├── 04_Project_Maps/
    ├── 05_Socratic_Questions/
    ├── 06_Reviews/
    └── 07_Learning_Profile/
        └── Knowledge_Tree.md
```

---

## 5. 常见问题

### Q: 为什么检测不到 hook？

A: 可能你只运行了 `./install.sh`（复制 skill 文件），但没有运行对应 agent 的 `./codex/install-hook.sh` 或 `./kimi/install-hook.sh` 等。检查完会提示你补跑哪一步。

### Q: vault 里为什么空空如也？

A: Teach Me 是“有值得学的才记录”，不是每轮对话都写。只有你完成了一轮有学习价值的开发/调试/复盘后，Stop hook 才会请求写入。如果你刚安装，可能还没有记录。

### Q: 可以手动触发一次记录吗？

A: 可以。对 agent 说“复盘一下刚才的过程”或“把刚才的调试写成学习笔记”。agent 会调用 `teach_me.py capture`。

### Q: Git sync 开启后没有自动 push？

A: 检查三点：

1. `--git-remote` 是否设置正确；
2. 本地仓库是否已初始化（`vault/.git` 是否存在）；
3. SSH key 是否有权限访问该仓库。

可以运行一次手动同步看看报错：

```bash
python3 ~/.codex/skills/teach-me/scripts/teach_me.py sync
```

---

## 6. 设计原则

- **零额外依赖**：只使用 Python 标准库。
- **只读默认**：`check_me.py report` 不会修改任何文件。
- **自然语言优先**：检查结果用日常语言呈现，并在末尾给出可直接说的后续指令示例。
- **不替代主 skill**：配置修改、笔记写入、同步等操作仍由 `teach_me.py` 负责；Check 只负责展示状态和引导下一步。
