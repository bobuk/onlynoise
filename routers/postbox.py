import time
from copy import copy

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from mongodb import DB
from .meta import IncomingMessage, Message, Meta, put_message_to_postbox, efl, db_get_account_by_postbox

router = APIRouter(prefix="/postboxes")


class GetPostboxMetaResponse(Meta):
    pass


class SetPostboxMetaRequest(Meta):
    pass


class DelPostboxResponse(BaseModel):
    status: str = Field("ok", title="Status")


class SetPostboxMetaResponse(BaseModel):
    status: str | None = Field("ok", title="Status")


class CreateMessageResponse(BaseModel):
    status: str = Field(..., title="Status")


class GetMessagesResponse(BaseModel):
    messages: list[Message] = Field(..., title="Messages list")


def remove_old_messages(db, account_id: str):
    db.messages.update_many(
        {
            "account_id": account_id,
            "created_at": {"$lt": int(time.time()) - 24 * 60 * 60 * 7},
        },
        {"$set": {"is_deleted": True}}
    )


@router.delete("/{postbox_id}", response_model=DelPostboxResponse, summary="Delete postbox (and unsubscribe from the subscription)")
def delete_postbox(postbox_id: str, response: Response):
    with DB as db:
        response.status_code = 200
        account = db_get_account_by_postbox(db, postbox_id, f"Postbox {postbox_id} not found")
        db.accounts.update_one(
            {"_id": account["_id"]},
            {"$pull": {"postboxes": {"postbox_id": postbox_id}}}
        )
        unique_id = efl(account["postboxes"], "postbox_id", postbox_id).get("subscription")
        if unique_id:
            db.accounts.update_one(
                {"subscriptions.unique_id": unique_id},
                {"$pull": {"subscriptions.$.subscribers": postbox_id}}
            )
        return DelPostboxResponse(status="ok")


@router.post("/{postbox_id}/meta", response_model=SetPostboxMetaResponse, summary="Set postbox properties")
def set_postbox_meta(postbox_id: str, request: SetPostboxMetaRequest, response: Response):
    with DB as db:
        account = db_get_account_by_postbox(db, postbox_id, f"Postbox {postbox_id} not found")
        req = dict(request)
        req["postbox_id"] = postbox_id
        db.accounts.update_one(
            {"_id": account["_id"], "postboxes.postbox_id": postbox_id},
            {"$set": {"postboxes.$": {"meta": req}}}
        )
        response.status_code = 200
        return SetPostboxMetaResponse(status="ok")


@router.get("/{postbox_id}/meta", response_model=GetPostboxMetaResponse, summary="Get postbox properties")
def get_postbox_meta(postbox_id: str, response: Response):
    with DB as db:
        account = db_get_account_by_postbox(db, postbox_id, f"Postbox {postbox_id} not found")
        response.status_code = 200
        postbox = efl(account["postboxes"], "postbox_id", postbox_id)
        return GetPostboxMetaResponse(sender=postbox.get("sender"), icon=postbox.get("icon"), color=postbox.get("color"))


@router.post("/{postbox_id}/messages", response_model=IncomingMessage, include_in_schema=False)
def create_message(postbox_id: str, request: IncomingMessage, response: Response):
    with DB as db:
        if not put_message_to_postbox(db, postbox_id, request.dict()):
            raise HTTPException(status_code=400, detail="message not saved")
        response.status_code = 201
        return CreateMessageResponse(status="ok")


@router.get("/{postbox_id}/messages", response_model=GetMessagesResponse, summary="Get list of messages for an postbox")
def get_messages(postbox_id: str, response: Response):
    with DB as db:
        messages = []
        for message in db.messages.find({"postbox_id": postbox_id, 'is_deleted': False}):
            message["id"] = copy(str(message["_id"]))
            del message["_id"], message["is_deleted"], message["is_sent"], message["account_id"]
            messages.append(message)
        response.status_code = 200
        return GetMessagesResponse(messages=messages)
