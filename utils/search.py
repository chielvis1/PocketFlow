"""
Search utilities for Repository Analysis to MCP Server system.
"""

import os
import json
import yaml
from typing import Dict, List, Any, Optional
from functools import lru_cache
from urllib.parse import urlparse

from .llm import call_llm
from .monitoring import log_execution_time

@lru_cache(maxsize=100)
@log_execution_time("web_search")
def search_web(query: str, max_results: int = 10) -> List[Dict[str, str]]:
    """
    Searches the web for relevant content.
    
    Args:
        query: Search query
        max_results: Maximum number of results to return
        
    Returns:
        List of result dictionaries with title, url, snippet, source
    """
    try:
        from serpapi import GoogleSearch
        
        api_key = os.environ.get("SERPAPI_API_KEY")
        if not api_key:
            return _mock_search_web(query, max_results)
            
        # Configure search parameters
        params = {
            "engine": "google",
            "q": query,
            "api_key": api_key,
            "num": max_results
        }
        
        try:
            # Execute search
            search = GoogleSearch(params)
            results = search.get_dict()
            
            # Extract organic results
            if "organic_results" not in results:
                return []
                
            processed_results = []
            for result in results["organic_results"][:max_results]:
                processed_results.append({
                    "title": result.get("title", ""),
                    "snippet": result.get("snippet", ""),
                    "link": result.get("link", ""),
                    "source": extract_domain(result.get("link", ""))
                })
                
            return processed_results
            
        except Exception as e:
            print(f"Search error: {str(e)}")
            return _mock_search_web(query, max_results)
            
    except ImportError:
        print("SerpAPI not installed. Using fallback search mechanism.")
        return _mock_search_web(query, max_results)

def _mock_search_web(query: str, max_results: int = 10) -> List[Dict[str, str]]:
    """
    Fallback search function when SerpAPI is not available.
    Uses LLM to generate mock search results based on the query.
    
    Args:
        query: Search query
        max_results: Maximum number of results to return
        
    Returns:
        List of simulated search results
    """
    prompt = f"""
Generate {max_results} realistic Google search results for the query: "{query}"
Focus specifically on GitHub repositories that might match this query.

For each result, include:
1. A realistic title for a GitHub repository
2. A realistic URL to a GitHub repository
3. A realistic description/snippet of the repository
4. Make sure at least 80% of results are directly GitHub repository links

Output in YAML format:
```yaml
results:
  - title: "Example Repository Title"
    link: "https://github.com/username/repository"
    snippet: "This repository contains implementation of X using Y technology..."
  - title: "Another Repository Title" 
    link: "https://github.com/username2/repo2"
    snippet: "A detailed implementation of Z with examples..."
```
Make all results focused on the specific query and technology mentioned.
"""
    
    try:
        response = call_llm(prompt, temperature=0.7)
        
        # Extract YAML
        yaml_str = response
        if "```yaml" in response:
            yaml_str = response.split("```yaml")[1].split("```")[0].strip()
        elif "```" in response:
            yaml_str = response.split("```")[1].split("```")[0].strip()
            
        # Parse YAML
        data = yaml.safe_load(yaml_str)
        
        # Extract and format results
        results = []
        for result in data.get("results", [])[:max_results]:
            if result.get("link") and result.get("title"):
                results.append({
                    "title": result.get("title", ""),
                    "snippet": result.get("snippet", ""),
                    "link": result.get("link", ""),
                    "source": extract_domain(result.get("link", ""))
                })
        
        return results
    except Exception as e:
        print(f"Error generating mock search results: {str(e)}")
        # Return a minimal result set if everything else fails
        return [
            {
                "title": "Example Repository for " + query,
                "snippet": "This is a simulated search result since the real search API is unavailable.",
                "link": "https://github.com/example/repository",
                "source": "github.com"
            }
        ]

