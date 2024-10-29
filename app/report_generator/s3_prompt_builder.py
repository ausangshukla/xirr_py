# PromptBuilder.py

import requests
import os
import fitz  # PyMuPDF

class S3PromptBuilder:
    def __init__(self, file_paths, template_path, download_dir="downloads"):
        """
        Initialize the S3PromptBuilder with file URLs and an HTML template.

        :param file_paths: List of file URLs.
        :param template_path: Path to the HTML template file.
        :param download_dir: Directory where the files will be downloaded.
        """
        self.file_paths = file_paths
        self.template_path = template_path
        self.download_dir = download_dir

        # Create the download directory if it does not exist
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)

    def download_file_from_url(self, file_url, index, extension="pdf"):
        """
        Downloads a file from the given URL and saves it locally.
        
        :param file_url: The URL of the file to download.
        :param index: Index of the file for naming purposes.
        :return: Local file path of the downloaded file.
        """
        response = requests.get(file_url)
        response.raise_for_status()  # Raise an error if the download fails

        # Save the file locally with a generic name (File1.pdf, File2.pdf, etc.)
        local_file_path = os.path.join(self.download_dir, f"File{index + 1}.{extension}")
        with open(local_file_path, 'wb') as file:
            file.write(response.content)
        
        return local_file_path

    def extract_text_from_pdf(self, pdf_file):
        """
        Extracts text from the provided PDF file.
        
        :param pdf_file: The path to the PDF file.
        :return: Extracted text as a string.
        """
        doc = fitz.open(pdf_file)
        pdf_text = ""

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pdf_text += page.get_text("text")  # Extract text from each page

        return pdf_text

    def read_html_template(self):
        """
        Reads the contents of the HTML template file and returns it as a string.
        
        :return: A string containing the HTML content.
        """

    
        with open(self.template_path, 'r', encoding='utf-8') as file:
            html_content = file.read()
        return f"<Report Template Start>{html_content}<Report Template End>"

    def build_prompt(self):
        """
        Builds the prompt by downloading the files from the URLs, extracting their content, and adding the HTML template.
        
        :return: A string containing the combined prompt.
        """
        all_texts = []

        # Download each file from the URLs, extract text, and label them as File1, File2, etc.
        for index, file_path in enumerate(self.file_paths):
            file_text = self.extract_text_from_pdf(file_path)

            # Label the file generically as File1, File2, etc.
            file_label = f"File{index + 1}"
            all_texts.append(f"<{file_label} Start>{file_text}<{file_label} End>")

        # Read the HTML template
        template = self.read_html_template()
        all_texts.append(template)

        # Combine all texts into a single prompt
        return "".join(all_texts)
