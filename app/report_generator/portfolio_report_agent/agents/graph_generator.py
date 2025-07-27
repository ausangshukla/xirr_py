from typing import Dict, Any, List
from langchain_core.messages import BaseMessage
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from ..graphs.state import AgentState

class GraphGeneratorNode:
    """
    Generates graph specifications (e.g., for D3.js, Chart.js, or a simple textual description)
    based on the extracted content and all available documents.
    """
    def __init__(self, llm):
        self.llm = llm
        self.parser = JsonOutputParser()
        self.prompt = PromptTemplate(
            template="""You are an expert at identifying and summarizing data suitable for graphical representation.
            Given the following documents and the current section content, identify key data points
            that can be visualized and propose suitable graph types and their data structures.
            The output should be a JSON array of objects, where each object has a 'title', 'type' (e.g., 'bar', 'line', 'pie', 'textual_description'),
            and 'data' key. The 'data' key should contain the necessary data for the graph.
            If a textual description is more appropriate for a specific visualization, set 'type' to 'textual_description' and
            provide a clear description in the 'data' field for that object.
            Always attempt to generate at least one graph if relevant data is present. If no suitable data for any graph is found, return an empty array: [].

            All Documents:
            {documents}

            Current Section Title: {current_section}
            Current Section Content: {current_section_content}
            Tabular Data for Current Section (if available): {tabular_data}

            Graph Instructions:
            {graph_instructions}

            Instructions:
            - Analyze the content and tabular data for trends, comparisons, or distributions.
            - Suggest a graph type that best represents the identified data. Never use stacked_bar
            - Provide the data in a structured format suitable for the chosen graph type.
            - The output MUST be a valid JSON array.

            Example Output (Multiple Graphs):
            [
                {{
                    "title": "Quarterly Revenue Comparison",
                    "type": "bar",
                    "data": {{
                        "labels": ["Q1", "Q2", "Q3", "Q4"],
                        "datasets": [
                            {{"label": "Revenue", "data": [100, 120, 150, 130]}}
                        ]
                    }}
                }},
                {{
                    "title": "Market Share Distribution",
                    "type": "pie",
                    "data": {{
                        "labels": ["Product A", "Product B", "Product C"],
                        "datasets": [
                            {{"data": [30, 45, 25]}}
                        ]
                    }}
                }}
            ]

            Example Output (Textual Description within array):
            [
                {{
                    "title": "Key Performance Indicators Overview",
                    "type": "textual_description",
                    "data": "The company has shown consistent growth in revenue over the last three quarters, with a slight dip in Q4 due to seasonal factors. Profit margins have remained stable."
                }}
            ]
            """,
            input_variables=["documents", "current_section", "current_section_content", "tabular_data", "graph_instructions"],
        )
        self.chain = self.prompt | self.llm | self.parser

    def generate_graph(self, state: AgentState) -> Dict[str, Any]:
        """
        Generates graph specifications for the current section.
        """
        print(f"--- Generating graph for section: '{state.get('current_section')}' ---")
        documents_content = "\n\n".join([doc["content"] for doc in state.get("documents", [])])
        current_section_content = state.get("current_section_content", "")
        current_section_title = state.get("current_section", "")
        tabular_data = state.get("tabular_data", {}) # Get tabular data if available
        current_section_references = state.get("current_section_references", []) # Get references from writer

        print(f"--- Debug: Input documents_content length: {len(documents_content)} ---")
        # print(f"--- Debug: Input current_section_content length: {len(current_section_content)} ---")
        # print(f"--- Debug: Input tabular_data: {tabular_data} ---")

        try:
            # Temporarily modify the chain to get raw LLM output before parsing
            raw_chain = self.prompt | self.llm
            graph_instructions = state.get("graph_instructions", "Only generate graphs of the most important data")
            if not graph_instructions.strip():
                graph_instructions = "Only generate graphs of the most important data"

            raw_llm_output = raw_chain.invoke({
                "documents": documents_content,
                "current_section": current_section_title,
                "current_section_content": current_section_content,
                "tabular_data": tabular_data,
                "graph_instructions": graph_instructions
            })
            print(f"--- Debug: Type of raw_llm_output: {type(raw_llm_output)} ---")
            # print(f"--- Debug: Raw LLM Output: {raw_llm_output} ---")
            # print(f"--- Debug: Type of raw_llm_output.content: {type(raw_llm_output.content)} ---")
            
            try:
                graph_specs = self.parser.parse(raw_llm_output.content) # Parse the raw output, expecting a list
                print(f"--- Debug: Type of graph_specs: {type(graph_specs)} ---")
                # print(f"--- Graph specs generated for '{current_section_title}': {graph_specs} ---")
                
                # Return the list of graph_specs and ensure other relevant state variables are passed through
                return {
                    "graph_specs": graph_specs, # Changed to graph_specs (plural)
                }
            except Exception as parse_error:
                print(f"--- Error parsing LLM output for graph generation: {parse_error} ---")
                print(f"--- Raw LLM output that caused parsing error: {raw_llm_output.content} ---")
                import traceback
                traceback.print_exc() # Print full traceback for parsing error
                return {
                    "graph_specs": [], # Return empty list if parsing fails
                }
 
        except Exception as e:
            print(f"--- General error generating graph for section '{current_section_title}': {e} ---")
            import traceback
            traceback.print_exc() # Print full traceback for general errors
            return {
                "graph_specs": [], # Return empty list if a general error occurs
                "current_section_content": current_section_content,
                "tabular_data": tabular_data
            }