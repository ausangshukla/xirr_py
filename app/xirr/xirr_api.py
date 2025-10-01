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

from typing import List
import pandas as pd
from pyxirr import xirr as pyxirr_xirr
from scipy.optimize import brentq, newton
from datetime import datetime


# Function to calculate XIRR using the pyxirr library
def calculate_xirr_with_pyxirr(dates, amounts):
    try:
        # Attempt to calculate XIRR using pyxirr
        xirr_val = pyxirr_xirr(dates, amounts, silent=False)
        # Check for unrealistic results
        if abs(xirr_val) > 1e10:
            raise ValueError("Unrealistic XIRR result from pyxirr")
        return xirr_val
    except Exception as e:
        # Log failure and return None
        print(f"[pyxirr] Failed: {e}")
        return None


# Function to calculate XIRR using numpy and numerical methods
def calculate_xirr_with_numpy(dates, amounts):
    # Define the Net Present Value (NPV) function
    def npv(rate):
        try:
            return sum([
                amt / ((1 + rate) ** ((d - dates[0]).days / 365))
                for amt, d in zip(amounts, dates)
            ])
        except (ZeroDivisionError, OverflowError):
            return float('inf')

    try:
        # Preferred method: Use Brent's method to find the root of the NPV function
        return brentq(npv, -0.9999, 10)
    except ValueError:
        try:
            # Fallback method: Use Newton-Raphson method with an initial guess
            return newton(npv, 0.1)
        except Exception as e:
            # Log failure and return 0
            print(f"[numpy] Failed to converge: {e}")
            return 0


# Main function to calculate XIRR for a list of transactions
def calculate_xirr(transactions: List, caller_id=None):
    # Convert transactions to a pandas DataFrame
    df = pd.DataFrame.from_records([s.to_dict() for s in transactions])

    # Return 0 if the DataFrame is empty
    if df.empty:
        return 0

    # Convert 'date' column to datetime and sort by date
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(by='date')

    # Save sanitized cashflows to a CSV file for debugging if caller_id is provided
    # if caller_id:
    #     df.to_csv(f"xirr-debug-{caller_id}.csv", index=False)

    # Print sanitized cashflows for debugging
    print("\nSanitized Cashflows:")
    print(df[['date', 'amount']])

    # Extract dates and amounts from the DataFrame
    dates = df['date'].tolist()
    amounts = df['amount'].tolist()

    # Attempt to calculate XIRR using pyxirr
    xirr_val = calculate_xirr_with_pyxirr(dates, amounts)
    if xirr_val is None:
        # Fallback to numpy-based calculation if pyxirr fails
        xirr_val = calculate_xirr_with_numpy(dates, amounts)

    # Print and return the calculated XIRR value
    print(f"xirr_val = {xirr_val:.4%}")
    return xirr_val or 0

# Root endpoint for the API
@router.get("/")
async def root():
    return {"message": "Hello Xirr"}

# Endpoint to merge Excel files
# Sample request: http://localhost:8000/merge_xl?template_path=data/template.xlsx&data_path=data/data.xlsx&output_path=data/merged.xlsx
@router.post("/merge_xl")
async def merge_xl(template_path: str, data_path: str, output_path: str):
    try:
        # Initialize the ExcelMerger and perform the merge
        xl_merger = ExcelMerger(template_path, data_path, output_path)
        xl_merger.copy_formulas_and_data()
        return {"message": "Merge completed successfully."}
    except FileNotFoundError as e:
        # Return a 404 Not Found response if a file is not found
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # Handle other unexpected errors, returning a 500 Internal Server Error
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")
    
# Endpoint to calculate XIRR for a list of transactions
@router.post("/calculate_xirr")
async def calculate(transactions: List[Transaction], caller_id=None):
    try:
        # Attempt to calculate XIRR
        xirr = calculate_xirr(transactions, caller_id)
        return {"xirr": xirr}
    except Exception as e:
        try:
            # Retry calculation in case of failure
            print("Newton failed, trying bisect")
            xirr = calculate_xirr(transactions, caller_id)
            return {"xirr": xirr}
        except Exception as e:
            # Return error details if all attempts fail
            return {"xirr": None, "error": repr(e)}
