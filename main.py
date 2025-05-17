"""
Main entry point for the Repository Analysis to MCP Server agent
and Tutorial Generation.

This script initializes the agent flow or tutorial flow and runs it.
"""

import argparse
import logging
import sys
import os
import json # For loading shared state if needed, or other JSON operations
from urllib.parse import urlparse

# PocketFlow and flow creation functions
from pocketflow import Flow
from flow import create_repo_analyzer_flow, create_tutorial_flow # Ensure create_tutorial_flow is imported

# Utility imports from the first set
from utils.monitoring import configure_logging
from utils.data_processing import get_user_selection # Existing utility
from utils.llm import call_llm, setup_llm_provider, setup_llm_provider_with_params # Existing LLM utils
from utils.search import interactive_search # Existing search utility
from utils.github import set_github_token, ensure_github_token, analyze_repository_metadata # Existing GitHub utils

# Node imports (mainly for type hinting or direct use if any, though flow handles execution)
from nodes import AnalyzeRepositoryNode, GenerateMCPServerNode # Example existing node import

# Default file patterns for tutorial generation (from second set)
DEFAULT_TUTORIAL_INCLUDE_PATTERNS = {
    "*.py", "*.js", "*.jsx", "*.ts", "*.tsx", "*.go", "*.java", "*.pyi", "*.pyx",
    "*.c", "*.cc", "*.cpp", "*.h", "*.md", "*.rst", "Dockerfile",
    "Makefile", "*.yaml", "*.yml",
}

DEFAULT_TUTORIAL_EXCLUDE_PATTERNS = {
    "venv/*", ".venv/*", "*test*", "tests/*", "docs/*", "examples/*", "v1/*",
    "dist/*", "build/*", "experimental/*", "deprecated/*",
    "legacy/*", ".git/*", ".github/*", ".next/*", ".vscode/*", "obj/*", "bin/*", "node_modules/*", "*.log"
}


def parse_cli_args():
    """Parse command line arguments for both agent and tutorial modes."""
    parser = argparse.ArgumentParser(
        description='Repository Analysis Agent and Tutorial Generator'
    )
    # Common arguments
    parser.add_argument(
        '-v', '--verbose', action='store_true',
        help='Enable verbose output for logging'
    )
    parser.add_argument(
        '--provider', type=str, default=os.environ.get('LLM_PROVIDER'), # Read from env first
        help='LLM provider to use (e.g., openai, google, anthropic, openrouter)'
    )
    parser.add_argument(
        '--model', type=str, default=os.environ.get('LLM_MODEL'), # Read from env first
        help='Specific LLM model to use'
    )
    parser.add_argument(
        '--github-token', type=str, default=os.environ.get('GITHUB_TOKEN'),
        help='GitHub personal access token (uses GITHUB_TOKEN env var if not specified)'
    )
    parser.add_argument(
        '--mode', type=str, choices=['test', 'prod'], default='test',
        help='Mode of operation: test=build and run Docker; prod=production (coming soon)'
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run', required=True)
    
    # --- Agent (Repository Analysis) command ---
    agent_parser = subparsers.add_parser('agent', help='Run repository analysis agent')
    agent_parser.add_argument(
        'query', nargs='?', type=str, default='',
        help='The initial query to start repository analysis (optional if interactive)'
    )
    agent_parser.add_argument(
        '--server', type=str,
        help='Use existing tutorial output directory to generate MCP server'
    )
    agent_parser.add_argument(
        '-i', '--interactive', '--search', action='store_true',
        help='Use interactive search mode for agent (alias: --search)'
    )
    agent_parser.add_argument(
        '--no-youtube', action='store_true',
        help='Disable YouTube search for agent'
    )
    agent_parser.add_argument(
        '--no-web', action='store_true',
        help='Disable web search for agent'
    )
    agent_parser.add_argument(
        '--youtube-count', type=int, default=5,
        help='Number of YouTube videos to search (agent)'
    )
    agent_parser.add_argument(
        '--web-count', type=int, default=10,
        help='Number of web pages to search (agent)'
    )
    agent_parser.add_argument(
        '--relevance-threshold', type=float, default=0.5, 
        help='Minimum relevance score (0.0-1.0) for filtering agent search results'
    )
    # Note: The old `analyze` subcommand from the original first set's `parse_args`
    # seems to be replaced or integrated into the `agent` command logic.
    # The `tutorial` command below covers the tutorial generation aspect.

    # --- Tutorial Generation command ---
    tutorial_parser = subparsers.add_parser('tutorial', help='Generate a tutorial from a repository or local directory')
    source_group = tutorial_parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        '--repo', type=str, 
        help='GitHub repository URL to generate tutorial from (e.g., https://github.com/owner/repo)'
    )
    source_group.add_argument(
        '--local-dir', type=str,
        help='Local directory path to generate tutorial from'
    )
    tutorial_parser.add_argument(
        '--project-name', type=str,
        help='Project name for the tutorial (optional, derived if not set)'
    )
    tutorial_parser.add_argument(
        '--output-dir', type=str, default='tutorial_output', # Changed default
        help='Output directory for tutorial files (default: tutorial_output)'
    )
    tutorial_parser.add_argument(
        '--language', type=str, default='english',
        help='Language to generate tutorial in (default: english)'
    )
    tutorial_parser.add_argument(
        '--include', nargs='+', default=None, # Default to None, then use DEFAULT_TUTORIAL_INCLUDE_PATTERNS
        help="File patterns to include for tutorial (e.g., '*.py' '*.js')"
    )
    tutorial_parser.add_argument(
        '--exclude', nargs='+', default=None, # Default to None, then use DEFAULT_TUTORIAL_EXCLUDE_PATTERNS
        help="File patterns to exclude for tutorial (e.g., 'tests/*' 'docs/*')"
    )
    tutorial_parser.add_argument(
        '--max-file-size', type=int, default=100000, # 100KB
        help='Maximum file size in bytes for tutorial files (default: 100000)'
    )
    
    return parser.parse_args()