@lru_cache(maxsize=50)
@log_execution_time("youtube_search")
def search_youtube(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Searches YouTube for relevant videos.
    
    Args:
        query: Search query
        max_results: Maximum number of videos to return
        
    Returns:
        List of result dictionaries with video info
    """
    # Using SerpAPI's YouTube engine
    try:
        from serpapi import GoogleSearch
        
        api_key = os.environ.get("SERPAPI_API_KEY")
        if not api_key:
            return _mock_search_youtube(query, max_results)
        
        # Configure search parameters for YouTube
        params = {
            "engine": "youtube",
            "search_query": query,
            "api_key": api_key,
            "num": max_results
        }
        
        try:
            # Execute search
            search = GoogleSearch(params)
            results = search.get_dict()
            
            # Extract video results
            if "video_results" not in results:
                return []
                
            processed_results = []
            for video in results["video_results"][:max_results]:
                processed_results.append({
                    "title": video.get("title", ""),
                    "link": video.get("link", ""),
                    "channel": video.get("channel", {}).get("name", ""),
                    "description": video.get("snippet", ""),
                    "thumbnail": video.get("thumbnail", {}).get("static", ""),
                    "published_at": video.get("published_date", "")
                })
                
            return processed_results
            
        except Exception as e:
            print(f"YouTube search error: {str(e)}")
            return _mock_search_youtube(query, max_results)
            
    except ImportError:
        print("SerpAPI not installed. Using fallback search mechanism.")
        return _mock_search_youtube(query, max_results)

def _mock_search_youtube(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Fallback YouTube search function when SerpAPI is not available.
    Uses LLM to generate mock YouTube results based on the query.
    
    Args:
        query: Search query
        max_results: Maximum number of results to return
        
    Returns:
        List of simulated YouTube search results
    """
    prompt = f"""
Generate {max_results} realistic YouTube search results for the query: "{query}"
Focus on tutorials and videos about coding repositories relevant to this query.

For each result, include:
1. A realistic video title
2. A YouTube URL (example: https://www.youtube.com/watch?v=EXAMPLE_ID)
3. A channel name
4. A brief description
5. A publication date

Output in YAML format:
```yaml
results:
  - title: "How to Implement Authentication with JWT in Node.js"
    link: "https://www.youtube.com/watch?v=example123"
    channel: "CodeWithExpert"
    description: "In this tutorial, I show how to implement JWT authentication in a Node.js Express application..."
    published_at: "2023-10-15"
```
Make all results focused on the specific query and technology mentioned.
"""
    
    try:
        response = call_llm(prompt, temperature=0.7)
        
        # Extract YAML
        yaml_str = response
        if "```yaml" in response:
            yaml_str = response.split("```yaml")[1].split("```")[0].strip()
        elif "```" in response:
            yaml_str = response.split("```")[1].split("```")[0].strip()
            
        # Parse YAML
        data = yaml.safe_load(yaml_str)
        
        # Extract and format results
        results = []
        for result in data.get("results", [])[:max_results]:
            if result.get("link") and result.get("title"):
                results.append({
                    "title": result.get("title", ""),
                    "link": result.get("link", ""),
                    "channel": result.get("channel", "Example Channel"),
                    "description": result.get("description", ""),
                    "thumbnail": "",
                    "published_at": result.get("published_at", "")
                })
        
        return results
    except Exception as e:
        print(f"Error generating mock YouTube results: {str(e)}")
        # Return a minimal result set if everything else fails
        return [
            {
                "title": "Tutorial on " + query,
                "link": "https://www.youtube.com/watch?v=example123",
                "channel": "TechTutorials",
                "description": "This is a simulated YouTube result since the real search API is unavailable.",
                "thumbnail": "",
                "published_at": "2023-01-01"
            }
        ]

def extract_domain(url: str) -> str:
    """
    Extract domain from URL.
    
    Args:
        url: URL to parse
        
    Returns:
        Domain name
    """
    try:
        return urlparse(url).netloc
    except:
        return ""

def check_content_relevance(content: Dict[str, str], 
                           keywords: List[str], 
                           tech_stack: List[str], 
                           features: List[str], 
                           threshold: float = 0.7) -> Dict[str, Any]:
    """
    Evaluates the relevance of search results specifically for the user's tech stack,
    features, and context.
    
    Args:
        content: Search result with title, url, snippet
        keywords: Keywords from user query
        tech_stack: Technologies from user query  
        features: Features the user is looking for
        threshold: Minimum relevance score (0.0-1.0)
        
    Returns:
        Content with relevance assessment
    """
    # Create prompt for LLM to evaluate relevance
    prompt = f"""
Evaluate how relevant this content is to the user's requirements:

CONTENT:
Title: "{content['title']}"
Snippet: "{content['snippet']}"

USER REQUIREMENTS:
Keywords: {keywords}
Tech Stack: {tech_stack}
Features: {features}

Evaluate specifically:
1. Does the content cover the specific features the user is looking for?
2. Does it mention or relate to the user's tech stack?
3. How directly relevant is it to implementing these features with this tech stack?

Output in YAML format:
```yaml
relevance_score: 0.0-1.0
tech_stack_match:
  - matched_tech1
  - matched_tech2
feature_match:
  - matched_feature1
  - matched_feature2
reasoning: detailed explanation of relevance judgment
```
"""
    
    response = call_llm(prompt, temperature=0.1)
    
    # Extract YAML from response
    yaml_content = ""
    in_yaml = False
    
    for line in response.split('\n'):
        if line.strip() == '```yaml' or line.strip() == '```':
            in_yaml = not in_yaml
            continue
        if in_yaml:
            yaml_content += line + '\n'
    
    try:
        relevance_data = yaml.safe_load(yaml_content)
        
        # Create result by combining original content and relevance data
        result = content.copy()
        result.update({
            "relevance_score": float(relevance_data.get("relevance_score", 0.0)),
            "tech_stack_match": relevance_data.get("tech_stack_match", []),
            "feature_match": relevance_data.get("feature_match", []),
            "reasoning": relevance_data.get("reasoning", ""),
            "is_relevant": float(relevance_data.get("relevance_score", 0.0)) >= threshold
        })
        
        return result
    except Exception as e:
        print(f"Error parsing relevance assessment: {str(e)}")
        return {
            **content,
            "relevance_score": 0.0,
            "tech_stack_match": [],
            "feature_match": [],
            "reasoning": "Error in relevance assessment",
            "is_relevant": False
        }

if __name__ == "__main__":
    # Test the functions
    print("Testing web search...")
    results = search_web("PocketFlow GitHub repository")
    print(f"Found {len(results)} results")
    for i, result in enumerate(results[:3]):
        print(f"{i+1}. {result['title']} - {result['source']}")
    
    print("\nTesting YouTube search...")
    videos = search_youtube("PocketFlow tutorial")
    print(f"Found {len(videos)} videos")
    for i, video in enumerate(videos[:2]):
        print(f"{i+1}. {video['title']} by {video['channel']}") 