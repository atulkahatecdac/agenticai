"""Local MCP server: Indian mutual fund NAV history (AMFI data via tigzig MFPRO download).

Data files (refresh with download_data.py):
  data/amfi_nav_master.parquet         full daily NAV history, every scheme
  data/amfi_nav_master_latest.parquet  one row per scheme: plan, option, first/last NAV date

Tools:
  get_nav_history  scheme name + plan + option + date window -> CSV file of NAVs
  search_schemes   find scheme names/codes and see which plan/option variants exist
"""

from __future__ import annotations

import itertools
import re
import warnings
from datetime import date, datetime
from pathlib import Path

import numpy as np
import polars as pl
from mcp.server.fastmcp import FastMCP
# Imported at startup, not inside the tool: a first-time statsmodels/scipy import inside an
# MCP request handler stalled for minutes on Windows, while at module load it takes ~2.5 s.
from statsmodels.tsa.statespace.sarimax import SARIMAX

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
NAV_FILE = DATA_DIR / "amfi_nav_master.parquet"
SCHEME_FILE = DATA_DIR / "amfi_nav_master_latest.parquet"

mcp = FastMCP("mf-nav")

# Words that describe plan/option rather than the fund itself. They are ignored when
# ranking name matches, so "HDFC Flexi Cap" matches "HDFC Flexi Cap Fund - Growth Option - Direct Plan".
VARIANT_WORDS = {
    "fund", "plan", "option", "options", "direct", "regular", "growth", "idcw", "dividend",
    "dividends", "payout", "pay", "out", "reinvestment", "reinvest", "re", "investment",
    "of", "income", "distribution", "cum", "capital", "withdrawal", "and", "the", "scheme",
}

PLAN_ALIASES = {"direct": "Direct", "d": "Direct", "regular": "Regular", "r": "Regular"}

# Option key -> (AMFI scheme_option value, sub-type)
OPTION_ALIASES = {
    "growth": ("Growth", None),
    "g": ("Growth", None),
    "dividend": ("IDCW", "payout"),
    "divident": ("IDCW", "payout"),
    "dividend payout": ("IDCW", "payout"),
    "divident payout": ("IDCW", "payout"),
    "idcw": ("IDCW", "payout"),
    "idcw payout": ("IDCW", "payout"),
    "payout": ("IDCW", "payout"),
    "dividend reinvest": ("IDCW", "reinvest"),
    "dividend reinvestment": ("IDCW", "reinvest"),
    "divident reinvest": ("IDCW", "reinvest"),
    "divident reinvestment": ("IDCW", "reinvest"),
    "dividend reivest": ("IDCW", "reinvest"),
    "divident reivest": ("IDCW", "reinvest"),
    "idcw reinvest": ("IDCW", "reinvest"),
    "idcw reinvestment": ("IDCW", "reinvest"),
    "reinvest": ("IDCW", "reinvest"),
    "reinvestment": ("IDCW", "reinvest"),
}


def _tokens(text: str) -> list[str]:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).split()


def _load_schemes() -> pl.DataFrame:
    if not SCHEME_FILE.exists() or not NAV_FILE.exists():
        raise FileNotFoundError(
            f"Data files missing in {DATA_DIR}. Run: python download_data.py"
        )
    df = pl.read_parquet(
        SCHEME_FILE,
        columns=["scheme_code", "scheme_name", "amc", "scheme_plan", "scheme_option",
                 "isin", "isin2", "first_date", "last_date", "is_active", "source"],
    )
    lower = df["scheme_name"].str.to_lowercase()
    norm = lower.str.replace_all(r"[^a-z0-9]+", " ").str.strip_chars()
    return df.with_columns(
        _norm=norm,
        _nospace=norm.str.replace_all(" ", ""),
        _has_reinv=lower.str.contains("reinv"),
        _has_payout=lower.str.contains("payout|pay out"),
    )


SCHEMES = _load_schemes()


