from fastapi import FastAPI

from .report_generator import report_generator_api
from .xirr import xirr_api

app = FastAPI()

app.include_router(xirr_api.router)
app.include_router(report_generator_api.router)
