from agents import Agent, Runner, function_tool
import sqlite3
from dotenv import load_dotenv
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "sales.db")
MAX_ROWS = 50

load_dotenv(override=True)


# A good tool description covers four things (see the deck slide
# "Writing Good Tool Descriptions"):
#   1. what the tool does and what it returns
#   2. the input format, with example queries
#   3. edge cases: no rows, bad input, too many rows
#   4. the neighbour tool to use instead, and when
@function_tool
def run_sql(query: str) -> str:
    """Run one read-only SQLite SELECT on the `sales` table
    (product, quantity, revenue, sale_date) and return the
    rows as text, one row per line.

    Input: a single SELECT statement, e.g.
      SELECT product, SUM(revenue) FROM sales GROUP BY product
      SELECT * FROM sales WHERE sale_date LIKE '2026-03%'

    Returns "No rows" when nothing matches and "Error: ..."
    for invalid SQL. Fix the query and retry. Output stops at
    50 rows, so use LIMIT or aggregate.

    For one product's total revenue, use
    get_product_revenue(product) instead.
    """
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute(query).fetchall()
    except sqlite3.Error as e:
        # Return the error as text so the model can fix its query and retry.
        return f"Error: {e}"
    finally:
        conn.close()

    if not rows:
        return "No rows"
    lines = [str(row) for row in rows[:MAX_ROWS]]
    if len(rows) > MAX_ROWS:
        lines.append(f"... {len(rows) - MAX_ROWS} more rows not shown")
    return "\n".join(lines)


@function_tool
def get_product_revenue(product: str) -> str:
    """Return the total revenue for one product, e.g. "Laptop".

    The match ignores case. Returns "Unknown product: ..." if
    no sale has that product name.

    For anything else (several products, dates, quantities,
    rankings), use run_sql instead.
    """
    conn = sqlite3.connect(DB_PATH)
    try:
        total = conn.execute(
            "SELECT SUM(revenue) FROM sales WHERE LOWER(product) = LOWER(?)",
            (product,),
        ).fetchone()[0]
    finally:
        conn.close()

    if total is None:
        return f"Unknown product: {product}"
    return f"{product}: total revenue {total}"


agent = Agent(
    name="Sales Assistant",
    model="gpt-4o-mini",
    instructions="""
    You help users answer questions about the sales database.
    Use the tools whenever database information is needed.
    """,
    tools=[run_sql, get_product_revenue],
)

result = Runner.run_sync(
    agent,
    # "What is the total revenue for Laptop?"   # -> get_product_revenue
    "Which products generated more than ₹200,000 in revenue?"  # -> run_sql
)

print(result.final_output)
