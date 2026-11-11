# pip install mcp
import os
import re
import sqlite3
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("sqlite-database-validation-demo")

# Separate DB file from 6_2_database_mcp_server.py's simple_db.sqlite, so
# running this demo can't corrupt/collide with that one.
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vulnerable_db.sqlite")


def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL
        )
    ''')
    # A table no tool is meant to expose - stands in for "some other
    # sensitive table in the same database" (e.g. credentials, API keys).
    # It exists purely so the injection demo below has something real and
    # damaging to steal, instead of just proving "the WHERE clause matched
    # more rows than intended".
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS secrets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_key TEXT NOT NULL
        )
    ''')
    cursor.execute("DELETE FROM users")
    cursor.execute("DELETE FROM secrets")
    cursor.executemany(
        "INSERT INTO users (name, email) VALUES (?, ?)",
        [("Alice", "alice@example.com"), ("Bob", "bob@example.com")],
    )
    cursor.execute("INSERT INTO secrets (api_key) VALUES (?)", ("sk-live-9f8a7b6c5d4e3f2a1b0c",))
    conn.commit()
    conn.close()


@mcp.tool()
def search_users_unsafe(name: str) -> str:
    """
    VULNERABLE: search users by name, built by directly formatting the
    input into the SQL string - do not copy this pattern.

    Args:
        name: name to search for
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # The vulnerability: `name` is spliced straight into the SQL text, so
    # any quotes/keywords the caller sends become part of the query
    # itself instead of being treated as a plain string value.
    query = f"SELECT id, name, email FROM users WHERE name = '{name}'"
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return "No users found"
    return "Users:\n" + "\n".join(f"ID: {r[0]}, Name: {r[1]}, Email: {r[2]}" for r in rows)


# Denylist covering the SQL metacharacters/keywords a name should never
# legitimately contain - real names don't have quotes, semicolons, `--`
# comments, or SQL keywords in them. This is a second, defense-in-depth
# layer; the parameterized query below is what actually stops injection
# even if a payload somehow slipped past this check.
_SUSPICIOUS_PATTERN = re.compile(
    r"""['";]|--|/\*|\*/|\b(union|select|insert|update|delete|drop|alter|exec)\b""",
    re.IGNORECASE,
)


@mcp.tool()
def search_users_safe(name: str) -> str:
    """
    SAFE: search users by name, with input validation AND a parameterized
    query - either one alone would stop the attacks this demo tries, but
    real systems use both (validation rejects obviously malicious input
    early with a clear error; parameterization is the actual guarantee
    that user input can never change the query's structure).

    Args:
        name: name to search for
    """
    if _SUSPICIOUS_PATTERN.search(name):
        return f"Rejected: '{name}' contains characters/keywords not allowed in a name search"

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Parameterized query: `name` is always bound as a single literal
    # value, never parsed as SQL, no matter what it contains.
    cursor.execute("SELECT id, name, email FROM users WHERE name = ?", (name,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return "No users found"
    return "Users:\n" + "\n".join(f"ID: {r[0]}, Name: {r[1]}, Email: {r[2]}" for r in rows)


if __name__ == "__main__":
    init_database()
    mcp.run()
