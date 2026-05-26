import re


def extract_data(text):
    data = {}

    text_lower = text.lower()

    # -------------------------
    # HANDLE UPDATE COMMAND FIRST (VERY IMPORTANT)
    # -------------------------
    update_match = re.search(
        r'update\s+(.*?)\s+to\s+(open|lead|quotation|opportunity|lost quotation|do not contact|interested|converted|replied)',
        text,
        re.IGNORECASE
    )

    if update_match:
        entity = update_match.group(1).strip()
        status = update_match.group(2).title()

        return {
            "name": None,
            "email": None,
            "company": entity,   # 🔥 treat as company/search value
            "phone": None,
            "gender": None,
            "job_title": None,
            "lead_type": None,
            "request_type": None,
            "status": status
        }

    # -------------------------
    # EMAIL
    # -------------------------
    email_match = re.search(r'[\w\.-]+@[\w\.-]+', text)
    data["email"] = email_match.group(0) if email_match else None

    # -------------------------
    # PHONE
    # -------------------------
    phone_match = re.search(r'\b\d{10}\b', text)
    data["phone"] = phone_match.group(0) if phone_match else None

    # -------------------------
    # CLEAN TEXT
    # -------------------------
    cleaned = re.sub(
        r'\b(add|create|new|lead|contact)\b',
        '',
        text,
        flags=re.IGNORECASE
    )

    # -------------------------
    # COMPANY (IMPROVED)
    # -------------------------
    company_match = re.search(
        r'(?:company is|company|from|at)\s+([A-Za-z\s]+)',
        text,
        re.IGNORECASE
    )

    if company_match:
        company = company_match.group(1)

        # stop unwanted trailing words
        company = re.split(
            r'\b(mobile|phone|email|gender|he|she|is|mob)\b',
            company,
            flags=re.IGNORECASE
        )[0].strip()

        data["company"] = company
    else:
        data["company"] = None

    # -------------------------
    # NAME (SMART)
    # -------------------------
    name_match = re.search(
        r'\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)?\b',
        cleaned
    )

    if name_match:
        name = name_match.group(0)

        # avoid wrong captures
        if name.lower() not in ["company", "mobile", "email"]:
            data["name"] = name
        else:
            data["name"] = None
    else:
        data["name"] = None

    # -------------------------
    # GENDER
    # -------------------------
    if re.search(r'\bmale\b', text_lower):
        data["gender"] = "Male"
    elif re.search(r'\bfemale\b', text_lower):
        data["gender"] = "Female"
    else:
        data["gender"] = None

    # -------------------------
    # JOB TITLE
    # -------------------------
    job_match = re.search(
        r'\b(owner|ceo|manager|developer|engineer|accountant|hr|intern)\b',
        text_lower
    )

    data["job_title"] = job_match.group(1).capitalize() if job_match else None

    # -------------------------
    # LEAD TYPE
    # -------------------------
    if "client" in text_lower:
        data["lead_type"] = "Client"
    elif "consultant" in text_lower:
        data["lead_type"] = "Consultant"
    elif "partner" in text_lower:
        data["lead_type"] = "Channel Partner"
    else:
        data["lead_type"] = None

    # -------------------------
    # REQUEST TYPE
    # -------------------------
    if "product" in text_lower:
        data["request_type"] = "Product Enquiry"
    elif "information" in text_lower:
        data["request_type"] = "Request for Information"
    elif "suggestion" in text_lower:
        data["request_type"] = "Suggestions"
    else:
        data["request_type"] = None

    return data