from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage # Added SystemMessage for context caching
from langchain_google_genai import ChatGoogleGenerativeAI # Using Gemini
from .state import AgentState
from ..agents.extractor import ExtractorNode
from ..agents.table_generator import TableGeneratorNode
from ..agents.graph_generator import GraphGeneratorNode
from ..agents.reviewer import ReviewerNode
from ..agents.writer import WriterNode
from ..tools.document_loader import load_documents_from_folder

class PortfolioAnalysisGraph:
    """
    Defines the LangGraph state machine for the portfolio analysis agent.
    Orchestrates the Extractor, Reviewer, and Writer nodes in an iterative loop.
    """
    def __init__(self, max_review_loops: int = 0):
        """
        Initializes the PortfolioAnalysisGraph with configuration.
        The LLM will be initialized within run_analysis to support context caching.

        Args:
            max_review_loops (int): The maximum number of times a section can be reviewed and rewritten.
        """
        self.max_review_loops = max_review_loops
        # Nodes will be initialized in run_analysis with the cached LLM
        self.extractor_node = None
        self.reviewer_node = None
        self.writer_node = None
        self.table_generator_node = None
        self.graph_generator_node = None
        self.graph = None # Graph will be built after LLM is ready

    def _build_graph(self):
        """
        Builds the LangGraph state machine. This method is now called
        within run_analysis after the LLM and nodes are initialized.
        """
        # Initialize the StateGraph with the AgentState schema.
        # This defines the structure of the data that will be passed between nodes.
        workflow = StateGraph(AgentState)

        # Add nodes to the graph. Each node represents a step in our agent's workflow.
        # "extractor": Uses the ExtractorNode to perform initial data extraction.
        workflow.add_node("extractor", self.extractor_node.extract)
        # "reviewer": Uses the ReviewerNode to critique the extracted content.
        workflow.add_node("reviewer", self.reviewer_node.review)
        # "writer": Uses the WriterNode to rewrite content based on critique.
        workflow.add_node("writer", self.writer_node.rewrite)
        # "table_graph_router": A router node to decide between table/graph generation.
        workflow.add_node("table_graph_router", self._table_graph_router_node) # Use a dedicated method
        # "table_generator": Generates tabular data for the section.
        workflow.add_node("table_generator", self.table_generator_node.generate_table)
        # "graph_generator": Generates graph specifications for the section.
        workflow.add_node("graph_generator", self.graph_generator_node.generate_graph)

        # Set the starting point of the graph.
        # The workflow will always begin by calling the "extractor" node.
        workflow.set_entry_point("extractor")

        # Define the edges (transitions) between nodes.
        # Conditional edges allow the graph to choose the next node based on the state.

        # After the "extractor" node runs, call the `_decide_next_step_after_extraction` function.
        # This function will return a string ("review" or "next_section") which determines the next node.
        workflow.add_conditional_edges(
            "extractor",
            self._decide_next_step_after_extraction,
            {
                # If the decider returns "review", transition to the "reviewer" node.
                "review": "reviewer",
                # If the decider returns "next_section", the current section's processing ends (END).
                "next_section": END
            }
        )

        # After the "reviewer" node runs, call the `_decide_next_step_after_review` function.
        # This function will return a string ("rewrite" or "next_section").
        workflow.add_conditional_edges(
            "reviewer",
            self._decide_next_step_after_review,
            {
                "rewrite": "writer",
                "generate_table_or_graph": "table_graph_router", # Transition to the new router node
                END: END
            }
        )

        workflow.add_conditional_edges(
            "writer",
            self._decide_next_step_after_writer,
            {
                "review": "reviewer",
                "generate_table_or_graph": "table_graph_router", # Transition to the new router node
                END: END
            }
        )

        # After table_graph_router, decide whether to generate tables, graphs or end
        workflow.add_conditional_edges(
            "table_graph_router",
            self._decide_table_or_graph_generation, # This function is now the decider for this edge
            {
                "table_generator": "table_generator",
                "graph_generator": "graph_generator",
                END: END
            }
        )

        # After table generation, decide whether to generate graphs or end
        workflow.add_conditional_edges(
            "table_generator",
            self._decide_after_table_generation,
            {
                "graph_generator": "graph_generator",
                END: END # Directly use END
            }
        )

        # After graph generation, the section ends
        workflow.add_edge("graph_generator", END)

        # Compile the workflow into a runnable LangGraph.
        # This prepares the graph for execution.
        return workflow.compile()

    def _table_graph_router_node(self, state: AgentState) -> Dict[str, Any]:
        """
        A router node that simply passes the state through.
        Its purpose is to act as a point for conditional edges.
        """
        print(f"--- Router: Entering table_graph_router for section '{state.get('current_section')}' ---")
        return state # Return the current state to ensure it's always a dictionary

    def _decide_next_step_after_extraction(self, state: AgentState) -> str:
        """
        Decider function: Determines the next step after the ExtractorNode has completed its run.
        In this design, after the initial extraction, we always proceed to the ReviewerNode
        to get feedback on the first draft.
        """
        print(f"--- Decider: After ExtractorNode for section '{state.get('current_section')}' ---")
        return "review" # Always go to review after extraction

    def _decide_next_step_after_review(self, state: AgentState) -> str:
        """
        Decider function: Determines the next step after the ReviewerNode has provided its critique.
        It checks if there's a valid critique (i.e., something to expand on or rephrase)
        and if the maximum number of review loops for the current section has not been reached.
        If both conditions are met, it transitions to the WriterNode for refinement.
        Otherwise, it signals that the current section is complete and moves to the next section.
        """
        print(f"--- Decider: After ReviewerNode for section '{state.get('current_section')}' ---")
        critique = state.get("critique")
        loop_count = state.get("loop_count", 0)
        # print(f"Decider: Critique content after ReviewerNode: {critique}") # Debug print
 
        if critique and (critique.get("expand_on") or critique.get("remove_or_rephrase")) and loop_count < self.max_review_loops:
            print(f"--- Decider: Critique present for '{state.get('current_section')}'. Loops remaining ({loop_count}/{self.max_review_loops}). Proceeding to rewrite.")
            return "rewrite"
        else:
            print(f"Decider: No actionable critique or max loops reached for '{state.get('current_section')}' ({loop_count}/{self.max_review_loops}). Proceeding to decide table/graph generation.")
            return "generate_table_or_graph"

    def _decide_next_step_after_writer(self, state: AgentState) -> str:
        """
        Decider function: Determines the next step after the WriterNode has rewritten a section.
        It increments the `loop_count` for the current section.
        If the `loop_count` is still below the `max_review_loops`, it transitions back to the
        ReviewerNode for another round of critique and refinement.
        Otherwise, it signals that the current section has undergone enough review cycles
        and moves to the next section.
        """
        print(f"--- Decider: After WriterNode for section '{state.get('current_section')}' ---")
        loop_count = state.get("loop_count", 0)
        # print(f"Decider: Sub-sections after WriterNode: {state.get('current_section_sub_sections', [])}") # Debug print
 
        # After writing, if there's still a need for review (e.g., max loops not reached), go back to reviewer.
        # Otherwise, proceed to table generation.
        if loop_count < self.max_review_loops:
            print(f"Decider: Loops remaining for '{state.get('current_section')}' ({loop_count}/{self.max_review_loops}). Proceeding to re-review.")
            return "review"
        else:
            print(f"Decider: Max loops reached for '{state.get('current_section')}' ({loop_count}/{self.max_review_loops}). Proceeding to decide table/graph generation.")
            return "generate_table_or_graph" # New transition to table/graph generation decider

    def _decide_table_or_graph_generation(self, state: AgentState) -> str:
        """
        Decider function: Determines whether to generate a table, a graph, or end the section.
        This is called after the review/writer loop is complete.
        """
        print(f"--- Decider: Deciding table/graph generation for section '{state.get('current_section')}' ---")
        include_table = state.get("include_table", False)
        include_graphs = state.get("include_graphs", False)

        if include_table:
            print(f"Decider: 'include_table' is True. Proceeding to table generation for '{state.get('current_section')}'.")
            return "table_generator"
        elif include_graphs:
            print(f"Decider: 'include_graphs' is True. Proceeding to graph generation for '{state.get('current_section')}'.")
            return "graph_generator"
        else:
            print(f"Decider: Neither table nor graph generation requested for '{state.get('current_section')}'. Ending section.")
            return END

    def _decide_after_table_generation(self, state: AgentState) -> str:
        """
        Decider function: Determines whether to generate a graph after table generation, or end the section.
        """
        print(f"--- Decider: After table generation for section '{state.get('current_section')}' ---")
        include_graphs = state.get("include_graphs", False)

        if include_graphs:
            print(f"Decider: 'include_graphs' is True. Proceeding to graph generation for '{state.get('current_section')}'.")
            return "graph_generator"
        else:
            print(f"Decider: 'include_graphs' is False. Ending section after table generation for '{state.get('current_section')}'.")
            return END

    def run_analysis(self, llm: Any, loaded_docs: List[Dict[str, Any]], sections: List[Dict[str, Any]]):
        """
        Executes the entire portfolio analysis process using the defined LangGraph.
        It initializes the agent state with pre-loaded documents, and then iteratively processes
        each specified section through the Extractor, Reviewer, and Writer nodes.

        Args:
            loaded_docs (List[Dict[str, Any]]): A list of pre-loaded documents, each with 'filename', 'content', and 'metadata'.
            sections (List[Dict[str, str]]): A list of dictionaries, where each dictionary contains
                                            'title' (the section title) and 'instruction' (additional LLM instruction).

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, where each dictionary represents
                                  a fully processed and refined section of the analysis.
                                  Each section includes its content and references.
        """
        if not loaded_docs:
            print("No documents provided. Exiting analysis.")
            return []

        # Initialize agent nodes with the provided LLM
        self.extractor_node = ExtractorNode(llm)
        self.reviewer_node = ReviewerNode(llm)
        self.writer_node = WriterNode(llm)
        self.table_generator_node = TableGeneratorNode(llm)
        self.graph_generator_node = GraphGeneratorNode(llm)
        
        # Build the graph now that nodes are initialized
        self.graph = self._build_graph()
        print("--- LangGraph built with cached LLM ---")

        # Initialize the overall state for the agent.
        initial_state: AgentState = {
            "documents": loaded_docs, # All loaded documents available to all nodes.
            "sections_to_process": sections, # List of sections to iterate through.
            "completed_sections": [], # Accumulates the final versions of processed sections.
            "current_section": None, # The section name currently being worked on by the graph.
            "current_section_instruction": None, # The instruction for the current section.
            "include_table": False, # Whether to include a table for the current section.
            "table_instructions": "", # Instructions for table generation.
            "include_graphs": False, # Whether to include graphs for the current section.
            "graph_instructions": "", # Instructions for graph generation.
            "loop_count": 0, # Tracks review iterations for the current section.
            "critique": None, # Stores feedback from the reviewer for the writer.
            "key_highlights": [], # Initialize key_highlights
            "current_section_sub_sections": [], # New: Initialize sub_sections
            "tabular_data": None, # Stores generated tabular data for the current section.
            "graph_specs": [], # Stores generated graph specifications for the current section (now a list).
            "messages": [BaseMessage(content="Analysis started.", type="info")] # Log of agent's actions.
        }

        # Iterate through each section defined in `sections_to_analyze`.
        for section_info in sections:
            section_name = section_info.get("name", "Untitled Section")
            section_instructions = section_info.get("section_instructions", "")
            include_table = section_info.get("include_table", False)
            table_instructions = section_info.get("table_instructions", "")
            include_graphs = section_info.get("include_graphs", False)
            graph_instructions = section_info.get("graph_instructions", "")

            print(f"\n--- Starting analysis for section: '{section_name}' with instruction: '{section_instructions}' ---")
            # Create a copy of the initial state for the current section's processing.
            current_section_state = initial_state.copy()
            current_section_state["current_section"] = section_name
            current_section_state["current_section_instruction"] = section_instructions
            current_section_state["include_table"] = include_table
            current_section_state["table_instructions"] = table_instructions
            current_section_state["include_graphs"] = include_graphs
            current_section_state["graph_instructions"] = graph_instructions
            current_section_state["critique"] = None # Reset critique for each new section.
            current_section_state["key_highlights"] = [] # Reset key_highlights for each new section.
            current_section_state["loop_count"] = 0 # Reset loop count for each new section.

            # Run the graph for the current section
            final_state_after_stream = None
            for i, s in enumerate(self.graph.stream(current_section_state)):
                # print(f"--- Debug: Stream yielded 's' at step {i} for '{section_name}': {s} ---")
                # LangGraph stream yields a dictionary where the key is the node name
                # and the value is the state update from that node.
                # We need to unwrap this to get the actual state update.
                node_output = list(s.values())[0]
                current_section_state.update(node_output)
                # It's crucial to ensure final_state_after_stream is updated with the latest state
                final_state_after_stream = current_section_state.copy() # Create a copy to avoid reference issues
                # print(f"--- Debug: State after stream step {i} for '{section_name}': {current_section_state} ---")
 
            print(f"--- Debug: Final state after stream for '{section_name}': {final_state_after_stream} ---")
            print(f"--- Debug: current_section_content in final state: {final_state_after_stream.get('current_section_content', '')[:500]}... ---")
            # print(f"--- Debug: current_section_sub_sections in final state: {final_state_after_stream.get('current_section_sub_sections', [])} ---")

            # After the graph for a single section completes (reaches END),
            # consolidate all relevant data for the current section and add it to completed_sections.
            finalized_section = {
                "name": section_name,
                "section_instructions": section_instructions, # Include the instruction in the finalized report
                "content": final_state_after_stream.get("current_section_content", ""),
                "sub_sections": final_state_after_stream.get("current_section_sub_sections", []),
                "references": final_state_after_stream.get("current_section_references", []),
                "key_highlights": final_state_after_stream.get("key_highlights", []), # Add key_highlights to the final section
                "include_table": include_table,
                "table_instructions": table_instructions,
                "tabular_data": final_state_after_stream.get("tabular_data", None),
                "include_graphs": include_graphs,
                "graph_instructions": graph_instructions,
                "graph_specs": final_state_after_stream.get("graph_specs", [])
            }
            
            print(f"--- Finalized section '{section_name}' ---")
            yield finalized_section
            
            # Update the overall `initial_state` with the finalized section.
            # This is crucial for subsequent sections to have access to previously
            # completed sections if needed for context.
            initial_state["completed_sections"].append(finalized_section)
 
        print("\n--- Portfolio Analysis Completed ---")

