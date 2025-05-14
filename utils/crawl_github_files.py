"""
GitHub repository crawler for fetching and processing code files.
"""

import requests
import base64
import os
import tempfile
import time
import fnmatch
from typing import Union, Set, List, Dict, Tuple, Any
from urllib.parse import urlparse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib3.exceptions import MaxRetryError
from requests.exceptions import RequestException
import sys
from .github import get_github_token
sys.setrecursionlimit(10000)
MAX_TRAVERSAL_DEPTH = 50

# Try to import git, but handle gracefully if it's not available
GIT_AVAILABLE = False
try:
    import git
    GIT_AVAILABLE = True
except ImportError:
    print("Warning: GitPython not installed. SSH and local clone functionality will be limited.")
    print("To enable full functionality, install with: pip install gitpython")

def crawl_github_files(
    repo_url, 
    token=None, 
    max_file_size: int = 1 * 1024 * 1024,  # 1 MB
    use_relative_paths: bool = False,
    include_patterns: Union[str, Set[str]] = None,
    exclude_patterns: Union[str, Set[str]] = None
):
    """
    Crawl files from a specific path in a GitHub repository at a specific commit.

    Args:
        repo_url (str): URL of the GitHub repository with specific path and commit
                        (e.g., 'https://github.com/microsoft/autogen/tree/e45a15766746d95f8cfaaa705b0371267bec812e/python/packages/autogen-core/src/autogen_core')
        token (str, optional): **GitHub personal access token.**
            - **Required for private repositories.**
            - **Recommended for public repos to avoid rate limits.**
            - Can be passed explicitly, stored in session, or from GITHUB_TOKEN env var.
        max_file_size (int, optional): Maximum file size in bytes to download (default: 1 MB)
        use_relative_paths (bool, optional): If True, file paths will be relative to the specified subdirectory
        include_patterns (str or set of str, optional): Pattern or set of patterns specifying which files to include (e.g., "*.py", {"*.md", "*.txt"}).
                                                       If None, all files are included.
        exclude_patterns (str or set of str, optional): Pattern or set of patterns specifying which files to exclude.
                                                       If None, no files are excluded.

    Returns:
        dict: Dictionary with files and statistics
    """
    # Use provided token or get from session store if not provided
    if not token:
        token = get_github_token()
    
    # Convert single pattern to set
    if include_patterns and isinstance(include_patterns, str):
        include_patterns = {include_patterns}
    if exclude_patterns and isinstance(exclude_patterns, str):
        exclude_patterns = {exclude_patterns}

    def should_include_file(file_path: str, file_name: str) -> bool:
        """Determine if a file should be included based on patterns"""
        # If no include patterns are specified, include all files
        if not include_patterns:
            include_file = True
        else:
            # Check if file matches any include pattern
            include_file = any(fnmatch.fnmatch(file_name, pattern) for pattern in include_patterns)

        # If exclude patterns are specified, check if file should be excluded
        if exclude_patterns and include_file:
            # Exclude if file matches any exclude pattern
            exclude_file = any(fnmatch.fnmatch(file_path, pattern) for pattern in exclude_patterns)
            return not exclude_file

        return include_file

    # Normalize GitHub URL if it's an API URL
    if "api.github.com" in repo_url:
        # Convert API URL to web URL
        parts = repo_url.split("api.github.com/repos/")
        if len(parts) > 1:
            repo_path = parts[1]
            repo_url = f"https://github.com/{repo_path}"
            print(f"Converted API URL to: {repo_url}")

    # Detect SSH URL (git@ or .git suffix)
    is_ssh_url = repo_url.startswith("git@") or repo_url.endswith(".git")

    if is_ssh_url:
        if not GIT_AVAILABLE:
            return {"files": {}, "stats": {"error": "GitPython not installed. Cannot clone SSH URLs."}}
            
        # Clone repo via SSH to temp dir
        with tempfile.TemporaryDirectory() as tmpdirname:
            print(f"Cloning SSH repo {repo_url} to temp dir {tmpdirname} ...")
            try:
                repo = git.Repo.clone_from(repo_url, tmpdirname)
            except Exception as e:
                print(f"Error cloning repo: {e}")
                return {"files": {}, "stats": {"error": str(e)}}

            # Walk directory
            files = {}
            skipped_files = []

            for root, dirs, filenames in os.walk(tmpdirname):
                for filename in filenames:
                    abs_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(abs_path, tmpdirname)

                    # Check file size
                    try:
                        file_size = os.path.getsize(abs_path)
                    except OSError:
                        continue

                    if file_size > max_file_size:
                        skipped_files.append((rel_path, file_size))
                        print(f"Skipping {rel_path}: size {file_size} exceeds limit {max_file_size}")
                        continue

                    # Check include/exclude patterns
                    if not should_include_file(rel_path, filename):
                        print(f"Skipping {rel_path}: does not match include/exclude patterns")
                        continue

                    # Read content
                    try:
                        with open(abs_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        files[rel_path] = content
                        print(f"Added {rel_path} ({file_size} bytes)")
                    except Exception as e:
                        print(f"Failed to read {rel_path}: {e}")

            return {
                "files": files,
                "stats": {
                    "downloaded_count": len(files),
                    "skipped_count": len(skipped_files),
                    "skipped_files": skipped_files,
                    "base_path": None,
                    "include_patterns": include_patterns,
                    "exclude_patterns": exclude_patterns,
                    "source": "ssh_clone"
                }
            }

    # Parse GitHub URL to extract owner, repo, commit/branch, and path
    parsed_url = urlparse(repo_url)
    path_parts = parsed_url.path.strip('/').split('/')
    
    if len(path_parts) < 2:
        raise ValueError(f"Invalid GitHub URL: {repo_url}")
    
    # Extract the basic components
    owner = path_parts[0]
    repo = path_parts[1]
    
    # Setup for GitHub API
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
        print(f"Using GitHub token for API requests to {owner}/{repo}")
    else:
        print(f"Warning: No GitHub token provided. API rate limits may apply for {owner}/{repo}")

    # Setup requests session with retry/backoff
    session = requests.Session()
    retry_strategy = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    def fetch_branches(owner: str, repo: str):
        """Get branches of the repository"""

        url = f"https://api.github.com/repos/{owner}/{repo}/branches"
        response = session.get(url, headers=headers)

        if response.status_code == 404:
            if not token:
                print(f"Error 404: Repository not found or is private.\n"
                      f"If this is a private repository, please provide a valid GitHub token via the 'token' argument or set the GITHUB_TOKEN environment variable.")
            else:
                print(f"Error 404: Repository not found or insufficient permissions with the provided token.\n"
                      f"Please verify the repository exists and the token has access to this repository.")
            return []
            
        if response.status_code != 200:
            print(f"Error fetching the branches of {owner}/{repo}: {response.status_code} - {response.text}")
            return []

        return response.json()

    def check_tree(owner: str, repo: str, tree: str):
        """Check the repository has the given tree"""

        url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{tree}"
        response = session.get(url, headers=headers)

        return True if response.status_code == 200 else False 

    # Check if URL contains a specific branch/commit
    if len(path_parts) > 2 and 'tree' == path_parts[2]:
        join_parts = lambda i: '/'.join(path_parts[i:])

        branches = fetch_branches(owner, repo)
        branch_names = [branch.get("name") for branch in branches if branch.get("name")]

        # Fetching branches is not successfully
        if len(branches) == 0:
            return {"files": {}, "stats": {"error": "Failed to fetch branches"}}

        # To check branch name
        relevant_path = join_parts(3)

        # Find a match with relevant path and get the branch name
        ref = None
        for name in branch_names:
            if relevant_path.startswith(name):
                ref = name
                break

        # If match is not found, check for is it a tree
        if ref is None:
            tree = path_parts[3]
            ref = tree if check_tree(owner, repo, tree) else None

        # If it is neither a tree nor a branch name
        if ref is None:
            print(f"The given path does not match with any branch and any tree in the repository.\n"
                  f"Please verify the path is exists.")
            return {"files": {}, "stats": {"error": "Invalid path in repository"}}

        # Combine all parts after the ref as the path
        part_index = 5 if '/' in ref else 4
        specific_path = join_parts(part_index) if part_index < len(path_parts) else ""
    else:
        # Don't put the ref param to query
        # and let Github decide default branch
        ref = None
        specific_path = ""
    
    # Dictionary to store path -> content mapping
    files = {}
    skipped_files = []
    
    def fetch_contents(path):
        """Iterative fetch of repository contents to avoid recursion."""
        stack = [(path, 0)]  # (path, depth)
        while stack:
            current_path, depth = stack.pop()
            if depth > MAX_TRAVERSAL_DEPTH:
                print(f"Skipping {current_path}: exceeds max depth {MAX_TRAVERSAL_DEPTH}")
                continue
            url = f"https://api.github.com/repos/{owner}/{repo}/contents/{current_path}"
            params = {"ref": ref} if ref is not None else {}
            response = session.get(url, headers=headers, params=params)

            # Rate-limit handling
            if response.status_code == 403 and 'rate limit exceeded' in response.text.lower():
                reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
                wait_time = max(reset_time - time.time(), 0) + 1
                print(f"Rate limit exceeded. Waiting for {wait_time:.0f} seconds...")
                time.sleep(wait_time)
                stack.append((current_path, depth))
                continue
            # 404 handling
            if response.status_code == 404:
                if not token:
                    print(f"Error 404: Repository not found or is private.\n"
                          f"If this is a private repository, please provide a valid GitHub token via the 'token' argument or set the GITHUB_TOKEN environment variable.")
                elif not current_path and ref == 'main':
                    print(f"Error 404: Repository not found. Check if the default branch is not 'main'\n"
                          f"Try adding branch name to the request i.e. python main.py --repo https://github.com/username/repo/tree/master")
                else:
                    print(f"Error 404: Path '{current_path}' not found in repository or insufficient permissions with the provided token.\n"
                          f"Please verify the token has access to this repository and the path exists.")
                continue
            # Other errors
            if response.status_code != 200:
                print(f"Error fetching {current_path}: {response.status_code} - {response.text}")
                continue
            # Parse contents
            try:
                contents_list = response.json()
                if not isinstance(contents_list, list):
                    contents_list = [contents_list]
            except Exception as e:
                print(f"Error parsing response for {current_path}: {e}")
                continue
                
            for item in contents_list:
                item_path = item.get("path", "")
                if not item_path:
                    continue
                    
                # Relative path logic
                if use_relative_paths and specific_path:
                    if item_path.startswith(specific_path):
                        rel_path = item_path[len(specific_path):].lstrip('/')
                    else:
                        rel_path = item_path
                else:
                    rel_path = item_path
                    
                if item.get("type") == "file":
                    # File inclusion and size checks
                    if not should_include_file(rel_path, item.get("name", "")):
                        print(f"Skipping {rel_path}: Does not match include/exclude patterns")
                        continue
                    file_size = item.get("size", 0)
                    if file_size > max_file_size:
                        skipped_files.append((item_path, file_size))
                        print(f"Skipping {rel_path}: File size ({file_size} bytes) exceeds limit ({max_file_size} bytes)")
                        continue
                    # Download file content
                    if item.get("download_url"):
                        file_response = session.get(item["download_url"], headers=headers)
                        content_length = int(file_response.headers.get('content-length', 0))
                        if content_length > max_file_size:
                            skipped_files.append((item_path, content_length))
                            print(f"Skipping {rel_path}: Content length ({content_length} bytes) exceeds limit ({max_file_size} bytes)")
                            continue
                        if file_response.status_code == 200:
                            files[rel_path] = file_response.text
                            print(f"Downloaded: {rel_path} ({file_size} bytes)")
                        else:
                            print(f"Failed to download {rel_path}: {file_response.status_code}")
                    else:
                        content_response = session.get(item["url"], headers=headers)
                        if content_response.status_code == 200:
                            content_data = content_response.json()
                            if content_data.get("encoding") == "base64" and "content" in content_data:
                                if len(content_data["content"]) * 0.75 > max_file_size:
                                    estimated_size = int(len(content_data["content"]) * 0.75)
                                    skipped_files.append((item_path, estimated_size))
                                    print(f"Skipping {rel_path}: Encoded content exceeds size limit")
                                    continue
                                files[rel_path] = base64.b64decode(content_data["content"]).decode('utf-8')
                                print(f"Downloaded: {rel_path} ({file_size} bytes)")
                            else:
                                print(f"Unexpected content format for {rel_path}")
                        else:
                            print(f"Failed to get content for {rel_path}: {content_response.status_code}")
                elif item.get("type") == "dir":
                    # Skip excluded directories
                    if exclude_patterns and any(fnmatch.fnmatch(item_path, pat) for pat in exclude_patterns):
                        continue
                    stack.append((item_path, depth + 1))

    # Start crawling from the specified path
    try:
        # Pre-check: count total files via GitHub tree API and fallback if >1000
        try:
            meta_resp = session.get(f"https://api.github.com/repos/{owner}/{repo}")
            default_branch = meta_resp.json().get('default_branch') if meta_resp.status_code == 200 else None
            if default_branch:
                tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1"
                tree_resp = session.get(tree_url, headers=headers)
                if tree_resp.status_code == 200:
                    total_files = sum(1 for e in tree_resp.json().get('tree', []) if e.get('type') == 'blob')
                    if total_files > 1000:
                        print(f"Repository file count {total_files} exceeds threshold; falling back to git clone...", flush=True)
                        raise RuntimeError("File threshold exceeded")
        except Exception:
            # any failure or threshold exceeded triggers clone fallback
            raise
        fetch_contents(specific_path)
        source = 'api'
    except (RequestException, MaxRetryError, RuntimeError) as e:
        print(f"API crawling failed: {e}\nFalling back to local git clone...", flush=True)
        if not GIT_AVAILABLE:
            print("GitPython not installed. Cannot perform local clone fallback.")
            print("Using API results collected so far.")
            return {'files': files, 'stats': {'error': "API crawling failed and GitPython not available for fallback", 'source': 'api_partial'}}
            
        source = 'git_clone'
        # persistent clone logic
        cache_root = os.path.join(tempfile.gettempdir(), "crawl_github_cache")
        os.makedirs(cache_root, exist_ok=True)
        cache_dir = os.path.join(cache_root, f"{owner}_{repo.replace('/', '_')}")
        try:
            if not os.path.isdir(cache_dir):
                print(f"Cloning {repo_url} into cache {cache_dir} (shallow)...", flush=True)
                repo = git.Repo.clone_from(repo_url, cache_dir, depth=1, single_branch=True)
            else:
                print(f"Pulling updates for {repo_url} into {cache_dir}", flush=True)
                repo = git.Repo(cache_dir)
                repo.git.pull('--ff-only')
        except Exception as clone_e:
            print(f"Persistent clone failed: {clone_e}", flush=True)
            return {'files': files, 'stats': {'error': str(clone_e), 'source': 'git_clone'}}
        
        files.clear()
        skipped_files.clear()
        root_dir = cache_dir
        if use_relative_paths:
            root_dir = os.path.join(cache_dir, os.path.normpath(specific_path))
        # walk and read files from persistent clone
        for root_, dirs, filenames in os.walk(root_dir):
            for filename in filenames:
                abs_path = os.path.join(root_, filename)
                rel_path = os.path.relpath(abs_path, root_dir) if use_relative_paths else os.path.relpath(abs_path, cache_dir)
                if not should_include_file(rel_path, filename):
                    continue
                try:
                    file_size = os.path.getsize(abs_path)
                except OSError:
                    continue
                if file_size > max_file_size:
                    skipped_files.append((rel_path, file_size))
                    continue
                try:
                    with open(abs_path, 'r', encoding='utf-8') as f:
                        files[rel_path] = f.read()
                        print(f"Cloned and added: {rel_path} ({file_size} bytes)", flush=True)
                except Exception as read_e:
                    print(f"Failed to read {rel_path}: {read_e}", flush=True)

    return {
        'files': files,
        'stats': {
            'downloaded_count': len(files),
            'skipped_count': len(skipped_files),
            'skipped_files': skipped_files,
            'base_path': specific_path if use_relative_paths else None,
            'include_patterns': include_patterns,
            'exclude_patterns': exclude_patterns,
            'source': source
        }
    }

if __name__ == "__main__":
    # Get token from environment variable (recommended for private repos)
    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        print("Warning: No GitHub token found in environment variable 'GITHUB_TOKEN'.\n"
              "Private repositories will not be accessible without a token.\n"
              "To access private repos, set the environment variable or pass the token explicitly.")
    
    repo_url = "https://github.com/pydantic/pydantic"
    
    # Example: Get Python and Markdown files, but exclude test files
    result = crawl_github_files(
        repo_url, 
        token=github_token,
        max_file_size=1 * 1024 * 1024,  # 1 MB in bytes
        use_relative_paths=True,  # Enable relative paths
        include_patterns={"*.py", "*.md"},  # Include Python and Markdown files
    )
    
    files = result["files"]
    stats = result["stats"]
    
    print(f"\nDownloaded {stats['downloaded_count']} files.")
    print(f"Skipped {stats['skipped_count']} files due to size limits or patterns.")
    print(f"Base path for relative paths: {stats['base_path']}")
    print(f"Include patterns: {stats['include_patterns']}")
    print(f"Exclude patterns: {stats['exclude_patterns']}")
    
    # Display all file paths in the dictionary
    print("\nFiles in dictionary:")
    for file_path in sorted(files.keys()):
        print(f"  {file_path}")
    
    # Example: accessing content of a specific file
    if files:
        sample_file = next(iter(files))
        print(f"\nSample file: {sample_file}")
        print(f"Content preview: {files[sample_file][:200]}...") 