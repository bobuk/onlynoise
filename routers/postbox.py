from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field
from mongodb import DB
import time
from copy import copy

# import pymongo

router = APIRouter(prefix="/postboxes")


class CreateMessageRequest(BaseModel):
    subject: str | None = Field("", title="Subject")
    body: str | None = Field("", title="Body")
    url: str | None = Field("", title="URL")
    image_url: str | None = Field("", title="Image URL")
    important: bool | None = Field(False, title="Important")


class CreateMessageResponse(BaseModel):
    status: str = Field(..., title="Status")


class Message(BaseModel):
    id: str = Field(..., title="Unique Message ID")
    subject: str | None = Field("", title="Subject")
    body: str | None = Field("", title="Body")
    url: str | None = Field("", title="URL")
    image_url: str | None = Field("", title="Image URL")
    important: bool = Field(False, title="Important")

    postbox_id: str = Field(..., title="Postbox ID")
    created_at: int = Field(..., title="Created At")


class GetMessagesResponse(BaseModel):
    status: str = Field(..., title="Status")
    messages: list[Message] = Field(..., title="Messages list")


def remove_old_messages(db, postbox_id: str):
    db.messages.update_many(
        {
            "postbox_id": postbox_id,
            "created_at": {"$lt": int(time.time()) - 24 * 60 * 60 * 7},
        },
        {"$set": {"is_deleted": True}}
    )


@router.post("/{postbox_id}/messages", response_model=CreateMessageResponse)
def create_message(postbox_id: str, request: CreateMessageRequest, response: Response):
    with DB as db:
        account = db.accounts.find_one({"postboxes.postbox_id": postbox_id})
        if not account:
            raise HTTPException(status_code=404, detail="Postbox not found")
        db.messages.insert_one(
            {
                "subject": request.subject,
                "body": request.body,
                "url": request.url,
                "image_url": request.image_url,
                "important": request.important,
                "postbox_id": postbox_id,
                "created_at": int(time.time()),
                "is_deleted": False,
                "is_sent": False,
            }
        )
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
        return GetMessagesResponse(status="ok", messages=messages)