def run_repo_analysis_agent(args):
    """Run the repository analysis agent flow (adapted from original run_agent)."""
    configure_logging(logging.DEBUG if args.verbose else logging.INFO)
    
    # If user provided an existing tutorial directory, generate MCP server spec and code only
    if getattr(args, 'server', None):
        from nodes import GenerateMCPServerNode
        server_dir = args.server
        print(f"\nGenerating MCP server from existing tutorial at {server_dir}...")
        # Prepare minimal shared data
        shared = {
            "tutorial_output_dir": server_dir,
            # tutorial_index defaults to server_dir/index.md
            "tutorial_index": os.path.join(server_dir, "index.md"),
            "features": []  # No features from agent in this mode
        }
        # Run the MCP generation node
        node = GenerateMCPServerNode()
        action = node.run(shared)
        if shared.get("mcp_server_code"):
            print(f"Generated MCP spec: {os.path.join(server_dir, 'mcp_spec.yaml')}")
            print(f"Generated MCP server code: {shared['mcp_server_code']}")
        else:
            print(f"Failed to generate MCP server: {shared.get('error')}")
        return
    
    if args.github_token:
        set_github_token(args.github_token)
    
    # LLM Setup
    llm_configured_successfully = False
    if args.provider or args.model:
        try:
            provider_info = setup_llm_provider_with_params(provider=args.provider, model=args.model, api_key=None) # api_key will be fetched if needed
            print(f"Using LLM provider: {provider_info[0]}, model: {provider_info[2]}")
            llm_configured_successfully = True
        except Exception as e:
            print(f"Warning: Failed to set up specified LLM provider/model: {e}")
            print("Attempting to proceed. LLM calls might fail or use other defaults if later setup succeeds.")
    
    shared_data = {"query": args.query} # Initialize shared data for the agent flow

    try:
        # Interactive search part (simplified from original run_agent)
        if args.interactive or not args.query:
            print("\nStarting interactive search mode for agent...")
            # interactive_search now takes initial_query
            search_inputs = interactive_search(initial_query=args.query if args.query else None)
            if not search_inputs:
                print("Interactive search cancelled or failed. Exiting agent.")
                return
            # Update shared_data with inputs from interactive search
            shared_data.update(search_inputs) 
            # Ensure query is set if it came from interactive search
            if not args.query and "query" in search_inputs:
                args.query = search_inputs["query"]
            # Perform search after interactive configuration
            from utils.search import search_and_scrape
            print(f"\nStarting agent with query: {shared_data['query']}")
            final_results = search_and_scrape(
                query=shared_data["query"],
                keywords=shared_data.get("keywords", []),
                tech_stack=shared_data.get("tech_stack", []),
                features=shared_data.get("features", []),
                youtube_count=shared_data.get("youtube_count", 5),
                web_count=shared_data.get("web_count", 10),
                use_youtube=shared_data.get("use_youtube", True),
                use_web=shared_data.get("use_web", True),
                use_llm=shared_data.get("use_llm", True),
                setup_llm_first=(not llm_configured_successfully),
                threshold=shared_data.get("relevance_threshold", 0.5)
            )
            shared_data.update(final_results)
        elif args.query: # Non-interactive, query provided
            from utils.search import search_and_scrape # Moved import here
            print(f"\nStarting agent with query: {args.query}")
            # Directly use search_and_scrape logic (needs more details from original run_agent)
            # This part needs to be fleshed out based on how search_and_scrape is called in the original logic.
            # For now, assume query is primary input.
            # The original `run_agent` had a complex logic block for `search_and_scrape`.
            # This is a simplified placeholder.
            # The key is to populate `shared_data` with `github_urls` and other relevant info.
            
            # Simplified call to search_and_scrape based on original structure
            if not llm_configured_successfully:
                print("LLM not configured via CLI, search_and_scrape might prompt or use defaults.")

            final_results = search_and_scrape(
                query=args.query,
                keywords=shared_data.get("keywords", []), # From interactive or pre-extracted
                tech_stack=shared_data.get("tech_stack", []),
                features=shared_data.get("features", []),
                youtube_count=args.youtube_count,
                web_count=args.web_count,
                use_youtube=not args.no_youtube,
                use_web=not args.no_web,
                use_llm=True, # Assuming LLM is generally used
                # setup_llm_first might be true if not args.provider/model
                setup_llm_first=(not llm_configured_successfully),
                threshold=args.relevance_threshold
            )
            shared_data.update(final_results)
        else:
            print("No query provided and not in interactive mode. Agent cannot proceed.")
            return


        github_urls = shared_data.get("github_urls", [])
        if not github_urls:
            print("No GitHub repositories found or selected by the agent. Exiting.")
            return

        print(f"\nAgent identified {len(github_urls)} GitHub repositories for potential analysis.")
        for i, url in enumerate(github_urls[:5], 1): # Show first 5
            print(f"{i}. {url}")
        if len(github_urls) > 5:
            print(f"...and {len(github_urls) - 5} more.")

        # Allow user to select repositories for detailed analysis (from original run_agent)
        if input("\nWould you like to analyze these repositories in detail? (y/n): ").lower() == 'y':
            ensure_github_token() # Make sure token is available
            
            # Simplified selection: analyze all found URLs for now.
            # The original had a more complex selection UI.
            # Let's assume we analyze the first one for simplicity in this merge,
            # or adapt the multi-selection from original `run_agent`.
            # For now, let's just use the first URL for the repo_analyzer_flow.
            
            # If we want to adapt the multi-selection from original main.py:
            print("\nSelect repositories to analyze:")
            print("- Enter numbers separated by commas (e.g. '1,3,5')")
            print("- Enter 'all' to analyze all repositories")
            selection = input("Enter your selection: ").strip().lower()
            
            selected_repo_urls_for_flow = []
            if selection == 'all':
                selected_repo_urls_for_flow = github_urls
            else:
                try:
                    selected_indices = [int(idx.strip()) -1 for idx in selection.split(',') if idx.strip()]
                    for idx in selected_indices:
                        if 0 <= idx < len(github_urls):
                            selected_repo_urls_for_flow.append(github_urls[idx])
                        else:
                             print(f"Ignoring invalid selection index {idx+1}")
                except ValueError:
                    print("Invalid selection format. Defaulting to no detailed analysis.")

            if not selected_repo_urls_for_flow:
                print("No valid repositories selected for detailed analysis.")
            else:
                print(f"Proceeding with detailed analysis for {len(selected_repo_urls_for_flow)} repositories.")
                # Run the repo_analyzer_flow for each selected repository
                repo_analyzer_flow = create_repo_analyzer_flow()
                all_analysis_results = {}

                for repo_url_to_analyze in selected_repo_urls_for_flow:
                    print(f"\n--- Analyzing: {repo_url_to_analyze} ---")
                    flow_shared_data = {
                        "repo_url": repo_url_to_analyze,
                        # other necessary shared data for this flow can be added
                    }
                    try:
                        repo_analyzer_flow.run(flow_shared_data)
                        if flow_shared_data.get("error"):
                            print(f"Error analyzing {repo_url_to_analyze}: {flow_shared_data['error']}")
                            all_analysis_results[repo_url_to_analyze] = {"error": flow_shared_data['error']}
                        else:
                            print(f"Analysis successful for {repo_url_to_analyze}.")
                            # Store relevant results, e.g., llm_analysis or repo_analysis
                            all_analysis_results[repo_url_to_analyze] = {
                                "validated_repo": flow_shared_data.get("validated_repo"),
                                "repo_analysis": flow_shared_data.get("repo_analysis"),
                                "llm_analysis": flow_shared_data.get("llm_analysis")
                            }
                    except Exception as e_flow:
                        print(f"Critical error running analysis flow for {repo_url_to_analyze}: {e_flow}")
                        all_analysis_results[repo_url_to_analyze] = {"error": str(e_flow)}
                
                # Process/display all_analysis_results
                print("\n--- Overall Agent Analysis Results ---")
                # print(json.dumps(all_analysis_results, indent=2, default=str))
                # Here, you might ask if user wants to generate a tutorial for one of the analyzed repos
                # This part is from original `run_agent`
                if all_analysis_results:
                    # Prompt whether to generate a tutorial
                    tutorial_ans = input("\nWould you like to generate a tutorial from one of these analyzed repositories? (y/n): ").strip().lower()
                    if tutorial_ans != 'y':
                        print("Skipping tutorial generation.")
                    else:
                        # List successfully analyzed repositories
                        analyzed_repo_urls = [url for url, res in all_analysis_results.items() if "error" not in res]
                        if not analyzed_repo_urls:
                            print("No repositories were successfully analyzed to generate a tutorial from.")
                        else:
                            print("\nAvailable repositories for tutorial generation:")
                            for i, url in enumerate(analyzed_repo_urls, 1):
                                print(f"{i}. {url}")
                            selection = input("Enter repository number to generate tutorial or 'n' to skip: ").strip().lower()
                            if selection == 'n' or not selection:
                                print("No tutorial selected. Exiting tutorial generation.")
                            else:
                                try:
                                    choice_idx = int(selection) - 1
                                    if 0 <= choice_idx < len(analyzed_repo_urls):
                                        selected_repo_for_tutorial = analyzed_repo_urls[choice_idx]
                                        print(f"\nProceeding to generate tutorial for: {selected_repo_for_tutorial}")
                                        tutorial_args_ns = argparse.Namespace(
                                            repo=selected_repo_for_tutorial,
                                            local_dir=None,
                                            project_name=all_analysis_results[selected_repo_for_tutorial].get("validated_repo", {}).get("repo_name"),
                                            output_dir=args.output_dir if hasattr(args, 'output_dir') else 'tutorial_output',
                                            language=args.language if hasattr(args, 'language') else 'english',
                                            include=args.include if hasattr(args, 'include') else None,
                                            exclude=args.exclude if hasattr(args, 'exclude') else None,
                                            max_file_size=args.max_file_size if hasattr(args, 'max_file_size') else 100000,
                                            github_token=args.github_token,
                                            provider=args.provider,
                                            model=args.model,
                                            verbose=args.verbose
                                        )
                                        run_tutorial_generation(tutorial_args_ns)
                                    else:
                                        print("Invalid selection index.")
                                except ValueError:
                                    print("Invalid input for tutorial selection.")
        else:
            print("Skipping detailed repository analysis.")


    except KeyboardInterrupt:
        print("\nAgent process interrupted by user.")
    except Exception as e:
        print(f"\nUnexpected error in agent: {e}")
        logging.exception("Agent error details:")

    # print("\nAgent run finished. Final shared data:")
    # print(json.dumps(shared_data, indent=2, default=str))


