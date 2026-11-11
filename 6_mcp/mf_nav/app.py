"""Flask front end for the mf-nav MCP server.

Run:  python app.py   then open http://127.0.0.1:5000

The app talks to mf_nav_server.py over MCP (stdio). One server process is started on the
first request and reused; it is restarted automatically if it dies.
"""

from __future__ import annotations

import asyncio
import csv
import json
import re
import sys
import threading
from contextlib import AsyncExitStack
from pathlib import Path

from flask import Flask, abort, render_template_string, request, send_from_directory
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

BASE_DIR = Path(__file__).resolve().parent
SERVER_SCRIPT = BASE_DIR / "mf_nav_server.py"
OUTPUT_DIR = BASE_DIR / "output"
CSV_NAME_RE = re.compile(r"(nav_\d+_\d{8}_\d{8}|forecast_\d+_\d{8}_(random_walk|arima|sarimax))\.csv")
MODELS = {
    "random_walk": "Random walk with drift (fast)",
    "arima": "ARIMA, auto-selected (a few seconds)",
    "sarimax": "SARIMAX, seasonal (5-10 seconds)",
}


class MCPBridge:
    """Synchronous wrapper around one long-lived MCP client session (runs on its own event loop thread)."""

    def __init__(self, script: Path):
        self.params = StdioServerParameters(command=sys.executable, args=[str(script)], cwd=str(script.parent))
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.loop.run_forever, daemon=True).start()
        self.stack: AsyncExitStack | None = None
        self.session: ClientSession | None = None

    async def _connect(self) -> None:
        self.stack = AsyncExitStack()
        read, write = await self.stack.enter_async_context(stdio_client(self.params))
        self.session = await self.stack.enter_async_context(ClientSession(read, write))
        await self.session.initialize()

    async def _reset(self) -> None:
        if self.stack:
            try:
                await self.stack.aclose()
            except Exception:
                pass
        self.stack = self.session = None

    async def _call_once(self, tool: str, args: dict):
        if self.session is None:
            await self._connect()
        assert self.session is not None
        return await self.session.call_tool(tool, args)

    async def _call(self, tool: str, args: dict) -> dict:
        try:
            result = await self._call_once(tool, args)
        except Exception:
            # Server process died or never started: restart it once and retry.
            await self._reset()
            result = await self._call_once(tool, args)
        text = "".join(getattr(c, "text", "") for c in result.content)
        if result.isError:
            return {"status": "error", "message": text or "MCP tool call failed."}
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"status": "error", "message": text}

    def call(self, tool: str, args: dict, timeout: float = 120) -> dict:
        return asyncio.run_coroutine_threadsafe(self._call(tool, args), self.loop).result(timeout)


