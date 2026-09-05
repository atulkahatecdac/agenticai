# pip install mcp
import os
import sqlite3
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("SupportPrompts")

# =====================================================================
# MCP has three kinds of building blocks: tools (functions the LLM can
# call), resources (data the client can read), and prompts (reusable,
# parameterized message templates the SERVER owns and the CLIENT fills
# in). This demo combines the first and third: a `get_product_info` tool
# grounds the answer in a real SQLite product catalog, and a support
# team's centrally reviewed "how do we phrase a product answer" and "how
# do we phrase a product-not-found reply" wording lives as versioned
# prompt templates on the server - so every client (a Flask app, a Slack
# bot, a CLI) renders the exact same reviewed wording, and the LLM
# answers only from the data the tool actually returned instead of
# guessing specs.
# =====================================================================

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "product_catalog.sqlite")


def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            stock_qty INTEGER NOT NULL,
            description TEXT NOT NULL
        )
    ''')
    cursor.execute("DELETE FROM products")
    cursor.executemany(
        "INSERT INTO products (name, category, price, stock_qty, description) VALUES (?, ?, ?, ?, ?)",
        [
            ("Wireless Mouse X200", "Accessories", 24.99, 150,
             "Ergonomic wireless mouse with adjustable DPI and a 12-month battery life."),
            ("Noise Cancelling Headphones Pro", "Audio", 199.99, 0,
             "Over-ear headphones with active noise cancellation and 30-hour playback."),
            ("Mechanical Keyboard K6", "Accessories", 89.99, 42,
             "Hot-swappable mechanical keyboard with per-key RGB lighting."),
            ("27-inch 4K Monitor", "Displays", 349.99, 18,
             "27-inch IPS panel, 4K resolution, USB-C with 65W power delivery."),
            ("Portable SSD 1TB", "Storage", 109.99, 76,
             "USB 3.2 external SSD rated for up to 1050 MB/s read speeds."),
        ],
    )
    conn.commit()
    conn.close()


@mcp.tool()
def get_product_info(product_name: str) -> str:
    """
    Look up a product's details by (exact or partial) name.

    Args:
        product_name: name or partial name of the product to search for
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name, category, price, stock_qty, description FROM products WHERE name LIKE ?",
        (f"%{product_name}%",),
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return "NOT_FOUND"

    name, category, price, stock_qty, description = row
    stock_status = f"{stock_qty} in stock" if stock_qty > 0 else "out of stock"
    return (
        f"Name: {name}\nCategory: {category}\nPrice: ${price:.2f}\n"
        f"Availability: {stock_status}\nDescription: {description}"
    )


@mcp.prompt()
def answer_product_question(product_name: str, product_details: str, customer_question: str) -> str:
    """Prompt template for answering a customer's product question from real catalog data"""
    return f"""A customer asked the following about "{product_name}": {customer_question}

Here is the product's actual catalog data - use ONLY this information to answer, and do not \
invent or assume any detail that isn't stated below:
{product_details}

Write a short, friendly answer under 80 words. If the catalog data doesn't actually cover what \
the customer asked, say so honestly instead of guessing. Sign off as "Customer Support Team"."""


@mcp.prompt()
def product_not_found_reply(product_name: str, customer_question: str) -> str:
    """Prompt template for replying when a product isn't in the catalog"""
    return f"""A customer asked the following about a product called "{product_name}", which does \
not exist in our catalog: {customer_question}

Write a short, polite email explaining that we couldn't find this product in our current catalog, \
and invite them to double-check the product name or browse our current lineup instead. Keep it \
under 60 words and sign off as "Customer Support Team"."""


if __name__ == "__main__":
    init_database()
    mcp.run()