def _match_name(name: str) -> pl.DataFrame:
    """Schemes whose name contains every word of `name` (or a scheme code / ISIN)."""
    q = name.strip()
    if re.fullmatch(r"\d+", q):
        return SCHEMES.filter(pl.col("scheme_code") == int(q))
    if re.fullmatch(r"[A-Za-z]{2}[A-Za-z0-9]{9}\d", q):
        up = q.upper()
        return SCHEMES.filter((pl.col("isin") == up) | (pl.col("isin2") == up))

    toks = _tokens(q)
    if not toks:
        return SCHEMES.clear()
    padded = pl.lit(" ") + pl.col("_norm") + pl.lit(" ")
    cond = pl.lit(True)
    for t in toks:
        cond = cond & padded.str.contains(f" {t} ", literal=True)
    hits = SCHEMES.filter(cond)
    if hits.is_empty():
        # Fallback for spacing differences, e.g. "flexicap" vs "flexi cap".
        hits = SCHEMES.filter(pl.col("_nospace").str.contains("".join(toks), literal=True))
    return hits


def _parse_date(value: str | None, label: str) -> date | None:
    if value is None or str(value).strip() == "":
        return None
    s = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d-%b-%Y", "%d %b %Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Could not parse {label} '{s}'. Use YYYY-MM-DD.")


def _describe(rows: pl.DataFrame, limit: int = 25) -> list[dict]:
    out = rows.sort(["is_active", "scheme_name"], descending=[True, False]).head(limit)
    return [
        {
            "scheme_code": r["scheme_code"],
            "scheme_name": r["scheme_name"],
            "plan": r["scheme_plan"],
            "option": r["scheme_option"],
            "first_nav_date": r["first_date"],
            "last_nav_date": r["last_date"],
            "active": r["is_active"],
        }
        for r in out.iter_rows(named=True)
    ]


def _extra_word_count(scheme_norm: str, query_tokens: set[str]) -> int:
    return len(set(scheme_norm.split()) - query_tokens - VARIANT_WORDS)


def _resolve_scheme(scheme_name: str, plan: str | None, option: str | None):
    """Resolve a name/code/ISIN plus plan and option to exactly one scheme.

    Returns (scheme_row, opt_key, notes, error). On failure scheme_row is None and error is the reply dict.
    """
    notes: list[str] = []
    is_code_or_isin = bool(re.fullmatch(r"\s*(\d+|[A-Za-z]{2}[A-Za-z0-9]{9}\d)\s*", scheme_name))

    # --- plan / option -------------------------------------------------------
    if plan is None or plan.strip() == "":
        plan_key = None if is_code_or_isin else "direct"
        if plan_key:
            notes.append("No plan given: using Direct.")
    else:
        plan_key = plan.strip().lower().replace("plan", "").strip()
        if plan_key not in PLAN_ALIASES:
            return None, None, notes, {"status": "error", "message": f"Unknown plan '{plan}'. Use 'direct' or 'regular'."}

    if option is None or option.strip() == "":
        opt_key = None if is_code_or_isin else "growth"
        if opt_key:
            notes.append("No option given: using Growth.")
    else:
        opt_key = " ".join(_tokens(option.replace("_", " ").replace("option", "")))
        if opt_key not in OPTION_ALIASES:
            return None, None, notes, {
                "status": "error",
                "message": f"Unknown option '{option}'. Use 'growth', 'dividend' or 'dividend reinvest'.",
            }

    # --- scheme lookup -------------------------------------------------------
    name_hits = _match_name(scheme_name)
    if name_hits.is_empty():
        return None, None, notes, {
            "status": "not_found",
            "message": f"Scheme '{scheme_name}' was not found. Try search_schemes with a shorter name.",
        }

    cands = name_hits
    if plan_key:
        want_plan = PLAN_ALIASES[plan_key]
        by_plan = cands.filter(pl.col("scheme_plan") == want_plan)
        if by_plan.is_empty() and want_plan == "Regular":
            # Pre-2013 schemes have no Direct/Regular split; their single plan is filed as "Other".
            by_plan = cands.filter(pl.col("scheme_plan") == "Other")
            if not by_plan.is_empty():
                notes.append("No plan filed as 'Regular'; using the legacy plan (AMFI plan 'Other'), "
                             "which is the regular plan for schemes from before the 2013 Direct/Regular split.")
        cands = by_plan
    if opt_key:
        want_opt, sub = OPTION_ALIASES[opt_key]
        cands = cands.filter(pl.col("scheme_option") == want_opt)
        if sub and not cands.is_empty():
            if sub == "reinvest":
                pref = cands.filter(~(pl.col("_has_payout") & ~pl.col("_has_reinv")))
                with_isin2 = pref.filter(pl.col("isin2").is_not_null())
                pref = with_isin2 if not with_isin2.is_empty() else pref
            else:
                pref = cands.filter(~(pl.col("_has_reinv") & ~pl.col("_has_payout")))
            if not pref.is_empty():
                cands = pref

    if cands.is_empty():
        return None, None, notes, {
            "status": "not_found",
            "message": (f"Scheme '{scheme_name}' was found, but not with plan={plan_key or 'any'} "
                        f"and option={opt_key or 'any'}. Available variants are listed."),
            "available_variants": _describe(name_hits),
        }

    # Prefer live schemes, then the closest name (fewest words beyond the query and plan/option words).
    if cands["is_active"].any():
        cands = cands.filter(pl.col("is_active"))
    qtok = set(_tokens(scheme_name))
    cands = cands.with_columns(
        _extra=pl.col("_norm").map_elements(lambda s: _extra_word_count(s, qtok), return_dtype=pl.Int64)
    )
    best = cands.filter(pl.col("_extra") == cands["_extra"].min())
    if best.height > 1:
        return None, None, notes, {
            "status": "ambiguous",
            "message": (f"'{scheme_name}' matches {best.height} schemes for this plan/option. "
                        "Call again with a more specific name or the scheme_code as scheme_name."),
            "candidates": _describe(best),
        }
    return best.row(0, named=True), opt_key, notes, None


