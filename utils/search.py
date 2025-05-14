"""
Search utilities for Repository Analysis to MCP Server system.
"""

import os
import json
import sys
import time  # Added time module import for sleep functionality
import random  # For random user agent selection
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urlparse

from .llm import call_llm
from .monitoring import log_execution_time
from .github import extract_github_urls

# Check if yt-dlp is installed
try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    print("yt-dlp not installed. Install with: pip install -U yt-dlp")
    YT_DLP_AVAILABLE = False

# Check if Search-Engines-Scraper is installed
SEARCH_ENGINES_AVAILABLE = None
try:
    # First try the SearchEngines class approach
    try:
        from search_engines_scraper import SearchEngines
        SEARCH_ENGINES_AVAILABLE = "class" 
    except ImportError:
        # Try individual engines approach
        try:
            from search_engines import Google, Bing, Yahoo, Duckduckgo
            SEARCH_ENGINES_AVAILABLE = "individual"
        except ImportError:
            SEARCH_ENGINES_AVAILABLE = None
except ImportError:
    print("Search-Engines-Scraper not installed. Install with: pip install -U git+https://github.com/tasos-py/Search-Engines-Scraper.git")
    SEARCH_ENGINES_AVAILABLE = None

# Check if requests is installed for scraping
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    print("requests not installed. Install with: pip install requests")
    REQUESTS_AVAILABLE = False

# Check if BeautifulSoup is installed for HTML parsing
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    print("BeautifulSoup not installed. Install with: pip install beautifulsoup4")
    BS4_AVAILABLE = False

@log_execution_time("web_search")
def search_web(query: str, max_results: int = 10, keywords: List[str] = None, 
               tech_stack: List[str] = None, features: List[str] = None) -> List[Dict[str, str]]:
    """
    Searches the web for relevant content using Search-Engines-Scraper.
    
    Args:
        query: Search query
        max_results: Maximum number of results to return
        keywords: List of keywords to focus search on
        tech_stack: List of technologies to focus search on
        features: List of features to focus search on
        
    Returns:
        List of result dictionaries with title, url, and snippet
    """
    if not SEARCH_ENGINES_AVAILABLE:
        raise ImportError("Search-Engines-Scraper is required for web search. Install with: pip install -U git+https://github.com/tasos-py/Search-Engines-Scraper.git")
    
    # Enhance query with keywords, tech_stack, and features if provided
    enhanced_query = query
    if keywords or tech_stack or features:
        additional_terms = []
        if keywords:
            additional_terms.extend(keywords[:2])  # Add top 2 keywords
        if tech_stack:
            additional_terms.extend([f"{tech} github" for tech in tech_stack[:2]])  # Add top 2 technologies
        if features:
            additional_terms.extend([f"{feature} implementation" for feature in features[:2]])  # Add top 2 features
            
        # Add GitHub-specific terms to improve repository finding
        additional_terms.append("github repository")
        enhanced_query = f"{query} {' '.join(additional_terms)}"
    
    results = []
    
    # Use the SearchEngines class if available, otherwise use individual engines
    if SEARCH_ENGINES_AVAILABLE == "class":
        from search_engines_scraper import SearchEngines
        
        # Initialize with multiple engines for better coverage
        engines = ["google", "bing", "duckduckgo"]
        search = SearchEngines(engines)
        
        # Execute search
        search_results = search.search(enhanced_query, pages=1)  # Get first page of results
        
        # Process and format results
        for engine, engine_results in search_results.items():
            for result in engine_results[:max_results]:
                if len(results) >= max_results:
                    break
                    
                # Extract relevant information
                title = result.get('title', '')
                url = result.get('url', '')
                snippet = result.get('description', '')
                source = extract_domain(url)
                
                if title and url and snippet:
                    results.append({
                        "title": title,
                        "url": url,
                        "snippet": snippet,
                        "source": source
                    })
            
            if len(results) >= max_results:
                break
    else:
        # Use individual engines approach as fallback
        from search_engines import Google, Bing, Duckduckgo
        engines = [Google(), Bing(), Duckduckgo()]
        
        for engine in engines:
            if len(results) >= max_results:
                break
                
            engine.search(enhanced_query, pages=1)  # Get just the first page of results
            search_results = engine.results
            
            # Limit number of results from each engine
            for result in search_results[:max_results]:
                if len(results) >= max_results:
                    break
                    
                # Extract relevant information
                title = result.get('title', '')
                url = result.get('link', '')
                snippet = result.get('text', '')
                source = extract_domain(url)
                
                if title and url and snippet:
                    results.append({
                        "title": title,
                        "url": url,
                        "snippet": snippet,
                        "source": source
                    })
    
    return results[:max_results]

