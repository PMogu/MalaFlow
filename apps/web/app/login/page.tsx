import Link from "next/link";
import { RestaurantLoginForm } from "@/components/RestaurantLoginForm";

export default function LoginPage() {
  return (
    <main className="shell">
      <section className="topbar">
        <div>
          <p className="eyebrow">MalaFlow campus pilot</p>
          <h1>Restaurant workspace</h1>
        </div>
        <Link className="button" href="/">
          Home
        </Link>
      </section>
      <RestaurantLoginForm />
    </main>
  );
}
