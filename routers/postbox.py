import time
from copy import copy

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field
from mongodb import DB
from .meta import IncomingMessage, Message, Meta, put_message_to_postbox, efl

router = APIRouter(prefix="/postboxes")


class GetPostboxMetaResponse(Meta):
    pass


class SetPostboxMetaRequest(Meta):
    pass


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


@router.delete("/{postbox_id}", summary="Delete postbox (and unsubscribe from the subscription)")
def delete_postbox(postbox_id: str, response: Response):
    account = DB.accounts_get_by_postbox(postbox_id, f"Postbox {postbox_id} not found")
    response.status_code = 200
    with DB as db:
        db.accounts.update_one(
            {"_id": account["_id"]},
            {"$pull": {"postboxes": {"postbox_id": postbox_id}}}
        )
    unique_id = efl(account["postboxes"], "postbox_id", postbox_id).get("subscription")
    if unique_id:
        with DB as db:
            db.accounts.update_one(
                {"subscriptions.unique_id": unique_id},
                {"$pull": {"subscriptions.$.subscribers": postbox_id}}
            )
    return

@router.post("/{postbox_id}/meta", summary="Set postbox properties")
def set_postbox_meta(postbox_id: str, request: SetPostboxMetaRequest, response: Response):
    account = DB.accounts_get_by_postbox(postbox_id, f"Postbox {postbox_id} not found")
    with DB as db:
        postbox = efl(account["postboxes"], "postbox_id", postbox_id)
        postbox["meta"] = request.dict()
        db.accounts.update_one(
            {"_id": account["_id"], "postboxes.postbox_id": postbox_id},
            {"$set": {"postboxes.$": postbox}}
        )
        response.status_code = 200
        return


@router.get("/{postbox_id}/meta", response_model=GetPostboxMetaResponse, summary="Get postbox properties")
def get_postbox_meta(postbox_id: str, response: Response):
    account = DB.accounts_get_by_postbox(postbox_id, f"Postbox {postbox_id} not found")
    response.status_code = 200
    postbox = efl(account["postboxes"], "postbox_id", postbox_id)
    return GetPostboxMetaResponse(sender=postbox.get("sender"), icon=postbox.get("icon"), color=postbox.get("color"))


@router.get("/{postbox_id}/messages", response_model=GetMessagesResponse, summary="Get list of messages for an postbox")
def get_messages(postbox_id: str, response: Response):
    messages = []
    with DB as db:
        for message in db.messages.find({"postbox_id": postbox_id, 'is_deleted': False}):
            message["id"] = copy(str(message["_id"]))
            del message["_id"], message["is_deleted"], message["is_sent"], message["account_id"]
            messages.append(message)
    response.status_code = 200
    return GetMessagesResponse(messages=messages)