@log_execution_time("youtube_search")
def search_youtube(query: str, max_results: int = 5, keywords: List[str] = None, 
                 tech_stack: List[str] = None, features: List[str] = None) -> List[Dict[str, str]]:
    """
    Searches YouTube for relevant videos using yt-dlp with focus on GitHub repositories.
    
    Args:
        query: Search query
        max_results: Maximum number of results to return
        keywords: List of keywords to focus search on
        tech_stack: List of technologies to focus search on
        features: List of features to focus search on
        
    Returns:
        List of result dictionaries with title, url, and description
    """
    if not YT_DLP_AVAILABLE:
        raise ImportError("yt-dlp is required for YouTube search. Install with: pip install -U yt-dlp")
    
    # Enhance query with keywords, tech_stack, and features if provided
    enhanced_query = query
    if keywords or tech_stack or features:
        additional_terms = []
        if keywords:
            additional_terms.extend(keywords[:2])  # Add top 2 keywords
        if tech_stack:
            additional_terms.extend([f"{tech}" for tech in tech_stack[:2]])  # Add top 2 technologies
        if features:
            additional_terms.extend([f"{feature}" for feature in features[:2]])  # Add top 2 features
            
        # Add GitHub-specific terms to improve repository finding
        additional_terms.append("github repository tutorial")
        enhanced_query = f"{query} {' '.join(additional_terms)}"
    
    # Configure yt-dlp options for more metadata
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'force_generic_extractor': True,
        'ignoreerrors': True,
        'no_warnings': True,
        'skip_download': True,
        'format': 'best',
        'getdescription': True,  # Get full video descriptions 
        'get_title': True,       # Ensure we get video titles
        'get_thumbnail': True,   # Get thumbnail URLs
        'get_duration': True,    # Get video durations
        'get_filename': True,    # Get video filenames
        'no_color': True,        # Disable color codes in output
        'playlistend': max_results, # Limit the number of results
    }
    
    # Format the search query for yt-dlp
    search_query = f"ytsearch{max_results}:{enhanced_query}"
    
    # Perform the search
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(search_query, download=False)
        if 'entries' not in info_dict:
            return []
            
        results = []
        for entry in info_dict['entries']:
            if entry is None:
                continue
                
            video_id = entry.get('id')
            if not video_id:
                continue
                
            title = entry.get('title', '')
            url = f"https://www.youtube.com/watch?v={video_id}"
            description = entry.get('description', '')
            channel = entry.get('channel', entry.get('uploader', ''))
            upload_date = entry.get('upload_date', '')
            thumbnail = entry.get('thumbnail', '')
            duration = entry.get('duration', 0)
            
            # Try to extract GitHub URLs from description immediately
            github_urls = extract_github_urls(description) if description else []
            
            results.append({
                "title": title,
                "url": url,
                "snippet": description or f"YouTube video: {title}",
                "channel": channel,
                "upload_date": upload_date,
                "thumbnail": thumbnail,
                "duration": duration,
                "github_urls": github_urls,  # Include any immediately found GitHub URLs
                "has_github_url": bool(github_urls)  # Flag for videos with GitHub URLs
            })
            
        return results

@log_execution_time("scrape_youtube")
def scrape_youtube_video(video_url: str) -> Dict[str, Any]:
    """
    Scrapes detailed information from a YouTube video using yt-dlp.
    Specifically focuses on extracting GitHub URLs from description and comments.
    
    Args:
        video_url: YouTube video URL
        
    Returns:
        Dictionary with video details and extracted GitHub URLs
    """
    if not YT_DLP_AVAILABLE:
        raise ImportError("yt-dlp is required for YouTube video scraping. Install with: pip install -U yt-dlp")
    
    # Initialize with default values and assume failure until proven otherwise
    video_data = {
        "title": "",
        "uploader": "",
        "upload_date": "",
        "view_count": 0,
        "duration": 0,
        "description": "",
        "comments": [],
        "github_urls": [],
        "other_potential_repo_links": [],
        "scrape_failed": True  # Assume failure until proven otherwise
    }
    
    try:
        # Configure yt-dlp options to extract comments and detailed info
        ydl_opts = {
            'quiet': True,
            'ignoreerrors': True,
            'no_warnings': True,
            'writeinfojson': True,
            'getcomments': True,
            'getdescription': True,
            'get_title': True,
            'get_id': True,
            'no_color': True,
            'skip_download': True,
            'format': 'best', # Just to avoid errors, not actually downloading
            'extract_flat': False, # We want full info, not just playlist metadata
            'extractor_args': {'youtube': {'skip': ['dash', 'hls']}}  # Skip streams for speed
        }
        
        # Extract video information
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            if not info:
                print(f"  Failed to extract info from {video_url}")
                return video_data
            
            # Extract basic video information
            video_data["title"] = info.get('title', '')
            video_data["description"] = info.get('description', '')
            video_data["uploader"] = info.get('uploader', '')
            video_data["view_count"] = info.get('view_count', 0)
            video_data["upload_date"] = info.get('upload_date', '')
            video_data["duration"] = info.get('duration', 0)
        
            # Extract comments if available
            comments = []
            comments_data = info.get('comments', [])
            for comment in comments_data[:30]:  # Check more comments for GitHub URLs
                if isinstance(comment, dict):
                    comment_text = comment.get('text', '')
                    if comment_text:
                        comments.append(comment_text)
                elif isinstance(comment, str):
                    comments.append(comment)
        
            video_data["comments"] = comments
            
            # Try to extract GitHub URLs from description
            description_urls = extract_github_urls(video_data["description"]) if video_data["description"] else []
        
            # Try to extract GitHub URLs from comments - all comments are now strings
            comment_text = "\n".join(comments)
            comment_urls = extract_github_urls(comment_text) if comment_text else []
        
            # Combine and deduplicate GitHub URLs
            all_github_urls = list(set(description_urls + comment_urls))
            video_data["github_urls"] = all_github_urls
        
            # Extract other links from description that might be GitHub repository references
            # but weren't caught by the regex pattern
            other_links = []
            if video_data["description"]:
                for line in video_data["description"].split('\n'):
                    if 'http' in line and 'git' in line.lower():
                        other_links.append(line.strip())
        
            video_data["other_potential_repo_links"] = other_links
            video_data["scrape_failed"] = False  # Mark scrape as successful
            
            return video_data
            
    except Exception as e:
        print(f"  Error scraping YouTube video {video_url}: {str(e)}")
        return video_data  # Return with scrape_failed=True

