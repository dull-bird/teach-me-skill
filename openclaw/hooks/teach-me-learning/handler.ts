import { promises as fs } from "node:fs";
import path from "node:path";
import os from "node:os";

const SESSION_DIR = path.join(
  os.homedir(),
  ".teach_me_skill",
  "openclaw-sessions",
);

const MANUAL_TRIGGERS = [
  "teach me",
  "grill me",
  "explain",
  "why",
  "教我",
  "讲讲",
  "解释",
  "原理",
  "复盘",
  "知识点",
  "知识图谱",
  "考我",
  "苏格拉底",
];

const DEV_SIGNALS = [
  "code",
  "coding",
  "debug",
  "bug",
  "frontend",
  "backend",
  "refactor",
  "review",
  "test",
  "build",
  "vite",
  "vue",
  "react",
  "node",
  "typescript",
  "javascript",
  "python",
  "api",
  "database",
  "algorithm",
  "architecture",
  "component",
  "hook",
  "代码",
  "开发",
  "项目",
  "前端",
  "后端",
  "调试",
  "报错",
  "实现",
  "修复",
  "重构",
  "评审",
  "测试",
  "构建",
  "算法",
  "架构",
  "组件",
  "页面",
  "接口",
  "数据库",
  "状态",
  "依赖",
];

interface WorkspaceBootstrapFile {
  name: string;
  path: string;
  content?: string;
  missing: boolean;
}

interface HookEvent {
  type: string;
  action: string;
  sessionKey: string;
  context: Record<string, unknown>;
  messages: string[];
}

interface SessionState {
  manual: boolean;
  devLike: boolean;
  prompt: string;
  updatedAt: string;
}

function statePath(sessionKey: string): string {
  const safe = (sessionKey || "default").replace(/[^a-zA-Z0-9_-]/g, "_");
  return path.join(SESSION_DIR, `${safe}.json`);
}

function includesAny(content: string, needles: string[]): boolean {
  const lowered = content.toLowerCase();
  return needles.some((needle) => lowered.includes(needle) || content.includes(needle));
}

async function writeSession(sessionKey: string, state: SessionState): Promise<void> {
  await fs.mkdir(SESSION_DIR, { recursive: true });
  await fs.writeFile(statePath(sessionKey), JSON.stringify(state), "utf8");
}

async function readSession(sessionKey: string): Promise<SessionState | null> {
  try {
    return JSON.parse(await fs.readFile(statePath(sessionKey), "utf8")) as SessionState;
  } catch {
    return null;
  }
}

function bootstrapContext(state: SessionState): string {
  const skillDir = path.join(os.homedir(), ".openclaw", "skills", "teach-me");
  const lines = [
    "Teach Me learning context:",
    "- Use the teach-me skill for this development-learning session.",
    `- installed skill dir: ${skillDir}`,
    "- default home: ~/.teach_me_skill",
    "- default vault: ~/.teach_me_skill/vault",
    "- first-use rule: before writing learning notes, ask the user to confirm the vault path and note language.",
    "- Do not interrupt implementation. At meaningful phase boundaries, capture 1-3 high-value concepts, algorithmic ideas, architecture/data-flow models, or project maps.",
    "- Valuable captures are not limited to tool names; capture reusable reasoning and hidden mechanisms.",
    "- Use: python3 ~/.openclaw/skills/teach-me/scripts/teach_me.py context|configure|capture|style",
  ];
  if (state.manual) {
    lines.push("- Manual teaching trigger detected: teach now and include gentle Socratic questions.");
  }
  return lines.join("\n");
}

const handler = async (event: HookEvent): Promise<void> => {
  if (event.type === "message" && event.action === "received") {
    const content = String((event.context as { content?: string }).content ?? "");
    await writeSession(event.sessionKey, {
      manual: includesAny(content, MANUAL_TRIGGERS),
      devLike: includesAny(content, DEV_SIGNALS),
      prompt: content.slice(0, 500),
      updatedAt: new Date().toISOString(),
    });
    return;
  }

  if (event.type === "agent" && event.action === "bootstrap") {
    const state = await readSession(event.sessionKey);
    if (!state || (!state.manual && !state.devLike)) return;
    const context = event.context as { bootstrapFiles: WorkspaceBootstrapFile[] };
    const files = context.bootstrapFiles ?? [];
    const target =
      files.find((f) => f.name === "AGENTS.md" && !f.missing) ??
      files.find((f) => !f.missing) ??
      files[0];
    if (!target) return;
    target.content = `${target.content ?? ""}\n\n<!-- teach-me-learning -->\n${bootstrapContext(state)}\n`;
  }
};

export default handler;
