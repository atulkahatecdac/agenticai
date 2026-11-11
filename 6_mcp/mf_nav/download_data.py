"""Refresh the NAV data used by mf_nav_server.py.

Same files as the "Download Full Database" page at
https://mfpro.tigzig.com/dashboard#returns/data-api/download (rebuilt 3x daily from AMFI).
"""

from pathlib import Path

import requests

BASE = "https://api.tigzig.com/mf/v1/download/"
FILES = ["amfi_nav_master.parquet", "amfi_nav_master_latest.parquet"]
DATA_DIR = Path(__file__).resolve().parent / "data"


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    for name in FILES:
        target = DATA_DIR / name
        tmp = target.with_suffix(".part")
        print(f"Downloading {name} ...")
        with requests.get(BASE + name, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(1 << 20):
                    f.write(chunk)
        tmp.replace(target)
        print(f"  saved {target} ({target.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