@log_execution_time("scrape_webpage")
def scrape_webpage(url: str, max_retries: int = 2) -> Dict[str, Any]:
    """
    Scrapes a webpage to extract content and GitHub URLs.
    Focuses specifically on finding GitHub repository references.
    Includes retry mechanism with fixed 5-second delay between retries for handling 403 errors.
    
    Args:
        url: Webpage URL
        max_retries: Maximum number of retry attempts (default: 2)
        
    Returns:
        Dictionary with page content and extracted GitHub URLs
    """
    if not REQUESTS_AVAILABLE:
        raise ImportError("requests is required for webpage scraping. Install with: pip install requests")
    
    if not BS4_AVAILABLE:
        raise ImportError("BeautifulSoup4 is required for webpage parsing. Install with: pip install beautifulsoup4")
    
    # Initialize with default values
    page_data = {
        "title": "",
        "content": "",
        "links": [],
        "github_urls": [],
        "code_blocks": [],
        "scrape_failed": True  # Assume failure until proven otherwise
    }
    
    # Auto-detect if URL is GitHub
    if "github.com" in url and "/blob/" not in url:
        # If it's already a GitHub repository
        page_data["github_urls"] = [url]
        page_data["scrape_failed"] = False
        return page_data
    
    for attempt in range(max_retries + 1):
        try:
            # Select user agent using centralized function
            headers = {
                'User-Agent': get_random_user_agent(attempt),
                'Accept': 'text/html,application/xhtml+xml,application/xml',
                'Accept-Language': 'en-US,en;q=0.9',
            }
            
            # Log retry attempts
            if attempt > 0:
                print(f"  Retry attempt {attempt}/{max_retries} for {url}")
                print("  Waiting 5 seconds before retry...")
                time.sleep(5)  # Fixed 5-second delay between retries
            
            # Make the request
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()  # Raise an exception for 4XX/5XX status codes
            
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract page title
            title = soup.title.string if soup.title else ""
            
            # Extract main content (prioritize article tags, main, or body)
            content_tags = soup.select('article, main, .content, .post, .entry, #content')
            if content_tags:
                content = content_tags[0].get_text(strip=True)
            else:
                content = soup.body.get_text(strip=True) if soup.body else ""
            
            # Limit content to avoid excessively large responses
            content = content[:5000] + "..." if len(content) > 5000 else content
            
            # Extract all links
            links = []
            for a_tag in soup.find_all('a', href=True):
                link_text = a_tag.get_text(strip=True)
                href = a_tag['href']
                
                # Convert relative URLs to absolute
                if href.startswith('/') and not href.startswith('//'):
                    parsed_url = urlparse(url)
                    href = f"{parsed_url.scheme}://{parsed_url.netloc}{href}"
                elif not (href.startswith('http://') or href.startswith('https://')):
                    # Skip javascript: and other non-http links
                    continue
                
                links.append({
                    "url": href,
                    "text": link_text[:100]  # Truncate long link text
                })
            
            # Extract GitHub URLs
            github_urls = extract_github_urls(response.text)
            
            # Extract code blocks that might contain GitHub references
            code_blocks = []
            for code_tag in soup.select('pre, code, .highlight'):
                code_text = code_tag.get_text(strip=True)
                if "github.com" in code_text and len(code_text) < 2000:  # Limit size
                    code_blocks.append(code_text)
                    # Also check for GitHub URLs in code blocks
                    code_github_urls = extract_github_urls(code_text)
                    if code_github_urls:
                        github_urls.extend(code_github_urls)
            
            # Deduplicate GitHub URLs
            github_urls = list(set(github_urls))
            
            # Update page data
            page_data = {
                "title": title,
                "content": content,
                "links": links,
                "github_urls": github_urls,
                "code_blocks": code_blocks,
                "scrape_failed": False  # Scraping was successful
            }
            
            return page_data
            
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if hasattr(e, 'response') else 0
            
            if status_code == 403:
                print(f"  Received 403 Forbidden error from {url}")
            else:
                print(f"  HTTP error {status_code} when scraping {url}: {str(e)}")
            
            # If we've exhausted retry attempts, return with scrape_failed flag
            if attempt == max_retries:
                return page_data
                
        except Exception as e:
            print(f"  Error scraping {url}: {str(e)}")
            
            # If we've exhausted retry attempts, return with scrape_failed flag
            if attempt == max_retries:
                return page_data
    
    # If we reach here, all retry attempts have failed
    return page_data

def extract_domain(url: str) -> str:
    """
    Extract the domain name from a URL.
    
    Args:
        url: URL to extract domain from
        
    Returns:
        Domain name
    """
    try:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        # Remove www. prefix if present
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except:
        return url

def get_random_user_agent(index=None):
    """
    Get a user agent from a predefined list, optionally by index.
    
    Args:
        index: Optional index to select a specific user agent
        
    Returns:
        User agent string
    """
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:90.0) Gecko/20100101 Firefox/90.0',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59'
    ]
    
    if index is not None:
        return user_agents[index % len(user_agents)]
    
    return random.choice(user_agents)

