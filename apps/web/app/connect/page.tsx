import Link from "next/link";

const MCP_URL = "https://api.malaflow.com/mcp/";
const GITHUB_URL = "https://github.com/PMogu/MalaFlow";
const FIRST_PROMPT =
  "Use the malaflow skill. I want something hot near Unimelb for pickup. Only use MalaFlow tools, do not browse the web. Please search MalaFlow, help me confirm an order, then wait for the pickup number or rejection result.";

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
        <section className="panel span-8 stack">
          <p className="eyebrow">Main path</p>
          <h2>Connect with ChatGPT</h2>
          <p className="muted">
            Add MalaFlow as a custom MCP server in ChatGPT. Paste this server URL:
          </p>
          <code className="code-block">{MCP_URL}</code>
          <p className="muted">
            When the MalaFlow login page opens, enter the Access Code provided by the pilot administrator. ChatGPT
            will then attach the required authorization automatically.
          </p>
        </section>
        <section className="panel span-4 stack">
          <p className="eyebrow">First prompt</p>
          <h2>Start with malaflow</h2>
          <code className="code-block">{FIRST_PROMPT}</code>
          <p className="muted">
            For the same agent, this first prompt is usually enough. After that, you can describe food requests
            naturally.
          </p>
        </section>
      </section>

      <section className="panel stack">
        <h2>Other agents</h2>
        <p className="muted">
          For Codex, Cursor, Claude, Continue, or other MCP clients, install the MalaFlow Ordering Skill from GitHub:
          {" "}
          <a href={GITHUB_URL} target="_blank" rel="noreferrer">
            {GITHUB_URL}
          </a>
          .
        </p>
        <p className="muted">
          Add the same MCP URL manually. If your client asks for a Bearer token, paste only the Access Code. If it asks
          for headers, add <code>Authorization: Bearer &lt;MalaFlow Access Code&gt;</code>.
        </p>
      </section>
    </main>
  );
}
