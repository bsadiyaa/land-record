import os
import json
import urllib.request
import urllib.error

import database as db
import blockchain as bc

MODEL = "gemini-flash-latest"


def load_key():
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    try:
        with open(".env") as f:
            for line in f:
                line = line.strip()
                if line.startswith("GEMINI_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return None


def build_context():
    lines = ["LAND RECORDS (survey_no, owner, village, area_sqft, latitude, longitude):"]
    for land in db.get_lands():
        lines.append(str(land))
    lines.append("")
    lines.append("BLOCKCHAIN TRANSACTIONS:")
    for b in bc.load_chain()[1:]:
        lines.append(json.dumps(b["data"]) + " at " + b["timestamp"])
    lines.append("Chain valid: " + str(bc.is_chain_valid()))
    return "\n".join(lines)


def ask(question):
    key = load_key()
    if not key:
        return "GEMINI_API_KEY not found. Check your .env file."
    instruction = ("You are the assistant of a Blockchain and GIS based land "
                   "management system. Answer only using the data below. If the "
                   "answer is not in the data, say so. Keep answers short and "
                   "simple.\n\n" + build_context())
    body = {
        "system_instruction": {"parts": [{"text": instruction}]},
        "contents": [{"role": "user", "parts": [{"text": question}]}],
    }
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           + MODEL + ":generateContent")
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"x-goog-api-key": key, "content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode())
            return data["candidates"][0]["content"]["parts"][0]["text"]
    except urllib.error.HTTPError as e:
        return "API error " + str(e.code) + ": " + e.read().decode()[:300]
    except Exception as e:
        return "Error: " + str(e)