def check_content_relevance(content: Dict[str, str], 
                         keywords: List[str] = None, 
                         tech_stack: List[str] = None, 
                         features: List[str] = None,
                         threshold: float = 0.5) -> Dict[str, Any]:
    """
    Checks if content is relevant based on keywords, tech stack, and features.
    
    Args:
        content: Dictionary with content info (title, url, snippet)
        keywords: List of keywords to check against
        tech_stack: List of technologies to check against
        features: List of features to check against
        threshold: Minimum relevance score (0-1)
        
    Returns:
        Dictionary with relevance analysis including:
        - is_relevant: Boolean indicating if content is relevant
        - relevance_score: Score between 0-1
        - matched_keywords: List of matched keywords
        - matched_tech: List of matched technologies
        - matched_features: List of matched features
        - reasoning: Explanation of relevance determination
    """
    # Initialize empty lists if not provided
    keywords = keywords or []
    tech_stack = tech_stack or []
    features = features or []
    
    # Combine title and snippet for checking
    text = f"{content.get('title', '')} {content.get('snippet', '')}"
    text = text.lower()
    
    # Find matches
    matched_keywords = [kw for kw in keywords if kw.lower() in text]
    matched_tech = [tech for tech in tech_stack if tech.lower() in text]
    matched_features = [feature for feature in features if feature.lower() in text]
    
    # Already extracted GitHub URLs if available
    has_github_urls = "github_urls" in content and bool(content["github_urls"])
    github_url_in_text = "github.com" in text
    
    # Calculate weights for different match types
    # GitHub URLs are most important, followed by features, tech stack, and keywords
    weights = {
        "github_urls": 0.4,  # 40% weight for GitHub URLs
        "features": 0.3,     # 30% weight for features
        "tech_stack": 0.2,   # 20% weight for tech stack
        "keywords": 0.1      # 10% weight for general keywords
    }
    
    # Calculate weighted score components
    github_score = weights["github_urls"] if (has_github_urls or github_url_in_text) else 0
    
    feature_score = 0
    if features:
        feature_score = weights["features"] * (len(matched_features) / len(features))
        
    tech_score = 0
    if tech_stack:
        tech_score = weights["tech_stack"] * (len(matched_tech) / len(tech_stack))
        
    keyword_score = 0
    if keywords:
        keyword_score = weights["keywords"] * (len(matched_keywords) / len(keywords))
    
    # Calculate overall relevance score
    relevance_score = github_score + feature_score + tech_score + keyword_score
    
    # Generate reasoning
    reasoning = []
    if has_github_urls or github_url_in_text:
        reasoning.append("Contains GitHub repository URLs")
    if matched_features:
        reasoning.append(f"Matches features: {', '.join(matched_features)}")
    if matched_tech:
        reasoning.append(f"Matches technologies: {', '.join(matched_tech)}")
    if matched_keywords:
        reasoning.append(f"Matches keywords: {', '.join(matched_keywords)}")
    
    is_relevant = relevance_score >= threshold
    
    return {
        "is_relevant": is_relevant,
        "relevance_score": relevance_score,
        "matched_keywords": matched_keywords,
        "matched_tech": matched_tech,
        "matched_features": matched_features,
        "has_github_urls": has_github_urls or github_url_in_text,
        "reasoning": "; ".join(reasoning) if reasoning else "No relevant matches found"
    }

def check_content_relevance_with_llm(content: Dict[str, str], 
                                query: str,
                                keywords: List[str] = None, 
                                tech_stack: List[str] = None, 
                                features: List[str] = None,
                                threshold: float = 0.5) -> Dict[str, Any]:
    """
    Uses LLM to check if content is relevant based on the query, keywords, tech stack, and features.
    Falls back to algorithm-based relevance checking if the LLM fails.
    
    Args:
        content: Dictionary with content info (title, url, snippet)
        query: The original or refined search query
        keywords: List of keywords to check against
        tech_stack: List of technologies to check against
        features: List of features to check against
        threshold: Minimum relevance score (0-1)
        
    Returns:
        Dictionary with relevance analysis
    """
    # Initialize empty lists if not provided
    keywords = keywords or []
    tech_stack = tech_stack or []
    features = features or []
    
    # Extract content to analyze
    title = content.get('title', '')
    snippet = content.get('snippet', '')
    url = content.get('url', '')
    
    # First check if we already know it has GitHub URLs - automatic relevance
    has_github_urls = "github_urls" in content and bool(content["github_urls"])
    if has_github_urls:
        return {
            "is_relevant": True,
            "relevance_score": 0.9,
            "matched_keywords": keywords,
            "matched_tech": tech_stack,
            "matched_features": features,
            "has_github_urls": True,
            "reasoning": "Already contains GitHub repository URLs"
        }
    
    # If snippet is too short or missing, fall back to algorithmic approach
    if not snippet or len(snippet) < 50:
        return check_content_relevance(content, keywords, tech_stack, features, threshold)
    
    # Keep snippet length reasonable for the LLM
    snippet_preview = snippet[:1000] + ("..." if len(snippet) > 1000 else "")
    
    # Format lists for the prompt
    keywords_str = ", ".join(keywords) if keywords else "None specified"
    tech_stack_str = ", ".join(tech_stack) if tech_stack else "None specified"
    features_str = ", ".join(features) if features else "None specified"
    
    prompt = f"""
    Assess if this content is relevant to the user's search for GitHub repositories:
    
    Content title: {title}
    Content URL: {url}
    Content snippet: {snippet_preview}
    
    User is looking for:
    - Query: {query}
    - Keywords: {keywords_str}
    - Technologies: {tech_stack_str}
    - Features: {features_str}
    
    Determine if this content is likely to:
    1. Contain or link to GitHub repositories
    2. Discuss implementations of the requested technologies
    3. Cover the desired features
    
    Respond with a JSON object in this exact format:
    {{
      "is_relevant": true/false,
      "relevance_score": 0.0-1.0,
      "reasoning": "brief explanation"
    }}
    """
    
    try:
        response = call_llm(prompt, temperature=0.1)
        # Extract JSON from the response
        import json
        import re
        
        # Find JSON object in the response using regex
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            json_str = json_match.group(0)
            result = json.loads(json_str)
            
            # Validate result structure
            if "is_relevant" in result and "relevance_score" in result:
                # Add the fields from the normal relevance check for consistency
                result["matched_keywords"] = keywords
                result["matched_tech"] = tech_stack
                result["matched_features"] = features
                result["has_github_urls"] = "github.com" in snippet.lower()
                return result
    
    except Exception as e:
        print(f"LLM-based relevance check failed: {str(e)}")
    
    # Fallback to algorithmic approach
    return check_content_relevance(content, keywords, tech_stack, features, threshold)

