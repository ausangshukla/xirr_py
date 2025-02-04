import traceback
import boto3
import logging
from openai import OpenAI
from htmldocx import HtmlToDocx
from .s3_prompt_builder import S3PromptBuilder
from typing import List, Optional
from langchain.chains import LLMChain
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import BedrockChat
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import AnalyzeDocumentChain
from langchain.schema import Document
from htmldocx import HtmlToDocx
import aiohttp
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

class ReportGenerator:    
    def __init__(self, api_key, anthropic_api_key, file_paths, template_path, additional_data, format: str = "html"):
        """
        Initialize the ReportGenerator with paths to input files and API keys.

        :param api_key: OpenAI API key
        :param anthropic_api_key: Anthropic API key
        :param file_paths: signed links to the files in S3. Sent by the rails job
        :param template_path: Path to the HTML template file.
        """
        self.api_key = api_key
        self.anthropic_api_key = anthropic_api_key
        
        if not self.api_key:
            raise ValueError("OpenAI API key not found.")
            
        if not self.anthropic_api_key:
            raise ValueError("Anthropic API key not found.")
        
        self.prompt_builder = S3PromptBuilder(file_paths, template_path, additional_data)

        # Initialize models
        self.openai_model = ChatOpenAI(
            api_key=api_key,
            model="gpt-4o",
            temperature=0
        )
        
        # Initialize Claude model
        self.anthropic_model = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            anthropic_api_key=anthropic_api_key,
            temperature=0,
            max_tokens=4096*2
        )
        
        # Initialize Bedrock client and model
        self.bedrock_client = boto3.client(
            service_name='bedrock-runtime',
            region_name="us-east-1",
        )
        
        self.bedrock_model = BedrockChat(
            client=self.bedrock_client,
            model_id="meta.llama3-2-11b-instruct-v1:0",
            model_kwargs={
                "temperature": 0,
                "top_p": 0.9,
                "max_tokens": 4096
            }
        )

        if format == "html":
            self.context = [
                {"role": "system", "content": "You are a financial analyst that answers questions based on the provided documents. The documents are attached with <Filename Start> and <Filename End> tags. Your role is to generate a report based on the extracted information and put it into the report template format supplied in the <Report Template Start> <Report Template End> tags. Please retain the <head> tags with styles, and ensure the result is well formed html. Do not add content outside the html tags. Do not modify or overwrite the css styles in the report. Do not add any ```html or ```css tags to start of the report."}
            ]
        elif format == "json":
            self.context = [
                {"role": "system", "content": "You are a financial analyst that answers questions based on the provided documents. The documents are attached with <Filename Start> and <Filename End> tags. Your role is to generate a report based on the extracted information and put it into the report template format supplied in the <Report Template Start> <Report Template End> tags. Please retain the JSON structure of the template. Do not add content outside the JSON structure. Do not add any ```json tags to start of the report."}
            ]

    def generate_report(self, model_type: str = "openai") -> str:
        """
        Generate a report using the specified model.
        
        Args:
            model_type: Which model to use - "openai", "claude", or "bedrock"
        
        Returns:
            str: Generated report in HTML format
        """
        try:
            # Create prompt
            prompt = self.prompt_builder.create_prompt()
            
            # Select model based on type
            if model_type == "openai":
                model = self.openai_model
            elif model_type == "anthropic":
                model = self.anthropic_model
            elif model_type == "bedrock":
                model = self.bedrock_model
            else:
                raise ValueError(f"Unsupported model type: {model_type}")
            
            # Create and run chain
            chain = prompt | model
            
            logger.debug(f"Generating report using {model_type}...")
            response = chain.invoke({
                "documents": self.prompt_builder.documents(),
                "template": self.prompt_builder.template(),
                "additional_data": self.prompt_builder.additional_data_value()
            })

            return response.content
            
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            traceback.print_exc()
            raise e

    def save_summary_to_file(self, output_path="template/output_report.html", model_type="openai"):
        """
        Generates the report and saves it to a file.
        
        :param output_path: Path to save the output report file.
        :param model_type: Which model to use - "openai", "claude", or "bedrock"
        """
        logger.debug(f"Generating summary using {model_type} and saving to '{output_path}'...")
        summary = self.generate_report(model_type=model_type)
        
        with open(output_path, "w") as f:
            f.write(summary)

        # Convert the HTML report to DOCX
        new_parser = HtmlToDocx()
        new_parser.parse_html_file(output_path, f"{output_path}")

        logger.debug(f"Summary has been generated and saved to '{output_path}'.")
        logger.debug(f"Summary has been converted to DOCX format and saved to '{output_path}.docx'.")

# Example usage
if __name__ == "__main__":
    investor_pdf = "docs/report_data/Investor presentation.pdf"
    kpi_pdf = "docs/report_data/KPI.pdf"
    portfolio_pdf = "docs/report_data/portfolio_investments.pdf"
    template_html = "template/report2.html"

    report_generator = ReportGenerator(
        api_key="your-openai-key",
        anthropic_api_key="your-anthropic-key",
        file_paths=[investor_pdf, kpi_pdf, portfolio_pdf],
        template_path=template_html
    )
    
    # Generate report using Claude
    report_generator.save_summary_to_file(
        output_path="template/output_report.html",
        model_type="claude"
    )