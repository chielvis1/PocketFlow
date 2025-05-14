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
4. **Add robust error handling** for common scraping errors like 403 Forbidden
5. **Implement retry mechanisms** with fixed 5-second delays between attempts

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

2. **Two-Level Page Scraping with Retry Mechanism**:
   - First level: Extract GitHub links directly from search results
   - Second level: Follow promising links to scrape for more repositories
   - Implement retry mechanism with 5-second delays

   ```python
   def extract_repos_from_page(url, max_retries=2):
       """Extract GitHub repositories from a web page using BeautifulSoup with retry mechanism"""
       try:
           import requests
           from bs4 import BeautifulSoup
           import time
           
           # User agents to rotate through
           user_agents = [
               'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
               'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15',
               'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
           ]
           
           for attempt in range(max_retries + 1):
               try:
                   # Use different user agent on each try
                   headers = {
                       'User-Agent': user_agents[attempt % len(user_agents)],
                       'Accept': 'text/html,application/xhtml+xml,application/xml',
                       'Accept-Language': 'en-US,en;q=0.9',
                       'Referer': 'https://www.google.com/'
                   }
                   
                   # Log retry attempt
                   if attempt > 0:
                       print(f"Retry attempt {attempt}/{max_retries} for {url}")
                   
                   # Make the request
                   response = requests.get(url, headers=headers, timeout=10)
                   response.raise_for_status()
                   
                   # Parse content
                   soup = BeautifulSoup(response.text, 'html.parser')
                   
                   # Extract all links
                   links = [a.get('href') for a in soup.find_all('a', href=True)]
                   
                   # Filter for GitHub repository links
                   github_repos = [link for link in links if is_github_repo_url(link)]
                   
                   return github_repos
                   
               except requests.exceptions.HTTPError as e:
                   status_code = e.response.status_code if hasattr(e, 'response') else 0
                   
                   if status_code == 403:
                       print(f"Received 403 Forbidden error from {url}")
                   else:
                       print(f"HTTP error when scraping {url}: {str(e)}")
                   
                   # If we've exhausted retries, return empty list
                   if attempt == max_retries:
                       return []
                   
                   # Wait 5 seconds before retry
                   print(f"Waiting 5 seconds before retry...")
                   time.sleep(5)
                   
               except Exception as e:
                   print(f"Error extracting repos from {url}: {str(e)}")
                   
                   # If we've exhausted retries, return empty list
                   if attempt == max_retries:
                       return []
                   
                   # Wait 5 seconds before retry
                   print(f"Waiting 5 seconds before retry...")
                   time.sleep(5)
           
           # If we get here, all retries failed
           return []
               
       except ImportError as e:
           print(f"Required library not installed: {str(e)}")
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

### 3. Scraping Retry Mechanism

The scraping functionality includes a retry mechanism that handles 403 Forbidden errors and other scraping failures:

```python
def scrape_webpage(url, max_retries=2):
    """
    Scrape a webpage with retry mechanism for handling 403 errors and other failures
    """
    # User agents to rotate through
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
    ]
    
    # Initialize with scrape_failed=True until proven otherwise
    page_data = {
        "scrape_failed": True,
        # Other default fields...
    }
    
    for attempt in range(max_retries + 1):
        try:
            # Select user agent based on attempt number
            headers = {
                'User-Agent': user_agents[attempt % len(user_agents)]
                # Other headers...
            }
            
            # Add 5-second delay between retries
            if attempt > 0:
                print(f"Retry attempt {attempt}/{max_retries} for {url}")
                print("Waiting 5 seconds before retry...")
                time.sleep(5)  # Fixed 5-second delay between retries
            
            # Make the request, parse, and extract content
            # ...
            
            # Mark as successful
            page_data["scrape_failed"] = False
            return page_data
            
        except requests.exceptions.HTTPError as e:
            # Handle HTTP errors (including 403 Forbidden)
            # Continue retry loop unless max_retries reached
            if attempt == max_retries:
                return page_data
                
        except Exception as e:
            # Handle other exceptions
            # Continue retry loop unless max_retries reached
            if attempt == max_retries:
                return page_data
    
    # If all retries fail, return with scrape_failed=True
    return page_data
```

The search_and_scrape function tracks scraping failures and proceeds to the next site in the list if a scrape fails:

```python
def search_and_scrape(query, *args, **kwargs):
    # ...
    
    scrape_failure_count = 0
    total_scrape_attempts = 0
    
    # Process search results...
    for i, page in enumerate(pages):
        # ...
        
        total_scrape_attempts += 1
        page_data = scrape_webpage(page['url'])
        
        # Check if scraping failed
        if page_data.get('scrape_failed', False):
            scrape_failure_count += 1
            print(f"Scraping failed for {page['url']} - skipping to next page")
            continue
        
        # Continue processing if scraping succeeded...
    
    # Report results including failure statistics
    print(f"Search complete. Found {len(unique_github_urls)} unique GitHub repositories.")
    if scrape_failure_count > 0:
        print(f"Scraping failed for {scrape_failure_count} out of {total_scrape_attempts} pages/videos.")
    
    # Return comprehensive results...
```

### 4. User Agent Rotation

To avoid being blocked by websites like Stack Overflow that might return 403 errors:

```python
def get_random_user_agent(index=None):
    """Get a user agent from a predefined list, optionally by index"""
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
    ]
    
    if index is not None:
        return user_agents[index % len(user_agents)]
    
    import random
    return random.choice(user_agents)
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
   
4. **Error Handling Tests**:
   - Test behavior with simulated 403 responses
   - Verify retry mechanism with 5-second delays
   - Test fallback content generation for the last site

## Conclusion

This implementation carefully replaces SerpAPI with two specialized tools while maintaining backward compatibility with the existing PocketFlow workflow. The changes are focused on the utility functions in `utils/search.py` and do not require modifications to the node implementations or flow structure.

By maintaining the same interface and behavior while enhancing the underlying implementation, we ensure a seamless transition from SerpAPI to the new tools. The advanced GitHub repository extraction capabilities will significantly improve the system's ability to discover relevant repositories without requiring structural changes to the codebase.

The added error handling mechanisms, particularly for 403 Forbidden responses, with fixed 5-second delays between retries, make the system more resilient against common web scraping challenges. This ensures a more reliable user experience even when faced with websites that implement scraping protections. 