def search_and_scrape(query: str, 
                     keywords: List[str] = None, 
                     tech_stack: List[str] = None,
                     features: List[str] = None,
                     youtube_count: int = 5, 
                     web_count: int = 5,
                     use_youtube: bool = True,
                     use_web: bool = True,
                     use_llm: bool = True,
                     setup_llm_first: bool = True,
                     threshold: float = 0.5) -> Dict[str, Any]:
    """
    Performs search and scrape process to find GitHub repositories.
    Combines YouTube and web search, with scraping to extract GitHub URLs.
    
    Args:
        query: Search query
        keywords: Keywords for relevance filtering
        tech_stack: Technologies for relevance filtering
        features: Features for relevance filtering
        youtube_count: Number of YouTube videos to search
        web_count: Number of web pages to search
        use_youtube: Whether to include YouTube search
        use_web: Whether to include web search
        use_llm: Whether to use LLM enhancements
        setup_llm_first: Whether to set up LLM before searching or defer to caller
        threshold: Minimum relevance score (0.0-1.0) for filtering results
        
    Returns:
        Dictionary with search results and extracted GitHub URLs
    """
    # Initialize empty lists if None
    keywords = keywords or []
    tech_stack = tech_stack or []
    features = features or []
    
    # Tracking variables
    youtube_results = []
    web_results = []
    all_github_urls = []
    scrape_failure_count = 0
    total_scrape_attempts = 0
    relevance_scores = []
    
    # Skip LLM refinement if setup_llm_first is False
    refined_query = query
    if use_llm and setup_llm_first:
        refined_query = refine_search_query(query, keywords, tech_stack, features)
        print(f"Refined query: {refined_query}")
    
    # Search and scrape YouTube videos
    if use_youtube and youtube_count > 0:
        print(f"Searching YouTube for: {refined_query}")
        videos = search_youtube(refined_query, max_results=youtube_count, 
                              keywords=keywords, tech_stack=tech_stack, features=features)
        
        for i, video in enumerate(videos):
            print(f"Scraping YouTube video {i+1}/{len(videos)}: {video['title']}")
            
            # Check relevance with standard or LLM-enhanced method
            if use_llm and setup_llm_first:
                relevance = check_content_relevance_with_llm(
                    video, refined_query, keywords, tech_stack, features, threshold=threshold
                )
            else:
                relevance = check_content_relevance(
                    video, keywords, tech_stack, features, threshold=threshold
                )
            
            # Track relevance scores for reporting
            relevance_scores.append(relevance['relevance_score'])
            
            if relevance["is_relevant"]:
                print(f"  Relevance: {relevance['relevance_score']:.2f} - {relevance['reasoning']}")
                
                total_scrape_attempts += 1
                video_data = scrape_youtube_video(video['url'])
                
                # Check if scraping failed
                if video_data.get('scrape_failed', False):
                    scrape_failure_count += 1
                    print(f"  Scraping failed for YouTube video {video['url']} - skipping to next video")
                    continue
                
                # Try enhanced URL extraction if enabled and no URLs found
                if use_llm and setup_llm_first and not video_data.get('github_urls'):
                    # Try LLM-enhanced extraction from description
                    description = video_data.get('description', '')
                    llm_urls_desc = extract_github_urls_with_llm(description)
                    
                    # Try LLM-enhanced extraction from comments
                    comments = video_data.get('comments', [])
                    
                    # Handle both list of strings and list of dictionaries
                    comment_texts = []
                    for c in comments[:5]:
                        if isinstance(c, dict):
                            comment_texts.append(c.get('text', ''))
                        elif isinstance(c, str):
                            comment_texts.append(c)
                    
                    comment_text = "\n".join(comment_texts)
                    llm_urls_comments = extract_github_urls_with_llm(comment_text)
                    
                    # Combine URLs from both sources
                    llm_urls = llm_urls_desc + llm_urls_comments
                    if llm_urls:
                        video_data['github_urls'] = llm_urls
                
                github_urls = video_data.get('github_urls', [])
                
                print(f"  GitHub URLs from scraping: {len(github_urls)}")
                
                if github_urls:
                    video['github_urls'] = github_urls
                    all_github_urls.extend(github_urls)
                    youtube_results.append(video)
                else:
                    print(f"  No GitHub URLs found in video {i+1}")
            else:
                print(f"  Skipping (not relevant): {relevance['reasoning']}")
    
    # Search and scrape web pages
    if use_web and web_count > 0:
        print(f"\nSearching web for: {refined_query}")
        pages = search_web(refined_query, max_results=web_count, 
                         keywords=keywords, tech_stack=tech_stack, features=features)
        
        for i, page in enumerate(pages):
            print(f"Scraping web page {i+1}/{len(pages)}: {page['title']}")
            
            # Check relevance with standard or LLM-enhanced method
            if use_llm and setup_llm_first:
                relevance = check_content_relevance_with_llm(
                    page, refined_query, keywords, tech_stack, features, threshold=threshold
                )
            else:
                relevance = check_content_relevance(
                    page, keywords, tech_stack, features, threshold=threshold
                )
            
            # Track relevance scores for reporting
            relevance_scores.append(relevance['relevance_score'])
            
            if relevance["is_relevant"]:
                print(f"  Relevance: {relevance['relevance_score']:.2f} - {relevance['reasoning']}")
                
                total_scrape_attempts += 1
                page_data = scrape_webpage(page['url'])
                
                # Check if scraping failed
                if page_data.get('scrape_failed', False):
                    scrape_failure_count += 1
                    print(f"  Scraping failed for web page {page['url']} - skipping to next page")
                    continue
                
                # Try enhanced URL extraction if enabled and no URLs found
                if use_llm and setup_llm_first and not page_data.get('github_urls'):
                    # Use LLM to extract GitHub URLs
                    page_text = page_data.get('text', '')
                    llm_urls = extract_github_urls_with_llm(page_text[:5000])  # Limit text length for LLM
                    if llm_urls:
                        page_data['github_urls'] = llm_urls
                
                github_urls = page_data.get('github_urls', [])
                
                print(f"  GitHub URLs from scraping: {len(github_urls)}")
                
                if github_urls:
                    page['github_urls'] = github_urls
                    all_github_urls.extend(github_urls)
                    web_results.append(page)
                else:
                    print(f"  No GitHub URLs found in page {i+1}")
            else:
                print(f"  Skipping (not relevant): {relevance['reasoning']}")
    
    # Deduplicate GitHub URLs
    unique_github_urls = list(set(all_github_urls))
    
    # Calculate average relevance score if available
    avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0
    
    # Skip repo quality assessment if not using LLM or deferring setup
    repos_with_quality = []
    if use_llm and setup_llm_first:
        print("Assessing repository quality...")
        for url in unique_github_urls:
            quality = assess_repository_quality(url, query, features)
            repos_with_quality.append({
                "url": url,
                "relevance_score": quality.get("relevance_score", 0.5),
                "quality_score": quality.get("quality_score", 0.5),
                "reasoning": quality.get("reasoning", "")
            })
        
        # Sort repos by relevance and quality
        repos_with_quality.sort(key=lambda x: (x["relevance_score"] + x["quality_score"]), reverse=True)
        
        # Update the list of URLs to be in quality order
        unique_github_urls = [repo["url"] for repo in repos_with_quality]
    
    print(f"\nSearch complete. Found {len(unique_github_urls)} unique GitHub repositories.")
    if scrape_failure_count > 0:
        print(f"Scraping failed for {scrape_failure_count} out of {total_scrape_attempts} pages/videos.")
    
    return {
        "query": query,
        "refined_query": refined_query,
        "keywords": keywords,
        "tech_stack": tech_stack,
        "features": features,
        "youtube_results": youtube_results,
        "web_results": web_results,
        "github_urls": unique_github_urls,
        "repos_with_quality": repos_with_quality,
        "total_github_urls": len(unique_github_urls),
        "llm_enhanced": use_llm and setup_llm_first,
        "average_relevance": avg_relevance,
        "scrape_success_rate": 1 - (scrape_failure_count / total_scrape_attempts) if total_scrape_attempts > 0 else 0
    }

