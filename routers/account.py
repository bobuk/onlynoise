import time
import random
import string
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field
from mongodb import DB
import pymongo

router = APIRouter(prefix="/accounts")


class CreateAccountResponse(BaseModel):
    account_id: str = Field(..., title="Account ID, prob 32 characters long")
    created_at: int = Field(default_factory=lambda: int(time.time()), title="Unix timestamp")
    status: str = Field(default_factory=lambda: "created", title="Status of the request")

class CreateDeviceResponse(BaseModel):
    created_at: int = Field(default_factory=lambda: int(time.time()), title="Unix timestamp")
    status: str = Field(default_factory=lambda: "created", title="Status of the request")

class CreateDeviceRequest(BaseModel):
    device_id: str = Field(..., title="Device ID")
    device_type: str = Field(..., title="Device type (like ios or android or web)")

def create_random_string(length: int = 32) -> str:
    return "".join(random.choice(string.ascii_letters + string.digits) for _ in range(length))


@router.post("/", response_model=CreateAccountResponse)
def create_account(response: Response):
    response.status_code = 201
    account_id = create_random_string()
    created_at = int(time.time())
    with DB as db:
        db.accounts.insert_one({
            "account_id": account_id,
            "created_at": created_at,
            "devices": [],
            "postboxes": [], # post robot boxes (stone)
        })
    return CreateAccountResponse(account_id=account_id, created_at=created_at, status="created")

@router.post("/{account_id:str}/devices", response_model=CreateDeviceResponse)
def create_device(account_id: str, request: CreateDeviceRequest, response: Response):
    created_at = int(time.time())
    with DB as db:
        account = db.accounts.find_one({"account_id": account_id})
        if not account:
            response.status_code  = 406
            return CreateDeviceRequest(status="account_id not found")
        full_device_id = f"{request.device_type}:{request.device_id}"
        if not [device for device in account["devices"] if device["device_id"] == full_device_id]:
            db.accounts.update_one(
                {"account_id": account_id},
                {"$push": {"devices": {
                    "device_id": full_device_id,
                    "created_at": created_at,
                }}}
            )

    response.status_code = 201
    return CreateDeviceResponse(created_at=created_at, status="created")

