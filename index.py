from mongodb import DB
from fastapi import FastAPI, Request, Response
from routers import modules as router_modules

app = FastAPI()
for module in router_modules:
    app.include_router(module.router, prefix="/v1")