"""STEP 11 (Capstone Part 2): performance test - latency, throughput and cost under load.

N simulated customers submit the 20 sample tickets at the same time and poll until each one
is resolved (or parked at the approval gate). The report answers the questions an operator asks
before go-live: how slow is it at p95, how many tickets a minute can it take, does anything break
under concurrency, and what does one ticket cost?

Start the API first (another terminal):   python 19_7_api.py            (add --offline for no LLM)
Then:                                      python 19_11_load_test.py --users 10 --tickets 40
Against a deployed copy:                   python 19_11_load_test.py --url https://<your-service>
"""
import argparse
import asyncio
import json
import re
import sys
import time

import httpx

from capstone_common import API_URL, TICKETS_FILE

sys.stdout.reconfigure(encoding="utf-8")
PRICE_IN, PRICE_OUT = 0.15, 0.60          # gpt-4o-mini, USD per 1M tokens - check current pricing


def pct(values: list[float], p: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(round(p / 100 * (len(ordered) - 1))))] if ordered else 0.0


def tokens(metrics_text: str) -> tuple[float, float]:
    get = lambda kind: float((re.search(rf'capstone_llm_tokens_total{{kind="{kind}"}} ([\d.e+]+)', metrics_text) or [0, 0])[1])
    return get("input"), get("output")


async def customer(client: httpx.AsyncClient, queue: asyncio.Queue, results: list):
    while not queue.empty():
        message = await queue.get()
        start = time.perf_counter()
        try:
            r = await client.post("/tickets", json={"message": message})
            r.raise_for_status()
            accepted = time.perf_counter() - start
            ticket_id = r.json()["ticket_id"]
            while True:
                t = (await client.get(f"/tickets/{ticket_id}")).json()
                if t["status"] != "running":
                    break
                await asyncio.sleep(0.25)
            results.append({"ok": t["status"] != "error", "status": t["status"], "accepted_s": accepted,
                            "resolved_s": time.perf_counter() - start, "error": t.get("reply") if t["status"] == "error" else None})
        except Exception as e:
            results.append({"ok": False, "status": "http_error", "accepted_s": 0, "resolved_s": time.perf_counter() - start, "error": str(e)})


async def main(url: str, users: int, n_tickets: int, slo_p95: float):
    with open(TICKETS_FILE, encoding="utf-8") as f:
        messages = [t["message"] for t in json.load(f)]
    queue: asyncio.Queue = asyncio.Queue()
    for i in range(n_tickets):
        queue.put_nowait(messages[i % len(messages)])

    async with httpx.AsyncClient(base_url=url, timeout=120) as client:
        health = (await client.get("/health")).json()
        before = tokens((await client.get("/metrics")).text)
        print(f"Target {url}  mode={health['mode']}  |  {users} concurrent customers, {n_tickets} tickets\n")
        results: list = []
        wall = time.perf_counter()
        await asyncio.gather(*(customer(client, queue, results) for _ in range(users)))
        wall = time.perf_counter() - wall
        after = tokens((await client.get("/metrics")).text)

    ok = [r for r in results if r["ok"]]
    resolved = [r["resolved_s"] for r in ok]
    accepted = [r["accepted_s"] for r in ok]
    tin, tout = after[0] - before[0], after[1] - before[1]
    cost = (tin * PRICE_IN + tout * PRICE_OUT) / 1e6

    print(f"{'':28}{'p50':>8}{'p95':>8}{'p99':>8}{'max':>8}")
    print(f"{'POST /tickets accepted (s)':28}{pct(accepted, 50):>8.2f}{pct(accepted, 95):>8.2f}{pct(accepted, 99):>8.2f}{max(accepted, default=0):>8.2f}")
    print(f"{'ticket resolved (s)':28}{pct(resolved, 50):>8.2f}{pct(resolved, 95):>8.2f}{pct(resolved, 99):>8.2f}{max(resolved, default=0):>8.2f}")
    print(f"\nThroughput : {len(ok) / wall * 60:.1f} tickets/minute ({len(ok)} in {wall:.1f}s)")
    print(f"Outcomes   : " + ", ".join(f"{s}={sum(r['status'] == s for r in results)}" for s in sorted({r['status'] for r in results})))
    print(f"Errors     : {len(results) - len(ok)}" + (f"  e.g. {next(r['error'] for r in results if not r['ok'])[:120]}" if len(ok) < len(results) else ""))
    if tin + tout:
        print(f"LLM cost   : {tin + tout:,.0f} tokens, ${cost:.4f} total, ${cost / max(1, len(ok)):.5f} per ticket "
              f"-> ${cost / max(1, len(ok)) * 1000:.2f} per 1,000 tickets")
    else:
        print("LLM cost   : 0 tokens (offline mode - run the API without --offline to measure cost)")

    verdict = pct(resolved, 95) <= slo_p95 and len(ok) == len(results)
    print(f"\nSLO (p95 resolution <= {slo_p95:.0f}s, no errors): {'PASS' if verdict else 'FAIL'}")
    return 0 if verdict else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=API_URL)
    ap.add_argument("--users", type=int, default=10)
    ap.add_argument("--tickets", type=int, default=40)
    ap.add_argument("--slo-p95", type=float, default=15.0, help="seconds")
    args = ap.parse_args()
    sys.exit(asyncio.run(main(args.url, args.users, args.tickets, args.slo_p95)))
