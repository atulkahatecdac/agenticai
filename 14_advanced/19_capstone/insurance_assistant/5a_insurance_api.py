# pip install flask
import json
import sqlite3
import sys
from datetime import datetime

from flask import Flask, jsonify, request

from common import INSURANCE_API_DB, INSURANCE_API_PORT

sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# STEP 5a: the "Insurance API" box in the diagram - a mock of the
# insurer's core policy system. No LLM here: it is an ordinary REST API.
#
# It accepts EXACTLY the JSON from the diagram:
#     POST /api/v1/policy-request
#     {"policy_id": "P12345", "customer_id": "C67890",
#      "coverage_type": "health", "request_type": "get_coverage"}
# and, for step 9 (the only WRITE):
#     POST /api/v1/claims   {"policy_id", "customer_id", "amount", "reason",
#                            "hospital", "admission_date"}
#
# The API checks its inputs itself (does this policy belong to this
# customer? is the amount within what is still available?). It never
# trusts the caller - including our agent.
#
# Run it (leave it running in its own terminal for steps 5b-10):
#   python 5a_insurance_api.py          serve on http://localhost:8020
#   python 5a_insurance_api.py --test   call every endpoint in-process and print the results
# =====================================================================

app = Flask(__name__)
REQUEST_TYPES = {"get_coverage", "get_status", "get_claims"}


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(INSURANCE_API_DB)
    conn.row_factory = sqlite3.Row
    return conn


def load_policy(conn, policy_id: str, customer_id: str):
    """Returns (row, None) or (None, (error response, status))."""
    row = conn.execute("SELECT * FROM coverage WHERE policy_id = ?", (policy_id,)).fetchone()
    if row is None:
        return None, (jsonify(error=f"Policy {policy_id} not found"), 404)
    if row["customer_id"] != customer_id:
        return None, (jsonify(error=f"Policy {policy_id} does not belong to customer {customer_id}"), 403)
    return row, None


@app.get("/health")
def health():
    return jsonify(status="ok")


@app.post("/api/v1/policy-request")
def policy_request():
    body = request.get_json(silent=True) or {}
    missing = [k for k in ("policy_id", "customer_id", "coverage_type", "request_type") if not body.get(k)]
    if missing:
        return jsonify(error=f"Missing fields: {missing}"), 400
    if body["request_type"] not in REQUEST_TYPES:
        return jsonify(error=f"request_type must be one of {sorted(REQUEST_TYPES)}"), 400

    conn = db()
    row, err = load_policy(conn, body["policy_id"], body["customer_id"])
    if err:
        conn.close()
        return err
    if row["coverage_type"] != body["coverage_type"]:
        conn.close()
        return jsonify(error=f"Policy {row['policy_id']} is a {row['coverage_type']} policy"), 400

    base = {"policy_id": row["policy_id"], "coverage_type": row["coverage_type"],
            "status": row["status"], "valid_till": row["valid_till"]}
    if body["request_type"] == "get_coverage":
        base.update(sum_insured=row["sum_insured"], claimed_amount=row["claimed_amount"],
                    available_amount=row["sum_insured"] - row["claimed_amount"],
                    room_rent_limit_per_day=row["room_rent_limit_per_day"],
                    copay_percent=row["copay_percent"], no_claim_bonus_percent=row["no_claim_bonus_percent"],
                    currency="INR")
    elif body["request_type"] == "get_claims":
        base["claims"] = [dict(r) for r in conn.execute(
            "SELECT claim_id, amount, reason, hospital, admission_date, status, submitted_at "
            "FROM claims WHERE policy_id = ? ORDER BY submitted_at DESC", (row["policy_id"],))]
    conn.close()
    return jsonify(base)


@app.post("/api/v1/claims")
def submit_claim():
    body = request.get_json(silent=True) or {}
    missing = [k for k in ("policy_id", "customer_id", "amount", "reason", "hospital", "admission_date")
               if not body.get(k)]
    if missing:
        return jsonify(error=f"Missing fields: {missing}"), 400
    try:
        amount = int(body["amount"])
    except (TypeError, ValueError):
        return jsonify(error="amount must be a whole number of rupees"), 400

    conn = db()
    row, err = load_policy(conn, body["policy_id"], body["customer_id"])
    if err:
        conn.close()
        return err
    available = row["sum_insured"] - row["claimed_amount"]
    problem = None
    if row["status"] != "Active":
        problem = f"Policy status is '{row['status']}' - claims can only be filed on an Active policy"
    elif not 0 < amount <= available:
        problem = f"Claim amount must be between 1 and the available amount ({available})"
    if problem:
        conn.close()
        return jsonify(error=problem), 422

    n = conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
    claim_id = f"CL-{1001 + n}"
    conn.execute("INSERT INTO claims VALUES (?,?,?,?,?,?,?,?,?,?)",
                 (claim_id, row["policy_id"], row["customer_id"], amount, body["reason"], body["hospital"],
                  body["admission_date"], "Submitted - under review", datetime.now().strftime("%Y-%m-%d %H:%M"),
                  body.get("approved_by", "")))
    conn.commit()
    conn.close()
    return jsonify(claim_id=claim_id, status="Submitted - under review", amount=amount,
                   policy_id=row["policy_id"]), 201


def run_tests() -> None:
    client = app.test_client()

    def call(title, path, body):
        r = client.post(path, json=body)
        print(f"\n{title}\n  POST {path} {json.dumps(body)}\n  -> {r.status_code} {json.dumps(r.get_json())}")

    diagram = {"policy_id": "P12345", "customer_id": "C67890", "coverage_type": "health",
               "request_type": "get_coverage"}
    call("1. The request from the diagram", "/api/v1/policy-request", diagram)
    call("2. Past claims", "/api/v1/policy-request", {**diagram, "request_type": "get_claims"})
    call("3. Someone else's policy (P99999 belongs to C11111)", "/api/v1/policy-request",
         {**diagram, "policy_id": "P99999"})
    call("4. Unknown request_type", "/api/v1/policy-request", {**diagram, "request_type": "delete_policy"})
    call("5. Claim on a LAPSED policy", "/api/v1/claims",
         {"policy_id": "P10001", "customer_id": "C67890", "amount": 5000, "reason": "Fever",
          "hospital": "City Hospital", "admission_date": "2026-09-20"})
    call("6. Claim larger than the available amount", "/api/v1/claims",
         {"policy_id": "P12345", "customer_id": "C67890", "amount": 900000, "reason": "Surgery",
          "hospital": "City Hospital", "admission_date": "2026-09-20"})
    print("\n(No claim was written: the test does not create data. Step 9 files a real one.)")


if __name__ == "__main__":
    if "--test" in sys.argv:
        run_tests()
    else:
        print(f"Insurance API on http://localhost:{INSURANCE_API_PORT}  (Ctrl+C to stop)")
        app.run(port=INSURANCE_API_PORT, debug=False)
