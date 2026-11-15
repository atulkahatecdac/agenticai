"""Write the API's OpenAPI spec to docs/openapi.json - the contract the UI and other teams code against.

    python docs/export_openapi.py        (from the warranty_returns folder)
FastAPI generates the spec from the code, so it cannot drift from what the API really accepts.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ.setdefault("CAPSTONE_OFFLINE", "1")

from capstone_common import load_step  # noqa: E402

app = load_step("19_7_api.py").app
spec = app.openapi()
with open(os.path.join(HERE, "openapi.json"), "w", encoding="utf-8") as f:
    json.dump(spec, f, indent=2)
    f.write("\n")
print(f"docs/openapi.json: {len(spec['paths'])} paths - " + ", ".join(spec["paths"]))
