import json
import os
import sqlite3
from mcp.server import FastMCP

# Same tools as 08a, but the orders live in a SQLite database (shop.db)
# instead of a Python dict, and start_return writes a real return record.
server = FastMCP("shopassist")

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, "shop.db")
TRACE_DIR = os.path.join(HERE, ".trace")


def get_db():
    """Open shop.db; on the first run, create the tables and two orders."""
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row          # rows behave like dicts
    db.execute("""CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY, item TEXT,
                    status TEXT, delivered_days_ago INTEGER)""")
    db.execute("""CREATE TABLE IF NOT EXISTS returns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT UNIQUE, label TEXT)""")
    db.execute("""INSERT OR IGNORE INTO orders VALUES
                    ('ORD-12345678', 'jacket', 'delivered', 20),
                    ('ORD-87654321', 'lamp',   'delivered', 45),
                    ('ORD-11112222', 'shoes',  'delivered', 3)""")
    db.commit()
    return db


def log(tool, order_id):
    os.makedirs(TRACE_DIR, exist_ok=True)
    with open(os.path.join(TRACE_DIR, "trace.jsonl"), "a") as f:
        f.write(json.dumps({"event": "tool", "tool": tool,
                            "order_id": order_id}) + "\n")


def error(category, customer_message, developer_message):
    return {"isError": True, "errorCategory": category, "isRetryable": False,
            "customerMessage": customer_message,
            "developerMessage": developer_message}


@server.tool()
def lookup_order(order_id: str) -> dict:
    """Look up an order by its ID. Returns the item, the status
    and how many days ago it was delivered."""
    log("lookup_order", order_id)
    with get_db() as db:
        row = db.execute("SELECT * FROM orders WHERE order_id = ?",
                         (order_id,)).fetchone()
    if row is None:
        return {"found": False, "message": "No order with this ID."}
    return {"found": True, "order": dict(row)}


@server.tool()
def start_return(order_id: str) -> dict:
    """Start a return for a delivered order inside the 30-day
    window. Returns the return label number. An order can be
    returned only once."""
    log("start_return", order_id)
    with get_db() as db:
        order = db.execute("SELECT * FROM orders WHERE order_id = ?",
                           (order_id,)).fetchone()
        if order is None:
            return error("validation", "We couldn't find an order with this ID.",
                         f"unknown order_id={order_id}")
        if order["delivered_days_ago"] > 30:
            return error("business", "This order is past the 30-day return window.",
                         f"delivered_days_ago={order['delivered_days_ago']} > 30")
        existing = db.execute("SELECT label FROM returns WHERE order_id = ?",
                              (order_id,)).fetchone()
        if existing:
            return error("business",
                         f"A return is already open for this order "
                         f"(label {existing['label']}).",
                         f"return exists for {order_id}")
        # New: save the return and make a new label from its row ID.
        cursor = db.execute("INSERT INTO returns (order_id) VALUES (?)", (order_id,))
        label = f"RET-{2000 + cursor.lastrowid}"
        db.execute("UPDATE returns SET label = ? WHERE id = ?",
                   (label, cursor.lastrowid))
    return {"return_label": label, "order_id": order_id}


if __name__ == "__main__":
    server.run(transport="stdio")
