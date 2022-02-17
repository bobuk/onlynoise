import asyncio, os
import websockets
import motor.motor_asyncio
import pymongo
import json
from copy import copy

client = None

MONGO_HOST = os.environ.get("MONGO", "localhost")


def DB():
    global client
    client = motor.motor_asyncio.AsyncIOMotorClient(f"mongodb://{MONGO_HOST}:27017")
    return client.ondb


async def postboxes_list(db, account_id: str) -> list[str]:
    account = await db.accounts.find_one({"account_id": account_id})
    if not account:
        return []
    return [postbox["postbox_id"] for postbox in account["postboxes"]]


# ws://URL:8765/v1/accounts/ACCOUNT_ID/messages


async def combiner(ws: websockets.WebSocketServerProtocol, path):
    db = DB()
    if not path.startswith("/v1/accounts/") or not path.endswith("/messages"):
        return
    account_id = path.split("/")[3]
    last_created_at = 0
    first_run = True
    while True:
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
                del message["_id"]
                if not first_run:
                    await ws.send(json.dumps(message, ensure_ascii=False))
            first_run = False
        await asyncio.sleep(1)


async def main():
    async with websockets.serve(combiner, os.environ.get("HOST", "0.0.0.0"), 8765):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
