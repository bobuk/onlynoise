import asyncio
import json
import os
from copy import copy

import motor.motor_asyncio
import pymongo
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

MONGO_HOST = os.environ.get("MONGO", "localhost")

router = APIRouter(prefix="/realtime")

client = motor.motor_asyncio.AsyncIOMotorClient(f"mongodb://{MONGO_HOST}:27017")


@router.get("/accounts/{account_id:str}/messages", summary="Get realtime updates with all the messages from an account")
async def eventsource_get_account_messages(account_id: str, request: Request):
    db = client.ondb

    async def event_generator():
        first_run = True
        last_created_at = 0
        while True:
            # If client closes connection, stop sending events
            if await request.is_disconnected():
                break

            cursor = db.messages.find(
                {"account_id": account_id, "is_deleted": False, "created_at": {"$gt": last_created_at}},
                cursor_type=pymongo.CursorType.TAILABLE_AWAIT,
                oplog_replay=True,
            )
            while cursor.alive:
                async for message in cursor:
                    last_created_at = message["created_at"]
                    message["id"] = copy(str(message["_id"]))
                    del message["_id"], message["is_deleted"], message["is_sent"], message["account_id"]
                    if not first_run:
                        yield {"data": json.dumps(message, ensure_ascii=False)}
                first_run = False
            await asyncio.sleep(1)

    return EventSourceResponse(event_generator())
