"""
Main entry point for the Repository Analysis to MCP Server agent.

This script initializes the agent flow and runs it with the user's query.
"""

import argparse
import logging
import sys
import os

from pocketflow import Flow
from flow import create_repo_analyzer_flow, create_tutorial_generator_flow
from utils.monitoring import configure_logging
from utils.data_processing import get_user_selection
from utils.llm import call_llm, setup_llm_provider, setup_llm_provider_with_params
from utils.search import interactive_search
from utils.github import set_github_token, ensure_github_token
from nodes import AnalyzeRepositoryNode

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
        '-v', '--verbose', action='store_true',
        help='Enable verbose output'
    )
    parser.add_argument(
        '-i', '--interactive', action='store_true',
        help='Use interactive search mode'
    )
    parser.add_argument(
        '-p', '--provider', type=str, default=None,
        help='LLM provider to use'
    )
    parser.add_argument(
        '-m', '--model', type=str, default=None,
        help='Specific model to use'
    )
    parser.add_argument(
        '--no-youtube', action='store_true',
        help='Disable YouTube search'
    )
    parser.add_argument(
        '--no-web', action='store_true',
        help='Disable web search'
    )
    parser.add_argument(
        '--youtube-count', type=int, default=5,
        help='Number of YouTube videos to search'
    )
    parser.add_argument(
        '--web-count', type=int, default=10,
        help='Number of web pages to search'
    )
    
    # Add tutorial generation arguments
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Repository analysis command (default)
    analyze_parser = subparsers.add_parser('analyze', help='Analyze repositories')
    
    # Tutorial generation command
    tutorial_parser = subparsers.add_parser('tutorial', help='Generate tutorial from repository')
    
    # Source group - repo or local-dir
    source_group = tutorial_parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        '--repo', type=str, 
        help='GitHub repository URL to generate tutorial from'
    )
    source_group.add_argument(
        '--local-dir', type=str,
        help='Local directory to generate tutorial from'
    )
    
    tutorial_parser.add_argument(
        '--output-dir', type=str, default='tutorial',
        help='Output directory for tutorial files'
    )
    tutorial_parser.add_argument(
        '--language', type=str, default='english',
        help='Language to generate tutorial in (default: english)'
    )
    tutorial_parser.add_argument(
        '--github-token', type=str, default=os.environ.get('GITHUB_TOKEN'),
        help='GitHub personal access token for private repos or to avoid rate limits (will use GITHUB_TOKEN env var if not specified)'
    )
    
    return parser.parse_args()

def run_interactive_search():
    """
    Run the interactive search mode from utils.search.
    
    Returns:
        Dictionary with search results including repository URLs and quality data
    """
    print("\nStarting interactive search mode...")
    search_results = interactive_search()
    
    if not search_results.get("github_urls"):
        print("\nNo GitHub repositories found. Please try a different query.")
        if input("Would you like to try again? (y/n): ").lower() == 'y':
            return run_interactive_search()
        return None
    
    return search_results

