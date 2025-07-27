from typing import Dict, Any, List
from langchain_core.messages import BaseMessage
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from ..graphs.state import AgentState

class TableGeneratorNode:
    """
    Generates tabular data based on the extracted content and all available documents.
    """
    def __init__(self, llm):
        self.llm = llm
        self.parser = JsonOutputParser()
        self.prompt = PromptTemplate(
            template="""You are an expert financial analyst, skilled at extracting, summarizing, and presenting complex financial and business information in clear, concise, and well-structured tabular formats.
            Given the following documents and the current section content, generate highly relevant and insightful tabular data
            The table should be in JSON format, with a 'title' and 'rows' key.
            Each row should be a dictionary where keys are column headers.

            All Documents:
            {documents}

            Current Section Title: {current_section}
            Current Section Content: {current_section_content}

            Table Instructions:
            {table_instructions}

            Instructions:
            - Focus on extracting key financial metrics, operational data, and comparative figures.
            - Include relevant time periods (e.g., quarters, fiscal years) and growth rates where applicable.
            - Structure the table to facilitate easy comparison and analysis, similar to a financial report.
            - Ensure the table is well-structured, easy to understand, and directly addresses the content of the current section.
            - If no relevant tabular data can be extracted, return an empty table structure: {{"title": "", "rows": []}}.
            - The output MUST be a valid JSON object.

            Example Output (Financial Highlights):
            {{
                "title": "Consolidated Financial Performance (USD Millions)",
                "rows": [
                    {{"Metric": "Revenue", "Q1 2024": "1,200", "Q1 2025": "1,500", "YoY Growth": "25%"}},
                    {{"Metric": "Gross Profit", "Q1 2024": "500", "Q1 2025": "650", "YoY Growth": "30%"}},
                    {{"Metric": "Net Income", "Q1 2024": "150", "Q1 2025": "200", "YoY Growth": "33.3%"}},
                    {{"Metric": "EPS (Diluted)", "Q1 2024": "1.25", "Q1 2025": "1.60", "YoY Growth": "28%"}}
                ]
            }}

            Example Output (Operational Metrics):
            {{
                "title": "Key Operational Metrics - Product X",
                "rows": [
                    {{"Metric": "Units Sold", "2023": "10,000", "2024": "12,500", "Growth": "25%"}},
                    {{"Metric": "Average Selling Price", "2023": "$120", "2024": "$115", "Change": "-$5"}},
                    {{"Metric": "Customer Acquisition Cost", "2023": "$50", "2024": "$45", "Change": "-$5"}}
                ]
            }}
            """,
            input_variables=["documents", "current_section", "current_section_content", "table_instructions"],
        )
        self.chain = self.prompt | self.llm | self.parser

    def generate_table(self, state: AgentState) -> Dict[str, Any]:
        """
        Generates tabular data for the current section.
        """
        print(f"--- Generating table for section: '{state.get('current_section')}' ---")
        documents_content = "\n\n".join([doc["content"] for doc in state.get("documents", [])])
        current_section_content = state.get("current_section_content", "")
        current_section_title = state.get("current_section", "")
        table_instructions = state.get("table_instructions", "Table should not have more than 8 rows.")
        if not table_instructions.strip():
            table_instructions = "Table should not have more than 8 rows."

        try:
            tabular_data = self.chain.invoke({
                "documents": documents_content,
                "current_section": current_section_title,
                "current_section_content": current_section_content,
                "table_instructions": table_instructions
            })
            print(f"--- Table generated for '{current_section_title}' ---")
            # Append the generated table to the current section's content or a new field
            # For now, let's add it to a new 'tabular_data' field in the state.
            # We might want to integrate this into 'completed_sections' later.
            
            # Return the tabular_data and ensure other relevant state variables are passed through
            result = {
                "tabular_data": tabular_data
            }
            # print(f"--- TableGeneratorNode returning: {result} ---")
            return result

        except Exception as e:
            print(f"Error generating table for section '{current_section_title}': {e}")
            import traceback
            traceback.print_exc()
            return {} # Return empty dict to avoid breaking the graph