from fastapi import APIRouter, HTTPException
import pandas as pd
import numpy as np
from scipy.optimize import bisect, newton
from ..models.models import Transaction 
from typing import List
from pyxirr import xirr
from datetime import date, datetime
from .excel_merger import ExcelMerger


router = APIRouter()
def calculate_xirr(transactions: List[Transaction], caller_id=None):
    df = pd.DataFrame.from_records([s.to_dict() for s in transactions])

    print(df)

    if df.empty:
        xirr_val = 0
    else:
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

# Sample request: http://localhost:8000/merge_xl?template_path=data/template.xlsx&data_path=data/data.xlsx&output_path=data/merged.xlsx
@router.post("/merge_xl")
async def merge_xl(template_path: str, data_path: str, output_path: str):
    try:
        xl_merger = ExcelMerger(template_path, data_path, output_path)
        xl_merger.copy_formulas_and_data()
        return {"message": "Merge completed successfully."}
    except FileNotFoundError as e:
        # Return a 404 Not Found response if a file is not found
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # Handle other unexpected errors, returning a 500 Internal Server Error
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")
    
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
    
