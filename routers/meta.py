import random
import string
import time

from pydantic import BaseModel, Field


def create_random_string(length: int = 32) -> str:
    return "".join(
        random.choice(string.ascii_letters + string.digits) for _ in range(length)
    )


def efl(d: list[dict], key: str, value: [str, int]) -> dict:
    for e in d:
        if e[key] == value:
            return e
    return {}


class Meta(BaseModel):
    sender: str | None = Field("", title="Sender's name")
    icon: str | None = Field("", title="Icon from font awesome (e.g. fa-envelope)")
    color: str | None = Field("", title="Color in hex or system name")


class Message(BaseModel):
    id: str = Field(..., title="Unique Message ID")
    subject: str | None = Field("", title="Subject")
    body: str | None = Field("", title="Body")
    url: str | None = Field("", title="URL")
    image_url: str | None = Field("", title="Image URL")
    important: bool = Field(False, title="Important")

    meta: Meta | None = Field({}, title="Meta")

    postbox_id: str = Field(..., title="Postbox ID")
    created_at: int = Field(..., title="Created At")


class IncomingMessage(BaseModel):
    subject: str | None = Field("", title="Subject")
    body: str | None = Field("", title="Body")
    url: str | None = Field("", title="URL")
    image_url: str | None = Field("", title="Image URL")
    important: bool | None = Field(False, title="Important")
    meta: Meta | None = Field({}, title="Meta")


def put_message_to_subscription(db, subscription_id, message):
    account = db.accounts.find_one({"subscriptions.subscription_id": subscription_id})
    subscription = efl(account["subscriptions"], "subscription_id", subscription_id)
    if not subscription:
        return None
    meta = subscription.get("meta", {})
    for k, v in dict(message["meta"]).items():
        if v:
            meta[k] = v
    for postbox in subscription.get("subscribers", []):
        print(postbox, message)
        put_message_to_postbox(db, postbox, message)


def put_message_to_postbox(db, postbox_id, message) -> bool:
    account = db.accounts.find_one({"postboxes.postbox_id": postbox_id})
    if not account:
        return False
    meta = efl(account["postboxes"], "postbox_id", postbox_id).get("meta", {})
    for k, v in message.get("meta", {}).items():
        if v:
            meta[k] = v
    db.messages.insert_one(
        {
            "subject": message["subject"],
            "body": message["body"],
            "url": message["url"],
            "image_url": message["image_url"],
            "important": message["important"],
            "account_id": account["account_id"],
            "postbox_id": postbox_id,
            "created_at": int(time.time()),
            "is_deleted": False,
            "is_sent": False,
            "meta": meta,
        }
    )
    return True
