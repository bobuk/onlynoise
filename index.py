from mongodb import DB
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from routers import modules as router_modules

app = FastAPI()
for module in router_modules:
    app.include_router(module.router, prefix="/v1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)