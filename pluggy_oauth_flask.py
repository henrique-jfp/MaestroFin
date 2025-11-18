"""Flask demo app showcasing the full OAuth flow with Pluggy.

Requirements:
    pip install pluggy-sdk-python flask python-dotenv

Set the following env vars (or .env file):
    PLUGGY_CLIENT_ID=...
    PLUGGY_CLIENT_SECRET=...
    PLUGGY_REDIRECT_URI=https://meusite.com/pluggy/callback
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from pluggy import Pluggy

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("pluggy-oauth-flask")

client = Pluggy(
    client_id=os.environ["PLUGGY_CLIENT_ID"],
    client_secret=os.environ["PLUGGY_CLIENT_SECRET"],
)

REDIRECT_URI = os.environ["PLUGGY_REDIRECT_URI"]
app = Flask(__name__)


def wait_for_final_status(item_id: str, timeout: int = 300, interval: int = 5) -> Dict[str, Any]:
    end_time = time.time() + timeout
    last_status = None

    while time.time() < end_time:
        item = client.items.get(item_id)
        status = item.get("status")

        if status != last_status:
            logger.info(
                "Item %s status=%s detail=%s",
                item_id,
                status,
                item.get("statusDetail"),
            )
            last_status = status

        if status in {"HEALTHY", "PARTIAL_SUCCESS"}:
            return item

        if status in {"LOGIN_ERROR", "INVALID_CREDENTIALS", "ERROR", "SUSPENDED"}:
            raise RuntimeError(f"Item failed with status={status}: {item.get('statusDetail')}")

        time.sleep(interval)

    raise TimeoutError("Item did not finish syncing in time")


@app.get("/health")
def health() -> Any:
    return {"status": "ok"}


@app.post("/pluggy/link-token")
def create_link_token() -> Any:
    payload = request.get_json(force=True)
    user_id = payload.get("userId")
    if not user_id:
        return jsonify({"error": "userId is required"}), 400

    link_token = client.link.create({
        "clientUserId": str(user_id),
        "redirectUri": REDIRECT_URI,
        "products": ["ACCOUNTS", "TRANSACTIONS"],
    })

    logger.info("Created link token %s for user %s", link_token["id"], user_id)
    return jsonify(link_token)


@app.post("/pluggy/connect")
def start_connection() -> Any:
    data = request.get_json(force=True)
    link_token_id = data.get("linkTokenId")
    connector_id = data.get("connectorId")
    cpf = data.get("cpf")  # adapt to connector requirements

    if not all([link_token_id, connector_id, cpf]):
        return jsonify({"error": "linkTokenId, connectorId and cpf are required"}), 400

    item = client.items.create({
        "connectorId": int(connector_id),
        "linkTokenId": link_token_id,
        "parameters": {"cpf": cpf},
        "redirectUri": REDIRECT_URI,
    })

    oauth_url = (
        item.get("nextAuthStep", {}).get("oauthRedirect")
        or item.get("redirectUrl")
        or item.get("url")
    )

    logger.info("Item %s created (status=%s)", item["id"], item.get("status"))

    return jsonify({
        "itemId": item["id"],
        "status": item.get("status"),
        "oauthUrl": oauth_url,
    })


@app.get("/pluggy/callback")
def pluggy_callback() -> Any:
    code = request.args.get("code")
    state = request.args.get("state")

    if not code or not state:
        logger.warning("Missing code/state on callback: code=%s state=%s", code, state)
        return "Missing code/state", 400

    logger.info("Received OAuth redirect for state=%s", state)

    result = client.items.exchange_oauth_code(code=code, state=state)
    item_id = result.get("itemId") or state

    logger.info("OAuth code exchanged. Item %s now updating", item_id)

    # Optionally trigger polling here synchronously or via background task
    try:
        final_item = wait_for_final_status(item_id)
        logger.info("Item %s finished with status %s", item_id, final_item.get("status"))
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Polling failed for item %s", item_id)
        return f"OAuth received, but polling failed: {exc}", 500

    return "OAuth completed! You can close this tab.", 200


@app.get("/pluggy/items/<item_id>")
def get_item(item_id: str) -> Any:
    try:
        item = client.items.get(item_id)
        return jsonify(item)
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Failed to get item %s", item_id)
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