def _load_nav(code: int) -> pl.DataFrame:
    return (
        pl.scan_parquet(NAV_FILE)
        .filter(pl.col("scheme_code") == code)
        .select("date", "nav")
        .collect()
        .with_columns(pl.col("date").str.to_date(), pl.col("nav").cast(pl.Float64))
        .sort("date")
    )


@mcp.tool()
def get_nav_history(
    scheme_name: str,
    plan: str | None = None,
    option: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
) -> dict:
    """Get daily NAVs for an Indian mutual fund between two dates and save them as a CSV file.

    Args:
        scheme_name: Fund name, e.g. "HDFC Flexi Cap" or "Parag Parikh Flexi Cap Fund".
            An AMFI scheme code (e.g. 118955) or ISIN is also accepted.
        plan: "direct" or "regular". Defaults to "direct" when omitted.
        option: "growth", "dividend" (IDCW payout) or "dividend reinvest" (IDCW reinvestment).
            Defaults to "growth" when omitted.
        from_date: Start date, YYYY-MM-DD. If omitted or before the scheme's first NAV,
            the scheme's first NAV date is used.
        to_date: End date, YYYY-MM-DD. If omitted or after the scheme's last available NAV,
            the last available NAV date is used.

    Returns the CSV file path, the scheme matched, the effective date range and row count.
    """
    # --- dates ---------------------------------------------------------------
    try:
        req_from = _parse_date(from_date, "from_date")
        req_to = _parse_date(to_date, "to_date")
    except ValueError as e:
        return {"status": "error", "message": str(e)}
    if req_from and req_to and req_from > req_to:
        return {"status": "error", "message": f"from_date {req_from} is after to_date {req_to}."}

    scheme, opt_key, notes, err = _resolve_scheme(scheme_name, plan, option)
    if err:
        return err
    code = scheme["scheme_code"]

    # --- NAV rows ------------------------------------------------------------
    nav = _load_nav(code)
    if nav.is_empty():
        return {"status": "not_found", "message": f"No NAV rows on file for scheme {code} ({scheme['scheme_name']})."}

    first_avail, last_avail = nav["date"].min(), nav["date"].max()
    eff_from, eff_to = req_from or first_avail, req_to or last_avail
    if eff_from < first_avail:
        notes.append(f"from_date {eff_from} is before the scheme's first NAV; using {first_avail}.")
        eff_from = first_avail
    if eff_to > last_avail:
        notes.append(f"to_date {eff_to} is after the last available NAV; using {last_avail}.")
        eff_to = last_avail
    if eff_from > eff_to:
        return {
            "status": "no_data",
            "message": (f"No NAVs in the requested window. {scheme['scheme_name']} has NAVs from "
                        f"{first_avail} to {last_avail}."),
        }

    window = nav.filter(pl.col("date").is_between(eff_from, eff_to))
    zero = window.filter(pl.col("nav") <= 0).height
    if zero:
        window = window.filter(pl.col("nav") > 0)
        notes.append(f"Dropped {zero} row(s) with NAV <= 0 (AMFI placeholder/closing entries).")

    isin = scheme["isin2"] if (opt_key and OPTION_ALIASES[opt_key][1] == "reinvest" and scheme["isin2"]) else (scheme["isin"] or scheme["isin2"])
    out = window.select(
        pl.lit(code).alias("scheme_code"),
        pl.lit(scheme["scheme_name"]).alias("scheme_name"),
        pl.lit(isin).alias("isin"),
        pl.col("date").dt.strftime("%Y-%m-%d").alias("date"),
        pl.col("nav"),
    )

    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / f"nav_{code}_{eff_from:%Y%m%d}_{eff_to:%Y%m%d}.csv"
    out.write_csv(path)

    if scheme["scheme_option"] == "IDCW":
        notes.append("IDCW payout and reinvestment are sub-options of the same plan and share one NAV series.")

    return {
        "status": "ok",
        "csv_file": str(path),
        "rows": out.height,
        "scheme_code": code,
        "scheme_name": scheme["scheme_name"],
        "amc": scheme["amc"],
        "plan": scheme["scheme_plan"],
        "option": scheme["scheme_option"],
        "isin": isin,
        "from_date": str(eff_from),
        "to_date": str(eff_to),
        "scheme_nav_range": f"{first_avail} to {last_avail}",
        "notes": notes,
    }


