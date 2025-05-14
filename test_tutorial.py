#!/usr/bin/env python3
"""
Test script for checking tutorial generation capability.

This script tests the repository analysis functionality with minimal dependencies
by using a small public repository.
"""

import os
import sys
import argparse
from utils.crawl_github_files import crawl_github_files

def test_repo_fetch(repo_url="https://github.com/the-pocket/PocketFlow", token=None):
    """Test fetching a repository with crawl_github_files"""
    print(f"\n=== Testing repository fetching: {repo_url} ===")
    
    # Only fetch Python files, limited to 100KB each
    include_patterns = {"*.py"}
    exclude_patterns = {".git/*", "venv/*", "tests/*", "examples/*"}
    max_file_size = 100 * 1024  # 100KB
    
    try:
        result = crawl_github_files(
            repo_url=repo_url,
            token=token,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            max_file_size=max_file_size,
            use_relative_paths=True
        )
        
        files = result.get("files", {})
        stats = result.get("stats", {})
        
        print(f"\nRepository fetch results:")
        print(f"- Downloaded {len(files)} files")
        print(f"- Skipped {stats.get('skipped_count', 0)} files")
        print(f"- Source: {stats.get('source', 'unknown')}")
        
        if files:
            print("\nFirst 5 files:")
            for i, (path, content) in enumerate(list(files.items())[:5]):
                size = len(content)
                print(f"  {i+1}. {path} ({size/1024:.1f} KB)")
            
            return True
        else:
            print("No files were fetched!")
            return False
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Test repository analysis functionality")
    parser.add_argument("--repo", type=str, default="https://github.com/the-pocket/PocketFlow",
                       help="GitHub repository URL to test")
    parser.add_argument("--token", type=str, default=os.environ.get("GITHUB_TOKEN"),
                       help="GitHub token (uses GITHUB_TOKEN env var if not specified)")
    
    args = parser.parse_args()
    
    success = test_repo_fetch(args.repo, args.token)
    
    if success:
        print("\n✅ Test completed successfully!")
        return 0
    else:
        print("\n❌ Test failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 