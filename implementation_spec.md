# Implementation Specification: YouTube and Web Search Integration

## Overview

This document outlines the implementation plan for replacing SerpAPI in the current PocketFlow application with two specialized tools:

1. **yt-dlp** - For YouTube video search, metadata extraction, and content retrieval
2. **Search-Engines-Scraper** - For multi-engine web searches and page scraping

The goal is to maintain the same interface and functionality while enhancing capabilities, ensuring backward compatibility with the existing workflow, particularly in the `utils/search.py` module.

## Current Implementation Analysis

Currently, PocketFlow's search functionality uses SerpAPI for both web searches (`search_web`) and YouTube searches (`search_youtube`). The system:

1. Attempts to import SerpAPI's `GoogleSearch` class
2. Falls back to mock implementations if SerpAPI is not installed
3. Returns structured data compatible with downstream nodes

The existing workflow in `flow.py` shows:
- `SearchWebNode` uses `search_web` and may trigger YouTube search
- `SearchYouTubeNode` uses `search_youtube` 
- Both feed into `ExtractGitHubReposNode` to find repositories

## Technical Architecture

The replacement implementation will:

1. **Maintain the same interface** (function signatures, return types)
2. **Preserve the fallback mechanism** for when libraries aren't installed
3. **Keep the same response structure** for compatibility with existing nodes

### Modifications to Utility Functions

#### 1. `search_web` function

```python
@lru_cache(maxsize=100)
@log_execution_time("web_search")
def search_web(query: str, max_results: int = 10) -> List[Dict[str, str]]:
    """
    Searches the web for relevant content using Search-Engines-Scraper.
    
    Args:
        query: Search query
        max_results: Maximum number of results to return
        
    Returns:
        List of result dictionaries with title, url, snippet, source
    """
    try:
        # Try to import Search-Engines-Scraper components
        from search_engines import Google, Bing, Yahoo, Duckduckgo
        
        # Select engines to use (configurable)
        engines = [Google(), Bing(), Duckduckgo()]
        processed_results = []
        
        for engine in engines:
            try:
                # Configure the search engine
                engine.pages = 1  # Limit to first page for speed
                
                # Execute search
                results = engine.search(query)
                
                # Extract links and organize results
                links = results.links()
                for link in links[:max_results]:
                    # Extract title and description
                    titles = results.titles()
                    descriptions = results.descriptions()
                    
                    # Find corresponding title and description for this link
                    title = ""
                    snippet = ""
                    
                    for i, url in enumerate(links):
                        if url == link and i < len(titles):
                            title = titles[i]
                            if i < len(descriptions):
                                snippet = descriptions[i]
                    
                    processed_results.append({
                        "title": title,
                        "snippet": snippet,
                        "link": link,
                        "source": extract_domain(link)
                    })
                    
                    # Break early if we've reached max_results
                    if len(processed_results) >= max_results:
                        break
                        
                # Break if we have enough results
                if len(processed_results) >= max_results:
                    break
                    
            except Exception as e:
                print(f"Error with {engine.__class__.__name__}: {str(e)}")
                continue
        
        # Remove duplicates (by URL)
        unique_results = []
        seen_urls = set()
        
        for result in processed_results:
            if result["link"] not in seen_urls:
                seen_urls.add(result["link"])
                unique_results.append(result)
        
        return unique_results[:max_results]
            
    except ImportError:
        print("Search-Engines-Scraper not installed. Using fallback search mechanism.")
        return _mock_search_web(query, max_results)
    except Exception as e:
        print(f"Search error: {str(e)}")
        return _mock_search_web(query, max_results)
```

#### 2. `search_youtube` function

```python
@lru_cache(maxsize=50)
@log_execution_time("youtube_search")
def search_youtube(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Searches YouTube for relevant videos using yt-dlp.
    
    Args:
        query: Search query
        max_results: Maximum number of videos to return
        
    Returns:
        List of result dictionaries with video info
    """
    try:
        # Try to import yt-dlp
        import yt_dlp
        
        # Configure yt-dlp
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'force_generic_extractor': True,
            'ignoreerrors': True,
            'no_warnings': True
        }
        
        try:
            # Search for videos
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                search_results = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
                
                # Process results
                processed_results = []
                
                if 'entries' in search_results:
                    for entry in search_results['entries']:
                        if entry:
                            # Extract video info
                            video_info = {
                                "title": entry.get("title", ""),
                                "link": f"https://www.youtube.com/watch?v={entry.get('id', '')}",
                                "channel": entry.get("uploader", ""),
                                "description": entry.get("description", ""),
                                "thumbnail": entry.get("thumbnail", ""),
                                "published_at": entry.get("upload_date", "")
                            }
                            processed_results.append(video_info)
                
                return processed_results[:max_results]
        
        except Exception as e:
            print(f"YouTube search error: {str(e)}")
            return _mock_search_youtube(query, max_results)
            
    except ImportError:
        print("yt-dlp not installed. Using fallback search mechanism.")
        return _mock_search_youtube(query, max_results)
```

### 3. Dependencies in requirements.txt

Add these dependencies to requirements.txt:

```
yt-dlp>=2023.9.24
search-engines>=0.6
```

