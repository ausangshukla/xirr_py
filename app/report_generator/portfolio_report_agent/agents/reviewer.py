from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.messages import BaseMessage
from ..graphs.state import AgentState # Assuming AgentState is in src/state.py

class ReviewerNode:
    """
    The ReviewerNode is responsible for critiquing the content of a generated section.
    It provides feedback on what to expand, what to remove, and suggests search terms
    for further refinement by the WriterNode.
    """
    def __init__(self, llm):
        """
        Initializes the ReviewerNode with a language model.

        Args:
            llm: An instance of a LangChain-compatible language model.
        """
        self.llm = llm
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert editor and financial analyst. Your task is to
             critique the provided section of a portfolio analysis report based *only* on the information present in the 'Section Content'.
             Provide constructive feedback to improve its clarity, conciseness, and structure.
             Do NOT ask for information that is not present in the 'Section Content'.
             Ensure that the content for 'expand_on', 'remove_or_rephrase', and 'search_terms' fields does NOT contain any markdown formatting (e.g., bold, italics, bullet points).
 
              Your critique should include:
              1.  **key_highlights**: A list of 3 concise, high-level summaries of the most important information or conclusions from the 'Section Content'.
              2.  **expand_on**: A list of specific topics or areas that need more detail or elaboration.
              3.  **remove_or_rephrase**: A list of sentences or ideas that should be removed,
                  condensed, or rephrased for clarity or conciseness.
              4.  **search_terms**: A list of up to 5 keywords or phrases that can be used to search
                  the original documents for more relevant information to address the 'expand_on' points.
 
              Output your response as a JSON object with these three keys.
              Example:
              {{
                  "key_highlights": ["Company showed strong growth in Q1", "New product launch was successful"],
                  "expand_on": ["company's market share", "recent financial performance"],
                  "remove_or_rephrase": ["The company is good."],
                  "search_terms": ["market share 2023", "Q4 2023 earnings"]
              }}
              
             """),
            ("user", "Section Title: {section_title}\n\nSection Content:\n{section_content}\n{section_instruction}")
        ])
        self.parser = JsonOutputParser()
        self.chain = self.prompt | self.llm | self.parser

    def review(self, state: AgentState) -> Dict[str, Any]:
        """
        Reviews the current section's content and generates a critique.

        Args:
            state (AgentState): The current state of the agent.

        Returns:
            Dict[str, Any]: A dictionary containing the updated state with the critique.
        """
        current_section_title = state.get("current_section")
        current_section_instruction = state.get("current_section_instruction", "")
        current_section_content = state.get("current_section_content", "") # Get content directly from state
        current_section_references = state.get("current_section_references", []) # Get references directly from state

        if not current_section_title or not current_section_content:
            print(f"ReviewerNode: No content found for section '{current_section_title}' to review. Skipping review.")
            return {
                "messages": state.get("messages", []) + [
                    BaseMessage(content=f"ReviewerNode: No content to review for '{current_section_title}'.", type="info")
                ],
                "critique": None # Ensure critique is reset or remains None if no content
            }

        print(f"--- ReviewerNode: Reviewing section '{current_section_title}' (Loop: {state.get('loop_count')}) ---")

        try:
            review_input = {
                "section_title": current_section_title,
                "section_content": current_section_content,
                "section_instruction": current_section_instruction
            }
            critique_result = self.chain.invoke(review_input)

            # Ensure the output matches the expected JSON structure
            critique = {
                "key_highlights": critique_result.get("key_highlights", []),
                "expand_on": critique_result.get("expand_on", []),
                "remove_or_rephrase": critique_result.get("remove_or_rephrase", []),
                "search_terms": critique_result.get("search_terms", [])
            }

            # Update the state with the critique, key highlights, and pass through content/references
            return {
                "critique": critique,
                "key_highlights": critique_result.get("key_highlights", []), # Add key_highlights to the state
                "current_section_content": current_section_content, # Preserve content
                "messages": state.get("messages", []) + [
                    BaseMessage(content=f"ReviewerNode: Critique for '{current_section_title}' generated.", type="tool_output")
                ]
            }
        except Exception as e:
            error_message = f"ReviewerNode: Error during review for '{current_section_title}': {e}"
            print(error_message)
            return {
                "messages": state.get("messages", []) + [
                    BaseMessage(content=error_message, type="error")
                ],
                "critique": None # Ensure critique is None on error
            }

