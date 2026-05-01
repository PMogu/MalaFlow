import { redirect } from "next/navigation";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "https://api.malaflow.com";

export default function AdminRedirectPage() {
  redirect(`${API_BASE_URL}/admin/login`);
}
