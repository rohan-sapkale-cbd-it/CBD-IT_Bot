import requests
import json
import re

def extract_with_llm(text):
    try:
        prompt = f"""
Extract the following fields from the text.

STRICT RULES:
- Return ONLY valid JSON
- No explanation
- No markdown
- No extra text

Format:
{{
"name": "",
"email": "",
"company": "",
"phone": "",
"gender": "",
"job_title": ""
}}

Text:
{text}
"""

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "tinyllama",
                "prompt": prompt,
                "stream": False
            }
        )

        result = response.json()
        raw_output = result.get("response", "").strip()

        print("LLM RAW:", raw_output)

        # 🔥 Clean output
        raw_output = raw_output.replace("```json", "").replace("```", "").strip()

        # Extract JSON safely
        match = re.search(r'\{.*\}', raw_output, re.DOTALL)

        if not match:
            return {}

        json_str = match.group(0)

        return json.loads(json_str)

    except Exception as e:
        print("LLM ERROR:", e)
        return {}
