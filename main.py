"""
Main entry point for the Repository Analysis to MCP Server agent.

This script initializes the agent flow and runs it with the user's query.
"""

import argparse
import logging
import sys
import os

from pocketflow import Flow
from flow import create_repo_analyzer_flow, create_tutorial_flow
from utils.monitoring import configure_logging
from utils.data_processing import get_user_selection
from utils.llm import call_llm, setup_llm_provider, setup_llm_provider_with_params
from utils.search import interactive_search
from utils.github import set_github_token, ensure_github_token, analyze_repository_metadata
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
    
    try:
        # First, collect inputs with interactive search
        # This only collects inputs but doesn't process them yet
        from utils.search import interactive_search
        search_results = interactive_search(initial_query=query)
        
        # Now process the search results
        if search_results and "github_urls" not in search_results:
            # Process the query inputs with LLM
            from utils.search import search_and_scrape
            
            try:
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
                    
                    # Allow user to select repositories for detailed analysis
                    if len(github_urls) > 0:
                        print("\n=== Found GitHub Repositories ===")
                        for i, url in enumerate(github_urls, 1):
                            print(f"{i}. {url}")
                        
                        if input("\nWould you like to analyze repositories in detail? (y/n): ").lower() == 'y':
                            # Show selection instructions
                            print("\nSelect repositories to analyze:")
                            print("- Enter numbers separated by commas (e.g. '1,3,5')")
                            print("- Enter 'all' to analyze all repositories")
                            
                            selection = input("Enter your selection: ").strip().lower()
                            
                            selected_repos = []
                            if selection == 'all':
                                # Use all repositories
                                selected_repos = github_urls
                                print(f"Selected all {len(github_urls)} repositories.")
                            else:
                                # Parse selection for multiple repositories
                                try:
                                    selected_indices = [int(idx.strip()) for idx in selection.split(',') if idx.strip()]
                                    
                                    # Validate all indices
                                    for idx in selected_indices:
                                        if 1 <= idx <= len(github_urls):
                                            selected_repos.append(github_urls[idx-1])
                                        else:
                                            print(f"Ignoring invalid selection {idx} (out of range)")
                                    
                                    if not selected_repos:
                                        print("No valid repositories selected.")
                                        return shared
                                    
                                    print(f"Selected {len(selected_repos)} repositories for analysis.")
                                except ValueError:
                                    print("Invalid selection format. Please use numbers separated by commas.")
                                    return shared
                            
                            # Store selected repositories in shared dictionary
                            shared["selected_repos"] = selected_repos
                            
                            # Ensure GitHub token is available for repo analysis
                            ensure_github_token()
                            
                            # Run detailed analysis
                            analysis_results = handle_user_selection(shared)
                            
                            if analysis_results:
                                print("\n=== Repository Analysis Complete ===")
                                
                                # Ask if user wants to create a tutorial from one of the analyzed repos
                                print("\nWould you like to generate a tutorial from one of these repositories?")
                                repo_choice = input("Enter repository number or 'n' to skip: ").strip().lower()
                                
                                if repo_choice != 'n':
                                    try:
                                        idx = int(repo_choice)
                                        if 1 <= idx <= len(github_urls):
                                            selected_repo = github_urls[idx-1]
                                            print(f"\nGenerating tutorial for: {selected_repo}")
                                            
                                            # Call tutorial generator with the selected repository
                                            tutorial_results = generate_tutorial(
                                                repo_url=selected_repo,
                                                output_dir="tutorial",
                                                language="english"
                                            )
                                            
                                            # Store tutorial results in shared data
                                            if tutorial_results:
                                                shared["tutorial_results"] = tutorial_results
                                        else:
                                            print(f"Invalid repository number. Skipping tutorial generation.")
                                    except ValueError:
                                        print("Invalid selection. Skipping tutorial generation.")
                else:
                    print("\nNo GitHub repositories found matching your criteria.")
            except KeyboardInterrupt:
                print("\nSearch process interrupted by user.")
                return shared
            except Exception as e:
                print(f"\nError during search: {e}")
                return shared
        else:
            if search_results and "github_urls" in search_results:
                print("\nSearch completed with direct results.")
                shared.update(search_results)
            else:
                print("\nSearch failed or was canceled.")
    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
    
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
        print("Error: Either repo_url or local_dir must be specified")
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
    
    # Default file patterns
    DEFAULT_INCLUDE_PATTERNS = {
        "*.py", "*.js", "*.jsx", "*.ts", "*.tsx", "*.go", "*.java", "*.pyi", "*.pyx",
        "*.c", "*.cc", "*.cpp", "*.h", "*.md", "*.rst", "Dockerfile",
        "Makefile", "*.yaml", "*.yml",
    }

    DEFAULT_EXCLUDE_PATTERNS = {
        "venv/*", ".venv/*", "*test*", "tests/*", "docs/*", "examples/*", "v1/*",
        "dist/*", "build/*", "experimental/*", "deprecated/*",
        "legacy/*", ".git/*", ".github/*", ".next/*", ".vscode/*", "obj/*", "bin/*", "node_modules/*", "*.log"
    }
    
    # Get project name from URL or directory
    project_name = None
    if repo_url:
        project_name = repo_url.split('/')[-1].replace('.git', '')
    elif local_dir:
        project_name = os.path.basename(os.path.abspath(local_dir))
    
    # Create shared store for data - match mcp-pipeline's structure exactly
    shared = {
        "repo_url": repo_url,
        "local_dir": local_dir, 
        "project_name": project_name,
        "github_token": github_token,
        "tutorial_output_dir": output_dir,
        "language": language,
        
        # Add include/exclude patterns and max file size
        "include_patterns": DEFAULT_INCLUDE_PATTERNS,
        "exclude_patterns": DEFAULT_EXCLUDE_PATTERNS,
        "max_file_size": 100000,  # 100KB matches mcp-pipeline default
        
        # Initialize empty containers for outputs
        "files": [],
        "abstractions": [],
        "relationships": {},
        "chapter_order": [],
        "chapters": [],
        "final_output_dir": None
    }
    
    # Show status message
    print(f"\nStarting tutorial generation for {'repository' if repo_url else 'local directory'}...")
    print(f"Project name: {project_name}")
    print(f"Output will be saved to: {os.path.abspath(output_dir)}")
    print(f"Tutorial language: {language}")
    
    # Create and run tutorial generator flow
    tutorial_flow = create_tutorial_flow()
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
    Uses API-only analysis without LLM to provide repository metadata.
    Supports selecting multiple repositories or all repositories.
    
    Args:
        shared: The shared data dictionary
    
    Returns:
        Dictionary of analysis results by repository URL
    """
    # Get the list of repositories to analyze
    selected_repos = shared.get("selected_repos", [])
    
    # Fallback to single repo selection if using the old format
    if not selected_repos and shared.get("selected_repo"):
        selected_repos = [shared.get("selected_repo")]
        
    if not selected_repos:
        # If we still have no repos, use all github_urls if available
        selected_repos = shared.get("github_urls", [])
        
    if not selected_repos:
        print("No repositories available for analysis.")
        return None
    
    # Store analysis results
    all_results = {}
    
    # Loop through and analyze each selected repository
    for repo_url in selected_repos:
        try:
            print(f"\nAnalyzing repository: {repo_url}")
            
            # Use API-only analysis
            repo_metadata = analyze_repository_metadata(repo_url)
            
            # Store the results
            all_results[repo_url] = repo_metadata
            
            # Print a summary of the findings
            print(f"\nRepository: {repo_metadata.get('name')} (by {repo_metadata.get('owner')})")
            print(f"Stars: {repo_metadata.get('stars')} | Forks: {repo_metadata.get('forks')}")
            print(f"Languages: {', '.join(list(repo_metadata.get('languages', {}).keys())[:5])}")
            print(f"Files: {repo_metadata.get('file_count')} | Size: {repo_metadata.get('size_kb')} KB")
            print(f"Last updated: {repo_metadata.get('days_since_update')} days ago")
            print(f"Maintenance status: {repo_metadata.get('maintenance_status')}")
            print(f"Has images: {'Yes' if repo_metadata.get('has_images') else 'No'}")
            
        except Exception as e:
            print(f"Error analyzing repository {repo_url}: {str(e)}")
    
    # Store the results in shared data for further use
    shared["repo_analysis"] = all_results
    
    # Return results for further processing
    return all_results

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