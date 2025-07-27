import os
import json
import datetime
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI # Example LLM
import sys
from .graphs.main_graph import PortfolioAnalysisGraph
from .utils.excel_to_csv_utils import convert_excel_to_csv
from .tools.document_loader import load_documents_from_folder
from .utils.report_generator import generate_html_report

DEFAULT_SECTIONS_TO_ANALYZE = [
    {
        "name": "Executive Summary",
        "section_instructions": "Highlight the key investment thesis for the company and summarize the main financial and operating metrics. Keep it focused with each sub_section being 3-4 lines only",
        "include_table": True,
        "table_instructions": "",
        "include_graphs": True,
        "graph_instructions": ""
    },
    {
        "name": "Overview",
        "section_instructions": "Provide a brief overview of the company, including its history, mission, and key products or services. Also include founder and key management.",
        "include_table": True,
        "table_instructions": "",
        "include_graphs": False,
        "graph_instructions": ""
    },
    {
        "name": "Strategic Insights",
        "section_instructions": "Summarize the strategic insights from the annual report, focusing on the company's long-term vision and strategic initiatives. Do not generate markdown tables, just text",
        "include_table": False,
        "table_instructions": "",
        "include_graphs": True,
        "graph_instructions": ""
    },
    {
        "name": "Financial Review",
        "section_instructions": "Analyze the financial performance of the company, including revenue, profit margins, and key financial ratios. Do not generate markdown tables, just text.",
        "include_table": True,
        "table_instructions": "",
        "include_graphs": True,
        "graph_instructions": ""
    },
    {
        "name": "Risks",
        "section_instructions": "Identify and analyze the key risks facing the company, including market, operational, and financial risks.",
        "include_table": True,
        "table_instructions": "",
        "include_graphs": False,
        "graph_instructions": ""
    }
]

def _initialize_environment():
    """
    Loads environment variables and initializes the Google Generative AI LLM.

    Returns:
        ChatGoogleGenerativeAI: Initialized LLM instance.
    
    Raises:
        ValueError: If GOOGLE_API_KEY is not found in environment variables.
    """
    load_dotenv()
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        raise ValueError("Error: GOOGLE_API_KEY not found in environment variables. Please set it in a .env file or directly in your environment.")
    
    return ChatGoogleGenerativeAI(model="gemini-2.5-flash-preview-05-20", google_api_key=google_api_key)

def _prepare_data_folder(data_folder: str):
    """
    Validates the data folder and converts any .xlsx files to .csv.

    Args:
        data_folder (str): The path to the data folder.
    
    Raises:
        FileNotFoundError: If the data folder does not exist.
    """
    if not os.path.exists(data_folder):
        raise FileNotFoundError(f"Error: Data folder '{data_folder}' not found. Please ensure the folder exists.")

    print(f"Checking for .xlsx files in '{data_folder}' to convert to .csv...")
    for root, _, files in os.walk(data_folder):
        for file in files:
            if file.endswith(".xlsx"):
                excel_file_path = os.path.join(root, file)
                print(f"Found Excel file: {excel_file_path}. Converting to CSV...")
                convert_excel_to_csv(excel_file_path, root) # Convert in place
    print("Excel to CSV conversion complete (if any .xlsx files were found).")

def _load_and_display_documents(data_folder: str):
    """
    Loads documents from the specified data folder and prints their details.

    Args:
        data_folder (str): The path to the data folder.

    Returns:
        list: A list of loaded documents.
    
    Raises:
        ValueError: If no documents are found in the data folder.
    """
    loaded_docs = load_documents_from_folder(data_folder)
    if not loaded_docs:
        raise ValueError("No documents found in the data folder. Exiting.")
    
    print("Documents identified for processing:")
    for doc in loaded_docs:
        print(f"- {doc['filename']} (Type: {doc['metadata'].get('type', 'unknown')})")
    return loaded_docs

def _execute_analysis_and_save_report(llm, loaded_docs, sections_to_analyze, output_dir):
    """
    Executes the portfolio analysis and saves the incremental JSON report.

    Args:
        llm: The initialized LLM instance.
        loaded_docs (list): List of loaded documents.
        sections_to_analyze (list): List of sections to analyze.
        output_dir (str): Directory to save the report.

    Returns:
        str: The path to the generated JSON report file.
    """
    agent_graph = PortfolioAnalysisGraph(max_review_loops=1)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"portfolio_analysis_report_{timestamp}.json")
    
    print(f"Starting portfolio analysis and writing incremental report to '{output_file}'...")
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("[\n")
        first_section = True
        for section_report in agent_graph.run_analysis(llm, loaded_docs, sections_to_analyze):
            if not first_section:
                f.write(",\n")
            json.dump(section_report, f, indent=2)
            first_section = False
        f.write("\n]\n")
        
    print(f"\nPortfolio analysis completed. Report saved to '{output_file}'")
    return output_file

def _generate_html_report(json_report_path: str, output_dir: str, output_file_name: str = None):
    """
    Generates an HTML report from the JSON report.

    Args:
        json_report_path (str): Path to the JSON report file.
        output_dir (str): Directory to save the HTML report.
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    if output_file_name is None:
        output_file_name = os.path.join(output_dir, f"portfolio_analysis_report_{timestamp}.html")
    generate_html_report(json_report_path, output_file_name)
    print(f"HTML report generated and saved to '{output_file_name}'")

def run_portfolio_analysis(folder_name: str, sections_to_analyze: list = None, output_file_name: str = None):
    """
    Orchestrates the portfolio analysis process.

    Args:
        folder_name (str): The name of the folder within 'langgraph_agent/data' to analyze.
        sections_to_analyze (list, optional): A list of dictionaries defining the sections
                                               to analyze. If None, a default set of sections
                                               will be used.
    """
    try:
        # 1. Initialize environment and LLM
        llm = _initialize_environment()

        # 2. Prepare data folder (validate existence and convert Excel files)
        data_folder = folder_name
        _prepare_data_folder(data_folder)

        # 3. Load and display documents
        loaded_docs = _load_and_display_documents(data_folder)

        # 4. Determine sections to analyze
        sections_to_analyze = sections_to_analyze if sections_to_analyze is not None else DEFAULT_SECTIONS_TO_ANALYZE

        # 5. Set up output directory
        output_dir = "outputs"
        os.makedirs(output_dir, exist_ok=True)

        # 6. Execute analysis and save JSON report
        json_report_path = _execute_analysis_and_save_report(llm, loaded_docs, sections_to_analyze, output_dir)

        # 7. Generate HTML report
        _generate_html_report(json_report_path, output_dir, output_file_name)

    except (ValueError, FileNotFoundError) as e:
        print(f"An error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def main():
    """
    Main function to run the portfolio analysis agent.
    It now accepts a folder name as a command-line argument to specify
    which data folder to load documents from.
    """
    if len(sys.argv) < 2:
        print("Usage: poetry run python run_agent.py <path_to_data_folder>")
        print("Please provide the full path to the data folder to analyze.")
        return
    
    folder_name = sys.argv[1]
    run_portfolio_analysis(folder_name)

if __name__ == "__main__":
    main()