def run_tutorial_generation(args):
    """Run the tutorial generation flow."""
    # Configure logging based on verbose flag (common arg)
    configure_logging(logging.DEBUG if args.verbose else logging.INFO)

    # LLM Setup (common args)
    if args.provider or args.model:
        try:
            provider_info = setup_llm_provider_with_params(provider=args.provider, model=args.model, api_key=None)
            print(f"Using LLM provider for tutorial: {provider_info[0]}, model: {provider_info[2]}")
        except Exception as e:
            print(f"Warning: Failed to set up LLM for tutorial: {e}. LLM calls might fail.")
    else:
        print("No specific LLM provider/model specified for tutorial. Nodes will attempt default setup or prompt if necessary.")

    # GitHub token (common arg)
    if args.github_token:
        set_github_token(args.github_token)
    elif args.repo: # If it's a repo URL, ensure token might be needed
        ensure_github_token() # Check env and prompt if missing

    # Compute tutorial output directory name from repo URL if provided
    if args.repo:
        parsed_url = urlparse(args.repo)
        # Domain base without TLD
        domain_base = parsed_url.netloc.split('.')[0]
        # Path part, remove leading/trailing slashes and convert to underscores
        path_part = parsed_url.path.strip('/')
        path_underscored = path_part.replace('/', '_') if path_part else ''
        computed_output_dir = f"{domain_base}_{path_underscored}" if path_underscored else domain_base
    else:
        computed_output_dir = args.output_dir

    # Prepare shared dictionary for the tutorial flow
    shared_data = {
        "repo_url": args.repo,
        "local_dir": args.local_dir,
        "tutorial_output_dir": computed_output_dir, # Node `CombineTutorial` uses this key
        "language": args.language,
        
        "include_patterns": set(args.include) if args.include else DEFAULT_TUTORIAL_INCLUDE_PATTERNS,
        "exclude_patterns": set(args.exclude) if args.exclude else DEFAULT_TUTORIAL_EXCLUDE_PATTERNS,
        "max_file_size": args.max_file_size,
        
        # Initialize placeholders for data passed between tutorial nodes
        "files": [], # List of (path, content) tuples from FetchRepo
        "file_count": 0,
        "abstractions": [], # List of dicts from IdentifyAbstractions
        "relationships": {}, # Dict from AnalyzeRelationships
        "chapter_order": [], # List of indices from OrderChapters
        "chapters": [], # List of Markdown strings from WriteChapters
        "final_output_dir": None, # Set by CombineTutorial
        "retry_count_map": {}, # For TutorialErrorHandler
        "current_stage": "" # For TutorialErrorHandler
    }

    source_display = args.repo if args.repo else args.local_dir
    print(f"\nStarting tutorial generation for: {source_display}")
    print(f"Language: {args.language.capitalize()}")
    print(f"Output will be in: {os.path.abspath(args.output_dir)}")
    print(f"Include patterns: {shared_data['include_patterns']}")
    print(f"Exclude patterns: {shared_data['exclude_patterns']}")
    print(f"Max file size: {args.max_file_size} bytes")

    tutorial_flow_instance = create_tutorial_flow()
    
    try:
        tutorial_flow_instance.run(shared_data)
        
        final_dir = shared_data.get("final_output_dir")
        if final_dir and os.path.exists(final_dir):
            print(f"\nTutorial generation process completed.")
            print(f"Output saved to: {final_dir}")
            # Further summary from shared_data if available
            total_chapters = shared_data.get("tutorial_total_chapters", 0)
            if total_chapters > 0:
                print(f"Generated {total_chapters} chapters.")
            print(f"Main tutorial index: {os.path.join(final_dir, 'index.md')}")
            # Prompt to serve tutorial as a knowledge base via MCP
            if input("\nWill you like to serve your generated tutorial as a knowledge base? (y/n): ").strip().lower() == 'y':
                import yaml, json
                from utils.mcp import create_mcp_server, start_mcp_server
                spec_path = os.path.join(final_dir, "mcp_spec.yaml")
                spec = yaml.safe_load(open(spec_path))
                tools = spec.get("tools", [])
                # If implementation guides exist in spec
                guides = spec.get("implementation_guides", {})
                server_name = os.path.basename(final_dir)
                mcp = create_mcp_server(server_name, tools, guides)
                server_info = start_mcp_server(mcp)
                print("\nMCP Server details:")
                print(json.dumps(server_info, indent=2))
        else:
            print("\nTutorial generation finished, but output directory might be missing or an error occurred.")
            if shared_data.get("error"):
                print(f"Error details: {shared_data['error']}")

    except KeyboardInterrupt:
        print("\nTutorial generation interrupted by user.")
        print("Partial results may be available in the output directory.")
    except Exception as e:
        print(f"\nError during tutorial generation: {e}")
        logging.exception("Tutorial generation critical error:")
        print("Check logs for details. Partial results may be available.")
    
    # print("\nTutorial flow finished. Final shared data:")
    # print(json.dumps(shared_data, indent=2, default=str))


