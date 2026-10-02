# pip install streamlit requests
import json
import time

import requests
import streamlit as st

from capstone_common import API_URL, TICKETS_FILE

# =====================================================================
# STEP 8 of the capstone: the Streamlit front-end.
#
# Two screens over the SAME FastAPI backend (19_7):
#   Customer   type a message (or pick a sample ticket), watch the agents
#              work step by step, read the reply
#   Approver   see tickets paused at the approval gate, approve or reject
#
# There is no business logic here - every button is one HTTP call:
#   Submit          -> POST /tickets, then GET /tickets/{id} until it stops
#   Approve/Reject  -> POST /tickets/{id}/approve
#
# Run it (two terminals, from 14_advanced/19_capstone):
#   python 19_7_api.py                  terminal 1 - the backend
#   streamlit run 19_8_ui_streamlit.py  terminal 2 - opens http://localhost:8501
# =====================================================================

st.set_page_config(page_title="ElectroMart Support", layout="wide")


def api(method: str, path: str, **kwargs):
    return requests.request(method, API_URL + path, timeout=10, **kwargs).json()


def show_ticket(ticket: dict):
    for event in ticket["events"]:
        st.write(f"**{event['node'].replace('_', ' ')}** - {event['detail']}")
    if ticket["status"] == "waiting_approval":
        st.warning("This request needs approval from a support approver. "
                   "Open the **Approver** tab to approve or reject it, then press *Check status*.")
    elif ticket["status"] == "done":
        st.success(f"Decision: {ticket['decision']}   |   Status: {ticket['final_status']}")
        st.text_area("Reply sent to the customer", ticket["reply"], height=230)
    elif ticket["status"] == "error":
        st.error(ticket["reply"])


try:
    health = api("GET", "/health")
except requests.RequestException:
    st.error(f"The backend is not running at {API_URL}. Start it first:  python 19_7_api.py")
    st.stop()

st.title("ElectroMart - Warranty & Returns Assistant")
st.caption(f"Backend: {API_URL}   |   mode: {health['mode']}   |   tickets this session: {health['tickets']}")

customer_tab, approver_tab = st.tabs(["Customer", "Approver"])

with customer_tab:
    with open(TICKETS_FILE, encoding="utf-8") as f:
        samples = {f"{t['id']} - {t['about']}": t["message"] for t in json.load(f)}
    choice = st.selectbox("Sample tickets (or type your own below)", ["(type my own)"] + list(samples))
    message = st.text_area("Your message", samples.get(choice, ""), height=90)

    left, right = st.columns([1, 5])
    if left.button("Submit", type="primary") and message.strip():
        created = api("POST", "/tickets", json={"message": message})
        st.session_state["ticket_id"] = created["ticket_id"]
        with st.status(f"Ticket {created['ticket_id']} - agents at work...", expanded=True) as progress:
            shown = 0
            while True:
                ticket = api("GET", f"/tickets/{created['ticket_id']}")
                for event in ticket["events"][shown:]:
                    st.write(f"**{event['node'].replace('_', ' ')}** - {event['detail']}")
                shown = len(ticket["events"])
                if ticket["status"] != "running":
                    break
                time.sleep(0.3)
            progress.update(label=f"Ticket {created['ticket_id']} - {ticket['status'].replace('_', ' ')}",
                            state="complete")
    if right.button("Check status") and "ticket_id" not in st.session_state:
        st.info("Submit a ticket first.")

    if "ticket_id" in st.session_state:
        st.divider()
        st.subheader(f"Ticket {st.session_state['ticket_id']}")
        show_ticket(api("GET", f"/tickets/{st.session_state['ticket_id']}"))

with approver_tab:
    st.button("Refresh")
    approvals = api("GET", "/approvals")
    if not approvals:
        st.info("No tickets are waiting for approval.")
    for item in approvals:
        amount = f" of Rs. {item['refund_amount']:,.0f}" if item["refund_amount"] else ""
        with st.expander(f"{item['ticket_id']} - proposed: {item['decision']}{amount}", expanded=True):
            st.write(f"**Customer message:** {item['message']}")
            st.write(f"**Why it needs approval:** {item['why_approval']}")
            st.write(f"**Agent's reasoning:** {item['reason']}")
            st.text_area("Draft reply", item["draft_reply"], height=180, key=f"draft-{item['ticket_id']}")
            approve, reject, _ = st.columns([1, 1, 6])
            if approve.button("Approve", key=f"yes-{item['ticket_id']}", type="primary"):
                api("POST", f"/tickets/{item['ticket_id']}/approve", json={"approved": True, "note": "approved in UI"})
                st.rerun()
            if reject.button("Reject", key=f"no-{item['ticket_id']}"):
                api("POST", f"/tickets/{item['ticket_id']}/approve", json={"approved": False, "note": "rejected in UI"})
                st.rerun()
