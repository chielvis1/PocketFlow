"""
GitHub utilities for Repository Analysis to MCP Server system.
"""

import os
import re
import json
import base64
import tempfile
import subprocess
from typing import Dict, List, Any, Optional, Union
from urllib.parse import urlparse

from .monitoring import log_execution_time

# Module-level token store
_GITHUB_TOKEN_STORE = {
    "token": os.environ.get("GITHUB_TOKEN")
}

def set_github_token(token: str) -> None:
    """
    Set GitHub token for the current session.
    
    Args:
        token: GitHub personal access token
    """
    _GITHUB_TOKEN_STORE["token"] = token
    
def get_github_token() -> Optional[str]:
    """
    Get the currently set GitHub token.
    
    Returns:
        Current GitHub token or None if not set
    """
    return _GITHUB_TOKEN_STORE.get("token")

def extract_github_urls(content: Union[str, Dict[str, Any]]) -> List[str]:
    """
    Extracts GitHub repository URLs from text or structured content.
    
    Args:
        content: Text content or structured content item
        
    Returns:
        List of GitHub repository URLs
    """
    # If content is a dictionary, extract text fields
    if isinstance(content, dict):
        text = ""
        for key in ["title", "snippet", "description"]:
            if key in content and isinstance(content[key], str):
                text += content[key] + " "
    else:
        text = content
    
    # Pattern for GitHub repository URLs
    # Matches:
    # - https://github.com/username/repo
    # - http://github.com/username/repo
    # - github.com/username/repo
    pattern = r'(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9\-_]+)/([a-zA-Z0-9\-\._]+)(?:/[^\s)]*)?'
    
    # Find all matches
    matches = re.findall(pattern, text)
    
    # Normalize and deduplicate URLs
    urls = []
    seen = set()
    
    for username, repo in matches:
        # Clean repo name (remove .git extension if present)
        repo = repo.replace(".git", "")
        
        # Normalize URL
        url = f"https://github.com/{username}/{repo}"
        
        if url not in seen:
            urls.append(url)
            seen.add(url)
    
    return urls

