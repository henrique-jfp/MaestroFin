"""FastAPI variant of the Pluggy OAuth demo.

Requirements:
    pip install pluggy-sdk-python fastapi uvicorn[standard] python-dotenv
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel
from pluggy import Pluggy

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("pluggy-oauth-fastapi")

client = Pluggy(
    client_id=os.environ["PLUGGY_CLIENT_ID"],
    client_secret=os.environ["PLUGGY_CLIENT_SECRET"],
)
REDIRECT_URI = os.environ["PLUGGY_REDIRECT_URI"]

app = FastAPI(title="Pluggy OAuth Demo")


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


class LinkTokenRequest(BaseModel):
    userId: str


class ConnectRequest(BaseModel):
    linkTokenId: str
    connectorId: int
    cpf: str


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/pluggy/link-token")
def create_link_token(body: LinkTokenRequest) -> Any:
    link_token = client.link.create({
        "clientUserId": body.userId,
        "redirectUri": REDIRECT_URI,
        "products": ["ACCOUNTS", "TRANSACTIONS"],
    })

    logger.info("Created link token %s for user %s", link_token["id"], body.userId)
    return link_token


@app.post("/pluggy/connect")
def start_connection(body: ConnectRequest) -> Any:
    item = client.items.create({
        "connectorId": body.connectorId,
        "linkTokenId": body.linkTokenId,
        "parameters": {"cpf": body.cpf},
        "redirectUri": REDIRECT_URI,
    })

    oauth_url = (
        item.get("nextAuthStep", {}).get("oauthRedirect")
        or item.get("redirectUrl")
        or item.get("url")
    )

    logger.info("Item %s created (status=%s)", item["id"], item.get("status"))

    return {
        "itemId": item["id"],
        "status": item.get("status"),
        "oauthUrl": oauth_url,
    }


@app.get("/pluggy/callback")
def pluggy_callback(code: str | None = None, state: str | None = None) -> PlainTextResponse:
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code/state")

    logger.info("Received OAuth redirect for state=%s", state)

    result = client.items.exchange_oauth_code(code=code, state=state)
    item_id = result.get("itemId") or state

    logger.info("OAuth code exchanged. Item %s updating", item_id)

    try:
        final_item = wait_for_final_status(item_id)
        logger.info("Item %s finished with status %s", item_id, final_item.get("status"))
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Polling failed for item %s", item_id)
        raise HTTPException(status_code=500, detail=f"OAuth received, polling failed: {exc}")

    return PlainTextResponse("OAuth completed! You can close this tab.")


@app.get("/pluggy/items/{item_id}")
def get_item(item_id: str) -> Any:
    try:
        item = client.items.get(item_id)
        return item
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Failed to get item %s", item_id)
        return JSONResponse(status_code=500, content={"error": str(exc)})
