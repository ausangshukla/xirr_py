
import uuid
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import List
from pathlib import Path
from ..services.report_tasks import generate_report_task

router = APIRouter()

class ReportRequest(BaseModel):
    api_key: str
    file_urls: List[str]
    template_html_url: str

@router.post("/generate-report/")
def generate_report(request: ReportRequest, background_tasks: BackgroundTasks):
    """
    Endpoint to initiate report generation based on provided file URLs and a template URL.
    """
    # Generate a unique request ID
    request_id = str(uuid.uuid4())

    print(f"Received a new report generation request with ID: {request_id}")
    print(f"Files: {request.file_urls}")
    print(f"Template: {request.template_html_url}")

    # Launch the background task
    background_tasks.add_task(
        generate_report_task,
        request.api_key,
        request.file_urls,
        request.template_html_url,
        request_id
    )

    # Return immediately to the client with the request ID
    results_folder = Path(f"results/{request_id}")
    return {
        "message": "Report generation started",
        "request_id": request_id,
        "folder_path": str(results_folder.resolve())
    }
