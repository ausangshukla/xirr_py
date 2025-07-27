from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.messages import BaseMessage
from pydantic.v1 import BaseModel, Field
from ..graphs.state import AgentState # Assuming AgentState is in src/state.py
import json # Added for json.dumps
class SubSection(BaseModel):
    title: str = Field(description="The title of the sub-section.")
    content: str = Field(description="The content of the sub-section.")

class RewrittenSection(BaseModel):
    sub_sections: List[SubSection] = Field(description="A list of rewritten sub-sections within the main section.")

class WriterNode:
    """
    The WriterNode is responsible for rewriting a section based on the critique
    from the ReviewerNode. It uses suggested search terms to find more information
    in the documents and generates an improved version of the section.
    """
    def __init__(self, llm):
        """
        Initializes the WriterNode with a language model.

        Args:
            llm: An instance of a LangChain-compatible language model.
        """
        self.llm = llm
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert financial report writer. Your task is to
             rewrite the provided section of a portfolio analysis report based on the
             given critique and any new information found from targeted searches.
 
             Critique:
             {critique}
 
             Original Section Sub-sections (JSON format):
             {original_sub_sections}
 
             New Information from Targeted Search (if any):
             {new_information}
 
             Integrate the new information, address the critique points (expand on, remove/rephrase),
             and produce a significantly improved version of the section.
             Ensure to update references if new information is used.
 
             Output your response as a JSON object with one key:
             'sub_sections': A list of sub-section objects, each with a 'title' and 'content' key.
             Your output MUST be ONLY the JSON object, with no markdown.
             Example:
             {{"sub_sections": [{{"title": "Introduction", "content": "..."}}, {{"title": "Analysis", "content": "..."}}]}}
             """),
            ("user", "Section Title: {section_title}\n{section_instruction}")
        ])
        self.parser = JsonOutputParser()
        self.chain = self.prompt | self.llm
 
    def rewrite(self, state: AgentState) -> Dict[str, Any]:
        """
        Rewrites the current section's content based on critique and new information.

        Args:
            state (AgentState): The current state of the agent.

        Returns:
            Dict[str, Any]: A dictionary containing the updated state with the
                            rewritten section content and references.
        """

        current_section_title = state.get("current_section")
        current_section_instruction = state.get("current_section_instruction", "")
        critique = state.get("critique")
        documents = state.get("documents")
        original_content = state.get("current_section_content", "") # Get content from current_section_content
        original_references = state.get("current_section_references", []) # Get references from current_section_references
        current_section_sub_sections = state.get("current_section_sub_sections", [])

        if not current_section_title:
            raise ValueError("No current section specified in the agent state.")
        if not critique:
            print(f"WriterNode: No critique available for section '{current_section_title}'. Skipping rewrite.")
            return {
                "messages": state.get("messages", []) + [
                    BaseMessage(content=f"WriterNode: No critique for '{current_section_title}'. Skipping rewrite.", type="info")
                ]
            }
 
        # If there are no sub-sections, use the original_content string
        if not current_section_sub_sections:
            if not original_content:
                print(f"WriterNode: No original content found for section '{current_section_title}'. Cannot rewrite.")
                return {
                    "messages": state.get("messages", []) + [
                        BaseMessage(content=f"WriterNode: No original content for '{current_section_title}'. Cannot rewrite.", type="error")
                    ]
                }
            original_sub_sections_json = json.dumps([{"title": "Content", "content": original_content}])
        else:
            # Convert Pydantic objects to dictionaries before dumping to JSON
            original_sub_sections_json = json.dumps(current_section_sub_sections)
 
        print(f"--- WriterNode: Rewriting section '{current_section_title}' (Loop: {state.get('loop_count')}) ---")
 
        # Simulate targeted search based on critique's search terms
        # In a real implementation, this would involve a more sophisticated RAG approach
        new_information = self._perform_targeted_search(documents, critique.get("search_terms", []))
        if new_information != "No new information found for search terms.":
            print(f"WriterNode: New information found for '{current_section_title}'.")
 
        try:
            rewrite_input = {
                "section_title": current_section_title,
                "critique": critique,
                "original_sub_sections": original_sub_sections_json, # Pass structured sub-sections
                "new_information": new_information,
                "section_instruction": current_section_instruction
            }
            raw_llm_output = self.llm.invoke(self.prompt.format_messages(**rewrite_input))
            
            # Clean the raw LLM output by removing markdown code block delimiters
            cleaned_output = raw_llm_output.content.strip()
            if cleaned_output.startswith("```json") and cleaned_output.endswith("```"):
                cleaned_output = cleaned_output[len("```json"): -len("```")].strip()
            elif cleaned_output.startswith("```") and cleaned_output.endswith("```"):
                cleaned_output = cleaned_output[len("```"): -len("```")].strip()
 
            parsed_dict = self.parser.parse(cleaned_output)
 
            # Manually create the Pydantic object for validation
            try:
                rewrite_result = RewrittenSection(**parsed_dict)
            except Exception as pydantic_error:
                print(f"WriterNode: Pydantic validation failed for '{current_section_title}': {pydantic_error}")
                raise
            
            rewritten_sub_sections = rewrite_result.sub_sections
            print(f"WriterNode: Generated rewritten_sub_sections for '{current_section_title}': {rewritten_sub_sections}") # Debug print
            
            # Fallback: If LLM returns empty sub_sections, create a default one from original content
            if not rewritten_sub_sections and original_content:
                print(f"WriterNode: LLM returned empty sub_sections. Creating fallback sub-section from original content for '{current_section_title}'.")
                rewritten_sub_sections = [{"title": "Content", "content": original_content}]
            elif not rewritten_sub_sections:
                print(f"WriterNode: LLM returned empty sub_sections and no original content. Defaulting to empty list for '{current_section_title}'.")
                rewritten_sub_sections = [] # Ensure it's an empty list if no content at all
 
            # Format sub_sections into a single markdown content string for the reviewer
            # This is for the 'content' field in the state, which is used for review.
            # The structured sub_sections are stored in 'current_section_sub_sections'.
            markdown_content_for_review = ""
            for sub_section in rewritten_sub_sections:
                markdown_content_for_review += f"### {sub_section.title}\n{sub_section.content}\n\n"
 
            updated_references = [] # References are no longer generated by the writer
 
            # Update the specific section in completed_sections
            # Update the state, including incrementing loop_count
            return {
                "current_section_content": markdown_content_for_review, # Update current_section_content with markdown
                "current_section_sub_sections": [s.dict() for s in rewritten_sub_sections], # Store structured sub-sections as dictionaries
                "current_section_references": updated_references, # Store references separately
                "key_highlights": critique.get("key_highlights", []), # Pass key_highlights from critique
                "loop_count": state.get("loop_count", 0) + 1, # Increment loop_count here
                "messages": state.get("messages", []) + [
                    BaseMessage(content=f"WriterNode: Section '{current_section_title}' rewritten.", type="tool_output")
                ]
            }
        except Exception as e:
            error_message = f"WriterNode: Error during rewrite for '{current_section_title}': {e}"
            print(error_message)
            return {
                "messages": state.get("messages", []) + [
                    BaseMessage(content=error_message, type="error")
                ]
            }
 
    def _perform_targeted_search(self, documents: List[Dict[str, Any]], search_terms: List[str]) -> str:
        """
        Simulates a targeted search within documents based on search terms.
        In a real application, this would be a sophisticated RAG operation.
        """
        if not search_terms:
            return "No specific search terms provided."
 
        found_info = []
        for term in search_terms:
            for doc in documents:
                content = doc.get("content", "")
                filename = doc.get("filename", "Unknown")
                # Simple keyword search for demonstration
                if term.lower() in content.lower():
                    # In a real scenario, you'd extract relevant snippets, not whole content
                    found_info.append(f"Found '{term}' in {filename}:\n{content[:200]}...") # Snippet
        return "\n".join(found_info) if found_info else "No new information found for search terms."
 
