import Link from "next/link";

const MCP_URL = "https://restaurant-skill-loop-api-production.up.railway.app/mcp/";
const GITHUB_URL = "https://github.com/PMogu/MalaFlow";

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
    </main>
  );
}
