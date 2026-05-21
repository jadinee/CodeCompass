import os
import asyncio
from flask import Flask, request, jsonify
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

PHOTON_API_KEY = os.getenv("PHOTON_API_KEY", "")

def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

def send_imessage_reply(line_id: str, recipient: str, message: str):
    """Send a reply back via Photon Spectrum."""
    url = "https://api.photon.codes/v1/messages"
    headers = {
        "Authorization": f"Bearer {PHOTON_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "line_id": line_id,
        "to": recipient,
        "body": message
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    return resp.status_code

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print(f"[Photon] Received: {data}")

    try:
        # Extract message details from Photon Spectrum payload
        message_body = data.get("body", "") or data.get("text", "") or data.get("message", "")
        sender = data.get("from", "") or data.get("sender", "")
        line_id = data.get("line_id", "") or data.get("line", "")

        if not message_body:
            return jsonify({"status": "no message"}), 200

        # Import here to avoid circular imports
        from pipeline_client import call_pipeline, call_followup

        # Check if it looks like an analyze request
        if "github.com" in message_body or message_body.lower().startswith("analyze"):
            from github_fetcher import get_project_context
            project_context, source_label = get_project_context(message_body)
            reply = run_async(call_pipeline(project_context))
        else:
            reply = run_async(call_pipeline(message_body))

        # Send reply back via iMessage
        if sender and line_id:
            send_imessage_reply(line_id, sender, reply)

        return jsonify({"status": "ok", "reply": reply}), 200

    except Exception as e:
        print(f"[Error] {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "CodeCompass iMessage server running"}), 200

if __name__ == "__main__":
    app.run(port=8080, debug=False)
