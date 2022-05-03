import time
from typing import List
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from mongodb import DB
from . import postbox
from .meta import IncomingMessage, Meta, create_random_string, put_message_to_subscription, efl

router = APIRouter(prefix="/accounts")


class CreateAccountResponse(BaseModel):
    account_id: str = Field(..., title="Account ID, prob 32 characters long")
    created_at: int = Field(
        default_factory=lambda: int(time.time()), title="Unix timestamp"
    )


class GetAccountResponse(BaseModel):
    account_id: str = Field(..., title="Account ID, prob 32 characters long")
    created_at: int = Field(
        default_factory=lambda: int(time.time()), title="Unix timestamp"
    )
    devices: list = Field(default_factory=list, title="List of devices associated with the account")
    postboxes: list = Field(default_factory=list, title="List of postboxes")
    subscriptions: list = Field(default_factory=list, title="List of subscriptions")


class CreateDeviceRequest(BaseModel):
    device_id: str = Field(..., title="Device ID")
    device_type: str = Field(..., title="Device type (like ios or android or web)")


class CreatePostboxResponse(BaseModel):
    subscription: str | None = Field("", title="Subscription Unique ID")
    postbox_id: str | None = Field("", title="Postbox ID")
    created_at: int = Field(
        default_factory=lambda: int(time.time()), title="Unix timestamp"
    )


class PostboxInfo(BaseModel):
    postbox_id: str = Field(..., title="Postbox ID")
    created_at: int = Field(..., title="Unix timestamp")
    meta: Meta | None = Field(None, title="Meta data")


class GetPostboxesResponse(BaseModel):
    postboxes: List[PostboxInfo] = Field(..., title="List of postboxes")


class CreateSubscriptionRequest(BaseModel):
    unique_id: str = Field(..., title="Unique subscription ID")
    meta: Meta | None = Field(None, title="Meta data")


@router.post("/", response_model=CreateAccountResponse, summary="Create an account")
def create_account(response: Response):
    res = DB.accounts_create()
    response.status_code = 201
    return CreateAccountResponse(**res)


@router.get("/{account_id:str}", response_model=GetAccountResponse, summary="Get an account info by ID")
def get_account(account_id: str):
    account = DB.accounts_get(account_id)
    return GetAccountResponse(**account)


@router.post("/{account_id:str}/devices", summary="Add a device to an account")
def create_device(account_id: str, request: CreateDeviceRequest, response: Response):
    account = DB.accounts_get(account_id)
    full_device_id = f"{request.device_type}:{request.device_id}"
    dev = efl(account["devices"], "device_id", full_device_id)
    if not dev:
        DB.accounts_add_device(account_id, full_device_id)
    response.status_code = 201
    return


@router.get("/{account_id:str}/postboxes", response_model=GetPostboxesResponse, summary="Get list of postboxes of an account")
def get_postboxes(account_id: str):
    account = DB.accounts_get(account_id)
    return GetPostboxesResponse(postboxes=account["postboxes"])


@router.post("/{account_id:str}/subscriptions", summary="Subscribe account to a subscription")
def create_subscription(account_id: str, request: CreateSubscriptionRequest, response: Response):
    account = DB.accounts_get(account_id)

    subscription_account = DB.accounts_get_by_filter({"subscriptions.unique_id": request.unique_id})
    if not subscription_account:
        raise HTTPException(status_code=406, detail="Subscription not found")
    if efl(account["postboxes"], "subscription", request.unique_id):
        raise HTTPException(status_code=409, detail="Already subscribed")
    postbox_id = create_random_string()
    DB.accounts_push_to(account_id, "postboxes", {
        "postbox_id": postbox_id,
        "subscription": request.unique_id,
        "created_at": int(time.time()),
        "meta": request.meta.dict() if request.meta else {}})
    DB.accounts_push_to(
        {"_id": subscription_account["_id"], "subscriptions.unique_id": request.unique_id},
        "subscriptions.$.subscribers", postbox_id)
    response.status_code = 201
    return


@router.post("/{account_id:str}/subscriptions/{unique_id:str}", summary="Send message to subscription owned by account")
def send_subscription_message(account_id: str, unique_id: str, request: IncomingMessage, response: Response):
    account = DB.accounts_get(account_id, exception="Subscription with this ID does not exist")
    subscriptions = account["subscriptions"]
    subscription = efl(subscriptions, "unique_id", unique_id)
    if not subscription:
        raise HTTPException(status_code=400, detail=f"Subscription `{unique_id}` not belong to this account")
    with DB as db:
        put_message_to_subscription(db, subscription["subscription_id"], request.dict())
        db.accounts.update_one(
            {"_id": account["_id"], "subscriptions.subscription_id": subscription["subscription_id"]},
            {"$set": {"subscriptions.$.updated_at": int(time.time())}})
    response.status_code = 202
    return


@router.get("/{account_id:str}/messages", response_model=postbox.GetMessagesResponse, summary="Get all messages from an account")
def get_all_messages(account_id: str, response: Response):
    messages = []
    with DB as db:
        for message in db.messages.find({"account_id": account_id}):
            message["id"] = str(message["_id"])
            messages.append(message)

    response.status_code = 200
    return postbox.GetMessagesResponse(messages=messages)
