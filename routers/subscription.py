import time

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from mongodb import DB
from .meta import Meta, create_random_string, efl

router = APIRouter(prefix="/subscriptions")


class CreateSubscriptionRequest(BaseModel):
    account_id: str = Field(..., title="Account ID")
    unique_id: str | None = Field(None, title="Unique ID. If not provided, a random one will be generated")
    meta: Meta | None = Field(default_factory=Meta, title="Meta data")


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
    DB.accounts_get(request.account_id, "Account with this ID does not exist")

    response.status_code = 201
    created_at = int(time.time())
    sub = {
        "subscription_id": subscription_id,
        "unique_id": request.unique_id,
        "created_at": created_at,
        "updated_at": created_at,
        "meta": request.meta.dict() if request.meta else {},
        "subscribers": [],
    }
    with DB as db:
        db.accounts.update_one({"account_id": request.account_id}, {"$push": {"subscriptions": sub}})
    return CreateSubscriptionResponse(
        status="created", subscription_id=subscription_id, unique_id=request.unique_id, created_at=created_at, meta=request.meta
    )


@router.post("/{subscription_id}/meta", response_model=CreateSubscriptionResponse, summary="Update subscription meta data")
def update_subscription_meta(subscription_id: str, request: CreateSubscriptionRequest, response: Response):
    account = DB.accounts_get_by_subscription(subscription_id, "Subscription with this ID does not exist")
    subscription = efl(account["subscriptions"], "subscription_id", subscription_id)
    with DB as db:
        db.account.update_one(
            {"_id": account["_id"], "subscriptions.subscription_id": subscription_id},
            {"$set": {
                "subscriptions.$.meta": request.meta.dict() if request.meta else {},
                "subscriptions.$.updated_at": int(time.time())}})
    response.status_code = 201
    return CreateSubscriptionResponse(
        status="updated", subscription_id=subscription_id, unique_id=subscription["unique_id"], created_at=subscription["created_at"], meta=request.meta
    )
