from fastapi import FastAPI
from .routers import xirr_api, report_generator_api

app = FastAPI()

app.include_router(xirr_api.router)
app.include_router(report_generator_api.router)
