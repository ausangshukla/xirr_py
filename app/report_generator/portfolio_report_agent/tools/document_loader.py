import os
from typing import List, Dict, Any
import pandas as pd
import PyPDF2 # For PDF processing
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_documents_from_folder(folder_path: str) -> List[Dict[str, Any]]:
    """
    Loads documents from a specified folder, supporting various formats (TXT, CSV, PDF).

    Args:
        folder_path (str): The path to the folder containing the documents.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, where each dictionary represents
                              a loaded document with its content and metadata.
    """
    if not os.path.isdir(folder_path):
        logging.error(f"Folder not found: {folder_path}")
        raise FileNotFoundError(f"Folder not found: {folder_path}")

    documents = []
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path):
            file_extension = os.path.splitext(filename)[1].lower()
            content = None
            doc_type = "unknown"

            try:
                if file_extension == ".txt":
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    doc_type = "text"
                    logging.info(f"Successfully loaded text file: {filename}")
                elif file_extension == ".csv":
                    df = pd.read_csv(file_path)
                    content = df.to_string() # Convert DataFrame to string for content
                    doc_type = "csv"
                    logging.info(f"Successfully loaded CSV file: {filename}")
                elif file_extension == ".pdf":
                    # Using PyPDF2 for PDF text extraction
                    with open(file_path, 'rb') as f:
                        reader = PyPDF2.PdfReader(f)
                        text_content = ""
                        for page_num in range(len(reader.pages)):
                            text_content += reader.pages[page_num].extract_text() or ""
                        content = text_content
                    doc_type = "pdf"
                    logging.info(f"Successfully loaded PDF file: {filename}")
                else:
                    logging.warning(f"Unsupported file type, skipping: {filename}")
                    continue # Skip unsupported file types

                documents.append({
                    "filename": filename,
                    "content": content,
                    "metadata": {"source": file_path, "type": doc_type}
                })
            except Exception as e:
                logging.error(f"Error processing {filename}: {e}")
                documents.append({
                    "filename": filename,
                    "content": None,
                    "metadata": {"source": file_path, "type": doc_type, "error": str(e)}
                })
    return documents

if __name__ == "__main__":
    # Example usage:
    # Create a dummy data folder and some files for testing
    dummy_data_folder = "temp_data_for_testing"
    os.makedirs(dummy_data_folder, exist_ok=True)
    with open(os.path.join(dummy_data_folder, "doc1.txt"), "w") as f:
        f.write("This is the content of document 1.")
    with open(os.path.join(dummy_data_folder, "doc2.csv"), "w") as f:
        f.write("header1,header2\nvalue1,value2")

    print(f"Loading documents from: {dummy_data_folder}")
    loaded_docs = load_documents_from_folder(dummy_data_folder)
    for doc in loaded_docs:
        print(f"--- Document: {doc['filename']} ---")
        print(f"Content: {doc['content'][:50]}...") # Print first 50 chars
        print(f"Metadata: {doc['metadata']}")
        print("-" * 30)

    # Clean up dummy data
    os.remove(os.path.join(dummy_data_folder, "doc1.txt"))
    os.remove(os.path.join(dummy_data_folder, "doc2.csv"))
    os.rmdir(dummy_data_folder)