@log_execution_time("repo_quality_check")
def check_repository_complexity_and_size(repo_url: str, min_stars: int = 10) -> Dict[str, Any]:
    """
    Evaluates repository quality, complexity metrics, and code size.
    
    Args:
        repo_url: GitHub repository URL
        min_stars: Minimum stars threshold
        
    Returns:
        Repository quality and size metrics
    """
    # Ensure GitHub token is available
    ensure_github_token()
    
    # Extract username and repo name from URL
    parsed_url = urlparse(repo_url)
    path_parts = parsed_url.path.strip('/').split('/')
    
    if len(path_parts) < 2:
        raise ValueError(f"Invalid GitHub URL: {repo_url}")
    
    username, repo_name = path_parts[0], path_parts[1]
    
    try:
        import requests
    except ImportError:
        raise ImportError("Please install requests: pip install requests")
    
    # Get GitHub token from session store
    github_token = get_github_token()
    
    # Set up headers with token if available
    headers = {}
    if github_token:
        headers["Authorization"] = f"token {github_token}"
    
    # Get repository metadata
    api_url = f"https://api.github.com/repos/{username}/{repo_name}"
    response = requests.get(api_url, headers=headers)
    
    if response.status_code != 200:
        return {
            "error": f"Failed to fetch repository data: {response.status_code}",
            "meets_criteria": False
        }
    
    repo_data = response.json()
    
    # Calculate metrics
    stars = repo_data.get("stargazers_count", 0)
    forks = repo_data.get("forks_count", 0)
    issues = repo_data.get("open_issues_count", 0)
    size = repo_data.get("size", 0)  # Size in KB
    last_update = repo_data.get("updated_at", "")
    
    # Get languages
    languages_url = f"https://api.github.com/repos/{username}/{repo_name}/languages"
    lang_response = requests.get(languages_url, headers=headers)
    languages = lang_response.json() if lang_response.status_code == 200 else {}
    
    # Get file structure for LOC estimation
    contents_url = f"https://api.github.com/repos/{username}/{repo_name}/git/trees/master?recursive=1"
    contents_response = requests.get(contents_url, headers=headers)
    
    file_count = 0
    if contents_response.status_code == 200:
        tree = contents_response.json().get("tree", [])
        # Count only files (not directories)
        file_count = sum(1 for item in tree if item.get("type") == "blob")
    
    # Estimate lines of code (rough approximation based on size)
    estimated_loc = size * 10  # Very rough estimate: ~10 lines per KB
    
    # Calculate complexity score (0-10 scale)
    # Factors: stars, forks, size, recent activity
    star_score = min(5, stars / min_stars)
    fork_score = min(2, forks / 5)
    
    # Size score - penalize if too small or too large
    if size < 100:  # Very small repos may be incomplete
        size_score = size / 100
    elif size > 100000:  # Very large repos may be too complex
        size_score = 2 - min(1, (size - 100000) / 900000)
    else:
        size_score = 1
    
    # Recent activity score
    from datetime import datetime
    last_update_date = datetime.strptime(last_update, "%Y-%m-%dT%H:%M:%SZ")
    days_since_update = (datetime.now() - last_update_date).days
    
    activity_score = 2 if days_since_update < 90 else \
                    1 if days_since_update < 365 else \
                    0.5
    
    # Overall score (0-10)
    complexity_score = star_score + fork_score + size_score + activity_score
    complexity_score = min(10, complexity_score)
    
    # Implementation difficulty assessment
    if estimated_loc < 5000:
        difficulty = "Easy"
    elif estimated_loc < 30000:
        difficulty = "Medium"
    else:
        difficulty = "Hard"
    
    # Check if meets minimum quality criteria
    meets_criteria = stars >= min_stars and complexity_score >= 3
    
    return {
        "stars": stars,
        "forks": forks,
        "issues": issues,
        "last_update": last_update,
        "size": size,
        "file_count": file_count,
        "loc": estimated_loc,
        "languages": languages,
        "complexity_score": complexity_score,
        "implementation_difficulty": difficulty,
        "meets_criteria": meets_criteria
    }

