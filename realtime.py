import asyncio
import websockets
import motor.motor_asyncio
import pymongo
import json

client = None


def DB():
    global client
    client = motor.motor_asyncio.AsyncIOMotorClient('mongodb://localhost:27017')
    return client.ondb


async def postboxes_list(db, account_id: str) -> list[str]:
    account = await db.accounts.find_one({'account_id': account_id})
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
    while True:
        postboxes = await postboxes_list(db, account_id)
        cursor = db.messages.find({'postbox_id': {'$in': postboxes}, 'created_at': {'$gt': last_created_at}},
                                  cursor_type=pymongo.CursorType.TAILABLE_AWAIT, oplog_replay=True)
        while cursor.alive:
            async for message in cursor:
                print(message)
                last_created_at = message["created_at"]
                del message["_id"]
                await ws.send(json.dumps(message, ensure_ascii=False))

        await asyncio.sleep(1)


async def main():
    async with websockets.serve(combiner, "localhost", 8765):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
