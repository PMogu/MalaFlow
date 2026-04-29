"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { apiFetch, clearRestaurantToken, MenuItem, Order, Restaurant } from "@/lib/api";

type MenuForm = {
  name: string;
  description: string;
  price: string;
  currency: string;
  category: string;
  tags: string;
  available: boolean;
};

const emptyMenu: MenuForm = {
  name: "",
  description: "",
  price: "15.80",
  currency: "AUD",
  category: "Rice",
  tags: "spicy",
  available: true
};

function menuFormFromItem(item: MenuItem): MenuForm {
  return {
    name: item.name,
    description: item.description || "",
    price: item.price,
    currency: item.currency,
    category: item.category || "",
    tags: item.tags.join(", "),
    available: item.available
  };
}

function menuPayload(form: MenuForm) {
  return {
    ...form,
    description: form.description || null,
    price: Number(form.price),
    category: form.category || null,
    tags: form.tags
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean)
  };
}

function playAlertSound() {
  const AudioContextClass =
    window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!AudioContextClass) return;
  const context = new AudioContextClass();
  const oscillator = context.createOscillator();
  const gain = context.createGain();
  oscillator.type = "sine";
  oscillator.frequency.value = 740;
  gain.gain.setValueAtTime(0.0001, context.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.12, context.currentTime + 0.02);
  gain.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + 0.28);
  oscillator.connect(gain);
  gain.connect(context.destination);
  oscillator.start();
  oscillator.stop(context.currentTime + 0.3);
}

