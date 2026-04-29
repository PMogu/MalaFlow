import Link from "next/link";
import { RestaurantLoginForm } from "@/components/RestaurantLoginForm";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "https://restaurant-skill-loop-api-production.up.railway.app";

export default function Home() {
  return (
    <main className="shell home-shell">
      <section className="topbar">
        <div>
          <p className="eyebrow">MalaFlow</p>
          <h1>AI assistant orders, handed to real restaurants</h1>
        </div>
        <Link className="button" href="/connect">
          Connect MCP
        </Link>
      </section>

      <section className="home-grid">
        <RestaurantLoginForm />
        <section className="panel stack pilot-note">
          <p className="eyebrow">Unimelb nearby restaurants</p>
          <h2>MalaFlow turns an Agent conversation into a pickup request staff can confirm.</h2>
          <p className="muted">
            Staff review the order, enter a pickup number, and accept it. The external Agent checks back through MCP
            and tells the user which number to quote at the counter.
          </p>
          <div className="mini-flow">
            <span>User</span>
            <span>Agent</span>
            <span>MCP</span>
            <span>Restaurant</span>
            <span>Pickup number</span>
          </div>
        </section>
      </section>

      <footer className="site-footer">
        <span>MalaFlow campus pilot.</span>
        <a href={`${API_BASE_URL}/admin/login`}>Admin</a>
      </footer>
    </main>
  );
}