## Implementation Steps

1. **Update the `utils/search.py` file**:
   - Replace SerpAPI imports with the new libraries
   - Implement the new search functions while maintaining the existing signature
   - Ensure fallbacks to the existing mock functions for compatibility

2. **Keep the existing fallback functions**:
   - Maintain `_mock_search_web` and `_mock_search_youtube` unchanged 
   - Use them when dependencies aren't installed or errors occur

3. **Test both functions** to ensure they:
   - Return the same data structure as before
   - Handle errors gracefully
   - Fall back to mock implementations when needed

4. **Add the dependencies** to requirements.txt

## Advanced GitHub Repository Extraction

The new tools provide significant opportunities to enhance GitHub repository extraction. Here's how we can implement these improvements:

### 1. Enhanced YouTube Repository Discovery

Using yt-dlp's advanced metadata extraction capabilities, we can:

1. **Deep Video Metadata Extraction**:
   ```python
   def extract_github_repos_from_video(video_id):
       """Extract GitHub repositories from a YouTube video using yt-dlp's advanced metadata extraction"""
       repos = []
       
       # Configure yt-dlp for detailed extraction
       ydl_opts = {
           'quiet': True,
           'skip_download': True,
           'writesubtitles': True,
           'writeautomaticsub': True,
           'subtitleslangs': ['en'],
           'getcomments': True,  # Get video comments
           'ignoreerrors': True
       }
       
       with yt_dlp.YoutubeDL(ydl_opts) as ydl:
           info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
           
           # Sources to check for GitHub repositories
           sources = [
               ('description', info.get('description', '')),
               ('title', info.get('title', ''))
           ]
           
           # Extract from comments if available
           if 'comments' in info:
               for comment in info['comments']:
                   if 'text' in comment:
                       sources.append(('comment', comment['text']))
                       
           # Extract from subtitles if available
           if 'subtitles' in info and 'en' in info['subtitles']:
               subtitle_text = " ".join([entry.get('text', '') for entry in info['subtitles']['en']])
               sources.append(('subtitles', subtitle_text))
               
           # Extract GitHub repositories from all sources
           for source_type, text in sources:
               urls = extract_github_urls(text)
               for url in urls:
                   repos.append({
                       'url': url,
                       'source': f'youtube_{source_type}',
                       'video_id': video_id
                   })
                   
           return repos
   ```

2. **Integration with Existing Results**: 
   - Enhance the `search_youtube` function to include this repository extraction in the description field
   - This enriched data will be available to `ExtractGitHubReposNode` without modifying its implementation

### 2. Multi-Engine Web Search and Page Scraping

Using Search-Engines-Scraper, we can implement a more sophisticated approach:

1. **Cross-Engine Repository Search**:
   ```python
   def search_github_repositories(query, max_results=10):
       """Search specifically for GitHub repositories across multiple search engines"""
       from search_engines import Google, Bing, Duckduckgo
       
       # Add GitHub-specific terms to search
       github_query = f"{query} site:github.com"
       engines = [Google(), Bing(), Duckduckgo()]
       all_repos = []
       
       for engine in engines:
           try:
               # Configure and execute search
               engine.pages = 1
               results = engine.search(github_query)
               
               # Extract GitHub repository links
               links = results.links()
               for link in links:
                   if is_github_repo_url(link):
                       all_repos.append({
                           'url': link,
                           'source': engine.__class__.__name__
                       })
                       
                   # Break if we have enough results
                   if len(all_repos) >= max_results:
                       break
                       
           except Exception as e:
               print(f"Error with {engine.__class__.__name__}: {str(e)}")
               continue
               
       return all_repos[:max_results]
   ```

2. **Two-Level Page Scraping**:
   - First level: Extract GitHub links directly from search results
   - Second level: Follow promising links to scrape for more repositories

   ```python
   def extract_repos_from_page(url, timeout=5):
       """Extract GitHub repositories from a web page using BeautifulSoup"""
       try:
           import requests
           from bs4 import BeautifulSoup
           
           response = requests.get(url, timeout=timeout)
           if response.status_code == 200:
               soup = BeautifulSoup(response.text, 'html.parser')
               
               # Extract all links
               links = [a.get('href') for a in soup.find_all('a', href=True)]
               
               # Filter for GitHub repository links
               github_repos = [link for link in links if is_github_repo_url(link)]
               
               return github_repos
               
           return []
           
       except Exception as e:
           print(f"Error extracting repos from {url}: {str(e)}")
           return []
   ```

3. **Improved Regex for Repository Detection**:
   ```python
   def is_github_repo_url(url):
       """Check if a URL is a GitHub repository using a comprehensive regex pattern"""
       import re
       
       # Pattern to match GitHub repository URLs
       # Handles various formats including:
       # - https://github.com/username/repo
       # - http://github.com/username/repo/
       # - github.com/username/repo
       # - www.github.com/username/repo
       pattern = r'(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9._-]+)/([a-zA-Z0-9._-]+)(?:/)?(?!\S)'
       
       return bool(re.match(pattern, url))
   ```

### 3. Integration with `ExtractGitHubReposNode`

