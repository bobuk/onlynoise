import time

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from mongodb import DB
from .meta import IncomingMessage, Meta, create_random_string, efl, put_message_to_subscription

router = APIRouter(prefix="/subscriptions")


class CreateSubscriptionRequest(BaseModel):
    account_id: str = Field(..., title="Account ID")
    unique_id: str | None = Field(None, title="Unique ID. If not provided, a random one will be generated")
    meta: Meta | None = Field(default_factory=Meta, title="Meta data")


class SendMessageToSubscription(BaseModel):
    status: str = Field(default="ok", title="Status")


class CreateSubscriptionResponse(BaseModel):
    status: str = Field(default="ok", title="Status")
    subscription_id: str = Field(title="Subscription ID")
    unique_id: str = Field(title="Unique ID")
    created_at: int = Field(..., title="Unix timestamp")
    meta: Meta | None = Field(default_factory=Meta, title="Meta data")


@router.post("/", response_model=CreateSubscriptionResponse, summary="Create a new subscription with unique ID")
def create_subscription(request: CreateSubscriptionRequest, response: Response):
    if request.unique_id is None:
        request.unique_id = create_random_string()
    subscription_id = create_random_string()
    with DB as db:
        if db.accounts.find_one({"subscriptions.unique_id": request.unique_id}):
            raise HTTPException(status_code=400, detail="Subscription with this unique ID already exists")
        acc = db.accounts.find_one({"account_id": request.account_id})
        if not acc:
            raise HTTPException(status_code=400, detail="Account with this ID does not exist")

    response.status_code = 201
    created_at = int(time.time())
    sub = {
        "subscription_id": subscription_id,
        "unique_id": request.unique_id,
        "created_at": created_at,
        "updated_at": created_at,
        "meta": request.meta.dict(),
        "subscribers": [],
    }
    with DB as db:
        db.accounts.update_one({"account_id": request.account_id}, {"$push": {"subscriptions": sub}})
    return CreateSubscriptionResponse(
        status="created", subscription_id=subscription_id, unique_id=request.unique_id, created_at=created_at, meta=request.meta
    )


@router.put("/{subscription_id}/meta", response_model=CreateSubscriptionResponse, summary="Update subscription meta data")
def update_subscription_meta(subscription_id: str, request: CreateSubscriptionRequest, response: Response):
    with DB as db:
        account = db.accounts.find_one({"subscriptions.subscription_id": subscription_id})
        if not account:
            raise HTTPException(status_code=400, detail="Subscription with this ID does not exist")
        subscription = efl(account["subscriptions"], "subscription_id", subscription_id)
        db.account.update_one(
            {"_id": account["_id"], "subscriptions.subscription_id": subscription_id},
            {"$set": {
                "subscriptions.$.meta": request.meta.dict(),
                "subscriptions.$.updated_at": int(time.time())}})
    response.status_code = 201
    return CreateSubscriptionResponse(
        status="updated", subscription_id=subscription_id, unique_id=subscription["unique_id"], created_at=subscription["created_at"], meta=request.meta
    )


@router.post("/{subscription_id}/messages", response_model=SendMessageToSubscription, summary="Send message to subscription")
def send_subscription_message(subscription_id: str, request: IncomingMessage, response: Response):
    with DB as db:
        account = db.accounts.find_one({"subscriptions.subscription_id": subscription_id})
        if not account:
            raise HTTPException(status_code=400, detail="Subscription with this ID does not exist")
        put_message_to_subscription(db, subscription_id, request.dict())

        db.accounts.update_one(
            {"_id": account["_id"], "subscriptions.subscription_id": subscription_id},
            {"$set": {"subscriptions.$.updated_at": int(time.time())}})
    response.status_code = 202
    return SendMessageToSubscription(status="ok")

