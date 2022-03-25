import time
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field
from mongodb import DB
from .meta import Meta, create_random_string, Message, put_message_to_subscription

import pymongo

router = APIRouter(prefix="/subscriptions")


class MessageToSubscription(BaseModel):
    subject: str | None = Field("", title="Subject")
    body: str | None = Field("", title="Body")
    url: str | None = Field("", title="URL")
    image_url: str | None = Field("", title="Image URL")
    important: bool | None = Field(False, title="Important")

    meta: Meta | None = Field({}, title="Meta")

class CreateSubscriptionRequest(BaseModel):
    account_id: str = Field(..., title="Account ID")
    unique_id: str | None = Field(None, title="Unique ID. If not provided, a random one will be generated")
    meta: Meta | None = Field(default_factory=Meta, title="Meta data")


class SendMessageToSubsription(BaseModel):
    status: str = Field(default="ok", title="Status")


class CreateSubscriptionResponse(BaseModel):
    status: str = Field(default="ok", title="Status")
    subscription_id: str = Field(title="Subscription ID")
    unique_id: str = Field(title="Unique ID")
    created_at: int = Field(..., title="Unix timestamp")
    meta: Meta | None = Field(default_factory=Meta, title="Meta data")


class SubscribePostboxToSubscriptionRequest(BaseModel):
    postbox_id: str = Field(..., title="Postbox ID")


class SubscribePostboxToSubscriptionResponse(BaseModel):
    status: str = Field(default="ok", title="Status")


@router.post("/", response_model=CreateSubscriptionResponse)
def create_subscription(request: CreateSubscriptionRequest, response: Response):
    if request.unique_id is None:
        request.unique_id = create_random_string()
    subscription_id = create_random_string()
    with DB as db:
        if db.subscriptions.find_one({"unique_id": request.unique_id}) or db.subscriptions.find_one({"subscription_id": subscription_id}):
            raise HTTPException(status_code=400, detail="Subscription with this unique ID already exists")
        acc = db.accounts.find_one({"account_id": request.account_id})
        if not acc:
            raise HTTPException(status_code=400, detail="Account with this ID does not exist")

    response.status_code = 201
    created_at = int(time.time())
    with DB as db:
        db.subscriptions.insert_one({
            "account_id": request.account_id,
            "subscription_id": subscription_id,
            "unique_id": request.unique_id,
            "created_at": created_at,
            "updated_at": created_at,
            "meta": request.meta.dict(),
            "subscribers": [],
        })
    return CreateSubscriptionResponse(
        status="created", subscription_id=subscription_id, unique_id=request.unique_id, created_at=created_at, meta=request.meta
    )


@router.put("/{subscription_id}/meta", response_model=CreateSubscriptionResponse)
def update_subscription_meta(subscription_id: str, request: CreateSubscriptionRequest, response: Response):
    with DB as db:
        subscription = db.subscriptions.find_one({"subscription_id": subscription_id})
        if not subscription:
            raise HTTPException(status_code=400, detail="Subscription with this ID does not exist")
        db.subscriptions.update_one(
            {"subscription_id": subscription_id},
            {"$set": {
                "meta": request.meta,
                "updated_at": int(time.time()),
            }}
        )
    return CreateSubscriptionResponse(
        status="updated", subscription_id=subscription_id, unique_id=subscription["unique_id"], created_at=subscription["created_at"], meta=request.meta
    )


@router.post("/{subscription_id}/messages", response_model=SendMessageToSubsription)
def send_subscription_message(subscription_id: str, request: MessageToSubscription, response: Response):
    with DB as db:
        subscription = db.subscriptions.find_one({"subscription_id": subscription_id})
        if not subscription:
            raise HTTPException(status_code=400, detail="Subscription with this ID does not exist")
        put_message_to_subscription(db, subscription_id, request)
        db.subsriptions.update_one({"_id": subscription["_id"]}, {"$set": {"updated_at": int(time.time())}})
    return SendMessageToSubsription(status="ok")


@router.post("/{unique_id}", response_model=SubscribePostboxToSubscriptionResponse)
def subscribe_postbox_to_subscription(unique_id: str, request: SubscribePostboxToSubscriptionRequest, response: Response):
    with DB as db:
        subscription = db.subscriptions.find_one({"unique_id": unique_id})
        if not subscription:
            raise HTTPException(status_code=400, detail="Subscription with this name does not exist")
        postbox = db.postboxes.find_one({"postbox_id": request.postbox_id})
        if not postbox:
            raise HTTPException(status_code=400, detail="Postbox with this ID does not exist")
        if postbox["postbox_id"] in subscription["subscribers"]:
            raise HTTPException(status_code=400, detail="Postbox is already subscribed to this subscription")
        db.subscriptions.update_one({"_id": subscription["_id"]}, {"$push": {"subscribers": postbox["postbox_id"]}})
    return SubscribePostboxToSubscriptionResponse(status="ok")
