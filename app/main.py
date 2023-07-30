from fastapi import FastAPI
from .routers import xirr_api

app = FastAPI()

app.include_router(xirr_api.router)