@log_execution_time("repo_analysis")
def analyze_repository(repo_url: str) -> Dict[str, Any]:
    """
    Extracts comprehensive data from a GitHub repository.
    
    Args:
        repo_url: GitHub repository URL
        
    Returns:
        Comprehensive repository data
    """
    # Ensure GitHub token is available
    ensure_github_token()
    
    # Extract username and repo name from URL
    parsed_url = urlparse(repo_url)
    path_parts = parsed_url.path.strip('/').split('/')
    
    if len(path_parts) < 2:
        raise ValueError(f"Invalid GitHub URL: {repo_url}")
    
    username, repo_name = path_parts[0], path_parts[1]
    
    try:
        import requests
    except ImportError:
        raise ImportError("Please install requests: pip install requests")
    
    # Get GitHub token from session store
    github_token = get_github_token()
    
    # Set up headers with token if available
    headers = {}
    if github_token:
        headers["Authorization"] = f"token {github_token}"
    
    # Get repository metadata
    api_url = f"https://api.github.com/repos/{username}/{repo_name}"
    response = requests.get(api_url, headers=headers)
    
    if response.status_code != 200:
        return {
            "error": f"Failed to fetch repository data: {response.status_code}"
        }
    
    basic_info = response.json()
    
    # Get README content
    readme_url = f"https://api.github.com/repos/{username}/{repo_name}/readme"
    readme_response = requests.get(readme_url, headers=headers)
    
    readme_content = ""
    if readme_response.status_code == 200:
        readme_data = readme_response.json()
        encoded_content = readme_data.get("content", "")
        if encoded_content:
            readme_content = base64.b64decode(encoded_content).decode('utf-8', errors='replace')
    
    # Get file structure
    contents_url = f"https://api.github.com/repos/{username}/{repo_name}/git/trees/master?recursive=1"
    contents_response = requests.get(contents_url, headers=headers)
    
    file_structure = {}
    if contents_response.status_code == 200:
        tree = contents_response.json().get("tree", [])
        
        # Organize files into directory structure
        for item in tree:
            path = item.get("path", "")
            item_type = item.get("type", "")
            
            if item_type == "blob":  # Regular file
                parts = path.split("/")
                current = file_structure
                
                # Build nested dictionary representing directory structure
                for i, part in enumerate(parts):
                    if i == len(parts) - 1:  # Last part (filename)
                        current[part] = {"type": "file", "path": path}
                    else:
                        if part not in current:
                            current[part] = {}
                        current = current[part]
    
    # Get language breakdown
    languages_url = f"https://api.github.com/repos/{username}/{repo_name}/languages"
    lang_response = requests.get(languages_url, headers=headers)
    languages = lang_response.json() if lang_response.status_code == 200 else {}
    
    # Get key files
    main_files = {}
    
    # Common important files to check
    key_files = [
        "README.md",
        "package.json",
        "requirements.txt",
        "setup.py",
        "Dockerfile",
        "docker-compose.yml",
        "main.py",
        "index.js",
        "app.py",
        "server.js"
    ]
    
    for file in key_files:
        file_url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{file}"
        file_response = requests.get(file_url, headers=headers)
        
        if file_response.status_code == 200:
            file_data = file_response.json()
            
            # Skip if it's a directory
            if isinstance(file_data, dict) and "content" in file_data:
                encoded_content = file_data.get("content", "")
                if encoded_content:
                    content = base64.b64decode(encoded_content).decode('utf-8', errors='replace')
                    main_files[file] = content
    
    # Calculate size metrics
    size_metrics = {
        "total_size_kb": basic_info.get("size", 0),
        "file_count": len(tree) if contents_response.status_code == 200 else 0,
        "language_breakdown": languages
    }
    
    # Assemble repository data
    repository_data = {
        "basic_info": {
            "name": repo_name,
            "owner": username,
            "url": repo_url,
            "description": basic_info.get("description", ""),
            "stars": basic_info.get("stargazers_count", 0),
            "forks": basic_info.get("forks_count", 0),
            "issues": basic_info.get("open_issues_count", 0),
            "last_update": basic_info.get("updated_at", ""),
            "license": basic_info.get("license", {}).get("name", "Unknown")
        },
        "readme_content": readme_content,
        "file_structure": file_structure,
        "main_files": main_files,
        "languages": languages,
        "size_metrics": size_metrics
    }
    
    return repository_data

def ensure_github_token() -> str:
    """
    Ensures a GitHub token is available, prompting the user if necessary.
    
    Returns:
        GitHub token
    """
    token = get_github_token()
    if not token:
        print("\nA GitHub personal access token is required for repository analysis.")
        print("This helps avoid rate limits and allows access to private repositories.")
        print("Create one at: https://github.com/settings/tokens")
        print("You need at least 'repo' scope for most operations.")
        
        token = input("\nEnter your GitHub token: ")
        if token:
            set_github_token(token)
            print("GitHub token set for this session.")
        else:
            print("No token provided. Some operations may be rate-limited.")
    
    return token

if __name__ == "__main__":
    # Test extracting GitHub URLs
    test_text = """
    Check out these repositories:
    - https://github.com/the-pocket/PocketFlow
    - github.com/openai/openai-python
    - Visit https://github.com/microsoft/TypeScript for TypeScript
    """
    urls = extract_github_urls(test_text)
    print("Extracted URLs:", urls)
    
    # Test repository complexity check
    repo_url = "https://github.com/the-pocket/PocketFlow"
    print(f"\nChecking repository complexity for {repo_url}...")
    complexity = check_repository_complexity_and_size(repo_url)
    print(json.dumps(complexity, indent=2))
    
    # Test full repository analysis
    print(f"\nAnalyzing repository {repo_url}...")
    analysis = analyze_repository(repo_url)
    print("Analysis complete. Keys:", list(analysis.keys())) 