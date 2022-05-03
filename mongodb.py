import pymongo
import os

import random
import string
import time
from fastapi import HTTPException

MONGO_HOST = os.environ.get("MONGO", "localhost")

def create_random_string(length: int = 32) -> str:
    return "".join(
        random.choice(string.ascii_letters + string.digits) for _ in range(length)
    )


class MongoDB:
    def __init__(self, url: str = f"mongodb://{MONGO_HOST}:27017"):
        self.url = url
        self.client: pymongo.MongoClient | None = None

    def __enter__(self):
        if self.client is None:
            self.connect()
        return self.client.ondb

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass  # self.client.close()

    def connect(self):
        self.client = pymongo.MongoClient(self.url)

    def accounts_get_by_filter(self, map_filter: dict, exception=None) -> dict:
        with self as db:
            account = db.accounts.find_one(map_filter)
            if not account:
                raise HTTPException(status_code=400, detail=exception if exception else f"Account not found")
            return account

    def accounts_create(self) -> dict:
        account_id = create_random_string()
        created_at = int(time.time())

        with self as db:
            db.accounts.insert_one(
                {
                    "account_id": account_id,
                    "created_at": created_at,
                    "devices": [],
                    "postboxes": [],
                    "subscriptions": []
                }
            )

            return db.accounts.find_one({"account_id": account_id})

    def accounts_get(self, account_id: str, exception: str | None = None) -> dict:
        return self.accounts_get_by_filter({"account_id": account_id}, exception)

    def accounts_get_by_subscription(self, subscription_id: str, exception: str | None = None) -> dict:
        return self.accounts_get_by_filter({"subscriptions.subscription_id": subscription_id}, exception)

    def accounts_get_by_postbox(self, postbox_id: str, exception: str | None = None) -> dict:
        return self.accounts_get_by_filter({"postboxes.postbox_id": postbox_id}, exception)

    def accounts_add_device(self, account_id: str, device_id: str):
        with self as db:
            db.accounts.update_one(
                {"account_id": account_id},
                {"$push": {
                    "devices": {
                        "device_id": device_id, "created_at": int(time.time())
                    }}
                },
            )

    def accounts_push_to(self, account_id: str | dict, selector: str, newdata: dict | str):
        with self as db:
            db.accounts.update_one(
                {"account_id": account_id} if type(account_id) == str else account_id,
                {"$push": {selector: newdata}}
            )

DB = MongoDB()
