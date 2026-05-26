import requests
import json
import re
import os
from dotenv import load_dotenv
from email_utils import send_email

# =========================
# CONFIG
# =========================
ERP_URL = "http://127.0.0.1:8000/api/resource"

load_dotenv()

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
print("API_KEY:", API_KEY)
print("API_SECRET:", API_SECRET)
headers = {
    "Authorization": f"token {API_KEY}:{API_SECRET}",
    "Content-Type": "application/json"
}

VALID_STATUS = [
    "Open", "Lead", "Quotation", "Opportunity",
    "Lost Quotation", "Do Not Contact",
    "Interested", "Converted", "Replied"
]

# =========================
# CREATE LEAD
# =========================
def create_lead(data):
    url = f"{ERP_URL}/Lead"

    payload = {
        "first_name": data.get("name"),
        "email_id": data.get("email"),
        "mobile_no": data.get("phone"),
        "company_name": data.get("company"),
        "gender": data.get("gender"),
        "job_title": data.get("job_title"),
        "status": "Open"
    }

    payload = {k: v for k, v in payload.items() if v}

    res = requests.post(url, json=payload, headers=headers)
    print("📦 Lead Created:", res.text)

    return res.json()

# =========================
# 🎫 CREATE TICKET
# =========================
def create_ticket(customer, description, priority):
    url = f"{ERP_URL}/Issue"

    payload = {
        "doctype": "Issue",
        "subject": f"Issue - {customer}",
        "customer": customer,
        "description": description,
        "priority": priority,
        "status": "Open"
    }

    res = requests.post(url, json=payload, headers=headers)

    if res.status_code in [200, 201]:
        return res.json()["data"]["name"]
    else:
        print("❌ Ticket creation failed:", res.text)
        return None

def handle_ticket_api(text, session):

    if session["step"] == "START":

        match = re.search(r'for\s+(.+)', text, re.IGNORECASE)

        if not match:
            return {"message": "Use: create ticket for <company>"}, session

        company = match.group(1)

        customers = search_customer(company)

        if not customers:
            return {"message": "No customer found"}, {"active": False}

        session["customer"] = customers[0]["name"]
        session["step"] = "WAIT_DESCRIPTION"

        return {"message": "Enter issue description"}, session

    elif session["step"] == "WAIT_DESCRIPTION":

        session["description"] = text
        session["step"] = "WAIT_PRIORITY"

        return {"message": "Enter priority (Low/Medium/High)"}, session

    elif session["step"] == "WAIT_PRIORITY":

        ticket_id = create_ticket(
            session["customer"],
            session["description"],
            text
        )

        return {
            "message": f"Ticket created: {ticket_id}"
        }, {"active": False}

def handle_ticket_flow(text, session):

    # STEP 1: get customer
    if session["step"] is None:

        match = re.search(r'for\s+(.+)', text, re.IGNORECASE)

        if not match:
            print("❌ Use: create ticket for <company>")
            return session

        company = match.group(1).strip()

        customers = search_customer(company)

        if not customers:
            print("❌ No matching customer found")
            return session

        selected = customers[0]

        session["customer"] = selected["name"]

        print(f"📌 Customer: {selected['customer_name']}")
        print("📝 Enter issue description:")

        session["step"] = "WAIT_DESCRIPTION"
        return session

    # STEP 2: description
    elif session["step"] == "WAIT_DESCRIPTION":

        if not text.strip():
            print("❌ Description required")
            return session

        session["description"] = text.strip()

        print("⚡ Enter priority (Low / Medium / High):")
        session["step"] = "WAIT_PRIORITY"
        return session

    # STEP 3: priority
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

        # RESET SESSION
        return {"intent": None, "step": None, "data": {}}

    return session
