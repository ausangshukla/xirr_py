from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.messages import BaseMessage
from pydantic.v1 import BaseModel, Field
from ..graphs.state import AgentState # Assuming AgentState is in src/state.py
import pdb;

class SubSection(BaseModel):
    title: str = Field(description="The title of the sub-section.")
    content: str = Field(description="The content of the sub-section.")

class ExtractedSection(BaseModel):
    sub_sections: List[SubSection] = Field(description="A list of sub-sections within the main section.")

class ExtractorNode:
    """
    The ExtractorNode is responsible for performing an initial extraction of information
    for a given section from the loaded documents. It generates a first draft of the
    section content and identifies relevant references.
    """
    def __init__(self, llm):
        """
        Initializes the ExtractorNode with a language model.

        Args:
            llm: An instance of a LangChain-compatible language model.
        """
        self.llm = llm
        self.parser = JsonOutputParser()
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert financial analyst. Your task is to extract relevant information from the provided documents to create a draft for the "{section_title}" section of a portfolio analysis report.

            Focus on extracting factual information and key insights from the documents.
            You must structure your output as a JSON object with a single key: "sub_sections".
            The value of "sub_sections" must be a list of JSON objects, where each object represents a sub-section and has two keys: "title" and "content".
            The 'content' field MUST NOT contain any markdown formatting (e.g., ###, **, -, *, `). It should be plain text.

            Analyze the documents provided and identify distinct topics or points that can be presented as sub-sections. For each sub-section, create a concise title and write the corresponding content based on the information in the documents.

            If you cannot find any relevant information for the section, or if the documents are empty, return a JSON with an empty list for "sub_sections". Do not add any explanatory text outside of the JSON structure. Do not add markdown to the json output.

            Example of desired output:
            {{
            "sub_sections": [
                {{
                "title": "Example Sub-Section Title 1",
                "content": "This is the extracted content for the first sub-section without markdown."
                }},
                {{
                "title": "Example Sub-Section Title 2",
                "content": "This is the extracted content for the second sub-section without markdown."
                }}
            ]
            }}

            Here are the formatting instructions:
            {format_instructions}
            """),
            ("user", "Documents:\n{documents}\n\nSection Title: {section_title}\n{section_instruction}")
        ])
        self.chain = self.prompt | self.llm
 
    def extract(self, state: AgentState) -> Dict[str, Any]:
        """
        Extracts information for the current section from the documents.
 
        Args:
            state (AgentState): The current state of the agent.
 
        Returns:
            Dict[str, Any]: A dictionary containing the updated state with the
                            extracted section content and references.
        """
        current_section_title = state.get("current_section")
        current_section_instruction = state.get("current_section_instruction", "")
        documents = state.get("documents")
 
        if not current_section_title:
            raise ValueError("No current section title specified in the agent state.")
        if not documents:
            raise ValueError("No documents available in the agent state for extraction.")
 
        # Format documents for the prompt
        formatted_documents = "\n".join([
            f"--- Document: {doc.get('filename', 'N/A')} ---\n"
            f"{doc.get('content', 'Content not available')}"
            for doc in documents
        ])
 
        print(f"--- ExtractorNode: Extracting for section '{current_section_title}' ---")
        # Log first 500 chars of documents for brevity
        print(f"ExtractorNode: Input documents for '{current_section_title}':\n{formatted_documents[:1]}...")
 
        
        try:
            # 1. Create input for the LLM
            extraction_input = {
                "section_title": current_section_title,
                "documents": formatted_documents,
                "section_instruction": current_section_instruction,
                "format_instructions": self.parser.get_format_instructions()
            }
            print(f"ExtractorNode: Invoking LLM for section '{current_section_title}'.")

            # 2. Invoke the LLM
            prompt_messages = self.prompt.format_messages(**extraction_input)
            raw_llm_output = self.llm.invoke(prompt_messages)
            # print(f"ExtractorNode: Raw LLM output for '{current_section_title}':\n---\n{raw_llm_output.content[:1]}\n---")

            # 3. Clean the LLM output
            cleaned_output = raw_llm_output.content.strip()
            if cleaned_output.startswith("```json") and cleaned_output.endswith("```"):
                cleaned_output = cleaned_output[len("```json"):-len("```")].strip()
            elif cleaned_output.startswith("```") and cleaned_output.endswith("```"):
                cleaned_output = cleaned_output[len("```"):-len("```")].strip()
            # print(f"ExtractorNode: Cleaned LLM output for parsing:\n---\n{cleaned_output}\n---")

            # 4. Parse the cleaned output into a dictionary
            try:
                parsed_dict = self.parser.parse(cleaned_output)
            except Exception as parse_error:
                error_message = f"ExtractorNode: JSON parsing failed for '{current_section_title}'. Raw output: {cleaned_output}. Error: {parse_error}"
                print(error_message)
                raise ValueError(error_message)

            if parsed_dict is None:
                error_message = f"ExtractorNode: Parsed dictionary is None for '{current_section_title}'. Raw output: {cleaned_output}"
                print(error_message)
                raise ValueError(error_message)

            print(f"ExtractorNode: Parsed dictionary keys: {parsed_dict.keys()}")

            # 5. Manually create the Pydantic object for validation and structured access
            try:
                extraction_result = ExtractedSection(**parsed_dict)
            except Exception as pydantic_error:
                error_message = f"ExtractorNode: Pydantic validation failed for '{current_section_title}': {pydantic_error}. Parsed dict: {parsed_dict}"
                print(error_message)
                raise ValueError(error_message)

            print(f"ExtractorNode: Pydantic model created successfully for '{current_section_title}': {type(extraction_result)}")
            sub_sections = extraction_result.sub_sections
            print(f"ExtractorNode: Extracted {len(sub_sections)} sub-sections for '{current_section_title}'.")

            if not sub_sections:
                print(f"ExtractorNode: Warning - No sub-sections were extracted for '{current_section_title}'. The LLM returned an empty list.")

            references = [] # References are no longer generated by the extractor
 
            # Format sub_sections into a single content string for the reviewer
            formatted_content = ""
            for sub_section in sub_sections:
                formatted_content += f"### {sub_section.title}\n{sub_section.content}\n\n"
 
            # 6. Update the state
            return {
                "current_section_content": formatted_content, # Populate with formatted content for reviewer
                "current_section_sub_sections": [s.dict() for s in sub_sections], # Pass the structured sub_sections as dictionaries
                "current_section_references": references,
                "messages": state.get("messages", []) + [
                    BaseMessage(content=f"ExtractorNode: Initial draft for '{current_section_title}' created.", type="tool_output")
                ]
            }
        except Exception as e:
            error_message = f"ExtractorNode: Error during extraction for '{current_section_title}': {e}"
            print(error_message)
            # It's better to raise the exception to let the graph's error handling manage it.
            raise
