import time
from copy import copy

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from mongodb import DB
from .meta import IncomingMessage, Message, Meta, put_message_to_postbox

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


def remove_old_messages(db, postbox_id: str):
    db.messages.update_many(
        {
            "postbox_id": postbox_id,
            "created_at": {"$lt": int(time.time()) - 24 * 60 * 60 * 7},
        },
        {"$set": {"is_deleted": True}}
    )


@router.delete("/{postbox_id}", response_model=DelPostboxResponse)
def delete_postbox(postbox_id: str, response: Response):
    with DB as db:
        postbox = db.postboxes.find_one({"postbox_id": postbox_id})
        if not postbox:
            raise HTTPException(status_code=404, detail="postbox not found")
        response.status_code = 200
        db.postboxes.delete_one({"postbox_id": postbox_id})
        account = db.accounts.find_one({"postboxes.postbox_id": postbox_id})
        if account:
            db.accounts.update_one(
                {"_id": account["_id"]},
                {"$pull": {"postboxes": {"postbox_id": postbox_id}}}
            )
        return DelPostboxResponse(status="ok")


@router.put("/{postbox_id}/meta", response_model=SetPostboxMetaResponse)
def set_postbox_meta(postbox_id: str, request: SetPostboxMetaRequest, response: Response):
    with DB as db:
        account = db.accounts.find_one({"postboxes.postbox_id": postbox_id})
        if not account:
            response.status_code = 404
            return SetPostboxMetaResponse(status="postbox not found")
        req = dict(request)
        req["postbox_id"] = postbox_id
        db.postboxes.replace_one(
            {"postbox_id": postbox_id},
            req,
            upsert=True
        )
        response.status_code = 200
        return SetPostboxMetaResponse(status="ok")


@router.get("/{postbox_id}/meta", response_model=GetPostboxMetaResponse)
def get_postbox_meta(postbox_id: str, response: Response):
    with DB as db:
        postbox = db.postboxes.find_one({"postbox_id": postbox_id})
        if not postbox:
            raise HTTPException(status_code=404, detail="postbox not found")
        response.status_code = 200
        return GetPostboxMetaResponse(sender=postbox.get("sender"), icon=postbox.get("icon"), color=postbox.get("color"))


@router.post("/{postbox_id}/messages", response_model=IncomingMessage)
def create_message(postbox_id: str, request: IncomingMessage, response: Response):
    with DB as db:
        account = db.accounts.find_one({"postboxes.postbox_id": postbox_id})
        if not account:
            raise HTTPException(status_code=404, detail="Postbox not found")
        put_message_to_postbox(db, postbox_id, request)
        # remove_old_messages(db, postbox_id)
        response.status_code = 201
        return CreateMessageResponse(status="ok")


@router.get("/{postbox_id}/messages", response_model=GetMessagesResponse)
def get_messages(postbox_id: str, response: Response):
    with DB as db:
        messages = []
        for message in db.messages.find({"postbox_id": postbox_id, 'is_deleted': False}):
            message["id"] = copy(str(message["_id"]))
            del message["_id"], message["is_deleted"], message["is_sent"]
            messages.append(message)
        response.status_code = 200
        return GetMessagesResponse(messages=messages)
