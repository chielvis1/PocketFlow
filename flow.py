"""
Flow definitions for GitHub Repository Analysis.

This file defines flows for analyzing GitHub repositories and generating tutorials.
"""

from pocketflow import Flow

from nodes import (
    # Nodes for repository analysis
    ParseRepositoryURLNode, AnalyzeRepositoryNode, 
    AnalyzeWithLLMNode, AnalysisErrorNode,
    
    # Nodes for tutorial generation
    FetchRepo, IdentifyAbstractions, AnalyzeRelationships, 
    OrderChapters, WriteChapters, CombineTutorial,
    TutorialErrorHandler
)

def create_repo_analyzer_flow():
    """
    Create a flow for repository analysis.
    
    Returns:
        Flow: The configured repository analyzer flow
    """
    # Create nodes
    parse_url_node = ParseRepositoryURLNode()
    analyze_repo_node = AnalyzeRepositoryNode()
    analyze_with_llm_node = AnalyzeWithLLMNode()
    analysis_error_node = AnalysisErrorNode()
    
    # Connect nodes
    parse_url_node >> analyze_repo_node
    analyze_repo_node - "default" >> analyze_with_llm_node
    analyze_repo_node - "analysis_error" >> analysis_error_node
    analyze_repo_node - "error" >> analysis_error_node
    
    # Create and return flow
    return Flow(start=parse_url_node)

def create_tutorial_flow():
    """
    Create and return the tutorial generation flow (1:1 match with mcp-pipeline reference).
    """
    # Create nodes
    fetch_repo = FetchRepo()
    identify_abstractions = IdentifyAbstractions(max_retries=5, wait=20)
    analyze_relationships = AnalyzeRelationships(max_retries=5, wait=20)
    order_chapters = OrderChapters(max_retries=5, wait=20)
    write_chapters = WriteChapters(max_retries=5, wait=20)
    combine_tutorial = CombineTutorial()
    error_handler = TutorialErrorHandler()

    # Connect nodes with default transitions
    fetch_repo - "default" >> identify_abstractions
    identify_abstractions - "default" >> analyze_relationships
    analyze_relationships - "default" >> order_chapters
    order_chapters - "default" >> write_chapters
    write_chapters - "default" >> combine_tutorial

    # Add error handling transitions
    fetch_repo - "error" >> error_handler
    identify_abstractions - "error" >> error_handler
    analyze_relationships - "error" >> error_handler
    order_chapters - "error" >> error_handler
    write_chapters - "error" >> error_handler
    combine_tutorial - "error" >> error_handler

    # Handle retry scenarios
    error_handler - "retry_fetch" >> fetch_repo
    error_handler - "retry_abstractions" >> identify_abstractions
    error_handler - "retry_relationships" >> analyze_relationships
    error_handler - "retry_chapters" >> order_chapters
    error_handler - "retry_write" >> write_chapters
    
    # The flow will end gracefully when the error handler returns "terminate"
    # No need to explicitly connect this action to any node

    return Flow(start=fetch_repo)

# Backward compatibility alias
create_tutorial_generator_flow = create_tutorial_flow 