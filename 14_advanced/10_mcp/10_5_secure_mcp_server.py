# Two server-side defences in one MCP server:
#
#   1. PERMISSION CHECKS - every tool declares the roles allowed to call it,
#      and the server refuses anything else. The caller's role comes from the
#      host that launches the server (env var MCP_CLIENT_ROLE here; over HTTP
#      it would come from the validated access token - see the OAuth2 demo in
#      6_mcp/authentication/version_3). Unknown role -> least privilege.
#   2. INPUT VALIDATION - the same name search written unsafely (string-built
#      SQL, injectable) and safely (validated + parameterized).
#
# Client: 10_5_secure_mcp_client.py runs the attacks as a "viewer", then as
# an "admin".
import functools
import os
import re
import sqlite3
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("sqlite-database-security-demo")

# ---------------------------------------------------------------------------
# 1. Permission checks
# ---------------------------------------------------------------------------
ROLE = os.getenv("MCP_CLIENT_ROLE", "viewer").lower()
KNOWN_ROLES = {"viewer", "admin"}
if ROLE not in KNOWN_ROLES:
    ROLE = "viewer"


def requires(*allowed_roles: str):
    """Decorator: run the tool only if the caller's role is allowed."""
    def decorator(func):
        @functools.wraps(func)  # keeps name, docstring and signature for the tool schema
        def wrapper(*args, **kwargs):
            if ROLE not in allowed_roles:
                return f"Permission denied: role '{ROLE}' cannot call {func.__name__} (needs {' or '.join(allowed_roles)})"
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Separate DB file from 10_3_database_mcp_server.py's simple_db.sqlite, so
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
    # Restart ids at 1 on every launch, so the demo's ids are predictable
    cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('users', 'secrets')")
    cursor.executemany(
        "INSERT INTO users (name, email) VALUES (?, ?)",
        [("Alice", "alice@example.com"), ("Bob", "bob@example.com")],
    )
    cursor.execute("INSERT INTO secrets (api_key) VALUES (?)", ("sk-live-9f8a7b6c5d4e3f2a1b0c",))
    conn.commit()
    conn.close()


@mcp.tool()
@requires("viewer", "admin")
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
@requires("viewer", "admin")
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


@mcp.tool()
@requires("admin")
def delete_user(user_id: int) -> str:
    """
    Delete a user by id. Admin only.

    Args:
        user_id: id of the user to delete (a positive integer)
    """
    # Validation still applies to admins: the type hint makes the SDK reject
    # non-integers, and the range check rejects nonsense ids.
    if user_id <= 0:
        return f"Rejected: user_id must be a positive integer, got {user_id}"
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return f"Deleted user {user_id}" if deleted else f"No user with id {user_id}"


if __name__ == "__main__":
    init_database()
    mcp.run()
