"""Repo-wide smoke test: catches broken scripts without calling any LLM/API.

The demo scripts run real work at import time (API calls, input() prompts,
Flask servers), so this never imports or runs them. Instead it checks:

  1. syntax    - every .py file compiles
  2. paths     - no string literal starting with a drive letter (C:\\code\\...
                 style absolute paths); use os.path.join(BASE_DIR, ...) instead
  3. imports   - every third-party package the scripts import can actually be
                 imported in the current environment (each in its own
                 subprocess). This is what catches pin drift, e.g. a package
                 upgraded to an incompatible version.

Usage (from the repo root, with the venv active):
    python tools/smoke_test.py               # all three checks
    python tools/smoke_test.py --no-imports  # quick: syntax + paths only (seconds)
    python tools/smoke_test.py --strict      # also fail on packages that aren't installed

Exit code is 1 if a syntax error, hardcoded path, or broken import is found.
A package that is simply not installed is only a warning (unless --strict),
because some folders deliberately need their own venv (see SEPARATE_ENV_*).
"""
import argparse
import ast
import os
import re
import subprocess
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SKIP_DIRS = {".git", ".venv", "venv", "env", "__pycache__", "node_modules", ".deepeval", ".claude"}

# Folders whose scripts are meant to run in their own venv, not the root one.
# Their imports are still syntax/path-checked, just not import-checked.
SEPARATE_ENV_DIRS = {
    os.path.join("7_n8n", "visual-demo"),  # own venv/ + requirements.txt (see its README)
    os.path.join("9_general", "dspy"),  # dspy conflicts with crewai (json-repair pin)
    os.path.join("12_project", "12_1_openai_agents_diet_agent"),  # ships its own venv/
    os.path.join("14_advanced", "02_gradio_fastapi"),  # own requirements.txt
    os.path.join("14_advanced", "07_langgraph"),  # own requirements.txt
    os.path.join("14_advanced", "18_Dockerizing"),  # runs inside Docker images
    os.path.join("14_advanced", "19_capstone"),  # each capstone has its own setup
}
# Packages documented as needing a separate venv wherever they appear.
# guardrails (14_advanced/16_guardrails/16_5) and phoenix (14_advanced/17_.../17_6) pull
# langchain-core 1.x / newer OpenTelemetry; each has its own 16_5_/17_6_requirements.txt.
SEPARATE_ENV_MODULES = {"dspy", "docling", "langchain_docling", "guardrails", "phoenix"}

# A string literal that starts with a drive letter, e.g. "C:\..." or 'd:/...'
ABS_PATH = re.compile(r"""(?<![A-Za-z0-9_])[rRbBfFuU]{0,2}(["'])[A-Za-z]:(\\|/)""")

IMPORT_TIMEOUT = 180


def iter_py_files():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for fn in sorted(filenames):
            if fn.endswith(".py"):
                yield os.path.join(dirpath, fn)


def rel(path):
    return os.path.relpath(path, ROOT)


def in_separate_env(path):
    r = rel(path)
    return any(r == d or r.startswith(d + os.sep) for d in SEPARATE_ENV_DIRS)


def is_local(module, script_path):
    """True if `module` is a .py file or package folder in the script's folder
    or any parent folder up to the repo root (sys.path[0] plus the usual
    "run it from the project folder" layouts)."""
    d = os.path.dirname(script_path)
    while True:
        if os.path.isfile(os.path.join(d, module + ".py")) or os.path.isdir(os.path.join(d, module)):
            return True
        if os.path.normcase(d) == os.path.normcase(ROOT):
            return False
        d = os.path.dirname(d)


def check_paths(source):
    hits = []
    for lineno, line in enumerate(source.splitlines(), 1):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        if ABS_PATH.search(line):
            hits.append((lineno, stripped[:120]))
    return hits


def top_level_imports(tree):
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            mods.add(node.module.split(".")[0])
    return mods


def try_import(module):
    try:
        proc = subprocess.run(
            [sys.executable, "-c", f"import {module}"],
            capture_output=True, text=True, timeout=IMPORT_TIMEOUT, cwd=ROOT,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
    except subprocess.TimeoutExpired:
        return module, "broken", f"import took longer than {IMPORT_TIMEOUT}s"
    if proc.returncode == 0:
        return module, "ok", ""
    err = proc.stderr.strip().splitlines()
    last = err[-1] if err else f"exit code {proc.returncode}"
    if f"No module named '{module}'" in last:
        return module, "missing", last
    return module, "broken", last


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-imports", action="store_true", help="skip the (slow) import check")
    ap.add_argument("--strict", action="store_true", help="treat not-installed packages as failures")
    ap.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 4))
    args = ap.parse_args()

    syntax_errors, path_hits = [], []
    module_users = defaultdict(list)
    files = list(iter_py_files())

    for path in files:
        try:
            with open(path, encoding="utf-8-sig") as f:
                source = f.read()
            tree = ast.parse(source, filename=path)
        except (SyntaxError, UnicodeDecodeError, ValueError) as e:
            syntax_errors.append((rel(path), f"{type(e).__name__}: {e}"))
            continue
        for lineno, text in check_paths(source):
            path_hits.append((rel(path), lineno, text))
        if not in_separate_env(path):
            for mod in top_level_imports(tree):
                if not is_local(mod, path):
                    module_users[mod].append(rel(path))

    print(f"Checked {len(files)} Python files under {ROOT}\n")

    print(f"[1] syntax: {len(syntax_errors)} error(s)")
    for p, err in syntax_errors:
        print(f"    {p}: {err}")

    print(f"[2] hardcoded absolute paths: {len(path_hits)} hit(s)")
    for p, lineno, text in path_hits:
        print(f"    {p}:{lineno}: {text}")

    broken, missing = [], []
    if args.no_imports:
        print("[3] imports: skipped (--no-imports)")
    else:
        stdlib = set(sys.stdlib_module_names)
        candidates = sorted(
            m for m in module_users
            if m not in stdlib and m not in SEPARATE_ENV_MODULES and m != "__future__"
        )
        print(f"[3] imports: checking {len(candidates)} third-party packages "
              f"with {args.workers} workers (this can take a few minutes)...")
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for module, status, detail in pool.map(try_import, candidates):
                users = module_users[module]
                where = f"{users[0]}" + (f" (+{len(users) - 1} more)" if len(users) > 1 else "")
                if status == "broken":
                    broken.append(module)
                    print(f"    BROKEN   {module}: {detail}\n             used by {where}")
                elif status == "missing":
                    missing.append(module)
                    print(f"    missing  {module}  (used by {where})")
        ok = len(candidates) - len(broken) - len(missing)
        print(f"    -> {ok} ok, {len(broken)} broken, {len(missing)} not installed")

    failed = bool(syntax_errors or path_hits or broken or (args.strict and missing))
    print("\nRESULT:", "FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
