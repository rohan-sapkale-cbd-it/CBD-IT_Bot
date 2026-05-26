from fastapi import FastAPI
from agent_core import process_message

app = FastAPI()

@app.post("/chat")
def chat(data: dict):
    user_id = data.get("user_id", "default")
    message = data.get("message")

    response = process_message(user_id, message)

    return response