def run_agent(query=None, verbose=False, provider=None, model=None, interactive=True, 
             use_youtube=True, use_web=True, youtube_count=5, web_count=10, 
             use_advanced_search=True, github_token=None, relevance_threshold=0.5):
    """
    Run the repository analysis agent flow.
    
    Args:
        query: The user's initial query (optional when interactive=True)
        verbose: Whether to enable verbose logging
        provider: The LLM provider to use
        model: The specific model to use
        interactive: Whether to use interactive search mode
        use_youtube: Whether to include YouTube search
        use_web: Whether to include web search
        youtube_count: Number of YouTube videos to search
        web_count: Number of web pages to search
        use_advanced_search: Whether to use advanced search with retry
        github_token: GitHub personal access token for repository access
        relevance_threshold: Minimum relevance score (0.0-1.0) for filtering results
    
    Returns:
        Dictionary with search results
    """
    # Configure logging based on verbose flag
    configure_logging(verbose)
    
    # Store GitHub token in session if provided via CLI
    if github_token:
        set_github_token(github_token)
    else:
        # We'll prompt for token if needed for repository access
        # but we don't need to do it right away - only when accessing GitHub
        pass
    
    # Set up LLM provider if provider or model is specified
    llm_configured = False
    if provider or model:
        try:
            from utils.llm import setup_llm_provider_with_params
            provider_info = setup_llm_provider_with_params(provider=provider, model=model)
            print(f"Using LLM provider: {provider or 'default'}, model: {model or 'default'}")
            llm_configured = True
        except Exception as e:
            print(f"Warning: Failed to set up specified LLM provider: {e}")
            print("Will attempt LLM setup during search process")
    
    # Create shared store for data
    shared = {}
    
    # First, collect inputs with interactive search
    # This only collects inputs but doesn't process them yet
    from utils.search import interactive_search
    search_results = interactive_search(initial_query=query)
    
    # Now process the search results
    if search_results and "github_urls" not in search_results:
        # Process the query inputs with LLM
        from utils.search import search_and_scrape
        final_results = search_and_scrape(
            query=search_results.get("query", ""),
            keywords=search_results.get("keywords", []),
            tech_stack=search_results.get("tech_stack", []),
            features=search_results.get("features", []),
            youtube_count=search_results.get("youtube_count", youtube_count),
            web_count=search_results.get("web_count", web_count),
            use_youtube=search_results.get("use_youtube", use_youtube),
            use_web=search_results.get("use_web", use_web),
            use_llm=search_results.get("use_llm", True),
            setup_llm_first=not llm_configured,  # Only skip LLM setup if we've already done it
            threshold=search_results.get("relevance_threshold", relevance_threshold)  # Use threshold from interactive search or the CLI parameter
        )
        
        # Store final results in shared store
        shared.update(final_results)
        
        # Extract GitHub URLs for display
        github_urls = final_results.get("github_urls", [])
        
        if github_urls:
            print(f"\nFound {len(github_urls)} GitHub repositories:")
            for i, url in enumerate(github_urls[:10], 1):
                print(f"{i}. {url}")
            
            if len(github_urls) > 10:
                print(f"...and {len(github_urls) - 10} more")
                
            # Allow user to select a repository for detailed analysis
            if len(github_urls) > 0:
                if input("\nAnalyze a repository in detail? (y/n): ").lower() == 'y':
                    selected_index = None
                    while selected_index is None:
                        try:
                            idx = int(input(f"Enter repository number (1-{len(github_urls)}): "))
                            if 1 <= idx <= len(github_urls):
                                selected_index = idx - 1
                            else:
                                print(f"Please enter a number between 1 and {len(github_urls)}")
                        except ValueError:
                            print("Please enter a valid number")
                    
                    # Store selected repository
                    shared["selected_repo"] = github_urls[selected_index]
                    
                    # Ensure GitHub token is available for repo analysis
                    ensure_github_token()
                    
                    # Run detailed analysis
                    analysis_result = handle_user_selection(shared)
                    if analysis_result:
                        print("\n=== Repository Analysis Complete ===")
                        print(f"Analysis for: {shared['selected_repo']}")
        else:
            print("\nNo GitHub repositories found matching your criteria.")
    else:
        print("\nSearch failed or was canceled.")
    
    return shared

def generate_tutorial(repo_url=None, local_dir=None, output_dir='tutorial', 
                      language='english', github_token=None, provider=None, model=None):
    """
    Generate a tutorial from a GitHub repository or local directory.
    
    Args:
        repo_url: GitHub repository URL
        local_dir: Local directory path
        output_dir: Output directory for tutorial files
        language: Language to generate tutorial in
        github_token: GitHub personal access token for private repos
        provider: The LLM provider to use
        model: The specific model to use
    
    Returns:
        Dictionary with tutorial information
    """
    if not repo_url and not local_dir:
        print("Error: Either --repo or --local-dir must be specified")
        return None
    
    # Configure logging
    configure_logging(True)
    
    # Store GitHub token in session if provided
    if github_token:
        set_github_token(github_token)
    
    # Set up LLM provider if specified
    if provider or model:
        try:
            setup_llm_provider_with_params(provider=provider, model=model)
            print(f"Using LLM provider: {provider or 'default'}, model: {model or 'default'}")
        except Exception as e:
            print(f"Warning: Failed to set up specified LLM provider: {e}")
            print("Will use default or interactive LLM setup when needed")
    
    # Create shared store for data
    shared = {
        "repo_url": repo_url,
        "local_dir": local_dir, 
        "tutorial_output_dir": output_dir,
        "language": language,
        "timeout": 300  # 5 minutes timeout for operations
    }
    
    # Show status message
    print(f"\nStarting tutorial generation for {'repository' if repo_url else 'local directory'}...")
    print(f"Output will be saved to: {os.path.abspath(output_dir)}")
    print(f"Tutorial language: {language}")
    
    # Create and run tutorial generator flow
    tutorial_flow = create_tutorial_generator_flow()
    try:
        tutorial_flow.run(shared)
        
        # Print summary of generated tutorial
        tutorial_dir = shared.get("tutorial_output_dir")
        total_chapters = shared.get("tutorial_total_chapters", 0)
        
        if tutorial_dir and os.path.exists(tutorial_dir):
            print(f"\nTutorial generation complete!")
            print(f"Generated {total_chapters} chapters in {tutorial_dir}/")
            print(f"Start reading: {tutorial_dir}/index.md")
        else:
            print("Tutorial generation failed!")
    except KeyboardInterrupt:
        print("\nTutorial generation interrupted by user.")
        print("Partial results may be available in the output directory.")
    except Exception as e:
        print(f"\nError during tutorial generation: {e}")
        print("Check logs for details. Partial results may be available.")
    
    return shared