def interactive_search(initial_query=None) -> Dict[str, Any]:
    """
    Interactive search mode with detailed configuration options.
    Allows users to set keywords, tech stack, and features, then collects
    all inputs for search configuration.
    
    When called from main.py, this function only collects user inputs but
    doesn't process them with LLM - that happens after LLM setup.
    
    Args:
        initial_query: Optional initial query to use as default
        
    Returns:
        Dictionary with search parameters (NOT results, just configuration)
    """
    print("\n=== GitHub Repository Finder: Interactive Search ===\n")
    
    # Step 1: Get the base query
    if initial_query:
        print(f"Using query: {initial_query}")
        query = initial_query
    else:
        query = input("Enter your search query: ")
    
    # Step 2: Get keywords
    print("\nEnter keywords to filter results (separated by commas):")
    print("Example: authentication, backend, api")
    keywords_input = input("Keywords: ")
    keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]
    
    # Step 3: Get tech stack
    print("\nEnter tech stack components (separated by commas):")
    print("Example: Node.js, Express, MongoDB")
    tech_input = input("Tech stack: ")
    tech_stack = [t.strip() for t in tech_input.split(",") if t.strip()]
    
    # Step 4: Get features
    print("\nEnter specific features you're looking for (separated by commas):")
    print("Example: JWT authentication, password reset, OAuth")
    features_input = input("Features: ")
    features = [f.strip() for f in features_input.split(",") if f.strip()]
    
    # Step 5: Configure search options
    print("\n=== Search Configuration ===")
    
    # YouTube search
    use_youtube = input("Include YouTube search? (y/n, default: y): ").lower() != "n"
    youtube_count = 5
    if use_youtube:
        try:
            count = input("Number of YouTube videos to search (default: 5): ")
            if count.strip():
                youtube_count = int(count)
        except ValueError:
            print("Invalid number. Using default: 5")
    
    # Web search
    use_web = input("Include web search? (y/n, default: y): ").lower() != "n"
    web_count = 10
    if use_web:
        try:
            count = input("Number of web pages to search (default: 10): ")
            if count.strip():
                web_count = int(count)
        except ValueError:
            print("Invalid number. Using default: 10")
    
    # LLM enhancement
    use_llm = input("Use LLM to enhance results and evaluate quality? (y/n, default: y): ").lower() != "n"
    
    # Relevance threshold
    relevance_threshold = 0.5
    if use_youtube or use_web:
        try:
            threshold_input = input("Set relevance threshold (0.0-1.0, default: 0.5): ")
            if threshold_input.strip():
                input_value = float(threshold_input)
                if 0.0 <= input_value <= 1.0:
                    relevance_threshold = input_value
                else:
                    print("Invalid threshold (must be between 0.0 and 1.0). Using default: 0.5")
        except ValueError:
            print("Invalid threshold format. Using default: 0.5")
    
    # Summary before execution
    print("\n=== Search Summary ===")
    print(f"Query: {query}")
    print(f"Keywords: {', '.join(keywords) if keywords else 'None'}")
    print(f"Tech Stack: {', '.join(tech_stack) if tech_stack else 'None'}")
    print(f"Features: {', '.join(features) if features else 'None'}")
    print(f"YouTube Search: {'Enabled' if use_youtube else 'Disabled'}{f' ({youtube_count} videos)' if use_youtube else ''}")
    print(f"Web Search: {'Enabled' if use_web else 'Disabled'}{f' ({web_count} pages)' if use_web else ''}")
    print(f"LLM Enhancement: {'Enabled' if use_llm else 'Disabled'}")
    print(f"Relevance Threshold: {relevance_threshold}")
    
    if input("\nProceed with search? (y/n, default: y): ").lower() == "n":
        print("Search canceled.")
        return {}
    
    print("\nPreparing search configuration...")
    
    # Return the parameters without processing them
    # The processing will be done after LLM setup in main.py
    return {
        "query": query,
        "keywords": keywords,
        "tech_stack": tech_stack,
        "features": features,
        "youtube_count": youtube_count,
        "web_count": web_count,
        "use_youtube": use_youtube,
        "use_web": use_web,
        "use_llm": use_llm,
        "relevance_threshold": relevance_threshold
    }

