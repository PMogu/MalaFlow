const PRODUCTION_API_BASE_URL = "https://api.malaflow.com";

export function getApiBaseUrl() {
  if (process.env.NEXT_PUBLIC_API_BASE_URL) {
    return process.env.NEXT_PUBLIC_API_BASE_URL;
  }
  return PRODUCTION_API_BASE_URL;
}

export type User = {
  id: string;
  phone: string;
  email: string | null;
  role: "restaurant";
  restaurant_id: string | null;
  is_active: boolean;
};

export type Restaurant = {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  location_text: string | null;
  location_phrase?: string | null;
  cuisine_tags: string[];
  service_modes: string[];
  status: "open" | "closed";
  mcp_visible: boolean;
  pickup_instructions: string | null;
};

export type MenuItem = {
  id: string;
  restaurant_id: string;
  name: string;
  description: string | null;
  price: string;
  currency: string;
  category: string | null;
  tags: string[];
  available: boolean;
  archived: boolean;
};

export type Order = {
  id: string;
  restaurant_id: string;
  status: "submitted" | "accepted" | "cancelled" | "rejected";
  order_number: string | null;
  customer_name: string | null;
  customer_contact: string | null;
  fulfillment_type: string;
  notes: string | null;
  reject_reason: string | null;
  cancel_reason: string | null;
  total_price: string;
  status_message?: string;
  items: Array<{
    id: string;
    menu_item_id: string;
    name_snapshot: string;
    price_snapshot: string;
    quantity: number;
    notes: string | null;
  }>;
  created_at: string;
};

const RESTAURANT_TOKEN_KEY = "rsl_restaurant_token";

export function getRestaurantToken() {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(RESTAURANT_TOKEN_KEY);
}

export function setRestaurantToken(token: string) {
  window.localStorage.setItem(RESTAURANT_TOKEN_KEY, token);
}

export function clearRestaurantToken() {
  window.localStorage.removeItem(RESTAURANT_TOKEN_KEY);
}

export async function apiFetch<T>(path: string, init: RequestInit = {}, authenticated = false): Promise<T> {
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type") && init.body) {
    headers.set("Content-Type", "application/json");
  }
  const token = authenticated ? getRestaurantToken() : null;
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...init,
    headers,
    cache: "no-store"
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || data.error || "Request failed");
  }
  return data as T;
}
