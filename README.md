# Live Streaming Orders Analytics

## Overview

This project demonstrates real-time order analytics using Python, Pandas, Matplotlib, and SQLite.

The application watches `orders.csv` for file changes using an **event-driven file watcher** and only reloads data when the file is actually modified — making it a true streaming pipeline rather than a periodic full re-read.

## Architecture

```
orders.csv
    │
    ▼ (on file-change event)
live_streamer.py  ──►  db_manager.py  ──►  orders.db (SQLite)
                                                │
                                                ▼
                                        stream_graph.py (Matplotlib)
```

| Module | Responsibility |
|---|---|
| `stream_graph.py` | Entry point; renders live bar + line charts |
| `live_streamer.py` | Background thread that watches the CSV for changes |
| `db_manager.py` | SQLite schema, parameterized inserts, query helpers |

## Features

- **Event-driven updates** — graphs only redraw when the CSV file changes
- **SQLite persistence** — all orders are stored in `orders.db` for reliable querying
- **Duplicate & invalid-data filtering** — negative quantities and exact duplicates are removed before insert
- **Graceful shutdown** — watcher thread and DB connection are closed cleanly on window close
- **Modular design** — streamer, database, and graph layers are cleanly separated

## Files

| File | Description |
|---|---|
| `stream_graph.py` | Main visualization script (entry point) |
| `live_streamer.py` | Event-driven CSV file watcher |
| `db_manager.py` | SQLite database manager (create / load / query) |
| `orders.csv` | Order dataset (append new rows to trigger live updates) |
| `requirements.txt` | Python dependencies |

## Technologies Used

- Python 3.x
- Pandas
- Matplotlib
- SQLite3 (built-in)

## How to Run

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the project:

```bash
python stream_graph.py
```

To simulate live streaming, append new rows to `orders.csv` while the application is running — the charts will update automatically.

## Output

- **Bar Chart** — product-wise total quantities (from DB)
- **Line Chart** — order trend over time, sorted chronologically (from DB)

## Author

Gunji Harsha Vardhan
