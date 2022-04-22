# from mongodb import DB
from fastapi import FastAPI
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("index:app", port=8080, reload=True, access_log=True, debug=True)
