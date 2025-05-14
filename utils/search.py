"""
Search utilities for Repository Analysis to MCP Server system.
"""

import os
import json
import sys
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
        
        # Extract basic video information
        title = info.get('title', '')
        description = info.get('description', '')
        uploader = info.get('uploader', '')
        view_count = info.get('view_count', 0)
        upload_date = info.get('upload_date', '')
        duration = info.get('duration', 0)
        
        # Extract comments if available
        comments = []
        comments_data = info.get('comments', [])
        for comment in comments_data[:30]:  # Check more comments for GitHub URLs
            comment_text = comment.get('text', '')
            if comment_text:
                comments.append(comment_text)
        
        # Try to extract GitHub URLs from description
        description_urls = extract_github_urls(description) if description else []
        
        # Try to extract GitHub URLs from comments
        comment_text = "\n".join(comments)
        comment_urls = extract_github_urls(comment_text) if comment_text else []
        
        # Combine and deduplicate GitHub URLs
        all_github_urls = list(set(description_urls + comment_urls))
        
        # Extract other links from description that might be GitHub repository references
        # but weren't caught by the regex pattern
        other_links = []
        if description:
            for line in description.split('\n'):
                if 'http' in line and 'git' in line.lower():
                    other_links.append(line.strip())
        
        return {
            "title": title,
            "uploader": uploader,
            "upload_date": upload_date,
            "view_count": view_count,
            "duration": duration,
            "description": description,
            "comments": comments,
            "github_urls": all_github_urls,
            "other_potential_repo_links": other_links
        }

