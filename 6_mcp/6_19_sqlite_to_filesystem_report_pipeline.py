# pip install mcp-server-sqlite (already in requirements.txt)
# Needs Node.js/npm (npx) for the filesystem server - no extra pip install for that one.
#
# Same two-server report pipeline as before, no LLM involved - this is
# plain orchestration, not an agent - but now seeded from a real sample of
# the Kaggle "Global Superstore" dataset
# (https://www.kaggle.com/datasets/fatihilhan/global-superstore-dataset,
# 6_mcp/datasets/superstore.csv, ~51k rows) instead of a handful of
# hardcoded rows:
#   1. Anthropic's official mcp-server-sqlite (also used in 6_13) holds a
#      random sample of real orders - pandas reads/cleans the CSV here in
#      the client; the MCP server itself only ever sees plain SQL text,
#      never the DataFrame.
#   2. Four read_query aggregates build a richer report: revenue/profit by
#      category, by region, the top 5 products by profit, and the yearly
#      sales trend.
#   3. The official @modelcontextprotocol/server-filesystem (also used in
#      6_14) writes the formatted report out as a real file, sandboxed to
#      a reports/ directory - the two servers never talk to each other
#      directly, this script is the thing that reads from one and writes
#      to the other.
import asyncio
import os
import sys

import pandas as pd
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "sales_report_data.db")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
CSV_PATH = os.path.join(BASE_DIR, "datasets", "superstore.csv")
os.makedirs(REPORTS_DIR, exist_ok=True)

SAMPLE_SIZE = 1500
BATCH_SIZE = 300

# The source CSV's headers (e.g. "Order.ID") aren't valid SQL/Python
# identifiers - this both selects the columns we need and renames them.
COLUMN_MAP = {
    "Order.ID": "order_id",
    "Order.Date": "order_date",
    "Ship.Date": "ship_date",
    "Ship.Mode": "ship_mode",
    "Segment": "segment",
    "Region": "region",
    "Market": "market",
    "Category": "category",
    "Sub.Category": "sub_category",
    "Product.Name": "product_name",
    "Sales": "sales",
    "Quantity": "quantity",
    "Discount": "discount",
    "Profit": "profit",
    "Order.Priority": "order_priority",
    "Year": "year",
}


def _escape(value) -> str:
    return str(value).replace("'", "''")


def load_sales_sample() -> list[tuple]:
    df = pd.read_csv(CSV_PATH)[list(COLUMN_MAP)].rename(columns=COLUMN_MAP)
    df = df.sample(n=SAMPLE_SIZE, random_state=42)
    # Timestamps arrive as "2011-01-07 00:00:00.000" - only the date part matters here.
    df["order_date"] = df["order_date"].str[:10]
    df["ship_date"] = df["ship_date"].str[:10]

    return [
        (
            _escape(r.order_id), r.order_date, r.ship_date, _escape(r.ship_mode),
            _escape(r.segment), _escape(r.region), _escape(r.market), _escape(r.category),
            _escape(r.sub_category), _escape(r.product_name), r.sales, int(r.quantity),
            r.discount, r.profit, _escape(r.order_priority), int(r.year),
        )
        for r in df.itertuples(index=False)
    ]


def build_insert_sql(rows: list[tuple]) -> str:
    values = ",".join(
        "('{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', {}, {}, {}, {}, '{}', {})".format(*row)
        for row in rows
    )
    return f"""INSERT INTO sales (
        order_id, order_date, ship_date, ship_mode, segment, region, market,
        category, sub_category, product_name, sales, quantity, discount,
        profit, order_priority, year
    ) VALUES {values}"""