def handle_user_selection(shared):
    """
    Handle user selection of repositories and run detailed analysis.
    
    Args:
        shared: The shared data dictionary
    
    Returns:
        The analysis results
    """
    selected_repo = shared.get("selected_repo")
    if not selected_repo:
        print("No repository selected.")
        return None
    
    # Create the analysis flow
    analyze_repo = AnalyzeRepositoryNode()
    
    # Create single-node flow 
    analysis_flow = Flow(start=analyze_repo)
    
    # Run analysis
    analysis_flow.run(shared)
    
    # Return the result
    return shared.get("analysis_results")

def main():
    """Main entry point."""
    # Create argument parser
    parser = argparse.ArgumentParser(description="GitHub Repository Analyzer CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Tutorial generator command
    tutorial_parser = subparsers.add_parser("tutorial", help="Generate a tutorial from a repository")
    tutorial_parser.add_argument("--repo", help="GitHub repository URL")
    tutorial_parser.add_argument("--local-dir", help="Local directory path")
    tutorial_parser.add_argument("--output-dir", default="tutorial", help="Output directory for tutorial files")
    tutorial_parser.add_argument("--language", default="english", help="Language to generate tutorial in")
    tutorial_parser.add_argument("--github-token", help="GitHub personal access token for repository access")
    tutorial_parser.add_argument("--provider", help="LLM provider to use (e.g., openai, google, anthropic, openrouter)")
    tutorial_parser.add_argument("--model", help="Specific LLM model to use")
    
    # Agent command
    agent_parser = subparsers.add_parser("agent", help="Run the repository analysis agent")
    agent_parser.add_argument("query", nargs="?", help="Initial query for the agent (optional)")
    agent_parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    agent_parser.add_argument("--no-interactive", dest="interactive", action="store_false", 
                           help="Disable interactive search mode (not recommended)")
    agent_parser.add_argument("--no-youtube", action="store_true", help="Disable YouTube search")
    agent_parser.add_argument("--no-web", action="store_true", help="Disable web search")
    agent_parser.add_argument("--youtube-count", type=int, default=5, help="Number of YouTube videos to search")
    agent_parser.add_argument("--web-count", type=int, default=10, help="Number of web pages to search")
    agent_parser.add_argument("--no-advanced-search", action="store_true", help="Disable advanced search with retry")
    agent_parser.add_argument("--github-token", help="GitHub personal access token for repository access")
    agent_parser.add_argument("--provider", help="LLM provider to use (e.g., openai, google, anthropic, openrouter)")
    agent_parser.add_argument("--model", help="Specific LLM model to use")
    agent_parser.add_argument("--relevance-threshold", type=float, default=0.5, 
                           help="Minimum relevance score (0.0-1.0) for filtering search results")
    
    args = parser.parse_args()
    
    if args.command == 'tutorial':
        generate_tutorial(
            repo_url=args.repo,
            local_dir=args.local_dir,
            output_dir=args.output_dir,
            language=args.language,
            github_token=args.github_token,
            provider=args.provider,
            model=args.model
        )
    elif args.command == 'agent':
        run_agent(
            query=args.query,
            verbose=args.verbose,
            provider=args.provider,
            model=args.model,
            interactive=args.interactive,
            use_youtube=not args.no_youtube,
            use_web=not args.no_web,
            youtube_count=args.youtube_count,
            web_count=args.web_count,
            use_advanced_search=not args.no_advanced_search,
            github_token=args.github_token,
            relevance_threshold=args.relevance_threshold
        )
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 