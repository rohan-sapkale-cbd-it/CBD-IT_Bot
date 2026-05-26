sessions = {}

def process_message(user_id, text):

    session = sessions.get(user_id, {"active": False, "step": None})

    # CONTINUE SESSION
    if session.get("active"):
        response, session = handle_ticket_api(text, session)
        sessions[user_id] = session
        return response

    # NEW INTENT
    intent = detect_intent(text)

    if intent == "ticket":
        session = {"active": True, "step": "START"}
        response, session = handle_ticket_api(text, session)
        sessions[user_id] = session
        return response

    elif intent == "create":
        data = extract_final_data(text)
        create_lead(data)
        return {"message": "Lead created successfully"}

    elif intent == "update":
        data = extract_final_data(text)
        handle_update(text, data)
        return {"message": "Lead updated"}

    elif intent == "quotation":
        return {"message": "Quotation flow needs UI inputs"}  # temp

    return {"message": "Unknown command"}
