import Link from "next/link";

const MCP_URL = "https://restaurant-skill-loop-api-production.up.railway.app/mcp/";

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
          <h2>Open an MCP-capable assistant</h2>
          <p className="muted">Use Codex, Claude, Cursor, Continue, or another client that can add an HTTP MCP server.</p>
        </section>
        <section className="panel span-4 stack">
          <p className="eyebrow">Step 2</p>
          <h2>Add this server</h2>
          <code className="code-block">{MCP_URL}</code>
          <p className="muted">Use your pilot access token as a Bearer token when the client asks for authorization.</p>
        </section>
        <section className="panel span-4 stack">
          <p className="eyebrow">Step 3</p>
          <h2>Try a campus pickup prompt</h2>
          <code className="code-block">I want beef noodles near Unimelb. Can you help me order pickup?</code>
        </section>
      </section>

      <section className="panel stack">
        <h2>Codex CLI</h2>
        <code className="code-block">
          export RESTAURANT_MCP_BEARER_TOKEN=&quot;&lt;pilot access token&gt;&quot;{"\n"}
          codex mcp add malaflow --url {MCP_URL} --bearer-token-env-var
          RESTAURANT_MCP_BEARER_TOKEN{"\n"}
          codex mcp list
        </code>
      </section>
    </main>
  );
}
