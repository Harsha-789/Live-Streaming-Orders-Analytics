"""
stream_graph.py - Main visualization entry point for Live Streaming Orders Analytics

Launches the file watcher (live_streamer) and renders two live-updating charts:
  1. Bar chart  — product-wise total quantity
  2. Line chart — date-wise order trend

The graph only redraws when the CSV file actually changes, so it is not
polling the disk on every animation tick.
"""

import threading

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

import db_manager
import live_streamer

CSV_FILE  = "orders.csv"
DB_FILE   = "orders.db"

# ── Shared redraw flag ──────────────────────────────────────────────────────
_needs_redraw = threading.Event()

def _on_data_changed() -> None:
    """Called by FileWatcher whenever new data is written to the DB."""
    _needs_redraw.set()

# ── Main-thread DB connection (read-only queries only) ──────────────────────
conn = db_manager.get_connection(DB_FILE)

# ── Start event-driven watcher ──────────────────────────────────────────────
watcher = live_streamer.FileWatcher(CSV_FILE, DB_FILE, _on_data_changed)
watcher.start()

# ── Figure setup ────────────────────────────────────────────────────────────
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
fig.suptitle("Live Streaming Orders Analytics — Gunji Harsha Vardhan",
             fontsize=13, fontweight="bold")


def plot_charts() -> None:
    """Query the DB and redraw both axes."""
    ax1.clear()
    ax2.clear()

    product_df = db_manager.query_product_totals(conn)
    date_df    = db_manager.query_date_totals(conn)

    # ── Bar chart: product-wise quantity ────────────────────────────────────
    if not product_df.empty:
        bars = ax1.bar(
            product_df["product_id"].astype(str),
            product_df["total_qty"],
            color="steelblue",
            edgecolor="white",
        )
        for bar, val in zip(bars, product_df["total_qty"]):
            ax1.text(bar.get_x() + bar.get_width() / 2,
                     bar.get_height() + 0.5,
                     str(val), ha="center", va="bottom", fontsize=8)
    ax1.set_title("Product-wise Total Quantity")
    ax1.set_xlabel("Product ID")
    ax1.set_ylabel("Total Quantity")
    ax1.grid(axis="y", linestyle="--", alpha=0.5)

    # ── Line chart: date-wise trend ─────────────────────────────────────────
    if not date_df.empty:
        ax2.plot(
            range(len(date_df)),
            date_df["total_qty"].values,
            marker="o",
            color="darkorange",
            linewidth=2,
            markersize=5,
        )
        ax2.fill_between(range(len(date_df)), date_df["total_qty"].values,
                         alpha=0.15, color="darkorange")
        ax2.set_xticks(range(len(date_df)))
        ax2.set_xticklabels(date_df["order_date"].tolist(),
                            rotation=45, ha="right", fontsize=7)
    ax2.set_title("Order Trend Over Time")
    ax2.set_xlabel("Order Date")
    ax2.set_ylabel("Total Quantity")
    ax2.grid(linestyle="--", alpha=0.5)

    plt.tight_layout()


def update(frame) -> None:
    """Animation callback — redraws only when new data has arrived."""
    if _needs_redraw.is_set():
        try:
            plot_charts()
        except Exception as exc:
            print(f"[stream_graph] Plot error: {exc}")
        finally:
            _needs_redraw.clear()


# Trigger an initial draw immediately
_needs_redraw.set()

ani = FuncAnimation(fig, update, interval=2000, cache_frame_data=False)

try:
    plt.show()
finally:
    print("[stream_graph] Window closed — stopping watcher …")
    watcher.stop()
    conn.close()
    print("[stream_graph] Shutdown complete.")