PAGE = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MF NAV Download</title>
<style>
  :root { --bg:#f6f7f9; --card:#fff; --text:#1d2330; --muted:#667085; --line:#e3e6eb; --accent:#1f5fbf; --ok:#1d7a46; --warn:#a15c00; --err:#b42318; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--text); font:15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
  main { max-width:960px; margin:0 auto; padding:24px 16px 48px; }
  h1 { font-size:22px; margin:0 0 4px; }
  .sub { color:var(--muted); margin:0 0 20px; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:18px; margin-bottom:18px; }
  .grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(170px, 1fr)); gap:12px; }
  .full { grid-column:1 / -1; }
  label { display:block; font-size:13px; font-weight:600; margin-bottom:4px; }
  input, select { width:100%; padding:8px 10px; border:1px solid var(--line); border-radius:6px; font:inherit; background:#fff; }
  .actions { display:flex; gap:10px; margin-top:14px; flex-wrap:wrap; }
  button, .btn { padding:9px 16px; border-radius:6px; border:1px solid var(--accent); font:inherit; font-weight:600; cursor:pointer; text-decoration:none; display:inline-block; }
  .primary { background:var(--accent); color:#fff; }
  .secondary { background:#fff; color:var(--accent); }
  .hint { color:var(--muted); font-size:13px; margin-top:8px; }
  .msg { padding:10px 12px; border-radius:6px; margin-bottom:12px; }
  .msg.err { background:#fdecea; color:var(--err); }
  .msg.warn { background:#fff4e5; color:var(--warn); }
  .msg.ok { background:#e9f6ef; color:var(--ok); }
  dl { display:grid; grid-template-columns:max-content 1fr; gap:4px 16px; margin:0 0 12px; }
  dt { color:var(--muted); }
  dd { margin:0; }
  ul.notes { margin:0 0 12px; padding-left:20px; color:var(--muted); }
  .tablewrap { overflow-x:auto; }
  table { border-collapse:collapse; width:100%; font-size:14px; }
  th, td { text-align:left; padding:6px 10px; border-bottom:1px solid var(--line); white-space:nowrap; }
  th { background:#fafbfc; font-weight:600; }
  td.num { font-variant-numeric:tabular-nums; text-align:right; }
  td.wrap { white-space:normal; }
  .gap td { text-align:center; color:var(--muted); }
  .badge { font-size:12px; padding:1px 7px; border-radius:10px; background:#eef1f5; color:var(--muted); }
  .badge.live { background:#e9f6ef; color:var(--ok); }
  a { color:var(--accent); }
  .chartbox { position:relative; height:360px; margin:6px 0 4px; }
  .fcform { display:flex; gap:8px; flex-wrap:wrap; margin:0; }
  .fcform select { width:auto; }
  summary { cursor:pointer; color:var(--accent); font-weight:600; margin-bottom:8px; }
</style>
</head>
<body>
<main>
  <h1>Mutual Fund NAV Download</h1>
  <p class="sub">Search a scheme and download its daily NAV history as CSV, served by the local <code>mf-nav</code> MCP server.</p>

  <form class="card" method="get" action="/">
    <div class="grid">
      <div class="full">
        <label for="scheme_name">Scheme name, code or ISIN</label>
        <input id="scheme_name" name="scheme_name" value="{{ form.scheme_name }}" placeholder="e.g. Parag Parikh Flexi Cap" required>
      </div>
      <div>
        <label for="plan">Plan</label>
        <select id="plan" name="plan">
          {% for v, t in [("", "Default (Direct)"), ("direct", "Direct"), ("regular", "Regular")] %}
          <option value="{{ v }}" {% if form.plan == v %}selected{% endif %}>{{ t }}</option>
          {% endfor %}
        </select>
      </div>
      <div>
        <label for="option">Option</label>
        <select id="option" name="option">
          {% for v, t in [("", "Default (Growth)"), ("growth", "Growth"), ("dividend", "Dividend (IDCW payout)"), ("dividend reinvest", "Dividend reinvest")] %}
          <option value="{{ v }}" {% if form.option == v %}selected{% endif %}>{{ t }}</option>
          {% endfor %}
        </select>
      </div>
      <div>
        <label for="from_date">From date</label>
        <input id="from_date" name="from_date" type="date" value="{{ form.from_date }}">
      </div>
      <div>
        <label for="to_date">To date</label>
        <input id="to_date" name="to_date" type="date" value="{{ form.to_date }}">
      </div>
    </div>
    <div class="actions">
      <button class="primary" type="submit" name="action" value="nav">Get NAVs</button>
      <button class="secondary" type="submit" name="action" value="search">Search schemes</button>
    </div>
    <p class="hint">Blank dates use the scheme's full NAV history. Dates outside the scheme's life are moved to its first or last NAV.</p>
  </form>

  {% if error %}<div class="msg err">{{ error }}</div>{% endif %}

  {% macro scheme_table(rows) %}
  <div class="tablewrap"><table>
    <tr><th>Code</th><th>Scheme</th><th>Plan</th><th>Option</th><th>NAV dates</th><th></th></tr>
    {% for s in rows %}
    <tr>
      <td>{{ s.scheme_code }}</td>
      <td class="wrap">{{ s.scheme_name }} {% if s.active %}<span class="badge live">live</span>{% else %}<span class="badge">matured</span>{% endif %}</td>
      <td>{{ s.plan }}</td>
      <td>{{ s.option }}</td>
      <td>{{ s.first_nav_date }} – {{ s.last_nav_date }}</td>
      <td><a href="{{ url_for('index', action='nav', scheme_name=s.scheme_code, from_date=form.from_date, to_date=form.to_date) }}">Get NAVs</a></td>
    </tr>
    {% endfor %}
  </table></div>
  {% endmacro %}

  {% if search %}
  <section class="card">
    {% if search.status == "ok" %}
      <p><strong>{{ search.total_matches }}</strong> matching scheme{{ "s" if search.total_matches != 1 }}{% if search.total_matches > search.schemes|length %} (showing {{ search.schemes|length }}; refine the name to narrow down){% endif %}.</p>
      {{ scheme_table(search.schemes) }}
    {% else %}
      <div class="msg err">{{ search.message }}</div>
    {% endif %}
  </section>
  {% endif %}

  {% if nav %}
  <section class="card">
    {% if nav.status == "ok" %}
      <div class="msg ok">{{ nav.rows }} NAV rows found.</div>
      <dl>
        <dt>Scheme</dt><dd>{{ nav.scheme_name }}</dd>
        <dt>Code / ISIN</dt><dd>{{ nav.scheme_code }} / {{ nav.isin or "–" }}</dd>
        <dt>AMC</dt><dd>{{ nav.amc }}</dd>
        <dt>Plan / Option</dt><dd>{{ nav.plan }} / {{ nav.option }}</dd>
        <dt>Dates returned</dt><dd>{{ nav.from_date }} to {{ nav.to_date }}</dd>
        <dt>NAVs on file</dt><dd>{{ nav.scheme_nav_range }}</dd>
      </dl>
      {% if nav.notes %}<ul class="notes">{% for n in nav.notes %}<li>{{ n }}</li>{% endfor %}</ul>{% endif %}
      <div class="actions" style="margin:0 0 14px; align-items:center">
        <a class="btn primary" href="{{ url_for('download', name=download_name) }}">Download CSV</a>
        <form class="fcform" method="get" action="/#forecast">
          {% for k, v in form.items() %}<input type="hidden" name="{{ k }}" value="{{ v }}">{% endfor %}
          <input type="hidden" name="action" value="forecast">
          <select name="model" aria-label="Forecast model">
            {% for k, label in models.items() %}<option value="{{ k }}" {% if k == model %}selected{% endif %}>{{ label }}</option>{% endfor %}
          </select>
          <button class="secondary" type="submit">Forecast 5 years</button>
        </form>
      </div>
      <div class="tablewrap"><table>
        <tr><th>Date</th><th>NAV</th></tr>
        {% for r in head_rows %}<tr><td>{{ r[3] }}</td><td class="num">{{ r[4] }}</td></tr>{% endfor %}
        {% if tail_rows %}
          <tr class="gap"><td colspan="2">… {{ nav.rows - head_rows|length - tail_rows|length }} more rows …</td></tr>
          {% for r in tail_rows %}<tr><td>{{ r[3] }}</td><td class="num">{{ r[4] }}</td></tr>{% endfor %}
        {% endif %}
      </table></div>
    {% elif nav.status == "ambiguous" %}
      <div class="msg warn">“{{ form.scheme_name }}” matches {{ nav.candidates|length }} schemes for this plan and option. Pick one below, or type a more specific name.</div>
      {{ scheme_table(nav.candidates) }}
    {% elif nav.status == "not_found" and nav.available_variants %}
      <div class="msg warn">“{{ form.scheme_name }}” exists, but not with the selected plan and option. These variants are available:</div>
      {{ scheme_table(nav.available_variants) }}
    {% else %}
      <div class="msg err">{{ nav.message }}</div>
    {% endif %}
  </section>
  {% endif %}

  {% if fc %}
  <section class="card" id="forecast">
    <h2 style="font-size:18px;margin:0 0 10px">5-year NAV projection</h2>
    {% if fc.status == "ok" %}
      <dl>
        <dt>Scheme</dt><dd>{{ fc.scheme_name }}</dd>
        <dt>Starting point</dt><dd>NAV {{ "%.4f"|format(fc.last_nav) }} on {{ fc.last_nav_date }}</dd>
        <dt>Estimated from</dt><dd>{{ fc.history_months }} months of NAVs since {{ fc.history_from }}</dd>
        <dt>Past growth / volatility</dt><dd>{{ fc.historical_cagr_pct }}% a year / {{ fc.annual_volatility_pct }}% a year</dd>
        <dt>Model</dt><dd>{{ fc.model }}</dd>
        <dt>Projected growth</dt><dd><strong>{{ fc.projected_cagr_pct }}% a year</strong>{% if fc.baseline_projected_cagr_pct is defined %} (random walk: {{ fc.baseline_projected_cagr_pct }}% a year){% endif %}</dd>
      </dl>
      {% set extra = fc.notes | reject("in", nav.notes) | list %}
      {% if extra %}<ul class="notes">{% for n in extra %}<li>{{ n }}</li>{% endfor %}</ul>{% endif %}

      <div class="chartbox"><canvas id="fcChart" aria-label="NAV history and 5-year projection"></canvas></div>
      <p class="hint">Solid line: monthly NAV history. Dashed line: median projection. Shaded bands: 80% (darker) and 95% (lighter) ranges.{% if fc.baseline_projected_cagr_pct is defined %} Grey dotted line: random-walk median, for comparison.{% endif %}</p>

      <div class="actions" style="margin:4px 0 14px">
        <a class="btn primary" href="{{ url_for('download', name=fc_download_name) }}">Download forecast CSV</a>
      </div>

      <div class="tablewrap"><table>
        {% set has_rw = fc.baseline_projected_cagr_pct is defined %}
        <tr><th>Date</th><th>Median NAV</th><th>80% range</th><th>95% range</th><th>Implied CAGR</th>{% if has_rw %}<th>Random walk median</th>{% endif %}</tr>
        {% for p in fc_yearly %}
        <tr>
          <td>{{ p.date }}</td>
          <td class="num">{{ "%.2f"|format(p.median) }}</td>
          <td class="num">{{ "%.2f"|format(p.low80) }} – {{ "%.2f"|format(p.high80) }}</td>
          <td class="num">{{ "%.2f"|format(p.low95) }} – {{ "%.2f"|format(p.high95) }}</td>
          <td class="num">{{ "%.1f"|format(((p.median / fc.last_nav) ** (1 / loop.index) - 1) * 100) }}%</td>
          {% if has_rw %}<td class="num">{{ "%.2f"|format(p.rw_median) }}</td>{% endif %}
        </tr>
        {% endfor %}
      </table></div>

      <details style="margin-top:12px">
        <summary>All {{ fc.forecast|length }} monthly points</summary>
        <div class="tablewrap"><table>
          <tr><th>Date</th><th>Median</th><th>Low 80%</th><th>High 80%</th><th>Low 95%</th><th>High 95%</th>{% if has_rw %}<th>RW median</th>{% endif %}</tr>
          {% for p in fc.forecast %}
          <tr><td>{{ p.date }}</td><td class="num">{{ "%.2f"|format(p.median) }}</td><td class="num">{{ "%.2f"|format(p.low80) }}</td><td class="num">{{ "%.2f"|format(p.high80) }}</td><td class="num">{{ "%.2f"|format(p.low95) }}</td><td class="num">{{ "%.2f"|format(p.high95) }}</td>{% if has_rw %}<td class="num">{{ "%.2f"|format(p.rw_median) }}</td>{% endif %}</tr>
          {% endfor %}
        </table></div>
      </details>

      <p class="hint" style="margin-top:14px">{{ fc.disclaimer }} The model assumes the fund keeps its past average growth and volatility; it cannot foresee market regime changes, fund manager changes or crashes.</p>

      <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
      <script>
        (function () {
          const hist = {{ fc.history | tojson }};
          const fc = {{ fc.forecast | tojson }};
          const lastNav = {{ fc.last_nav | tojson }}, lastDate = {{ fc.last_nav_date | tojson }};
          const labels = hist.map(p => p.date).concat([lastDate], fc.map(p => p.date));
          const nH = hist.length, pad = n => Array(n).fill(null);
          // Forecast series start at the latest actual NAV so the lines join up.
          const f = key => pad(nH).concat([lastNav], fc.map(p => p[key]));
          const hLine = hist.map(p => p.nav).concat([lastNav], pad(fc.length));
          const band = (data, color, fill) => ({ data, borderWidth: 0, pointRadius: 0, backgroundColor: color, fill, spanGaps: false });
          new Chart(document.getElementById("fcChart"), {
            type: "line",
            data: {
              labels,
              datasets: [
                Object.assign(band(f("high95"), "rgba(31,95,191,0.10)", false), { label: "95% high" }),
                Object.assign(band(f("low95"), "rgba(31,95,191,0.10)", "-1"), { label: "95% range" }),
                Object.assign(band(f("high80"), "rgba(31,95,191,0.20)", false), { label: "80% high" }),
                Object.assign(band(f("low80"), "rgba(31,95,191,0.20)", "-1"), { label: "80% range" }),
                { label: "Median projection", data: f("median"), borderColor: "#1f5fbf", borderDash: [6, 4], borderWidth: 2, pointRadius: 0, fill: false },
                { label: "NAV history", data: hLine, borderColor: "#1d2330", borderWidth: 1.6, pointRadius: 0, fill: false },
              ].concat("rw_median" in fc[0] ? [
                { label: "Random walk median", data: f("rw_median"), borderColor: "#8a94a6", borderDash: [2, 3], borderWidth: 1.6, pointRadius: 0, fill: false },
              ] : []),
            },
            options: {
              responsive: true, maintainAspectRatio: false, animation: false,
              interaction: { mode: "index", intersect: false },
              plugins: {
                legend: { labels: { filter: i => !i.text.endsWith("high") } },
                tooltip: { filter: i => i.raw !== null && !i.dataset.label.endsWith("high"),
                           callbacks: { label: c => `${c.dataset.label}: ${Number(c.raw).toFixed(2)}` } },
              },
              scales: {
                x: { ticks: { maxTicksLimit: 10, callback: function (v) { return this.getLabelForValue(v).slice(0, 7); } } },
                y: { title: { display: true, text: "NAV (₹)" } },
              },
            },
          });
        })();
      </script>
    {% else %}
      <div class="msg err">{{ fc.message }}</div>
    {% endif %}
  </section>
  {% endif %}
</main>
</body>
</html>
'''


bridge = MCPBridge(SERVER_SCRIPT)
app = Flask(__name__)


def _preview(csv_path: Path, n: int = 5) -> tuple[list[str], list[list[str]], list[list[str]]]:
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    header, body = rows[0], rows[1:]
    if len(body) <= 2 * n:
        return header, body, []
    return header, body[:n], body[-n:]


@app.route("/")
def index():
    form = {k: request.args.get(k, "").strip() for k in ("scheme_name", "plan", "option", "from_date", "to_date")}
    action = request.args.get("action")
    model = request.args.get("model", "random_walk")
    if model not in MODELS:
        model = "random_walk"
    ctx: dict = {"form": form, "action": action, "model": model, "models": MODELS}

    if action and not form["scheme_name"]:
        ctx["error"] = "Enter a scheme name."
    elif action == "search":
        try:
            ctx["search"] = bridge.call("search_schemes", {"query": form["scheme_name"], "limit": 50})
        except Exception as e:
            ctx["error"] = f"Could not reach the MCP server: {e}"
    elif action in ("nav", "forecast"):
        args = {k: v for k, v in form.items() if v}
        try:
            res = bridge.call("get_nav_history", args)
        except Exception as e:
            res = {"status": "error", "message": f"Could not reach the MCP server: {e}"}
        ctx["nav"] = res
        if res.get("status") == "ok":
            path = Path(res["csv_file"])
            ctx["download_name"] = path.name
            ctx["header"], ctx["head_rows"], ctx["tail_rows"] = _preview(path)
            if action == "forecast":
                # Forecast the exact scheme just resolved, by code, from its latest NAV.
                try:
                    fc = bridge.call("forecast_nav",
                                     {"scheme_name": str(res["scheme_code"]), "years": 5, "model": model})
                except Exception as e:
                    fc = {"status": "error", "message": f"Could not reach the MCP server: {e}"}
                ctx["fc"] = fc
                if fc.get("status") == "ok":
                    ctx["fc_download_name"] = Path(fc["csv_file"]).name
                    ctx["fc_yearly"] = [p for i, p in enumerate(fc["forecast"], 1) if i % 12 == 0]
    return render_template_string(PAGE, **ctx)


@app.route("/download/<name>")
def download(name: str):
    if not CSV_NAME_RE.fullmatch(name) or not (OUTPUT_DIR / name).is_file():
        abort(404)
    return send_from_directory(OUTPUT_DIR, name, as_attachment=True, mimetype="text/csv")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