async def main():
    sqlite_params = StdioServerParameters(
        command="mcp-server-sqlite",
        args=["--db-path", DB_PATH],
    )
    filesystem_params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", REPORTS_DIR],
    )

    sales_rows = load_sales_sample()

    async with stdio_client(sqlite_params) as (sql_read, sql_write):
        async with ClientSession(sql_read, sql_write) as sql:
            await sql.initialize()

            print("=== [SQLite] create_table + seed sales sample ===")
            # DROP first: an older run of this script may have left a
            # "sales" table behind with the previous (different) schema,
            # and CREATE TABLE IF NOT EXISTS would silently keep that one.
            await sql.call_tool("write_query", {"query": "DROP TABLE IF EXISTS sales"})
            await sql.call_tool("create_table", {"query": """
                CREATE TABLE IF NOT EXISTS sales (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT NOT NULL,
                    order_date TEXT NOT NULL,
                    ship_date TEXT NOT NULL,
                    ship_mode TEXT NOT NULL,
                    segment TEXT NOT NULL,
                    region TEXT NOT NULL,
                    market TEXT NOT NULL,
                    category TEXT NOT NULL,
                    sub_category TEXT NOT NULL,
                    product_name TEXT NOT NULL,
                    sales REAL NOT NULL,
                    quantity INTEGER NOT NULL,
                    discount REAL NOT NULL,
                    profit REAL NOT NULL,
                    order_priority TEXT NOT NULL,
                    year INTEGER NOT NULL
                )
            """})
            await sql.call_tool("write_query", {"query": "DELETE FROM sales"})
            for i in range(0, len(sales_rows), BATCH_SIZE):
                batch = sales_rows[i:i + BATCH_SIZE]
                await sql.call_tool("write_query", {"query": build_insert_sql(batch)})
            print(f"Seeded {len(sales_rows)} rows sampled from {CSV_PATH}")

            print("\n=== [SQLite] read_query: revenue & profit by category ===")
            by_category = await sql.call_tool("read_query", {"query": """
                SELECT category, SUM(quantity) AS total_units,
                       ROUND(SUM(sales), 2) AS total_revenue, ROUND(SUM(profit), 2) AS total_profit
                FROM sales GROUP BY category ORDER BY total_revenue DESC
            """})
            print(by_category.content[0].text)

            print("\n=== [SQLite] read_query: revenue & profit by region ===")
            by_region = await sql.call_tool("read_query", {"query": """
                SELECT region, ROUND(SUM(sales), 2) AS total_revenue, ROUND(SUM(profit), 2) AS total_profit
                FROM sales GROUP BY region ORDER BY total_revenue DESC
            """})
            print(by_region.content[0].text)

            print("\n=== [SQLite] read_query: top 5 products by profit ===")
            top_products = await sql.call_tool("read_query", {"query": """
                SELECT product_name, category, ROUND(SUM(profit), 2) AS total_profit
                FROM sales GROUP BY product_name, category ORDER BY total_profit DESC LIMIT 5
            """})
            print(top_products.content[0].text)

            print("\n=== [SQLite] read_query: yearly sales trend ===")
            by_year = await sql.call_tool("read_query", {"query": """
                SELECT year, ROUND(SUM(sales), 2) AS total_revenue, ROUND(SUM(profit), 2) AS total_profit
                FROM sales GROUP BY year ORDER BY year
            """})
            print(by_year.content[0].text)

    # Build the report text from the four query results above.
    report = f"""# Global Superstore Sales Report

Sampled {len(sales_rows)} orders from the Kaggle Global Superstore dataset.

## Revenue & Profit by Category
{by_category.content[0].text}

## Revenue & Profit by Region
{by_region.content[0].text}

## Top 5 Products by Profit
{top_products.content[0].text}

## Yearly Sales Trend
{by_year.content[0].text}
"""

    async with stdio_client(filesystem_params) as (fs_read, fs_write):
        async with ClientSession(fs_read, fs_write) as fs:
            await fs.initialize()

            print("\n=== [Filesystem] write_file: sales_report.md ===")
            result = await fs.call_tool("write_file", {"path": "sales_report.md", "content": report})
            print(result.content[0].text)

            print("\n=== [Filesystem] read_text_file: confirm it was written ===")
            result = await fs.call_tool("read_text_file", {"path": "sales_report.md"})
            print(result.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