The enhanced repository extraction can work directly with the existing node:

1. **Option 1: Embedded Integration**:
   - Include repository extraction directly in `search_youtube` and `search_web`
   - Add extracted repositories to the description/snippet fields

2. **Option 2: Pre-extraction**:
   - Create a new utility function that's called from within `search_youtube` and `search_web`
   - Include extracted repositories in a new field that `ExtractGitHubReposNode` can check

These enhancements will provide significantly better GitHub repository discovery without requiring changes to the existing node structure.

## Error Handling and Reliability

Each tool requires specific error handling approaches:

### 1. yt-dlp Error Handling

```python
def safe_youtube_search(query, max_results=5):
    """Robust error handling for yt-dlp"""
    try:
        import yt_dlp
        from time import sleep
        from random import uniform
        
        # Basic exponential backoff implementation
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Configure yt-dlp
                ydl_opts = {
                    'quiet': True,
                    'extract_flat': True,
                    'force_generic_extractor': True,
                    'ignoreerrors': True,
                    'no_warnings': True
                }
                
                # Add random delay to avoid rate limiting
                if attempt > 0:
                    delay = uniform(2 ** attempt, 2 ** (attempt + 1))
                    print(f"Retrying YouTube search after {delay:.2f}s delay (attempt {attempt+1}/{max_retries})")
                    sleep(delay)
                
                # Perform search
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    search_results = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
                    # Process results...
                    return processed_results
                    
            except yt_dlp.utils.DownloadError as e:
                if "HTTP Error 429" in str(e) and attempt < max_retries - 1:
                    # Rate limited, will retry with backoff
                    continue
                else:
                    # Other error or final retry failed
                    print(f"YouTube search error: {str(e)}")
                    return _mock_search_youtube(query, max_results)
                    
    except ImportError:
        return _mock_search_youtube(query, max_results)
```

### 2. Search-Engines-Scraper Error Handling

```python
def safe_web_search(query, max_results=10):
    """Robust error handling for Search-Engines-Scraper"""
    try:
        from search_engines import Google, Bing, Duckduckgo
        import time
        
        # List of engines with fallbacks
        primary_engines = [Google(), Bing(), Duckduckgo()]
        fallback_engines = [Yahoo()]  # Use different engines as fallbacks
        
        processed_results = []
        
        # Try primary engines first
        for engine in primary_engines:
            try:
                # Configure and run search
                engine.pages = 1
                
                # Random delay between engine searches (0.5-1.5s)
                time.sleep(0.5 + time.random())
                
                results = engine.search(query)
                # Process results...
                
                # If we got enough results, return them
                if len(processed_results) >= max_results:
                    return processed_results[:max_results]
                    
            except Exception as e:
                print(f"Error with {engine.__class__.__name__}: {str(e)}")
                continue
        
        # If we didn't get enough results, try fallback engines
        if len(processed_results) < max_results:
            for engine in fallback_engines:
                try:
                    # Configure and run search
                    engine.pages = 1
                    
                    # Longer delay for fallbacks to avoid detection (1-2s)
                    time.sleep(1 + time.random())
                    
                    results = engine.search(query)
                    # Process results...
                    
                    # If we got enough results, return them
                    if len(processed_results) >= max_results:
                        return processed_results[:max_results]
                        
                except Exception as e:
                    print(f"Error with fallback {engine.__class__.__name__}: {str(e)}")
                    continue
        
        # Return whatever results we managed to get
        return processed_results
        
    except ImportError:
        return _mock_search_web(query, max_results)
```

### 3. Proxy Support for Avoiding IP Blocks

Both tools support proxies, which can be critical for production use:

```python
def configure_proxy(tool_name):
    """Configure proxy settings for different tools"""
    import os
    import random
    
    # Get proxy settings from environment variables
    proxy_list = os.environ.get("PROXY_LIST", "").split(",")
    
    if not proxy_list or proxy_list[0] == "":
        return None
        
    # Randomly select a proxy from the list
    proxy = random.choice(proxy_list).strip()
    
    if tool_name == "yt-dlp":
        return {
            'http_proxy': proxy,
            'https_proxy': proxy
        }
    elif tool_name == "search-engines":
        return proxy
    
    return None
```

## Test Cases

Create test cases to verify:

1. **Basic Functionality**:
   - Ensure both functions return the expected data structure
   - Verify they handle errors correctly
   
2. **Integration Tests**:
   - Verify the functions work with the existing `SearchWebNode` and `SearchYouTubeNode`
   - Check that results feed correctly into `ExtractGitHubReposNode`

3. **Fallback Tests**:
   - Test behavior when dependencies are missing
   - Test behavior when search requests fail

## Conclusion

This implementation carefully replaces SerpAPI with two specialized tools while maintaining backward compatibility with the existing PocketFlow workflow. The changes are focused on the utility functions in `utils/search.py` and do not require modifications to the node implementations or flow structure.

By maintaining the same interface and behavior while enhancing the underlying implementation, we ensure a seamless transition from SerpAPI to the new tools. The advanced GitHub repository extraction capabilities will significantly improve the system's ability to discover relevant repositories without requiring structural changes to the codebase. 