@log_execution_time("scrape_webpage")
def scrape_webpage(url: str) -> Dict[str, Any]:
    """
    Scrapes a webpage to extract content and GitHub URLs.
    Focuses specifically on finding GitHub repository references.
    
    Args:
        url: Webpage URL
        
    Returns:
        Dictionary with page content and extracted GitHub URLs
    """
    if not REQUESTS_AVAILABLE:
        raise ImportError("requests is required for webpage scraping. Install with: pip install requests")
    
    if not BS4_AVAILABLE:
        raise ImportError("BeautifulSoup is required for webpage scraping. Install with: pip install beautifulsoup4")
    
    # Fetch the webpage
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    
    # Parse HTML
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract title
    title = soup.title.string if soup.title else ""
    
    # Extract main content (prioritize article or main content areas)
    content = ""
    
    # Try to find article content first
    article_tags = soup.find_all(['article', 'main', 'div.content', 'div.post'])
    if article_tags:
        for tag in article_tags:
            content += tag.get_text(separator="\n", strip=True) + "\n\n"
    else:
        # Fallback to body content, excluding scripts, styles, etc.
        for tag in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'li']):
            content += tag.get_text(separator="\n", strip=True) + "\n"
    
    # Extract all links
    links = []
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        text = a_tag.get_text(strip=True)
        if href and text:
            # Normalize GitHub URLs if they're relative or incomplete
            if 'github.com' in href or 'github.com' in text.lower():
                # Try to convert relative GitHub URLs to absolute ones
                if href.startswith('/'):
                    if 'github.com' in url:
                        href = f"https://github.com{href}"
            
            links.append({"url": href, "text": text})
    
    # Extract all GitHub URLs from the entire page
    github_urls = extract_github_urls(response.text) if response.text else []
    
    # Look for code blocks that might contain GitHub references
    code_blocks = []
    for code_tag in soup.find_all(['code', 'pre']):
        code_text = code_tag.get_text(strip=True)
        if 'github.com' in code_text or 'git clone' in code_text:
            code_blocks.append(code_text)
    
    return {
        "title": title,
        "content": content[:5000],  # Limit content size
        "links": links[:50],  # Limit number of links
        "github_urls": github_urls,
        "code_blocks": code_blocks[:10]  # Include potential code blocks with GitHub references
    }

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
                     use_llm: bool = True) -> Dict[str, Any]:
    """
    Performs a complete search and scrape workflow to find GitHub repositories.
    
    Args:
        query: Search query
        keywords: Additional keywords for relevance filtering
        tech_stack: Technologies from user query
        features: Features the user is looking for
        youtube_count: Number of YouTube videos to search
        web_count: Number of web pages to search
        use_youtube: Whether to include YouTube search
        use_web: Whether to include web search
        use_llm: Whether to use LLM enhancements for search refinement and relevance checking
        
    Returns:
        Dictionary with search results and extracted GitHub URLs
    """
    if not keywords:
        keywords = []
    if not tech_stack:
        tech_stack = []
    if not features:
        features = []
    
    # Refine the search query using LLM if enabled
    if use_llm:
        try:
            refined_query = refine_search_query(query, keywords, tech_stack, features)
        except Exception as e:
            print(f"Query refinement failed: {str(e)}. Using original query.")
            refined_query = query
    else:
        refined_query = query
    
    all_github_urls = []
    all_repo_quality = {}  # Store quality assessments by URL
    youtube_results = []
    web_results = []
    
    # Search and scrape YouTube videos
    if use_youtube and youtube_count > 0:
        print(f"Searching YouTube for: {refined_query}")
        videos = search_youtube(refined_query, max_results=youtube_count, 
                              keywords=keywords, tech_stack=tech_stack, features=features)
        
        for i, video in enumerate(videos):
            print(f"Scraping YouTube video {i+1}/{len(videos)}: {video['title']}")
            
            # Check relevance with standard or LLM-enhanced method
            if use_llm:
                relevance = check_content_relevance_with_llm(
                    video, refined_query, keywords, tech_stack, features
                )
            else:
                relevance = check_content_relevance(
                    video, keywords, tech_stack, features
                )
            
            if relevance["is_relevant"]:
                print(f"  Relevance: {relevance['relevance_score']:.2f} - {relevance['reasoning']}")
                
                # Skip scraping if we already have GitHub URLs from the search
                if video.get("github_urls"):
                    github_urls = video.get("github_urls", [])
                    print(f"  GitHub URLs from search: {len(github_urls)}")
                    
                    if github_urls:
                        video['github_urls'] = github_urls
                        all_github_urls.extend(github_urls)
                        youtube_results.append(video)
                        continue
                
                # If we don't have GitHub URLs yet, scrape the video
                video_data = scrape_youtube_video(video['url'])
                
                # Try enhanced URL extraction if enabled and no URLs found
                if use_llm and not video_data.get('github_urls'):
                    description = video_data.get('description', '')
                    comments_text = "\n".join(video_data.get('comments', []))
                    
                    # Try to extract URLs from description
                    llm_urls_desc = extract_github_urls_with_llm(description)
                    
                    # Try to extract URLs from comments
                    llm_urls_comments = extract_github_urls_with_llm(comments_text)
                    
                    # Combine and deduplicate
                    llm_urls = list(set(llm_urls_desc + llm_urls_comments))
                    
                    if llm_urls:
                        print(f"  GitHub URLs found by LLM: {len(llm_urls)}")
                        video_data['github_urls'] = llm_urls
                
                github_urls = video_data.get('github_urls', [])
                
                print(f"  GitHub URLs from scraping: {len(github_urls)}")
                
                if github_urls:
                    video['github_urls'] = github_urls
                    all_github_urls.extend(github_urls)
                    youtube_results.append(video)
            else:
                print(f"  Skipping (not relevant): {relevance['reasoning']}")
    
    # Search and scrape web pages
    if use_web and web_count > 0:
        print(f"Searching web for: {refined_query}")
        pages = search_web(refined_query, max_results=web_count, 
                         keywords=keywords, tech_stack=tech_stack, features=features)
        
        for i, page in enumerate(pages):
            print(f"Scraping webpage {i+1}/{len(pages)}: {page['title']}")
            
            # Check relevance with standard or LLM-enhanced method
            if use_llm:
                relevance = check_content_relevance_with_llm(
                    page, refined_query, keywords, tech_stack, features
                )
            else:
                relevance = check_content_relevance(
                    page, keywords, tech_stack, features
                )
            
            if relevance["is_relevant"]:
                print(f"  Relevance: {relevance['relevance_score']:.2f} - {relevance['reasoning']}")
                
                page_data = scrape_webpage(page['url'])
                
                # Try enhanced URL extraction if enabled and no URLs found
                if use_llm and not page_data.get('github_urls'):
                    # Try LLM-enhanced extraction from content
                    content = page_data.get('content', '')
                    llm_urls = extract_github_urls_with_llm(content)
                    
                    if llm_urls:
                        print(f"  GitHub URLs found by LLM: {len(llm_urls)}")
                        page_data['github_urls'] = llm_urls
                
                github_urls = page_data.get('github_urls', [])
                
                print(f"  GitHub URLs from scraping: {len(github_urls)}")
                
                if github_urls:
                    page['github_urls'] = github_urls
                    all_github_urls.extend(github_urls)
                    web_results.append(page)
            else:
                print(f"  Skipping (not relevant): {relevance['reasoning']}")
    
    # Deduplicate GitHub URLs
    unique_github_urls = list(set(all_github_urls))
    
    # Assess repository quality if LLM is enabled
    repos_with_quality = []
    if use_llm:
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
    
    return {
        "query": query,
        "refined_query": refined_query if use_llm else query,
        "keywords": keywords,
        "tech_stack": tech_stack,
        "features": features,
        "youtube_results": youtube_results,
        "web_results": web_results,
        "github_urls": unique_github_urls,
        "repos_with_quality": repos_with_quality if use_llm else [],
        "total_github_urls": len(unique_github_urls),
        "llm_enhanced": use_llm
    }

