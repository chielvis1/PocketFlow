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
    OrderChapters, WriteChapters, CombineTutorial
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
    fetch_repo = FetchRepo()
    identify_abstractions = IdentifyAbstractions(max_retries=5, wait=20)
    analyze_relationships = AnalyzeRelationships(max_retries=5, wait=20)
    order_chapters = OrderChapters(max_retries=5, wait=20)
    write_chapters = WriteChapters(max_retries=5, wait=20)
    combine_tutorial = CombineTutorial()

    fetch_repo >> identify_abstractions
    identify_abstractions >> analyze_relationships
    analyze_relationships >> order_chapters
    order_chapters >> write_chapters
    write_chapters >> combine_tutorial

    return Flow(start=fetch_repo)

# Backward compatibility alias
create_tutorial_generator_flow = create_tutorial_flow 