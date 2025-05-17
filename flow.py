"""
Flow definitions for GitHub Repository Analysis and Tutorial Generation.

This file defines flows for analyzing GitHub repositories and generating tutorials.
"""

from pocketflow import Flow

from nodes import (
    # Nodes for repository analysis (existing)
    ParseRepositoryURLNode, AnalyzeRepositoryNode, 
    AnalyzeWithLLMNode, AnalysisErrorNode,
    
    # Nodes for tutorial generation (added/adapted)
    FetchRepo, IdentifyAbstractions, AnalyzeRelationships, 
    OrderChapters, WriteChapters, CombineTutorial,
    GenerateMCPServerNode,
    TutorialErrorHandler, # Added Error Handler
    StartMCPServerNode # Dynamically serve MCP
)

def create_repo_analyzer_flow():
    """
    Create a flow for repository analysis. (Existing flow)
    
    Returns:
        Flow: The configured repository analyzer flow
    """
    # Create nodes
    parse_url_node = ParseRepositoryURLNode()
    analyze_repo_node = AnalyzeRepositoryNode()
    analyze_with_llm_node = AnalyzeWithLLMNode()
    analysis_error_node = AnalysisErrorNode() # General error handler for this flow
    
    # Connect nodes
    parse_url_node >> analyze_repo_node # Default transition
    # Conditional transitions based on outcome string from node's post method
    parse_url_node - "error" >> analysis_error_node 

    analyze_repo_node >> analyze_with_llm_node # Default transition
    analyze_repo_node - "analysis_error" >> analysis_error_node # Specific error from analysis
    analyze_repo_node - "error" >> analysis_error_node # More general error from analysis node

    analyze_with_llm_node - "error" >> analysis_error_node # Error from LLM analysis

    # Create and return flow
    # The flow ends implicitly when a node has no further default or matched conditional transition.
    # analysis_error_node is a terminal node for error paths in this simple setup.
    return Flow(start=parse_url_node)

def create_tutorial_flow():
    """
    Create and return the tutorial generation flow.
    (Adapted from the second set to use first set's conventions and error handling)
    """
    # Instantiate nodes for tutorial generation
    fetch_repo_node = FetchRepo()
    identify_abstractions_node = IdentifyAbstractions(max_retries=3, wait=10) # Example retry config
    analyze_relationships_node = AnalyzeRelationships(max_retries=3, wait=10)
    order_chapters_node = OrderChapters(max_retries=3, wait=10)
    write_chapters_node = WriteChapters(max_retries=2, wait=15) # Regular Node, not BatchNode
    combine_tutorial_node = CombineTutorial()
    
    # Instantiate the error handler node
    error_handler_node = TutorialErrorHandler()

    # Connect nodes in the main sequence (default transitions)
    fetch_repo_node >> identify_abstractions_node
    identify_abstractions_node >> analyze_relationships_node
    analyze_relationships_node >> order_chapters_node
    order_chapters_node >> write_chapters_node
    write_chapters_node >> combine_tutorial_node

    # After combining tutorial, generate MCP server specification and code
    generate_mcp_server_node = GenerateMCPServerNode()
    combine_tutorial_node >> generate_mcp_server_node
    # Then start the dynamic MCP server
    start_mcp_server_node = StartMCPServerNode()
    generate_mcp_server_node >> start_mcp_server_node

    # Define error transitions from each main sequence node to the error handler
    fetch_repo_node - "error" >> error_handler_node
    identify_abstractions_node - "error" >> error_handler_node
    analyze_relationships_node - "error" >> error_handler_node
    order_chapters_node - "error" >> error_handler_node
    write_chapters_node - "error" >> error_handler_node
    combine_tutorial_node - "error" >> error_handler_node # Errors during final combination
    generate_mcp_server_node - "error" >> error_handler_node # Handle MCP generation errors
    start_mcp_server_node - "error" >> error_handler_node # Handle server start errors

    # Define retry transitions from the error handler back to the respective nodes
    # The string returned by error_handler_node.post() (e.g., "retry_fetch") must match these conditions.
    error_handler_node - "retry_fetch" >> fetch_repo_node
    error_handler_node - "retry_abstractions" >> identify_abstractions_node
    error_handler_node - "retry_relationships" >> analyze_relationships_node
    error_handler_node - "retry_chapters" >> order_chapters_node # Assuming OrderChapters can be retried
    error_handler_node - "retry_write" >> write_chapters_node
    # Usually don't retry start_mcp; errors are fatal

    # Create the flow, starting with the FetchRepo node
    tutorial_flow = Flow(start=fetch_repo_node)

    return tutorial_flow

# Backward compatibility alias if used elsewhere (from first set)
create_tutorial_generator_flow = create_tutorial_flow
