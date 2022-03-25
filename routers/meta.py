from pydantic import BaseModel, Field
import random
import time
import string


def create_random_string(length: int = 32) -> str:
    return "".join(
        random.choice(string.ascii_letters + string.digits) for _ in range(length)
    )


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

def put_message_to_subscription(db, subscription_id, message):
    subscription = db.subscriptions.find_one({"subscription_id": subscription_id})
    print(subscription, f'db.subscriptions.find_one(["subscription_id": {subscription_id}])')
    if not subscription:
        return None
    subscription_meta = subscription.get("meta", {})
    if subscription_meta:
        for k, v in dict(subscription_meta).items():
            if v:
                message.meta[k] = v

    for postbox in subscription.get("subscribers", []):
        print(postbox, message)
        put_messsage_to_postbox(db, postbox, message)

def put_messsage_to_postbox(db, postbox_id, message):
    meta = {}
    postbox_meta = db.postboxes.find_one({"postbox_id": postbox_id})
    if postbox_meta:
        del postbox_meta["_id"], postbox_meta["postbox_id"]
        meta = dict(postbox_meta)
    if message.meta:
        for k, v in dict(message.meta).items():
            if v:
                meta[k] = v
    db.messages.insert_one(
        {
            "subject": message.subject,
            "body": message.body,
            "url": message.url,
            "image_url": message.image_url,
            "important": message.important,
            "postbox_id": postbox_id,
            "created_at": int(time.time()),
            "is_deleted": False,
            "is_sent": False,
            "meta": meta,
        }
    )
