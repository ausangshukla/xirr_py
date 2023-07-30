from fastapi import APIRouter
import pandas as pd
import numpy as np
from scipy.optimize import bisect, newton
from ..models.models import Transaction 
from typing import List
from pyxirr import xirr
from datetime import date, datetime


router = APIRouter()
def calculate_xirr(transactions: List[Transaction], caller_id=None):
    df = pd.DataFrame.from_records([s.to_dict() for s in transactions])

    print(df)

    df.to_csv(f"tmp/xirr-{caller_id}.csv", encoding='utf-8')

    xirr_val = xirr(df['date'], df['amount'], silent=False)
    print(f"xirr_val = {xirr_val}")

    return xirr_val or 0
    
def calculate_xirr_old(transactions: List[Transaction], algo="newton"):
    df = pd.DataFrame.from_records([s.to_dict() for s in transactions])

    print(df)
    df.to_csv('xirr.csv', encoding='utf-8')


    df = df.sort_values(by='date')
    df['year_frac'] = (df['date'] - df['date'].min()) / pd.Timedelta(days=365)

    def xnpv(rate):
        return np.sum(df['amount'] / (1 + rate) ** df['year_frac'])

    def xirr_newton(df):
        guess = 0.1
        return newton(xnpv, guess, maxiter=100, full_output=True, tol=1e-3)
    
    
    def xirr_bisect(df):
        # provide the interval [a, b] where the function changes sign
        a = -0.99
        b = 10000000.0
        return bisect(xnpv, a, b, full_output=True, rtol=1e-3)
    
    if algo == "newton":
        return xirr_newton(df)
    else:
        return xirr_bisect(df)

@router.get("/")
async def root():
    return {"message": "Hello Xirr"}
    
@router.post("/calculate_xirr")
async def calculate(transactions: List[Transaction], caller_id=None):
    try:
        xirr = calculate_xirr(transactions, caller_id)
        return {"xirr": xirr}
    except Exception as e:
        try:
            print("Newton failed, trying bisect")
            xirr = calculate_xirr(transactions, caller_id)
            return {"xirr": xirr}
        except Exception as e:
            return {"xirr": None, "error": repr(e)}
    
