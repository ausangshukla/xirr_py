# report_tasks.py

import os
import uuid
import logging
import requests
from pathlib import Path
from urllib.parse import urlparse
from app.report_generator.portfolio_report_agent.run_agent import run_portfolio_analysis

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

def generate_report_task(file_urls, additional_data, output_file_name, request_id):
    """
    Background task to generate a report based on provided file URLs and a template URL.
    """
    # Create a unique directory for this request using UUID
    results_folder = Path(f"/tmp/report_generator/{request_id}")
    results_folder.mkdir(parents=True, exist_ok=True)

    # Download files (PDF, XLSX, etc.)
    try:
        for index, file_url in enumerate(file_urls):
            parsed_url = urlparse(file_url)
            file_extension = Path(parsed_url.path).suffix
            if not file_extension:
                logger.warning(f"Could not determine file extension for {file_url}. Skipping.")
                continue

            file_name = f"File{index + 1}{file_extension}"
            file_path = results_folder / file_name
            download_file(file_url, str(file_path))
    except Exception as e:
        error_data = {"request_id": request_id, "error": f"Failed to download files: {str(e)}"}
        logger.debug(f"Error: {error_data}")
        return

    # Run Portfolio Analysis Agent
    logger.debug("Running Portfolio Analysis Agent...")
    try:
        # additional_data might contain sections_to_analyze
        sections_to_analyze = additional_data.get("sections_to_analyze") if additional_data else None
        run_portfolio_analysis(str(results_folder), sections_to_analyze=sections_to_analyze, output_file_name=output_file_name)
    except Exception as e:
        error_data = {"request_id": request_id, "error": f"Portfolio analysis failed: {str(e)}"}
        logger.debug(f"Error: {error_data}")
        return

    logger.debug(f"Portfolio analysis completed. Results are stored in: {results_folder.resolve()}")
