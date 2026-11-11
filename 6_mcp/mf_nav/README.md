# MF NAV: mutual fund NAV MCP server + Flask app

Look up, download and forecast the daily NAV (net asset value) of any Indian mutual fund.

- **`mf_nav_server.py`** is an MCP server (stdio) with three tools. It can be used by the Flask app, by Claude, or by any MCP client.
- **`app.py`** is a Flask web page that calls the MCP server, shows the results and lets you download them as CSV.
- **`download_data.py`** downloads the AMFI NAV history the server reads.

No LLM and no API keys are involved. The data is the complete AMFI NAV history (April 2006 onward, about 38,500 schemes, 37M+ daily rows), published as free Parquet files by [MFPRO / tigzig](https://mfpro.tigzig.com/dashboard#returns/data-api/download) and rebuilt 3 times a day.

```
mf_nav/
├── mf_nav_server.py   MCP server: get_nav_history, search_schemes, forecast_nav
├── app.py             Flask UI on http://127.0.0.1:5000 (MCP client of the server above)
├── download_data.py   fetches data/*.parquet
├── data/              NAV Parquet files, ~180 MB (git-ignored)
└── output/            generated NAV and forecast CSVs (git-ignored, created on first use)
```

## Setup (once)

These steps use the repo-wide venv at `C:\code\agenticai\.venv`. See the root `README.md` if it doesn't exist yet.

**1. Activate the venv** (PowerShell, from the repo root):

```powershell
cd C:\code\agenticai
.venv\Scripts\Activate.ps1
```

**2. Install the dependencies.** They're all pinned in the root `requirements.txt`: `mcp`, `flask`, `numpy`, `polars`, `statsmodels`, `requests`. If the venv was set up before this folder was added, install just the two new packages:

```powershell
uv pip install polars==1.40.1 statsmodels==0.14.6
```

(Or run `uv pip install -r requirements.txt`, which only adds or upgrades packages. Never run `uv pip sync`.)

**3. Download the data** (~180 MB, takes about a minute):

```powershell
python 6_mcp\mf_nav\download_data.py
```

Run this again whenever you want the latest NAVs. The source files are rebuilt 3 times a day.

## Run the web app

```powershell
python 6_mcp\mf_nav\app.py
```

Open http://127.0.0.1:5000. The app starts `mf_nav_server.py` itself, on the first request, using the same Python as the app (the venv). You don't need to start the server separately. Press **Ctrl+C** to stop the app; that also stops the server.

On the page:

1. Enter a **scheme name** (for example `Parag Parikh Flexi Cap`), a scheme code (`122639`) or an ISIN.
2. Pick a **plan** (Direct or Regular) and an **option** (Growth, Dividend, or Dividend reinvest). If you leave them blank, the app uses Direct and Growth.
3. Enter **from/to dates**, or leave them blank for the full history. A start date before the scheme's first NAV moves forward to that first NAV. An end date after the latest NAV moves back to the latest NAV.
4. **Get NAVs** shows a summary and a preview, plus a **Download CSV** button.
5. **Search schemes** lists the funds that match the name, with every plan and option variant. Click one to get its NAVs.
6. **Forecast 5 years**, next to Download, projects the NAV 60 months ahead. It shows a line chart, a yearly table and the full monthly table, and offers a CSV download. Pick the model from the dropdown:

   | Model | What it does | Time |
   |---|---|---|
   | Random walk with drift (default) | Uses the fund's average monthly growth and volatility over the last 10 years. The bands widen with the square root of time. | instant |
   | ARIMA | Tries ARIMA(p,1,q) with drift for p, q from 0 to 2 and keeps the best AIC score | 1–5 s |
   | SARIMAX | Tries ARIMA(p,1,q)(P,0,Q)[12] with drift for p, q, P, Q from 0 to 1 and keeps the best AIC score. There's no outside data to feed it, so the "X" part is unused. | 3–8 s |

   ARIMA and SARIMAX also draw the random-walk median as a grey dotted line, for comparison. For most equity funds AIC picks ARIMA(0,1,0), which is the random walk itself, and the page says so. Every forecast is a statistical projection from past NAVs, not investment advice.

## Use the MCP server from Claude (or another MCP client)

Register it with Claude Code, using the venv's Python so `polars` and `statsmodels` are found:

```powershell
claude mcp add mf-nav -- C:\code\agenticai\.venv\Scripts\python.exe C:\code\agenticai\6_mcp\mf_nav\mf_nav_server.py
```

For Claude Desktop, add this to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mf-nav": {
      "command": "C:\\code\\agenticai\\.venv\\Scripts\\python.exe",
      "args": ["C:\\code\\agenticai\\6_mcp\\mf_nav\\mf_nav_server.py"]
    }
  }
}
```

### Tools

| Tool | Arguments | Returns |
|---|---|---|
| `get_nav_history` | `scheme_name`, `plan` (`direct`/`regular`), `option` (`growth`/`dividend`/`dividend reinvest`), `from_date`, `to_date` (`YYYY-MM-DD`) | The path of a CSV (`scheme_code, scheme_name, isin, date, nav`) in `output/`, the scheme it matched, the dates it actually used, and notes on any adjustments |
| `search_schemes` | `query`, `active_only`, `limit` | The matching schemes with their plan, option, first/last NAV date and live/matured status |
| `forecast_nav` | `scheme_name`, `plan`, `option`, `years` (1–10, default 5), `lookback_years` (2–20, default 10), `model` (`random_walk`/`arima`/`sarimax`) | Model details, the monthly history used, monthly median and 80%/95% ranges, and a CSV path |

Possible `status` values in replies:
- `ok`
- `not_found`: the scheme is unknown, or it exists but not with that plan/option. In the second case the reply lists the variants that do exist.
- `ambiguous`: several schemes match. The reply lists them; call again with a more specific name or the `scheme_code`.
- `no_data`
- `error`

## How it works

- **Data.** The server reads `data/amfi_nav_master.parquet` straight from disk with polars, filtering by scheme code. The file is sorted by scheme code, so a lookup reads only a few row groups and takes about 30 ms. There's no database to build.
- **Name matching.** Every word you type must appear in the scheme name; case and punctuation are ignored, and a no-spaces fallback handles names like "Flexicap". Live schemes win over matured ones, and then the name with the fewest extra words wins. Plan and option words ("Direct", "Growth", "IDCW", ...) don't count as extra words.
- **Dividend = IDCW.** AMFI files dividend options as "IDCW". Payout and reinvest are sub-options of the same plan and share one NAV series; only the ISIN differs (`isin` for payout, `isin2` for reinvest).
- **Regular plan of older funds.** Schemes from before the 2013 Direct/Regular split have their single plan filed as "Other". Asking for Regular falls back to it, and the reply notes this.
- **Data cleaning.** Rows with NAV ≤ 0 (AMFI closing or placeholder entries) are dropped. Forecasts ignore one-day jumps above 2x (unit splits or face-value changes) and refuse matured schemes or schemes with less than 2 years of history.
- **Flask ↔ MCP.** `app.py` keeps one long-lived MCP stdio session on a background asyncio thread, so requests don't pay the ~3 s server start-up each time. If the server process dies, the app starts it again.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Data files missing ... Run: python download_data.py` | Run step 3 of Setup |
| `ModuleNotFoundError: polars` / `statsmodels` | The venv isn't active, or the packages aren't installed. See Setup steps 1–2. |
| ARIMA/SARIMAX fails with `fmin_l_bfgs_b() got an unexpected keyword argument 'disp'` | statsmodels is older than 0.14.6 while SciPy is 1.18+. Run `uv pip install statsmodels==0.14.6`. |
| A new button or option doesn't appear after you change the code | Restart `app.py`. It runs without auto-reload, and the MCP server it started keeps running the old code until then. |
| Port 5000 is already in use | Another app (or an old copy of this one) is still running. Stop it, or change `port=5000` at the bottom of `app.py`. |
| A fund isn't found by an old name (e.g. "SBI Bluechip") | The data only keeps current names ("SBI Large Cap"). Use **Search schemes** with part of the name. |