# =========================
# 🔍 SEARCH CUSTOMER
# =========================
def search_customer(company_name):
    url = f"{ERP_URL}/Customer"

    search_value = company_name.lower().strip()

    print("🔍 Searching Customer for:", search_value)

    # Step 1: direct LIKE
    filters = json.dumps([
        ["customer_name", "like", f"%{company_name}%"]
    ])

    full_url = f'{url}?fields=["name","customer_name"]&filters={filters}'

    res = requests.get(full_url, headers=headers)
    data = res.json().get("data", [])

    if data:
        print("✅ Direct match:", data[0])
        return data

    # Step 2: fetch all + token match
    print("⚠️ Trying fallback match...")

    all_url = f'{url}?fields=["name","customer_name"]'
    res = requests.get(all_url, headers=headers)
    all_customers = res.json().get("data", [])

    tokens = normalize(company_name).split()

    for cust in all_customers:
        name = normalize(cust.get("customer_name", ""))

        if any(token in name for token in tokens):
            print("✅ Token match:", cust)
            return [cust]

    print("❌ No customer found")
    return []


def get_customer_details(customer_name):
    url = f"{ERP_URL}/Customer/{customer_name}"

    params = {
        "fields": '["name","customer_name","custom_tally_serial_no"]'
    }

    res = requests.get(url, headers=headers, params=params)

    if res.status_code == 200:
        data = res.json().get("data", {})
        print("🧾 CUSTOMER DOC:", data)  # ✅ DEBUG WORKS NOW
        return data
    else:
        print("❌ Failed to fetch customer details:", res.text)
        return None
# =========================
# FIND LEAD
# =========================
def find_lead(data):
    url = f"{ERP_URL}/Lead"

    search_value = data.get("company") or data.get("name")

    if not search_value:
        print("❌ No search value")
        return None

    print("🔍 Searching Lead for:", search_value)

    # 🔹 Step 1: Direct LIKE search
    filters = json.dumps([
        ["company_name", "like", f"%{search_value}%"]
    ])

    full_url = f'{url}?fields=["name","lead_name","company_name","status","email_id"]&filters={filters}'

    res = requests.get(full_url, headers=headers)

    leads = res.json().get("data", [])

    if leads:
        print("✅ Direct match:", leads[0])
        return leads[0]

    # 🔹 Step 2: Token-based fallback
    print("⚠️ Trying token match...")

    all_leads_url = f'{url}?fields=["name","company_name","status"]'
    res = requests.get(all_leads_url, headers=headers)

    all_leads = res.json().get("data", [])

    input_tokens = normalize(search_value).split()

    for lead in all_leads:
        company = normalize(lead.get("company_name", ""))

        # check if ANY token matches
        if any(token in company for token in input_tokens):
            print("✅ Token match:", lead)
            return lead

    print("❌ No lead found")
    return None


def normalize(text):
    if not text:
        return ""
    
    text = text.lower().strip()
    text = text.replace("industries", "")
    text = text.replace("industry", "")
    text = text.replace("pvt ltd", "")
    text = text.replace("private limited", "")
    text = text.replace("company", "")
    
    return text.strip()
    
    return text.strip()
def get_all_leads():
    url = f"{ERP_URL}/Lead?fields=[\"name\",\"company_name\",\"status\",\"email_id\"]"

    res = requests.get(url, headers=headers)

    if res.status_code != 200:
        print("❌ Failed to fetch leads:", res.text)
        return []

    return res.json().get("data", [])

# =========================
# UPDATE STATUS
# =========================
def update_lead_status(data, new_status):
    if new_status not in VALID_STATUS:
        print("❌ Invalid status")
        return

    lead = find_lead(data)

    if not lead:
        print("❌ No lead found")
        return

    url = f"{ERP_URL}/Lead/{lead['name']}"
    payload = {"status": new_status}

    res = requests.put(url, json=payload, headers=headers)
    print("🔁 Status Updated:", res.text)


# =========================
# GET ITEM CODE
# =========================
def get_item_code(item_name):
    url = f"{ERP_URL}/Item"

    filters = json.dumps([["item_name", "=", item_name]])
    full_url = f'{url}?fields=["item_code","item_name"]&filters={filters}'

    res = requests.get(full_url, headers=headers)
    items = res.json().get("data", [])

    if items:
        return items[0]["item_code"]

    return None


