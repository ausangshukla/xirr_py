# src/pdf_query/main.py

import os
import logging
import requests
import tempfile


from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl

import tempfile
from .pdf_query_tool import PDFQueryTool

router = APIRouter()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Define a Pydantic model for the response
class QueryResponse(BaseModel):
    answer: str

# Define a Pydantic model for the request
class QueryRequest(BaseModel):
    api_key: str
    file_url: HttpUrl
    question: str

# Define a Pydantic model for the response
class QueryResponse(BaseModel):
    answer: str

@router.post("/docs-qna", response_model=QueryResponse)
def query_pdf(request: QueryRequest):
    """
    Endpoint to download a PDF from a URL and ask a question based on its content.
    """
    api_key = request.api_key
    file_url = request.file_url
    question = request.question

    logger.info(f"Received request to process PDF from URL: {file_url}")


    # Download the PDF file
    try:
        response = requests.get(file_url)
        response.raise_for_status()
        logger.info(f"Successfully downloaded PDF from {file_url}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download PDF: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to download PDF: {e}")

    # Save the PDF to a temporary file
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(response.content)
            tmp_file_path = tmp_file.name
        logger.info(f"Saved PDF to temporary file: {tmp_file_path}")
    except Exception as e:
        logger.error(f"Failed to save PDF to temporary file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save PDF: {e}")

    # Initialize the PDFQueryTool with the provided API key
    tool = PDFQueryTool(api_key=api_key)

    # Run the tool to get the answer
    try:
        answer = tool.run(tmp_file_path, question)
        logger.info("Successfully obtained answer from PDFQueryTool.")
    except Exception as e:
        logger.error(f"An error occurred while processing the PDF: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred while processing the PDF: {e}")
    finally:
        # Clean up the temporary file
        try:
            os.remove(tmp_file_path)
            logger.info(f"Deleted temporary file: {tmp_file_path}")
        except Exception as e:
            logger.warning(f"Failed to delete temporary file {tmp_file_path}: {e}")

    return QueryResponse(answer=answer)