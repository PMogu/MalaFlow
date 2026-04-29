import { redirect } from "next/navigation";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "https://restaurant-skill-loop-api-production.up.railway.app";

export default function AdminRedirectPage() {
  redirect(`${API_BASE_URL}/admin/login`);
}