def refine_search_query(query: str, keywords: List[str] = None, 
                       tech_stack: List[str] = None, features: List[str] = None) -> str:
    """
    Uses LLM to refine the search query to be more effective at finding relevant GitHub repositories.
    
    Args:
        query: Original search query
        keywords: List of keywords for context
        tech_stack: List of technologies being searched for
        features: List of features being searched for
        
    Returns:
        Refined search query optimized for finding relevant GitHub repositories
    """
    # Skip refinement if the original query is very short
    if not query or len(query) < 5:
        return query
        
    # Format lists for the prompt
    keywords_str = ", ".join(keywords) if keywords else "None specified"
    tech_stack_str = ", ".join(tech_stack) if tech_stack else "None specified"
    features_str = ", ".join(features) if features else "None specified"
    
    prompt = f"""
    Refine this search query to find GitHub repositories:
    
    Original query: {query}
    Keywords: {keywords_str}
    Technologies: {tech_stack_str}
    Desired features: {features_str}
    
    Create a search query that will effectively find GitHub repositories 
    with relevant code implementations. Focus on the core technologies and features.
    The query should be concise (under 10 words) and highly specific.
    Use common technical terminology that would likely appear in repository descriptions.
    
    Return only the optimized search query text without any explanations or quotes.
    """
    
    try:
        refined_query = call_llm(prompt, temperature=0.3)
        # Remove any quotes or extra formatting the LLM might add
        refined_query = refined_query.strip(' "\'\n')
        
        # If the refinement is valid and not too long, use it
        if refined_query and 5 <= len(refined_query) <= 100:
            print(f"Refined query: '{refined_query}' (original: '{query}')")
            return refined_query
        else:
            return query
    except Exception as e:
        print(f"Query refinement failed: {str(e)}")
        return query

def extract_github_urls_with_llm(text: str) -> List[str]:
    """
    Extract GitHub repository URLs from text using LLM when regex doesn't find any.
    
    Args:
        text: Text to extract GitHub URLs from
        
    Returns:
        List of GitHub repository URLs found in the text
    """
    if not text:
        return []
        
    # First use standard regex extraction (more efficient)
    from .github import extract_github_urls
    regex_urls = extract_github_urls(text)
    
    # If regex found URLs, return them
    if regex_urls:
        return regex_urls
    
    # Only use LLM if the text is reasonable in length (to save tokens)
    if len(text) > 10000:
        # For very long text, just return empty list as LLM would be too expensive
        return []
    
    # Use shorter preview for very long text
    text_preview = text[:8000] if len(text) > 8000 else text
    
    prompt = f"""
    Extract all GitHub repository URLs from this text. Only return valid GitHub 
    repository URLs (i.e., https://github.com/username/repository).
    
    Instructions:
    1. Look for GitHub repository URLs in any format
    2. Include URLs that may be in markdown format like [repo](https://github.com/user/repo)
    3. Also look for phrases like "github repo: user/repo" or "git clone https://github.com/user/repo"
    
    Return the URLs as a JSON array of strings. Return an empty array [] if none are found.
    
    Text: {text_preview}
    """
    
    try:
        response = call_llm(prompt, temperature=0.1)
        
        # Try to extract JSON array
        import json
        import re
        
        # Look for array pattern in response
        array_match = re.search(r'\[[\s\S]*\]', response)
        if array_match:
            array_str = array_match.group(0)
            # Parse the JSON array
            urls = json.loads(array_str)
            
            # Filter to ensure we only have valid GitHub URLs
            github_urls = [url for url in urls if isinstance(url, str) and "github.com" in url]
            
            if github_urls:
                print(f"LLM found {len(github_urls)} GitHub URLs not detected by regex")
                return github_urls
                
    except Exception as e:
        print(f"LLM-based GitHub URL extraction failed: {str(e)}")
    
    # If LLM extraction failed, return empty list
    return []