def _add_months(d: date, k: int) -> date:
    y, m = divmod(d.month - 1 + k, 12)
    y, m = d.year + y, m + 1
    last_day = [31, 29 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 28,
                31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1]
    return date(y, m, min(d.day, last_day))


MODEL_ALIASES = {
    "random_walk": "random_walk", "random walk": "random_walk", "rw": "random_walk", "gbm": "random_walk", "": "random_walk",
    "arima": "arima",
    "sarimax": "sarimax", "sarima": "sarimax", "seasonal": "sarimax",
}
Z80, Z95 = 1.2815516, 1.9599640


def _fit_random_walk(y: np.ndarray, h: int) -> tuple[dict, dict]:
    """Log-drift random walk: drift = mean monthly log return, bands widen with sqrt(k)."""
    rets = np.diff(y)
    mu, sigma = float(rets.mean()), float(rets.std(ddof=1))
    k = np.arange(1, h + 1)
    centre, spread = y[-1] + mu * k, sigma * np.sqrt(k)
    paths = {
        "median": centre,
        "low80": centre - Z80 * spread, "high80": centre + Z80 * spread,
        "low95": centre - Z95 * spread, "high95": centre + Z95 * spread,
    }
    return paths, {"model": "Log-drift random walk (geometric Brownian motion) on monthly NAVs"}


def _fit_arima_family(y: np.ndarray, h: int, seasonal: bool) -> tuple[dict, dict]:
    """Grid-search SARIMAX on monthly log NAV by AIC (d=1 with drift); return log-space paths."""
    pq = range(2) if seasonal else range(3)
    seasonal_grid = [(P, Q) for P in range(2) for Q in range(2)] if seasonal else [(0, 0)]
    best = None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for (p, q), (P, Q) in itertools.product(itertools.product(pq, pq), seasonal_grid):
            try:
                res = SARIMAX(
                    y, order=(p, 1, q),
                    seasonal_order=(P, 0, Q, 12) if (P or Q) else (0, 0, 0, 0),
                    # With d=1, SARIMAX's trend applies to the differenced series, so "c" is a
                    # constant monthly drift. ("t" would make the drift itself grow every month.)
                    trend="c",
                ).fit(disp=False, maxiter=200)
            except Exception:
                continue
            if np.isfinite(res.aic) and (best is None or res.aic < best[0]):
                best = (res.aic, res, (p, 1, q), (P, 0, Q))
    if best is None:
        raise RuntimeError("no ARIMA specification could be fitted to this series")
    aic, res, order, sorder = best
    fc = res.get_forecast(h)
    mean = np.asarray(fc.predicted_mean)
    ci80, ci95 = np.asarray(fc.conf_int(alpha=0.20)), np.asarray(fc.conf_int(alpha=0.05))
    paths = {"median": mean, "low80": ci80[:, 0], "high80": ci80[:, 1], "low95": ci95[:, 0], "high95": ci95[:, 1]}
    p, d, q = order
    if seasonal:
        label = f"SARIMAX({p},{d},{q})({sorder[0]},{sorder[1]},{sorder[2]})[12] with drift, no exogenous inputs"
    else:
        label = f"ARIMA({p},{d},{q}) with drift"
    info = {
        "model": f"{label} on monthly log NAV (chosen by AIC = {aic:.1f})",
        "aic": round(float(aic), 2),
        "order": list(order),
        "seasonal_order": [*sorder, 12] if seasonal else None,
    }
    return paths, info


