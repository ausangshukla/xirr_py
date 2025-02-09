# report_tasks.py

import os
import uuid
import logging
import requests
from pathlib import Path
from .report_generator import ReportGenerator

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Change to DEBUG for more verbosity
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

def download_file(url: str, save_path: str):
    """
    Downloads a file from a URL and saves it to the specified path.
    """
    logger.debug(f"Downloading file from {url} to {save_path}")
    response = requests.get(url)
    response.raise_for_status()
    with open(save_path, 'wb') as f:
        f.write(response.content)

def generate_report_task(openai_api_key, anthropic_api_key, file_urls, template_html_url, additional_data, output_file_name, request_id):
    """
    Background task to generate a report based on provided file URLs and a template URL.
    """
    # Create a unique directory for this request using UUID
    results_folder = Path(f"/tmp/report_generator/{request_id}")
    results_folder.mkdir(parents=True, exist_ok=True)

    # Define paths for temporary files
    template_path = results_folder / "template.html"
    output_path = results_folder / output_file_name

    # Download the HTML template
    try:
        download_file(template_html_url, str(template_path))
    except Exception as e:
        error_data = {"request_id": request_id, "error": f"Failed to fetch template HTML: {str(e)}"}
        logger.debug(f"Error: {error_data}")
        return

    # Download PDF files
    file_paths = []
    try:
        for index, file_url in enumerate(file_urls):
            file_path = results_folder / f"File{index + 1}.pdf"
            file_paths.append(str(file_path))
            download_file(file_url, str(file_path))
    except Exception as e:
        error_data = {"request_id": request_id, "error": f"Failed to download files: {str(e)}"}
        logger.debug(f"Error: {error_data}")
        return

    # Run ReportGenerator
    logger.debug("Running ReportGenerator...")
    report_generator = ReportGenerator(openai_api_key, anthropic_api_key, file_paths, str(template_path), additional_data)
    try:
        report_generator.save_summary_to_file(output_path, "openai")
    except Exception as e:
        error_data = {"request_id": request_id, "error": f"Report generation failed: {str(e)}"}
        logger.debug(f"Error: {error_data}")
        return

    logger.debug(f"Report generation completed. Results are stored in: {results_folder.resolve()}")
