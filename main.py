"""
Main entry point for the Repository Analysis to MCP Server agent.

This script initializes the agent flow and runs it with the user's query.
"""

import argparse
import logging
import sys
import os

from pocketflow import Flow
from flow import create_repo_analyzer_flow, handle_user_selection
from utils.monitoring import configure_logging
from utils.data_processing import get_user_selection
from utils.llm import call_llm, setup_llm_provider

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Repository Analysis to MCP Server agent'
    )
    parser.add_argument(
        'query', nargs='?', type=str, default='',
        help='The initial query to start repository analysis'
    )
    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help='Enable verbose output'
    )
    parser.add_argument(
        '--provider', '-p', type=str, choices=['openai', 'anthropic', 'google', 'openrouter'],
        default='', help='The LLM provider to use'
    )
    parser.add_argument(
        '--model', '-m', type=str, default='',
        help='The specific LLM model to use (if empty, will prompt for selection)'
    )
    parser.add_argument(
        '--test-llm', '-t', action='store_true',
        help='Test the LLM connection and exit'
    )
    return parser.parse_args()

def get_user_query(args):
    """Get the user's query from arguments or prompt."""
    if args.query:
        return args.query
    
    print("Welcome to the Repository Analysis to MCP Server agent!")
    print("This tool helps you find GitHub repositories that match your requirements")
    print("and creates an MCP server with implementation guides.\n")
    
    query = input("Enter your query (e.g., 'authentication in Node.js with JWT'): ")
    return query

def run_agent(query, verbose=False, provider=None, model=None):
    """
    Run the repository analysis agent flow.
    
    Args:
        query: The user's initial query
        verbose: Whether to enable verbose logging
        provider: The LLM provider to use
        model: The specific model to use
    """
    # Configure logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logger = configure_logging(log_level)
    
    # Create the flow
    flow = create_repo_analyzer_flow()
    
    # Initialize shared data
    shared = {
        "user_query": query,
        "llm_config": {
            "provider": provider,
            "model": model
        }
    }
    
    logger.info(f"Starting agent with query: {query}")
    if provider:
        logger.info(f"Using LLM provider: {provider}, model: {model or 'user-selected'}")
    
    # First segment: analyze query and search for repositories
    start_flow = Flow(start=flow.start_node)
    result = start_flow.run(shared)
    
    # Check if clarification is needed
    if result == "default" and "clarification_prompt" in shared:
        print("\n" + shared["clarification_prompt"])
        clarified_query = input("Your response: ")
        shared["user_query"] = clarified_query
        
        # Restart from the beginning with the clarified query
        logger.info(f"Restarting with clarified query: {clarified_query}")
        return run_agent(clarified_query, verbose, provider, model)
    
    # Handle no repositories found
    if "error_message" in shared and not shared.get("repository_display"):
        print("\n" + shared["error_message"])
        if input("\nWould you like to try again with a different query? (y/n): ").lower() == 'y':
            query = input("Enter a new query: ")
            return run_agent(query, verbose, provider, model)
        else:
            print("Exiting.")
            return
    
    # Display repositories and get user selection
    if "repository_display" in shared:
        print("\n" + shared["repository_display"])
        
        # Get repository options from shared
        if "quality_repositories" in shared and shared["quality_repositories"]:
            repo_options = shared["quality_repositories"]
        else:
            repo_options = shared.get("repository_quality_data", [])
        
        if not repo_options:
            print("No repositories available for selection.")
            return
        
        # Get user selection
        selection_prompt = "Select a repository to analyze by number:"
        selected_repo = get_user_selection(selection_prompt, repo_options)
        
        # Handle selection
        if selected_repo:
            logger.info(f"Selected repository: {selected_repo.get('url', 'Unknown')}")
            shared["selected_repository"] = selected_repo
        else:
            print("Selection canceled. Exiting.")
            return
    
    # Second segment: analyze the selected repository
    analyze_flow = Flow(start=flow.start_node.successors.get("analyze_repo"))
    if analyze_flow.start_node:
        logger.info("Starting repository analysis")
        result = analyze_flow.run(shared)
        
        # Display completion message or error
        if "completion_message" in shared:
            print("\n" + shared["completion_message"])
        elif "error_message" in shared:
            print("\n" + shared["error_message"])
    else:
        logger.error("Could not initialize analysis flow")
        print("Error: Could not initialize analysis flow.")

def main():
    """Main entry point for the agent."""
    args = parse_args()
    
    # Test LLM connection if requested
    if args.test_llm:
        provider = args.provider
        model = args.model
        
        print("\nTesting LLM connection")
        
        # Use our dynamic LLM setup if provider or model not specified
        if not provider or not model:
            try:
                provider, api_key, model = setup_llm_provider()
                print(f"\nSelected provider: {provider}")
                print(f"Selected model: {model}")
            except Exception as e:
                print(f"\nError setting up LLM provider: {str(e)}")
                return
        
        # Test the LLM connection
        try:
            print("\nSending test prompt to the LLM...")
            response = call_llm(
                "Hello, world! Please respond with a short greeting.", 
                provider=provider, 
                model=model
            )
            print(f"\nResponse: {response}")
            print("\nLLM connection test completed successfully.")
        except Exception as e:
            print(f"\nError testing LLM connection: {str(e)}")
            if args.verbose:
                import traceback
                traceback.print_exc()
        
        return
    
    query = get_user_query(args)
    
    if not query:
        print("No query provided. Exiting.")
        return
    
    try:
        run_agent(query, args.verbose, args.provider, args.model)
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting.")
    except Exception as e:
        print(f"\nError: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main() 