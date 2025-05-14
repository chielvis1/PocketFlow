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

def create_tutorial_generator_flow():
    """
    Create a flow for generating a tutorial from a repository.
    
    Returns:
        Flow: The configured tutorial generator flow
    """
    # Create nodes
    fetch_repo = FetchRepo()
    identify_abstractions = IdentifyAbstractions()
    analyze_relationships = AnalyzeRelationships()
    order_chapters = OrderChapters()
    write_chapters = WriteChapters()
    combine_tutorial = CombineTutorial()
    
    # Connect nodes with error handling
    fetch_repo - "default" >> identify_abstractions
    fetch_repo - "error" >> AnalysisErrorNode()
    
    identify_abstractions - "default" >> analyze_relationships
    identify_abstractions - "error" >> AnalysisErrorNode()
    
    analyze_relationships - "default" >> order_chapters
    analyze_relationships - "error" >> AnalysisErrorNode()
    
    order_chapters - "default" >> write_chapters
    order_chapters - "error" >> AnalysisErrorNode()
    
    write_chapters - "default" >> combine_tutorial
    write_chapters - "error" >> AnalysisErrorNode()
    
    # Create and return flow
    return Flow(start=fetch_repo) 