def main():
    """Main entry point dispatching to agent or tutorial generation."""
    args = parse_cli_args()

    # Handle test/prod mode
    if args.mode == 'test':
        import subprocess, os, time, re
        # Determine which tutorial directory to serve
        if args.command == 'tutorial':
            tutorial_dir = args.output_dir
        elif args.command == 'agent' and getattr(args, 'server', None):
            tutorial_dir = args.server
        else:
            print("Test mode requires a tutorial directory. Use `tutorial` command or `agent --server`.")
            return
        tutorial_name = os.path.basename(tutorial_dir.rstrip('/'))
        host_tutorial_abs = os.path.abspath(tutorial_dir)
        image_name = "pocketflow-test"
        print(f"Building Docker image {image_name} (Dockerfile.test)...")
        subprocess.run(["docker", "build", "-t", image_name, "-f", "Dockerfile.test", "."], check=True)
        print(f"Launching Docker container serving tutorial '{tutorial_name}' on localhost:8000 in detached mode...")
        # Run container detached and capture its ID
        container_id = subprocess.check_output([
            "docker", "run", "-d", "--rm",
            "-p", "8000:8000",
            "-e", f"TUTORIAL_NAME={tutorial_name}",
            "-v", f"{host_tutorial_abs}:/tutorials/{tutorial_name}",
            image_name
        ], text=True).strip()
        print(f"Container started in detached mode: {container_id}")
        # Allow server to initialize
        time.sleep(2)
        # Fetch container logs
        logs = subprocess.check_output(["docker", "logs", container_id], text=True)
        # Extract JSON details from logs
        match = re.search(r'(\{.*\})', logs, re.DOTALL)
        if match:
            print("\nMCP Server JSON details:")
            print(match.group(1))
        else:
            print("\nCould not find JSON details in container logs. Full logs:")
            print(logs)
        return
    elif args.mode == 'prod':
        print("Production mode coming soon!")
        return
    
    if args.command == 'agent':
        run_repo_analysis_agent(args)
    elif args.command == 'tutorial':
        run_tutorial_generation(args)
    else:
        # Should not happen due to `required=True` in subparsers
        parser.print_help()


if __name__ == "__main__":
    main()