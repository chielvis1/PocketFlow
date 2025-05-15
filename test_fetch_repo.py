#!/usr/bin/env python3
"""
Test script to verify FetchRepo node functionality.
"""

import os
import sys
import time
from pocketflow import Node
from utils.github import ensure_github_token
from utils.llm import setup_llm_provider_with_params

def test_fetch_repo(repo_url):
    """Test the FetchRepo node with a specific repository URL."""
    try:
        start_time = time.time()
        print("Starting FetchRepo test...")
        
        # Initialize LLM provider first to avoid hanging
        try:
            # Use OpenAI GPT-4.1-mini model for speed and efficiency
            provider = "openai"
            model = "gpt-4.1-mini"
            
            # Set up with minimal interaction (won't prompt if keys are in env vars)
            print(f"Setting up LLM provider: {provider}, model: {model}")
            setup_llm_provider_with_params(provider=provider, model=model)
        except Exception as e:
            print(f"Warning: Failed to set up LLM provider: {e}")
            print("This may cause issues if the FetchRepo node requires LLM calls")

        # Import the node and crawl_github_files directly
        from nodes import FetchRepo
        from utils.crawl_github_files import crawl_github_files
        
        # Ensure we have a GitHub token
        token = ensure_github_token()
        print(f"Using GitHub token: {'Yes' if token else 'No'}")

        # Test the direct utility function first with stricter parameters
        print("\nSTEP 1: Testing direct API call with crawl_github_files...")
        print(f"Fetching repository: {repo_url}")
        
        # Limit to only MD, HTML, JS, and JSON files
        include_patterns = {"*.md", "*.json", "*.js", "*.html", "*.txt", "package.json"}
        # Exclude common directories that are large and not essential for analysis
        exclude_patterns = {"node_modules/*", ".git/*", "dist/*", "build/*", ".next/*"}
        max_file_size = 100 * 1024  # 100 KB max file size
        
        # Call the function directly with logging
        direct_result = crawl_github_files(
            repo_url, 
            token=token,
            max_file_size=max_file_size,
            use_relative_paths=True,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns
        )
        
        print("Direct API call completed")
        
        # Check for errors in direct call
        if "stats" in direct_result and "error" in direct_result["stats"]:
            print(f"Error in direct API call: {direct_result['stats']['error']}")
        
        # Print statistics
        direct_file_count = len(direct_result.get("files", {}))
        print(f"Files fetched via direct API: {direct_file_count}")
        print(f"Source: {direct_result.get('stats', {}).get('source', 'unknown')}")
        
        # Now test through the FetchRepo node
        print("\nSTEP 2: Testing through FetchRepo node...")
        
        # Create the FetchRepo node
        fetch_repo = FetchRepo()
        
        # Create a shared dictionary with the repository URL and filtering parameters
        shared = {
            "repo_url": repo_url,
            "local_dir": None,
            "timeout": 300,  # 5 minutes timeout
            "include_patterns": include_patterns,
            "exclude_patterns": exclude_patterns,
            "max_file_size": max_file_size
        }
        
        # First test prep to ensure parameters are set correctly
        prep_result = fetch_repo.prep(shared)
        print(f"Prep result: {prep_result}")
        
        # Run the node with parameters from prep
        print("Running FetchRepo.exec with parameters")
        result = fetch_repo.exec(prep_result)
        
        # result is a list of (path, content) tuples
        if not isinstance(result, list):
            print(f"Error: Unexpected result type: {type(result)}")
            return False

        file_count = len(result)
        print(f"Successfully fetched {file_count} files")

        print("\nFirst 10 files:")
        for i, (path, _) in enumerate(result[:10], 1):
            print(f"{i}. {path}")

        if file_count > 0:
            first_path, file_content = result[0]
            preview = file_content[:100] if isinstance(file_content, str) else str(file_content)[:100]
            print(f"\nSample content from {first_path}:")
            print(f"{preview}...")

        end_time = time.time()
        duration = end_time - start_time
        print(f"\nTotal execution time: {duration:.2f} seconds")
        
        return True
        
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Get repo URL from command line or use a default
    repo_url = sys.argv[1] if len(sys.argv) > 1 else "https://github.com/lmac-1/google-map-search-nextjs"
    
    print(f"Testing FetchRepo with {repo_url}")
    success = test_fetch_repo(repo_url)
    
    print("\nTest result:", "PASSED" if success else "FAILED")
    sys.exit(0 if success else 1) 