"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, setRestaurantToken, User } from "@/lib/api";

export function RestaurantLoginForm() {
  const router = useRouter();
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<{ access_token: string; user: User }>("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ phone, password })
      });
      setRestaurantToken(data.access_token);
      router.push("/restaurant");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to login");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form className="panel login-panel stack" onSubmit={submit}>
      <div>
        <p className="eyebrow">MalaFlow login</p>
        <h2>Open the pickup queue</h2>
      </div>
      <label className="field">
        <span className="label">Phone</span>
        <input
          autoComplete="tel"
          className="input"
          inputMode="tel"
          required
          placeholder="+614..."
          value={phone}
          onChange={(event) => setPhone(event.target.value)}
        />
      </label>
      <label className="field">
        <span className="label">Password</span>
        <input
          autoComplete="current-password"
          className="input"
          required
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
      </label>
      {error ? <p className="notice error">{error}</p> : null}
      <button className="button primary" disabled={loading} type="submit">
        {loading ? "Signing in" : "Sign in"}
      </button>
    </form>
  );
}
