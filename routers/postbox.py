from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field
from mongodb import DB
import pymongo

router = APIRouter(prefix="/postboxes")

class SendMessageRequest(BaseModel):
    subject: str = Field(..., title="Subject")
    body: str = Field(..., title="Body")
    url: str = Field(..., title="URL")
    image_url: str = Field(None, title="Image URL")
    important: bool = Field(False, title="Important")