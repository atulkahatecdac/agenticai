# Needs Node.js/npm (npx) - same official Playwright MCP server as
# 6_10_playwright_mcp_gold_price_client.py. Runs headed by default so you
# can watch the browser fill the form and log in - pass "--headless" as
# an extra npx arg below if you'd rather run it invisibly.
#
# practice.expandtesting.com/login is a well-known QA/automation practice
# site (the successor to the same author's the-internet.herokuapp.com)
# with published test credentials right on the page - no real account,
# no scraping-etiquette concerns, safe to hit repeatedly. This demonstrates
# browser_fill_form + browser_click, then checks the resulting page for
# the site's own success/failure banner text - once deliberately wrong,
# once with the correct password, to show both real outcomes.
#
# Order matters here: a correct login sets a session cookie, and visiting
# /login again while already authenticated just redirects straight to
# /secure - so the WRONG attempt runs first, while still unauthenticated.
import asyncio
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

sys.stdout.reconfigure(encoding="utf-8")

LOGIN_URL = "https://practice.expandtesting.com/login"
USERNAME = "practice"
CORRECT_PASSWORD = "SuperSecretPassword!"
WRONG_PASSWORD = "wrongpassword"


async def attempt_login(session: ClientSession, password: str, label: str):
    print(f"\n=== Attempt: {label} ===")
    await session.call_tool("browser_navigate", {"url": LOGIN_URL})

    await session.call_tool("browser_fill_form", {"fields": [
        {"target": "#username", "name": "Username", "type": "textbox", "value": USERNAME},
        {"target": "#password", "name": "Password", "type": "textbox", "value": password},
    ]})

    result = await session.call_tool("browser_click", {
        "target": "#submit-login", "element": "Login button",
    })
    landed_url = next((line.split(": ", 1)[1] for line in result.content[0].text.splitlines()
                        if line.startswith("- Page URL:")), "unknown")
    print(f"Landed on: {landed_url}")

    # The login page's own instructions mention "secure area" too, so
    # checking the URL Playwright actually landed on is the reliable
    # success signal - only a correct login redirects to /secure.
    if landed_url.rstrip("/").endswith("/secure"):
        result = await session.call_tool("browser_find", {"text": "You logged into a secure area"})
        found = "Found" in result.content[0].text
        print(f"Result: LOGIN SUCCEEDED (success banner present: {found})")
    else:
        result = await session.call_tool("browser_find", {"text": "Your password is invalid"})
        found = "Found" in result.content[0].text
        print(f"Result: LOGIN REJECTED (site's own 'invalid' error banner present: {found})")


async def main():
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@playwright/mcp@latest"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            await attempt_login(session, WRONG_PASSWORD, "wrong password")
            await attempt_login(session, CORRECT_PASSWORD, "correct credentials")

            input("\nPress Enter to close the browser...")
            await session.call_tool("browser_close", {})


if __name__ == "__main__":
    asyncio.run(main())