def interactive_search() -> Dict[str, Any]:
    """
    Runs an interactive search session to find GitHub repositories.
    Provides user control over search configuration.
    
    Returns:
        Search results with GitHub URLs
    """
    print("=" * 50)
    print("GitHub Repository Finder")
    print("=" * 50)
    
    query = input("Enter your search query: ")
    
    # Get additional filtering parameters
    keywords_input = input("Enter keywords for filtering (comma-separated, or press Enter to skip): ")
    keywords = [k.strip() for k in keywords_input.split(",")] if keywords_input else []
    
    tech_stack_input = input("Enter technologies/frameworks (comma-separated, or press Enter to skip): ")
    tech_stack = [t.strip() for t in tech_stack_input.split(",")] if tech_stack_input else []
    
    features_input = input("Enter desired features (comma-separated, or press Enter to skip): ")
    features = [f.strip() for f in features_input.split(",")] if features_input else []
    
    # Ask about search sources
    use_youtube = input("Include YouTube search? (y/n, default: y): ").lower() != 'n'
    use_web = input("Include web search? (y/n, default: y): ").lower() != 'n'
    
    # Ask about LLM enhancements
    use_llm = input("Use LLM enhancements for smarter search? (y/n, default: y): ").lower() != 'n'
    
    # Get count parameters
    youtube_count = 0
    web_count = 0
    
    if use_youtube:
        youtube_count = int(input("Number of YouTube videos to analyze (default: 5): ") or 5)
    
    if use_web:
        web_count = int(input("Number of web pages to analyze (default: 5): ") or 5)
    
    # Set minimum threshold for relevance
    relevance_threshold = float(input("Minimum relevance score (0.0-1.0, default: 0.5): ") or 0.5)
    
    print("\nStarting search and scrape process...")
    results = search_and_scrape(
        query=query,
        keywords=keywords,
        tech_stack=tech_stack,
        features=features,
        youtube_count=youtube_count,
        web_count=web_count,
        use_youtube=use_youtube,
        use_web=use_web,
        use_llm=use_llm
    )
    
    print("\n" + "=" * 50)
    print(f"Search Results for: {query}")
    if use_llm and results.get("refined_query") != query:
        print(f"Refined query: {results.get('refined_query')}")
    print("=" * 50)
    
    if results['youtube_results']:
        print(f"\nYouTube Results ({len(results['youtube_results'])} videos with GitHub URLs):")
        for i, video in enumerate(results['youtube_results']):
            print(f"{i+1}. {video['title']}")
            print(f"   Channel: {video.get('channel', 'Unknown')}")
            print(f"   URL: {video['url']}")
            print(f"   GitHub URLs: {', '.join(video.get('github_urls', []))}")
    
    if results['web_results']:
        print(f"\nWeb Results ({len(results['web_results'])} pages with GitHub URLs):")
        for i, page in enumerate(results['web_results']):
            print(f"{i+1}. {page['title']}")
            print(f"   URL: {page['url']}")
            print(f"   GitHub URLs: {', '.join(page.get('github_urls', []))}")
    
    print(f"\nTotal unique GitHub repositories found: {results['total_github_urls']}")
    if results['github_urls']:
        print("\nAll GitHub URLs:")
        
        # Show repos with quality scores if available
        if use_llm and results.get('repos_with_quality'):
            print("\nRepositories (sorted by relevance and quality):")
            for i, repo in enumerate(results.get('repos_with_quality', [])):
                print(f"{i+1}. {repo['url']}")
                print(f"   Relevance: {repo['relevance_score']:.2f}, Quality: {repo['quality_score']:.2f}")
                print(f"   Assessment: {repo['reasoning']}")
        else:
            for i, url in enumerate(results['github_urls']):
                print(f"{i+1}. {url}")
    
    return results

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
    Assess a GitHub repository's quality and relevance to the user's query using LLM.
    
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
            "maintenance_score": 0.0,
            "reasoning": "Not a valid GitHub repository URL"
        }
    
    # Format features for the prompt
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
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        interactive_search()
    else:
        # Simple test
        print("Testing search utilities...")
        print("To run interactive search, use: python -m utils.search --interactive")
        
        try:
            # Test web search
            print("\nTesting web search...")
            query = "python web framework"
            results = search_web(query, max_results=2)
            print(f"Found {len(results)} web search results for '{query}'")
            for i, result in enumerate(results):
                print(f"{i+1}. {result['title']}")
                print(f"   URL: {result['url']}")
                
            # Test YouTube search
            print("\nTesting YouTube search...")
            query = "python tutorial github"
            results = search_youtube(query, max_results=2)
            print(f"Found {len(results)} YouTube search results for '{query}'")
            for i, result in enumerate(results):
                print(f"{i+1}. {result['title']}")
                print(f"   URL: {result['url']}")
                if result.get("github_urls"):
                    print(f"   GitHub URLs: {', '.join(result['github_urls'])}")
        except ImportError as e:
            print(f"Error: {e}")
            print("Please install the required libraries listed in requirements.txt") 