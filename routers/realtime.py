import asyncio, os
import motor.motor_asyncio
import pymongo
import json

from sse_starlette.sse import EventSourceResponse
from fastapi import APIRouter, HTTPException, Response,Request

from copy import copy


MONGO_HOST = os.environ.get("MONGO", "localhost")

router = APIRouter(prefix="/realtime")


async def postboxes_list(db, account_id: str) -> list[str]:
    account = await db.accounts.find_one({"account_id": account_id})
    if not account:
        return []
    return [postbox["postbox_id"] for postbox in account["postboxes"]]

client = motor.motor_asyncio.AsyncIOMotorClient(f"mongodb://{MONGO_HOST}:27017")

@router.get("/accounts/{account_id:str}/messages")
async def eventsource_get_account_messages(account_id: str, request: Request):
    db = client.ondb


    async def event_generator():
        first_run = True
        last_created_at = 0
        while True:
            # If client closes connection, stop sending events
            if await request.is_disconnected():
                break

            postboxes = await postboxes_list(db, account_id)
            cursor = db.messages.find(
                {"postbox_id": {"$in": postboxes}, "is_deleted": False, "created_at": {"$gt": last_created_at}},
                cursor_type=pymongo.CursorType.TAILABLE_AWAIT,
                oplog_replay=True,
            )
            while cursor.alive:
                async for message in cursor:
                    last_created_at = message["created_at"]
                    message["id"] = copy(str(message["_id"]))
                    del message["_id"], message["is_deleted"], message["is_sent"]
                    if not first_run:
                        yield {"data": json.dumps(message, ensure_ascii=False }
                first_run = False
            await asyncio.sleep(1)

    return EventSourceResponse(event_generator())
