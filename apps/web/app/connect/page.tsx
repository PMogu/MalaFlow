import Link from "next/link";

const MCP_URL = "https://restaurant-skill-loop-api-production.up.railway.app/mcp/";
const GITHUB_URL = "https://github.com/PMogu/MalaFlow";
const AGENTS_SNIPPET =
  "For Unimelb food ordering, pickup, restaurant search, menu recommendations, and order status, use the malaflow skill. Only use MalaFlow MCP tools; do not browse the web for ordering results. If MalaFlow is unavailable or has no match, tell the user directly.";

export default function ConnectPage() {
  return (
    <main className="shell">
      <section className="topbar">
        <div>
          <p className="eyebrow">Connect your AI assistant</p>
          <h1>Order food through MalaFlow</h1>
        </div>
        <Link className="button" href="/">
          Workspace login
        </Link>
      </section>

      <section className="grid">
        <section className="panel span-4 stack">
          <p className="eyebrow">Step 1</p>
          <h2>Install the MalaFlow Ordering Skill</h2>
          <p className="muted">
            Install the MalaFlow Ordering Skill from GitHub:{" "}
            <a href={GITHUB_URL} target="_blank" rel="noreferrer">
              {GITHUB_URL}
            </a>
          </p>
          <p className="muted">If you don&apos;t know where to put the file, ask your agent.</p>
        </section>
        <section className="panel span-4 stack">
          <p className="eyebrow">Step 2</p>
          <h2>Add this server</h2>
          <code className="code-block">{MCP_URL}</code>
          <p className="muted">
            You will need a MalaFlow Access Code, also called a Bearer token, from the pilot administrator.
          </p>
        </section>
        <section className="panel span-4 stack">
          <p className="eyebrow">Step 3</p>
          <h2>Start with the skill</h2>
          <code className="code-block">
            Use the MalaFlow skill. I want something hot near Unimelb for pickup. Can you help me order?
          </code>
        </section>
      </section>

      <section className="panel stack">
        <h2>Use it once per agent</h2>
        <p className="muted">
          If you keep using the same agent, you usually only need to mention the malaflow skill once. You can also
          paste this into AGENTS.md for that project:
        </p>
        <code className="code-block">{AGENTS_SNIPPET}</code>
      </section>
    </main>
  );
}
