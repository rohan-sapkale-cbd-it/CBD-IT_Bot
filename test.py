from erp_client import (
    create_lead,
    update_lead_status,
    handle_quotation_flow,
    create_ticket,
    search_customer,
    update_issue_status
)
#
from extractor import extract_data
from llm_extractor import extract_with_llm
import re


# =========================
# INTENT DETECTION
# =========================
def detect_intent(text):
    text = text.lower()

    if "ticket" in text or "issue" in text or "support" in text:
        return "ticket"

    if "share quotation" in text:
        return "quotation"

    if "issue" in text and ("update" in text or "change" in text):
        return "issue_update"

    if "update" in text or "status" in text or "change" in text:
        return "update"

    if "create" in text or "add" in text or "new lead" in text:
        return "create"

    return "unknown"


# =========================
# DATA EXTRACTION
# =========================
def extract_final_data(text):
    regex_data = extract_data(text)
    llm_data = extract_with_llm(text)

    final_data = {}

    for key in ["name", "email", "company", "phone", "gender", "job_title"]:
        final_data[key] = regex_data.get(key) or llm_data.get(key)

    return final_data


# =========================
# 🎫 TICKET FLOW (STATEFUL)
# =========================
def handle_ticket(text, session):

    # STEP 1 → Identify customer
    if session["step"] == "START":

        match = re.search(r'for\s+(.+)', text, re.IGNORECASE)

        if not match:
            print("❌ Use: create ticket for <company>")
            return session

        company = match.group(1).strip()

        print("🔍 Searching Customer for:", company)

        customers = search_customer(company)

        if not customers:
            print("❌ No customer found")
            return {"active": False}

        customer = customers[0]

        session["customer"] = customer["name"]

        print(f"📌 Customer: {customer['customer_name']}")
        print("📝 Enter issue description:")

        session["step"] = "WAIT_DESCRIPTION"
        return session

    # STEP 2 → Description
    elif session["step"] == "WAIT_DESCRIPTION":

        if not text.strip():
            print("❌ Description required")
            return session

        session["description"] = text.strip()

        print("⚡ Enter priority (Low / Medium / High):")
        session["step"] = "WAIT_PRIORITY"
        return session

    # STEP 3 → Priority
    elif session["step"] == "WAIT_PRIORITY":

        priority = text.strip().capitalize()

        if priority not in ["Low", "Medium", "High"]:
            print("❌ Invalid priority. Use Low / Medium / High")
            return session

        ticket_id = create_ticket(
            customer=session["customer"],
            description=session["description"],
            priority=priority
        )

        if ticket_id:
            print(f"✅ Ticket Created: {ticket_id}")
        else:
            print("❌ Ticket failed")

        # FULL RESET
        return {"active": False, "step": None}

    return session


# =========================
# 🔁 LEAD UPDATE FLOW
# =========================
def handle_update(text, data):

    VALID_STATUS = [
        "Open", "Lead", "Quotation", "Opportunity",
        "Lost Quotation", "Do Not Contact",
        "Interested", "Converted", "Replied"
    ]

    status = None
    for s in VALID_STATUS:
        if s.lower() in text.lower():
            status = s
            break

    if not status:
        print("❌ No valid status found")
        return

    print(f"📌 Company: {data.get('company')}")
    print(f"🔁 Status: {status}")

    update_lead_status(data, status)


# =========================
# 🎫 ISSUE STATUS UPDATE
# =========================
def handle_issue_update(text):

    match = re.search(
        r'(?:update|change)\s+(?:issue|ticket)\s+(ISS-\d+)\s+to\s+(open|replied|on hold|resolved|closed)',
        text,
        re.IGNORECASE
    )

    if not match:
        print("❌ Use: Update issue ISS-00001 to Resolved")
        return

    issue_id = match.group(1).upper()
    status = match.group(2).title()

    if status.lower() == "on hold":
        status = "On Hold"

    print(f"🎫 Issue: {issue_id}")
    print(f"🔁 New Status: {status}")

    update_issue_status(issue_id, status)


# =========================
# 🤖 MAIN AGENT
# =========================
def agent():
    print("\n🤖 CRM AI Agent Ready")
    print("Type 'exit' to quit\n")

    session = {"active": False, "step": None}

    while True:
        try:
            text = input("🧠 You: ").strip()

            if not text:
                continue

            if text.lower() in ["exit", "quit"]:
                print("👋 Exiting agent...")
                break

            # -------------------------
            # CONTINUE SESSION
            # -------------------------
            if session.get("active"):
                session = handle_ticket(text, session)
                continue

            # -------------------------
            # NEW INTENT
            # -------------------------
            intent = detect_intent(text)

            if intent == "ticket":
                session = {"active": True, "step": "START"}
                session = handle_ticket(text, session)

            elif intent == "issue_update":
                handle_issue_update(text)

            elif intent == "update":
                data = extract_final_data(text)
                handle_update(text, data)

            elif intent == "create":
                data = extract_final_data(text)
                print("🚀 Creating lead...")
                create_lead(data)

            elif intent == "quotation":
                handle_quotation_flow(text)

            else:
                print("🤖 Try:")
                print("- Create lead for Rohan from ABC company")
                print("- Update ABC company to Quotation")
                print("- Create ticket for ABC company")
                print("- Update issue ISS-00001 to Resolved")

        except KeyboardInterrupt:
            print("\n👋 Agent stopped")
            break

        except Exception as e:
            print("❌ Error:", str(e))


if __name__ == "__main__":
    agent()