export default function RestaurantPage() {
  const [restaurant, setRestaurant] = useState<Restaurant | null>(null);
  const [menuItems, setMenuItems] = useState<MenuItem[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [menuForm, setMenuForm] = useState<MenuForm>(emptyMenu);
  const [editingItemId, setEditingItemId] = useState<string | null>(null);
  const [editMenuForm, setEditMenuForm] = useState<MenuForm>(emptyMenu);
  const [orderNumbers, setOrderNumbers] = useState<Record<string, string>>({});
  const [rejectReasons, setRejectReasons] = useState<Record<string, string>>({});
  const [alertsEnabled, setAlertsEnabled] = useState(false);
  const [notificationPermission, setNotificationPermission] = useState<NotificationPermission | "unsupported">(
    "default"
  );
  const [error, setError] = useState<string | null>(null);
  const initializedOrdersRef = useRef(false);
  const seenSubmittedRef = useRef<Set<string>>(new Set());

  const submittedOrders = useMemo(() => orders.filter((order) => order.status === "submitted"), [orders]);
  const submittedCount = submittedOrders.length;

  async function loadOrders() {
    const orderData = await apiFetch<{ orders: Order[] }>("/api/restaurant/orders", {}, true);
    setOrders(orderData.orders);
  }

  async function load() {
    const [restaurantData, menuData, orderData] = await Promise.all([
      apiFetch<{ restaurant: Restaurant }>("/api/restaurant/me", {}, true),
      apiFetch<{ menu_items: MenuItem[] }>("/api/restaurant/menu", {}, true),
      apiFetch<{ orders: Order[] }>("/api/restaurant/orders", {}, true)
    ]);
    setRestaurant(restaurantData.restaurant);
    setMenuItems(menuData.menu_items);
    setOrders(orderData.orders);
  }

  useEffect(() => {
    setAlertsEnabled(window.localStorage.getItem("rsl_order_alerts") === "true");
    setNotificationPermission("Notification" in window ? Notification.permission : "unsupported");
    void load().catch((cause) => setError(cause instanceof Error ? cause.message : "Unable to load workspace"));
    const interval = window.setInterval(() => {
      void loadOrders().catch((cause) => setError(cause instanceof Error ? cause.message : "Unable to refresh orders"));
    }, 12000);
    return () => window.clearInterval(interval);
  }, []);

  useEffect(() => {
    const submittedIds = submittedOrders.map((order) => order.id);
    if (!initializedOrdersRef.current) {
      seenSubmittedRef.current = new Set(submittedIds);
      initializedOrdersRef.current = true;
    } else {
      const freshIds = submittedIds.filter((id) => !seenSubmittedRef.current.has(id));
      if (freshIds.length && alertsEnabled) {
        triggerOrderAlert(freshIds.length);
      }
      seenSubmittedRef.current = new Set(submittedIds);
    }
    document.title = submittedCount ? `(${submittedCount}) MalaFlow orders` : "MalaFlow workspace";
  }, [submittedOrders, submittedCount, alertsEnabled]);

  useEffect(() => {
    return () => {
      document.title = "MalaFlow";
    };
  }, []);

  function triggerOrderAlert(count: number) {
    playAlertSound();
    if ("Notification" in window && Notification.permission === "granted") {
      try {
        new Notification("New MCP order", {
          body: `${count} submitted order${count === 1 ? "" : "s"} waiting for a pickup number.`
        });
      } catch {
        // Browser notifications can fail in some embedded contexts; the in-page badge remains visible.
      }
    }
  }

  async function enableAlerts() {
    if ("Notification" in window) {
      const permission = await Notification.requestPermission();
      setNotificationPermission(permission);
    } else {
      setNotificationPermission("unsupported");
    }
    window.localStorage.setItem("rsl_order_alerts", "true");
    setAlertsEnabled(true);
    playAlertSound();
  }

  async function saveRestaurant(event: FormEvent) {
    event.preventDefault();
    if (!restaurant) return;
    setError(null);
    try {
      const data = await apiFetch<{ restaurant: Restaurant }>(
        "/api/restaurant/me",
        {
          method: "PATCH",
          body: JSON.stringify(restaurant)
        },
        true
      );
      setRestaurant(data.restaurant);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to save restaurant");
    }
  }

  async function createMenuItem(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await apiFetch(
        "/api/restaurant/menu",
        {
          method: "POST",
          body: JSON.stringify(menuPayload(menuForm))
        },
        true
      );
      setMenuForm(emptyMenu);
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to create menu item");
    }
  }

  async function saveMenuItem(itemId: string) {
    setError(null);
    try {
      await apiFetch(
        `/api/restaurant/menu/${itemId}`,
        {
          method: "PATCH",
          body: JSON.stringify(menuPayload(editMenuForm))
        },
        true
      );
      setEditingItemId(null);
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to update menu item");
    }
  }

  async function removeMenuItem(item: MenuItem) {
    if (!window.confirm(`Remove ${item.name} from the active menu?`)) return;
    setError(null);
    try {
      await apiFetch(`/api/restaurant/menu/${item.id}`, { method: "DELETE" }, true);
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to remove menu item");
    }
  }

  async function accept(orderId: string) {
    setError(null);
    try {
      await apiFetch(
        `/api/restaurant/orders/${orderId}/accept`,
        {
          method: "PATCH",
          body: JSON.stringify({ order_number: orderNumbers[orderId] || "" })
        },
        true
      );
      await loadOrders();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to accept order");
    }
  }

  async function reject(orderId: string) {
    setError(null);
    try {
      await apiFetch(
        `/api/restaurant/orders/${orderId}/reject`,
        {
          method: "PATCH",
          body: JSON.stringify({ reason: rejectReasons[orderId] || "Restaurant rejected the order" })
        },
        true
      );
      await loadOrders();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to reject order");
    }
  }

  return (
    <main className="shell">
      <section className="topbar">
        <div>
          <p className="eyebrow">Campus pilot workspace</p>
          <h1>{restaurant?.name || "Restaurant queue"}</h1>
        </div>
        <div className="row">
          <button
            className="button ghost"
            onClick={() => {
              clearRestaurantToken();
              location.href = "/login";
            }}
          >
            Logout
          </button>
        </div>
      </section>

      {error ? <p className="notice error">{error}</p> : null}

      <section className={`alert-strip ${submittedCount ? "active" : ""}`}>
        <strong>{submittedCount} submitted order{submittedCount === 1 ? "" : "s"}</strong>
        <span>Enter a pickup number and accept so the user&apos;s Agent can report it back.</span>
        <button className="button" type="button" onClick={() => void enableAlerts()}>
          {alertsEnabled ? "Alerts enabled" : "Enable alerts"}
        </button>
        <span className="muted">Notification: {notificationPermission}</span>
      </section>

      <section className="grid">
        <section className="panel span-4 stack">
          <p className="eyebrow">Queue</p>
          <h2>{submittedCount} waiting for pickup number</h2>
          <p className="muted">
            Accepted means the order has a number the user can quote at the counter. Payment still happens offline.
          </p>
          <div className="row">
            <span className={`status ${restaurant?.status}`}>{restaurant?.status || "loading"}</span>
            <span className="status">{restaurant?.mcp_visible ? "MCP visible" : "MCP hidden"}</span>
          </div>
        </section>

        <form className="panel span-8 stack" onSubmit={saveRestaurant}>
          <h2>Restaurant status</h2>
          <div className="split">
            <label className="field">
              <span className="label">Name</span>
              <input
                className="input"
                value={restaurant?.name || ""}
                onChange={(event) => restaurant && setRestaurant({ ...restaurant, name: event.target.value })}
              />
            </label>
            <label className="field">
              <span className="label">Status</span>
              <select
                className="select"
                value={restaurant?.status || "open"}
                onChange={(event) =>
                  restaurant && setRestaurant({ ...restaurant, status: event.target.value as Restaurant["status"] })
                }
              >
                <option value="open">open</option>
                <option value="closed">closed</option>
              </select>
            </label>
          </div>
          <label className="field">
            <span className="label">Restaurant location</span>
            <input
              className="input"
              placeholder="Near Unimelb, e.g. Swanston St"
              value={restaurant?.location_text || ""}
              onChange={(event) => restaurant && setRestaurant({ ...restaurant, location_text: event.target.value })}
            />
          </label>
          <label className="field">
            <span className="label">Pickup instructions</span>
            <input
              className="input"
              value={restaurant?.pickup_instructions || ""}
              onChange={(event) =>
                restaurant && setRestaurant({ ...restaurant, pickup_instructions: event.target.value })
              }
            />
          </label>
          <div className="row">
            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={Boolean(restaurant?.mcp_visible)}
                onChange={(event) => restaurant && setRestaurant({ ...restaurant, mcp_visible: event.target.checked })}
              />
              MCP visible
            </label>
            <button className="button primary" type="submit">
              Save status
            </button>
          </div>
        </form>

        <section className="panel full stack">
          <h2>Submitted order queue</h2>
          <table className="table">
            <thead>
              <tr>
                <th>Order</th>
                <th>Items</th>
                <th>Notes</th>
                <th>Total</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {submittedOrders.length ? (
                submittedOrders.map((order) => (
                  <tr key={order.id}>
                    <td>{order.id}</td>
                    <td>{order.items.map((item) => `${item.quantity}x ${item.name_snapshot}`).join(", ")}</td>
                    <td>{order.notes || "-"}</td>
                    <td>${order.total_price}</td>
                    <td>
                      <div className="stack compact-actions">
                        <input
                          className="input"
                          placeholder="Pickup number, e.g. A17"
                          value={orderNumbers[order.id] || ""}
                          onChange={(event) => setOrderNumbers({ ...orderNumbers, [order.id]: event.target.value })}
                        />
                        <div className="row">
                          <button className="button primary" type="button" onClick={() => void accept(order.id)}>
                            Accept
                          </button>
                          <input
                            className="input reject-input"
                            placeholder="Reject reason"
                            value={rejectReasons[order.id] || ""}
                            onChange={(event) =>
                              setRejectReasons({ ...rejectReasons, [order.id]: event.target.value })
                            }
                          />
                          <button className="button danger" type="button" onClick={() => void reject(order.id)}>
                            Reject
                          </button>
                        </div>
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5}>No submitted orders right now.</td>
                </tr>
              )}
            </tbody>
          </table>
        </section>

        <form className="panel span-4 stack" onSubmit={createMenuItem}>
          <h2>Add menu item</h2>
          <label className="field">
            <span className="label">Name</span>
            <input className="input" value={menuForm.name} onChange={(event) => setMenuForm({ ...menuForm, name: event.target.value })} />
          </label>
          <label className="field">
            <span className="label">Description</span>
            <textarea className="textarea" value={menuForm.description} onChange={(event) => setMenuForm({ ...menuForm, description: event.target.value })} />
          </label>
          <div className="split">
            <label className="field">
              <span className="label">Price</span>
              <input className="input" value={menuForm.price} onChange={(event) => setMenuForm({ ...menuForm, price: event.target.value })} />
            </label>
            <label className="field">
              <span className="label">Category</span>
              <input className="input" value={menuForm.category} onChange={(event) => setMenuForm({ ...menuForm, category: event.target.value })} />
            </label>
          </div>
          <label className="field">
            <span className="label">Tags</span>
            <input className="input" value={menuForm.tags} onChange={(event) => setMenuForm({ ...menuForm, tags: event.target.value })} />
          </label>
          <label className="checkbox-row">
            <input type="checkbox" checked={menuForm.available} onChange={(event) => setMenuForm({ ...menuForm, available: event.target.checked })} />
            Available
          </label>
          <button className="button primary" type="submit">
            Add item
          </button>
        </form>

        <section className="panel span-8 stack">
          <h2>Menu</h2>
          <table className="table">
            <thead>
              <tr>
                <th>Item</th>
                <th>Category</th>
                <th>Price</th>
                <th>Available</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {menuItems.map((item) => (
                <tr key={item.id}>
                  {editingItemId === item.id ? (
                    <>
                      <td>
                        <input className="input" value={editMenuForm.name} onChange={(event) => setEditMenuForm({ ...editMenuForm, name: event.target.value })} />
                        <textarea className="textarea compact-textarea" value={editMenuForm.description} onChange={(event) => setEditMenuForm({ ...editMenuForm, description: event.target.value })} />
                      </td>
                      <td>
                        <input className="input" value={editMenuForm.category} onChange={(event) => setEditMenuForm({ ...editMenuForm, category: event.target.value })} />
                        <input className="input" value={editMenuForm.tags} onChange={(event) => setEditMenuForm({ ...editMenuForm, tags: event.target.value })} />
                      </td>
                      <td>
                        <input className="input" value={editMenuForm.price} onChange={(event) => setEditMenuForm({ ...editMenuForm, price: event.target.value })} />
                      </td>
                      <td>
                        <label className="checkbox-row">
                          <input type="checkbox" checked={editMenuForm.available} onChange={(event) => setEditMenuForm({ ...editMenuForm, available: event.target.checked })} />
                          yes
                        </label>
                      </td>
                      <td>
                        <div className="row">
                          <button className="button primary" type="button" onClick={() => void saveMenuItem(item.id)}>
                            Save
                          </button>
                          <button className="button ghost" type="button" onClick={() => setEditingItemId(null)}>
                            Cancel
                          </button>
                        </div>
                      </td>
                    </>
                  ) : (
                    <>
                      <td>
                        <strong>{item.name}</strong>
                        <p className="muted">{item.description || "-"}</p>
                      </td>
                      <td>{item.category || "-"}</td>
                      <td>${item.price}</td>
                      <td>{item.available ? "yes" : "no"}</td>
                      <td>
                        <div className="row">
                          <button
                            className="button"
                            type="button"
                            onClick={() => {
                              setEditingItemId(item.id);
                              setEditMenuForm(menuFormFromItem(item));
                            }}
                          >
                            Edit
                          </button>
                          <button className="button danger" type="button" onClick={() => void removeMenuItem(item)}>
                            Remove
                          </button>
                        </div>
                      </td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section className="panel full stack">
          <h2>Recent orders</h2>
          <table className="table">
            <thead>
              <tr>
                <th>Order</th>
                <th>Status</th>
                <th>Pickup number</th>
                <th>Total</th>
              </tr>
            </thead>
            <tbody>
              {orders.slice(0, 10).map((order) => (
                <tr key={order.id}>
                  <td>{order.id}</td>
                  <td>
                    <span className={`status ${order.status}`}>{order.status}</span>
                  </td>
                  <td>{order.order_number || "-"}</td>
                  <td>${order.total_price}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </section>
    </main>
  );
}