@mcp.tool()
def forecast_nav(
    scheme_name: str,
    plan: str | None = None,
    option: str | None = None,
    years: int = 5,
    lookback_years: int = 10,
    model: str = "random_walk",
) -> dict:
    """Project a mutual fund's NAV forward month by month (default 5 years) from its latest NAV.

    Models (all fitted to month-end log NAV from the last `lookback_years` of history):
      - "random_walk" (default): log-drift random walk / geometric Brownian motion. Drift and
        volatility of monthly log returns; bands widen with the square root of time.
      - "arima": best ARIMA(p,1,q) with drift, p,q in 0..2, chosen by AIC.
      - "sarimax": best seasonal ARIMA(p,1,q)(P,0,Q)[12] with drift, p,q,P,Q in 0..1, chosen by AIC.
        No exogenous regressors are used (none are available in this dataset).
    For "arima" and "sarimax" each point also carries the random-walk median (rw_median) for comparison.
    Output is the median path with 80% and 95% ranges. A statistical projection, not a prediction.

    Args:
        scheme_name: Fund name, scheme code or ISIN (same matching as get_nav_history).
        plan: "direct" (default) or "regular".
        option: "growth" (default), "dividend" or "dividend reinvest".
        years: Forecast horizon in years, 1-10. Default 5.
        lookback_years: Years of history used to estimate the model, 2-20. Default 10.
        model: "random_walk" (default), "arima" or "sarimax".

    Returns model details, monthly history used, monthly forecast points and a CSV path.
    """
    years = max(1, min(int(years), 10))
    lookback_years = max(2, min(int(lookback_years), 20))
    model_key = MODEL_ALIASES.get((model or "").strip().lower().replace("-", "_"))
    if model_key is None:
        return {"status": "error", "message": f"Unknown model '{model}'. Use 'random_walk', 'arima' or 'sarimax'."}

    scheme, _opt_key, notes, err = _resolve_scheme(scheme_name, plan, option)
    if err:
        return err
    code = scheme["scheme_code"]

    nav = _load_nav(code).filter(pl.col("nav") > 0)
    if nav.height < 60:
        return {"status": "error", "message": f"Not enough NAV history to forecast {scheme['scheme_name']}."}
    last_date = nav["date"].max()
    age = (date.today() - last_date).days
    if age > 31:
        return {
            "status": "error",
            "message": (f"{scheme['scheme_name']} has not published a NAV since {last_date} "
                        "(matured or closed), so there is nothing to project forward from."),
        }

    # Clean daily log returns: a one-day move beyond 2x is a split / face-value change, not performance.
    lr = nav["nav"].log().diff().fill_null(0.0)
    jumps = int((lr.abs() > np.log(2)).sum())
    lr = pl.Series(np.where(np.abs(lr.to_numpy()) > np.log(2), 0.0, lr.to_numpy()))
    adj = lr.cum_sum()
    adj = adj + (np.log(nav["nav"][-1]) - adj[-1])  # anchor to the latest actual NAV
    series = nav.select("date").with_columns(log_nav=adj)
    if jumps:
        notes.append(f"Ignored {jumps} one-day NAV jump(s) above 2x (unit splits or face-value changes).")

    start = date(last_date.year - lookback_years, last_date.month, min(last_date.day, 28))
    train = series.filter(pl.col("date") > start)
    monthly = (
        train.group_by_dynamic("date", every="1mo").agg(pl.col("date").last().alias("d"), pl.col("log_nav").last())
        .select(pl.col("d").alias("date"), "log_nav")
    )
    y = monthly["log_nav"].to_numpy()
    if len(y) < 25:
        return {"status": "error",
                "message": f"{scheme['scheme_name']} has under 2 years of history; too short for a meaningful projection."}
    if len(y) < 12 * lookback_years:
        notes.append(f"Only {len(y)} months of history available (asked for {lookback_years} years).")
    if model_key == "sarimax" and len(y) < 48:
        notes.append("Under 4 years of monthly data: seasonal terms are poorly identified.")

    h = 12 * years
    last_nav = float(nav["nav"][-1])
    rw_paths, rw_info = _fit_random_walk(y, h)
    if model_key == "random_walk":
        paths, info = rw_paths, rw_info
    else:
        try:
            paths, info = _fit_arima_family(y, h, seasonal=(model_key == "sarimax"))
        except Exception as e:
            return {"status": "error", "message": f"{model_key.upper()} could not be fitted: {e}"}
        no_seasonal = info["seasonal_order"] is None or info["seasonal_order"][:3] == [0, 0, 0]
        if info["order"] == [0, 1, 0] and no_seasonal:
            notes.append("AIC chose ARIMA(0,1,0) with drift, which is the random-walk model, so the two lines coincide.")
        elif model_key == "sarimax" and no_seasonal:
            notes.append("AIC preferred no seasonal terms, so SARIMAX reduced to a plain ARIMA for this fund.")

    points = []
    for i in range(h):
        pt = {"date": str(_add_months(last_date, i + 1))}
        for key in ("median", "low80", "high80", "low95", "high95"):
            pt[key] = round(float(np.exp(paths[key][i])), 4)
        if model_key != "random_walk":
            pt["rw_median"] = round(float(np.exp(rw_paths["median"][i])), 4)
        points.append(pt)

    if scheme["scheme_option"] == "IDCW":
        notes.append("IDCW NAVs drop on every payout, so the trend understates total return; "
                     "use the Growth option to project fund performance.")

    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / f"forecast_{code}_{last_date:%Y%m%d}_{model_key}.csv"
    pl.DataFrame(points).select(
        pl.lit(code).alias("scheme_code"), pl.lit(scheme["scheme_name"]).alias("scheme_name"),
        pl.lit(model_key).alias("model"), pl.all(),
    ).write_csv(path)

    rets = np.diff(y)
    history = [{"date": str(d), "nav": round(float(np.exp(v)), 4)} for d, v in zip(monthly["date"], y)]

    def cagr(end_nav: float) -> float:
        return round(float((end_nav / last_nav) ** (1 / years) - 1) * 100, 2)

    out = {
        "status": "ok",
        "csv_file": str(path),
        "scheme_code": code,
        "scheme_name": scheme["scheme_name"],
        "plan": scheme["scheme_plan"],
        "option": scheme["scheme_option"],
        "model_key": model_key,
        "model": info["model"],
        "last_nav_date": str(last_date),
        "last_nav": last_nav,
        "history_from": history[0]["date"],
        "history_months": len(history),
        "historical_cagr_pct": round(float(np.exp(12 * rets.mean()) - 1) * 100, 2),
        "annual_volatility_pct": round(float(rets.std(ddof=1) * np.sqrt(12)) * 100, 2),
        "projected_cagr_pct": cagr(points[-1]["median"]),
        "horizon_years": years,
        "history": history,
        "forecast": points,
        "notes": notes,
        "disclaimer": "Statistical projection from past NAVs only. Not investment advice; actual NAVs can fall outside these ranges.",
    }
    if model_key != "random_walk":
        out["aic"] = info["aic"]
        out["baseline_model"] = rw_info["model"]
        out["baseline_projected_cagr_pct"] = cagr(points[-1]["rw_median"])
    return out


@mcp.tool()
def search_schemes(query: str, active_only: bool = False, limit: int = 25) -> dict:
    """Search mutual fund schemes by name (or scheme code / ISIN) and list their plan/option variants.

    Args:
        query: Words from the fund name, e.g. "parag parikh flexi".
        active_only: Only return schemes that still publish NAVs.
        limit: Maximum rows to return (max 100).
    """
    hits = _match_name(query)
    if active_only:
        hits = hits.filter(pl.col("is_active"))
    if hits.is_empty():
        return {"status": "not_found", "message": f"No scheme matches '{query}'."}
    return {"status": "ok", "total_matches": hits.height, "schemes": _describe(hits, min(max(limit, 1), 100))}


if __name__ == "__main__":
    mcp.run()