# =========================
# CREATE QUOTATION
# =========================
def create_quotation(lead, item_code, qty, rate):

    url = f"{ERP_URL}/Quotation"

    payload = {
        "doctype": "Quotation",
        "quotation_to": "Lead",
        "party_name": lead["name"],
        "transaction_date": "2026-04-01",
        "valid_till": "2026-04-10",
        "items": [
            {
                "item_code": item_code,
                "qty": qty,
                "rate": rate
            }
        ]
    }

    print("🚀 FINAL PAYLOAD:", payload)

    res = requests.post(url, json=payload, headers=headers)

    print("STATUS:", res.status_code)
    print("RAW:", res.text)

    response = res.json()

    # ✅ EMAIL TRIGGER (ONLY ON SUCCESS)
    if response.get("data"):
        quotation_name = response["data"]["name"]

        print("📄 Quotation Created:", quotation_name)

        pdf = get_quotation_pdf(quotation_name)

        if pdf and lead.get("email_id"):
            send_email(
            to_email=lead["email_id"],
            subject="Your Quotation",
            body=f"""
Hello {lead.get('lead_name')},

Please find attached your quotation.

Quotation ID: {quotation_name}

Thank you.
""",
            attachment=pdf,
            filename=f"{quotation_name}.pdf"
        )


# =========================
# 🔥 QUOTATION FLOW
# =========================
def handle_quotation_flow(text):

    match = re.search(r'share quotation to (.+)', text, re.IGNORECASE)

    if not match:
        print("❌ Could not extract company")
        return

    company = match.group(1).strip()
    print("📌 Searching for:", company)

    lead = find_lead({"company": company})

    if not lead:
        print("❌ Lead not found")
        return

    if lead.get("status") != "Quotation":
        print(f"⚠️ Lead status is '{lead.get('status')}'")
        print("👉 Update status to 'Quotation' first")
        return

    print("✅ Lead ready:", lead["name"])

    # PRODUCT MENU
    print("\n📦 Select Product:")
    print("1. Tally Prime Single User")
    print("2. Tally Prime Multi User")
    print("3. Tally Prime Single User Renewal")
    print("4. Tally Prime Multi User Renewal")
    print("5. Tally Prime Whatsapp Subscription")
    print("6. Tally Prime WhatsApp Renewal")

    choice = input("Enter choice (1-6): ").strip()

    product_map = {
        "1": "Tally Prime Single User",
        "2": "Tally Prime Multi User",
        "3": "Tally Prime Single User Renewal",
        "4": "Tally Prime Multi User Renewal",
        "5": "Tally Prime Whatsapp Subscription",
        "6": "Tally Prime WhatsApp Renewal"
    }

    item_name = product_map.get(choice)

    if not item_name:
        print("❌ Invalid choice")
        return

    item_code = get_item_code(item_name)

    if not item_code:
        print("❌ Item not found in ERP:", item_name)
        return

    try:
        qty = int(input("Enter Quantity: "))
        rate = float(input("Enter Rate: "))
    except ValueError:
        print("❌ Invalid input")
        return

    create_quotation(lead, item_code, qty, rate)

def update_issue_status(issue_name, new_status):
    VALID_STATUS = ["Open", "Replied", "On Hold", "Resolved", "Closed"]

    if new_status not in VALID_STATUS:
        print("❌ Invalid issue status")
        return

    url = f"{ERP_URL}/Issue/{issue_name}"

    payload = {
        "status": new_status
    }

    res = requests.put(url, json=payload, headers=headers)

    if res.status_code in [200, 201]:
        print(f"✅ Issue {issue_name} updated to {new_status}")
    else:
        print("❌ Issue update failed:", res.text)
def get_quotation_pdf(quotation_name):
    url = "http://127.0.0.1:8000/api/method/frappe.utils.print_format.download_pdf"

    params = {
        "doctype": "Quotation",
        "name": quotation_name,
        "format": "Standard"
    }

    res = requests.get(url, params=params, headers=headers)

    if res.status_code == 200:
        return res.content  # binary PDF
    else:
        print("❌ Failed to fetch PDF:", res.text)
        return None