def assess_repository_quality(github_url: str, query: str, features: List[str] = None) -> Dict[str, Any]:
    """
    Assess a GitHub repository's quality and relevance to the user's query.
    Uses both GitHub API data (via check_repository_complexity_and_size) and LLM assessment.
    
    Args:
        github_url: URL of the GitHub repository
        query: The user's search query
        features: List of features the user is looking for
        
    Returns:
        Dictionary with quality assessment metrics
    """
    if not github_url or "github.com" not in github_url:
        return {
            "relevance_score": 0.0,
            "quality_score": 0.0,
            "reasoning": "Not a valid GitHub repository URL"
        }
    
    # Get GitHub data using API (will prompt for token if needed)
    from utils.github import check_repository_complexity_and_size
    try:
        print(f"Getting GitHub data for {github_url}...")
        github_data = check_repository_complexity_and_size(github_url)
        stars = github_data.get("stars", 0)
        forks = github_data.get("forks", 0)
        complexity_score = github_data.get("complexity_score", 0)
        
        # If we have good GitHub data, we can make a better assessment
        if "error" not in github_data:
            # Format features for the prompt
            features_str = ", ".join(features) if features else "None specified"
            
            prompt = f"""
            Assess this GitHub repository's relevance and quality:
            Repository: {github_url}
            User query: {query}
            Desired features: {features_str}
            
            Repository metrics:
            - Stars: {stars}
            - Forks: {forks}
            - Complexity score: {complexity_score}/10
            - Languages: {', '.join(github_data.get('languages', {}).keys())}
            
            Return a JSON object with this format:
            {{
              "relevance_score": 0.0-1.0,
              "quality_score": 0.0-1.0,
              "reasoning": "brief explanation of your assessment"
            }}
            """
            
            try:
                response = call_llm(prompt, temperature=0.3)
                
                # Extract JSON from the response
                import json
                import re
                
                # Look for JSON object pattern
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    json_str = json_match.group(0)
                    result = json.loads(json_str)
                    
                    # Ensure required fields exist
                    if "relevance_score" in result and "quality_score" in result:
                        return result
            
            except Exception as e:
                print(f"Repository quality LLM assessment failed: {str(e)}")
    
    except Exception as e:
        print(f"Repository data retrieval failed: {str(e)}")
    
    # Fallback to the original approach of URL-based assessment
    features_str = ", ".join(features) if features else "None specified"
    
    prompt = f"""
    Assess this GitHub repository's relevance and quality:
    Repository: {github_url}
    User query: {query}
    Desired features: {features_str}
    
    Based on the URL and repository name alone (without fetching data), evaluate:
    1. Does this repository likely implement the features from the user's query?
    2. Is this likely a quality implementation based on naming conventions and organization?
    3. Is this from a reputable developer or organization?
    
    Return a JSON object with this format:
    {{
      "relevance_score": 0.0-1.0,
      "quality_score": 0.0-1.0,
      "reasoning": "brief explanation of your assessment"
    }}
    """
    
    try:
        response = call_llm(prompt, temperature=0.3)
        
        # Extract JSON from the response
        import json
        import re
        
        # Look for JSON object pattern
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            json_str = json_match.group(0)
            result = json.loads(json_str)
            
            # Ensure required fields exist
            if "relevance_score" in result and "quality_score" in result:
                return result
    
    except Exception as e:
        print(f"Repository quality assessment failed: {str(e)}")
    
    # Return default values if assessment fails
    return {
        "relevance_score": 0.5,
        "quality_score": 0.5,
        "reasoning": "Unable to assess repository quality"
    }

if __name__ == "__main__":
    """
    Command line interface for testing search functions.
    
    Usage:
        python -m utils.search interactive
        python -m utils.search "query"
        
    Options:
        --no-youtube            Disable YouTube search
        --no-web                Disable web search
        --no-llm                Disable LLM enhancement
        --youtube-count N       Set number of YouTube videos to search
        --web-count N           Set number of web pages to search
        --threshold N           Set relevance threshold (0.0-1.0)
    """
    import sys
    
    # Default to interactive mode with no arguments
    if len(sys.argv) == 1 or sys.argv[1] == "interactive":
        results = interactive_search()
        
        # Print results
        if results and results.get("github_urls"):
            print("\n=== Found GitHub Repositories ===")
            for i, url in enumerate(results["github_urls"][:10], 1):
                print(f"{i}. {url}")
            
            if len(results["github_urls"]) > 10:
                print(f"...and {len(results['github_urls']) - 10} more.")
        else:
            print("No GitHub repositories found.")
    
    # Process query from command line
    elif len(sys.argv) > 1:
        query = sys.argv[1]
        print(f"Searching for: {query}")
        
        # Parse optional parameters
        youtube_count = 5
        web_count = 10
        use_youtube = True
        use_web = True
        use_llm = True
        threshold = 0.5
        
        for i, arg in enumerate(sys.argv[2:]):
            if arg == "--no-youtube":
                use_youtube = False
            elif arg == "--no-web":
                use_web = False
            elif arg == "--no-llm":
                use_llm = False
            elif arg == "--youtube-count" and i+3 <= len(sys.argv):
                try:
                    youtube_count = int(sys.argv[i+3])
                except ValueError:
                    pass
            elif arg == "--web-count" and i+3 <= len(sys.argv):
                try:
                    web_count = int(sys.argv[i+3])
                except ValueError:
                    pass
            elif arg == "--threshold" and i+3 <= len(sys.argv):
                try:
                    threshold_val = float(sys.argv[i+3])
                    if 0.0 <= threshold_val <= 1.0:
                        threshold = threshold_val
                    else:
                        print("Threshold must be between 0.0 and 1.0. Using default: 0.5")
                except ValueError:
                    print("Invalid threshold format. Using default: 0.5")
        
        # Execute search
        results = search_and_scrape(
            query=query,
            youtube_count=youtube_count,
            web_count=web_count,
            use_youtube=use_youtube,
            use_web=use_web,
            use_llm=use_llm,
            threshold=threshold
        )
        
        # Print results
        if results and results.get("github_urls"):
            print("\n=== Found GitHub Repositories ===")
            for i, url in enumerate(results["github_urls"][:10], 1):
                print(f"{i}. {url}")
            
            if len(results["github_urls"]) > 10:
                print(f"...and {len(results['github_urls']) - 10} more.")
        else:
            print("No GitHub repositories found.")
            
        # Print search statistics
        if "scrape_success_rate" in results:
            success_rate = results["scrape_success_rate"] * 100
            print(f"\nScraping success rate: {success_rate:.1f}%")
        
        if "average_relevance" in results:
            avg_relevance = results["average_relevance"] * 100
            print(f"Average content relevance: {avg_relevance:.1f}%")
    
    else:
        print("Usage:")
        print("  python -m utils.search interactive")
        print("  python -m utils.search \"your search query\"")
        print("  python -m utils.search \"your search query\" --no-youtube --no-web --youtube-count 3 --web-count 5") 