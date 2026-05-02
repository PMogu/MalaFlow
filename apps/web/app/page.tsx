import Link from "next/link";
import { RestaurantLoginForm } from "@/components/RestaurantLoginForm";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "https://api.malaflow.com";
const GITHUB_URL = "https://github.com/PMogu/MalaFlow";

export default function Home() {
  const adminLink = `${API_BASE_URL}/admin/login`;

  return (
    <main className="shell home-shell">
      <section className="landing-hero">
        <div className="landing-copy">
          <p className="eyebrow">MalaFlow</p>
          <h1>AI ordering that fits your current workflow.</h1>
          <p className="landing-lede">
            MalaFlow lets students order through their AI assistant. Your restaurant receives a simple pickup request,
            assigns a pickup number, and handles payment the way you already do.
          </p>
          <div className="hero-actions">
            <a className="button primary" href="#restaurant-login">
              Restaurant login
            </a>
            <Link className="button" href="/connect">
              Connect MCP
            </Link>
          </div>
          <div className="pilot-band" aria-label="Pilot scope">
            <span>No POS integration</span>
            <span>No delivery changes</span>
            <span>Small beta near Unimelb</span>
          </div>
        </div>

        <RestaurantLoginForm footerLink={{ href: adminLink, label: "Admin setup" }} id="restaurant-login" />
      </section>

      <section className="landing-section">
        <div className="section-head">
          <p className="eyebrow">How it works</p>
          <h2>A confirmed AI order becomes a small staff task.</h2>
        </div>
        <div className="step-grid">
          <article className="landing-card">
            <span className="step-number">1</span>
            <h3>A customer asks an AI assistant</h3>
            <p className="muted">They describe what they want near Unimelb, without downloading another app.</p>
          </article>
          <article className="landing-card">
            <span className="step-number">2</span>
            <h3>MalaFlow creates a pickup request</h3>
            <p className="muted">The assistant checks your menu and submits a confirmed order.</p>
          </article>
          <article className="landing-card">
            <span className="step-number">3</span>
            <h3>Staff assign a pickup number</h3>
            <p className="muted">You review the order, enter a number, and accept or reject it.</p>
          </article>
          <article className="landing-card">
            <span className="step-number">4</span>
            <h3>The assistant updates the customer</h3>
            <p className="muted">The customer receives the pickup number and walks in as usual.</p>
          </article>
        </div>
      </section>

      <section className="landing-section pilot-grid">
        <article className="pilot-copy">
          <p className="eyebrow">For pilot restaurants</p>
          <h2>Built for a small campus pilot</h2>
          <p>
            No POS integration. No delivery. No payment changes. No need to watch a new dashboard all day. When an
            order arrives, you get a reminder and decide whether to accept it.
          </p>
        </article>
        <article className="staff-board" aria-label="Example staff order card">
          <div className="staff-board-top">
            <span className="status submitted">submitted</span>
            <span className="eyebrow">Pickup request</span>
          </div>
          <h3>1x Spicy beef noodle</h3>
          <p className="muted">Note: pickup ASAP</p>
          <label className="field compact-field">
            <span className="label">Pickup number</span>
            <input className="input" readOnly value="A17" />
          </label>
          <div className="row">
            <span className="button primary preview-button">Accept</span>
            <span className="button ghost preview-button">Reject</span>
          </div>
        </article>
      </section>

      <section className="landing-section why-section">
        <div className="section-head">
          <p className="eyebrow">Why try MalaFlow?</p>
          <h2>These are the things we keep hearing</h2>
        </div>
        <div className="pain-grid">
          <p className="pain-item">□ Nearby students do not always know our restaurant exists.</p>
          <p className="pain-item">□ It is hard for students to discover us directly through existing platforms.</p>
          <p className="pain-item">□ We want more pickup orders, but do not want to adopt a complex system.</p>
          <p className="pain-item">
            □ Large platforms take high commissions, but we do not have a lightweight ordering channel of our own.
          </p>
          <p className="pain-item">
            □ We do not really know what nearby students want to order, or when they want it.
          </p>
          <p className="pain-item">
            □ We have menu items or offers to promote, but it is hard to reach nearby students.
          </p>
          <p className="pain-item">
            □ If it does not interrupt our current workflow, we are open to trying a new order channel.
          </p>
          <p className="pain-item">
            □ Others...
          </p>
        </div>
      </section>

      <footer className="site-footer">
        <span>MalaFlow is an early campus pilot near Unimelb.</span>
        <a href={GITHUB_URL}>GitHub</a>
      </footer>
    </main>
  );
}
