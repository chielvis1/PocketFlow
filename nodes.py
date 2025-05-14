"""
Node definitions for Repository Analysis to MCP Server agent.

This file contains all the nodes used in the agent flow, which analyzes
GitHub repositories and creates an MCP server based on the analysis.
"""

from pocketflow import Node, BatchNode
from typing import Dict, List, Any, Optional, Union

from utils.llm import call_llm, extract_keywords_and_techstack, analyze_repository_with_llm
from utils.search import search_web, search_youtube, check_content_relevance
from utils.github import extract_github_urls, check_repository_complexity_and_size, analyze_repository
from utils.data_processing import format_for_mcp, generate_implementation_guides_from_analysis, format_repository_list, get_user_selection
from utils.mcp import create_mcp_server, start_mcp_server
from utils.monitoring import log_execution_time

class QueryAnalysisNode(Node):
    """Analyzes the user's query to extract keywords, tech stack, and features."""
    
    def prep(self, shared):
        # Get user query and LLM configuration
        query = shared.get("user_query", "")
        llm_config = shared.get("llm_config", {})
        return query, llm_config
    
    def exec(self, inputs):
        query, llm_config = inputs
        
        if not query:
            return {
                "original_query": "",
                "keywords": [],
                "tech_stack": [],
                "features": [],
                "context": ""
            }
        
        # Use LLM configuration if provided
        provider = llm_config.get("provider")
        model = llm_config.get("model")
        
        return extract_keywords_and_techstack(
            query=query,
            model=model,
            provider=provider
        )
    
    def post(self, shared, prep_res, exec_res):
        shared["query_analysis"] = exec_res
        shared["keywords"] = exec_res.get("keywords", [])
        shared["tech_stack"] = exec_res.get("tech_stack", [])
        shared["features"] = exec_res.get("features", [])
        
        # Determine next action based on analysis quality
        if not exec_res.get("keywords") and not exec_res.get("features"):
            return "clarify"  # Need to clarify with the user
        return "search"  # Continue to search

class ClarifyQueryNode(Node):
    """Ask the user to clarify their query if the initial analysis was insufficient."""
    
    def prep(self, shared):
        return shared.get("query_analysis", {})
    
    def exec(self, query_analysis):
        original_query = query_analysis.get("original_query", "")
        
        prompt = f"""
The query "{original_query}" doesn't provide enough information to find relevant repositories.

Please help me understand:
1. What specific features are you looking to implement?
2. What technologies or programming languages will you be using?
3. What is the goal or purpose of your project?

Please provide these details so I can find the most helpful repositories.
"""
        return prompt
    
    def post(self, shared, prep_res, exec_res):
        # Store the clarification prompt
        shared["clarification_prompt"] = exec_res
        return "default"  # Waits for user's clarified response

class SearchWebNode(Node):
    """Searches the web for repositories based on the query analysis."""
    
    def prep(self, shared):
        keywords = shared.get("keywords", [])
        tech_stack = shared.get("tech_stack", [])
        features = shared.get("features", [])
        
        # Construct an effective search query
        search_terms = []
        
        # Add specific features
        if features:
            search_terms.extend(features[:2])  # Include top 2 features
        
        # Add technologies
        if tech_stack:
            search_terms.extend(tech_stack[:2])  # Include top 2 technologies
        
        # Add general keywords
        if keywords:
            search_terms.extend(keywords[:2])  # Include top 2 keywords
        
        # Add 'GitHub repository' to focus on repositories
        search_terms.append("GitHub repository")
        
        # Join into a search query
        search_query = " ".join(search_terms)
        
        return search_query
    
    def exec(self, search_query):
        # Search the web
        return search_web(search_query, max_results=15)
    
    def post(self, shared, prep_res, exec_res):
        # Store the search results
        shared["web_search_results"] = exec_res
        
        # Determine next steps based on search results
        if not exec_res:
            return "youtube_search"  # Try YouTube if web search has no results
        return "filter_results"  # Continue to filter results

class SearchYouTubeNode(Node):
    """Searches YouTube for tutorials and videos about the repositories."""
    
    def prep(self, shared):
        keywords = shared.get("keywords", [])
        tech_stack = shared.get("tech_stack", [])
        features = shared.get("features", [])
        
        # Construct a search query
        search_terms = []
        
        if features:
            search_terms.append(features[0])  # Top feature
        
        if tech_stack:
            search_terms.append(tech_stack[0])  # Top technology
        
        if keywords:
            search_terms.append(keywords[0])  # Top keyword
        
        # Add 'tutorial repository' to focus on tutorial videos
        search_terms.append("tutorial repository")
        
        # Join into a search query
        search_query = " ".join(search_terms)
        
        return search_query
    
    def exec(self, search_query):
        return search_youtube(search_query, max_results=5)
    
    def post(self, shared, prep_res, exec_res):
        # Store the YouTube results
        shared["youtube_results"] = exec_res
        return "extract_repos"  # Extract repos from all search results

class FilterSearchResultsNode(BatchNode):
    """Filters search results for relevance to user's requirements."""
    
    def prep(self, shared):
        results = shared.get("web_search_results", [])
        if not results:
            return []
        
        return results
    
    def exec(self, result):
        keywords = self.params.get("keywords", [])
        tech_stack = self.params.get("tech_stack", [])
        features = self.params.get("features", [])
        
        # Check relevance using our enhanced check_content_relevance
        relevance_data = check_content_relevance(
            result, 
            keywords=keywords, 
            tech_stack=tech_stack, 
            features=features, 
            threshold=0.5
        )
        
        # Add relevance data to the result
        result.update(relevance_data)
        
        return result
    
    def post(self, shared, prep_res, relevance_data_list):
        # Filter for relevant results
        relevant_results = [result for result in relevance_data_list if result.get("is_relevant", False)]
        
        # Store filtered results
        shared["relevant_results"] = relevant_results
        
        return "extract_repos"

class ExtractGitHubReposNode(Node):
    """Extracts GitHub repository URLs from search results."""
    
    def prep(self, shared):
        # Combine all available search results
        all_results = []
        
        # Add web search results
        web_results = shared.get("relevant_results") or shared.get("web_search_results", [])
        all_results.extend(web_results)
        
        # Add YouTube results
        youtube_results = shared.get("youtube_results", [])
        all_results.extend(youtube_results)
        
        return all_results
    
    def exec(self, all_results):
        # Extract GitHub URLs from all results
        all_urls = []
        
        for result in all_results:
            # Extract from title and snippet/description
            text_to_check = ""
            
            if isinstance(result, dict):
                for field in ["title", "snippet", "description"]:
                    if field in result and result[field]:
                        text_to_check += " " + result[field]
            
            # Extract GitHub URLs
            urls = extract_github_urls(text_to_check)
            all_urls.extend(urls)
        
        # Deduplicate URLs
        unique_urls = list(set(all_urls))
        
        return unique_urls
    
    def post(self, shared, prep_res, exec_res):
        # Store the repository URLs
        shared["repository_urls"] = exec_res
        
        if not exec_res:
            return "no_repos_found"  # No repositories found
        
        return "check_repos"  # Continue to check repositories

class CheckRepositoriesNode(BatchNode):
    """Checks the quality and complexity of repositories."""
    
    def prep(self, shared):
        return shared.get("repository_urls", [])
    
    def exec(self, repo_url):
        # Check repository complexity and quality
        return check_repository_complexity_and_size(repo_url)
    
    def post(self, shared, prep_res, exec_res_list):
        # Pair URLs with complexity data
        repo_data = []
        
        for i, url in enumerate(prep_res):
            if i < len(exec_res_list):
                repo_data.append({
                    "url": url,
                    **exec_res_list[i]
                })
        
        # Filter for repositories that meet quality criteria
        quality_repos = [repo for repo in repo_data if repo.get("meets_criteria", False)]
        
        # Store repository data
        shared["repository_quality_data"] = repo_data
        shared["quality_repositories"] = quality_repos
        
        if not quality_repos:
            return "no_quality_repos"  # No quality repositories found
        
        return "display_repos"  # Display repositories to the user

class NoReposFoundNode(Node):
    """Handles the case when no repositories are found."""
    
    def exec(self, _):
        return "No GitHub repositories were found in the search results. Let's refine your query to find relevant repositories."
    
    def post(self, shared, prep_res, exec_res):
        shared["error_message"] = exec_res
        return "clarify"  # Go back to clarify the query

class NoQualityReposNode(Node):
    """Handles the case when no quality repositories are found."""
    
    def prep(self, shared):
        return shared.get("repository_quality_data", [])
    
    def exec(self, repo_data):
        if not repo_data:
            return "No repositories were found that match your requirements."
        
        return "Found repositories, but none meet the quality criteria. Consider refining your search or adjusting your requirements."
    
    def post(self, shared, prep_res, exec_res):
        shared["error_message"] = exec_res
        return "display_all_repos"  # Display all repos, even low quality ones

class DisplayRepositoriesNode(Node):
    """Displays repositories to the user for selection."""
    
    def prep(self, shared):
        # Get the repositories to display
        if "quality_repositories" in shared and shared["quality_repositories"]:
            return shared["quality_repositories"]
        return shared.get("repository_quality_data", [])
    
    def exec(self, repositories):
        # Format repositories for display
        return format_repository_list(repositories)
    
    def post(self, shared, prep_res, exec_res):
        # Store the formatted list
        shared["repository_display"] = exec_res
        return "select_repo"  # Prompt user to select a repository

class SelectRepositoryNode(Node):
    """Prompts the user to select a repository for analysis."""
    
    def prep(self, shared):
        # Get repositories for selection
        if "quality_repositories" in shared and shared["quality_repositories"]:
            repos = shared["quality_repositories"]
        else:
            repos = shared.get("repository_quality_data", [])
        
        return repos
    
    def exec(self, repositories):
        # Create a selection prompt
        selection_prompt = "Please select a repository to analyze:"
        return {
            "prompt": selection_prompt,
            "options": repositories
        }
    
    def post(self, shared, prep_res, exec_res):
        # Store selection data
        shared["selection_data"] = exec_res
        return "wait_for_selection"  # Wait for user's selection

class AnalyzeRepositoryNode(Node):
    """Performs detailed analysis of the selected repository."""
    
    def prep(self, shared):
        # Get the selected repository URL
        selected_repo = shared.get("selected_repository", {})
        return selected_repo.get("url", "")
    
    def exec(self, repo_url):
        if not repo_url:
            return {"error": "No repository URL provided"}
        
        # Analyze the repository
        return analyze_repository(repo_url)
    
    def post(self, shared, prep_res, exec_res):
        # Store the repository analysis
        shared["repository_analysis"] = exec_res
        
        # Check for errors
        if "error" in exec_res:
            return "analysis_error"
        
        return "analyze_with_llm"  # Continue to LLM analysis

class AnalysisErrorNode(Node):
    """Handles repository analysis errors."""
    
    def prep(self, shared):
        return shared.get("repository_analysis", {}).get("error", "An error occurred during repository analysis")
    
    def exec(self, error_message):
        return f"Error analyzing repository: {error_message}\n\nPlease select another repository to analyze."
    
    def post(self, shared, prep_res, exec_res):
        shared["error_message"] = exec_res
        return "display_repos"  # Go back to repository display

class AnalyzeWithLLMNode(Node):
    """Analyzes repository data using an LLM to evaluate its usefulness."""
    
    def prep(self, shared):
        # Gather required inputs
        repo_data = shared.get("repository_data", {})
        keywords = shared.get("keywords", [])
        tech_stack = shared.get("tech_stack", [])
        features = shared.get("features", [])
        llm_config = shared.get("llm_config", {})
        
        # Validate necessary data is present
        if not repo_data:
            raise ValueError("Repository data is missing")
        
        if not features and not keywords and not tech_stack:
            raise ValueError("User requirements are missing")
            
        return {
            "repo_data": repo_data,
            "keywords": keywords,
            "tech_stack": tech_stack,
            "features": features,
            "llm_config": llm_config
        }
    
    @log_execution_time
    def exec(self, inputs):
        repo_data = inputs["repo_data"]
        keywords = inputs["keywords"]
        tech_stack = inputs["tech_stack"]
        features = inputs["features"]
        llm_config = inputs["llm_config"]
        
        # Get LLM configuration if provided
        provider = llm_config.get("provider")
        model = llm_config.get("model")
        
        return analyze_repository_with_llm(
            repo_data, keywords, tech_stack, features,
            model=model, provider=provider
        )
    
    def post(self, shared, prep_res, exec_res):
        # Store the LLM analysis
        shared["repository_llm_analysis"] = exec_res
        return "generate_guides"

class GenerateImplementationGuidesNode(Node):
    """Generates implementation guides based on the repository analysis."""
    
    def prep(self, shared):
        analysis = shared.get("repository_analysis", {}).get("detailed_analysis", {})
        tech_stack = shared.get("tech_stack", [])
        
        return {
            "analysis": analysis,
            "tech_stack": tech_stack
        }
    
    def exec(self, inputs):
        analysis = inputs.get("analysis", {})
        tech_stack = inputs.get("tech_stack", [])
        
        # Generate implementation guides
        guides = generate_implementation_guides_from_analysis(analysis, tech_stack)
        
        return guides
    
    def post(self, shared, prep_res, exec_res):
        # Store the implementation guides
        shared["implementation_guides"] = exec_res
        shared["repository_analysis"]["implementation_guides"] = exec_res
        
        return "format_for_mcp"  # Continue to MCP formatting

class FormatForMCPNode(Node):
    """Formats the analysis data for MCP server."""
    
    def prep(self, shared):
        return shared.get("repository_analysis", {})
    
    def exec(self, repo_analysis):
        # Format data for MCP
        return format_for_mcp(repo_analysis)
    
    def post(self, shared, prep_res, exec_res):
        # Store the MCP package
        shared["mcp_package"] = exec_res
        
        return "create_mcp"  # Continue to create MCP server

class CreateMCPServerNode(Node):
    """Creates an MCP server with the formatted data."""
    
    def prep(self, shared):
        mcp_package = shared.get("mcp_package", {})
        
        return {
            "name": mcp_package.get("name", "repository-mcp"),
            "tools": mcp_package.get("tools", []),
            "implementation_guides": mcp_package.get("implementation_guides", {})
        }
    
    def exec(self, inputs):
        name = inputs.get("name", "repository-mcp")
        tools = inputs.get("tools", [])
        guides = inputs.get("implementation_guides", {})
        
        # Create MCP server
        mcp_server = create_mcp_server(name, tools, guides)
        
        return mcp_server
    
    def post(self, shared, prep_res, exec_res):
        # Store the MCP server
        shared["mcp_server"] = exec_res
        
        return "start_mcp"  # Continue to start the server

class StartMCPServerNode(Node):
    """Starts the MCP server."""
    
    def prep(self, shared):
        return shared.get("mcp_server")
    
    def exec(self, mcp_server):
        if not mcp_server:
            return {"status": "error", "message": "No MCP server available"}
        
        # Start the server
        server_info = start_mcp_server(mcp_server)
        
        return server_info
    
    def post(self, shared, prep_res, exec_res):
        # Store server info
        shared["server_info"] = exec_res
        
        if exec_res.get("status") == "error":
            return "server_error"
        
        return "complete"  # Process complete

class ServerErrorNode(Node):
    """Handles MCP server startup errors."""
    
    def prep(self, shared):
        return shared.get("server_info", {}).get("error", "Unknown error starting server")
    
    def exec(self, error):
        return f"Error starting MCP server: {error}\n\nImplementation guides have been generated but the server could not be started."
    
    def post(self, shared, prep_res, exec_res):
        shared["error_message"] = exec_res
        return "complete"  # Complete with error

class ProcessCompleteNode(Node):
    """Finalizes the process and presents results to the user."""
    
    def prep(self, shared):
        server_info = shared.get("server_info", {})
        repo_name = shared.get("repository_analysis", {}).get("basic_info", {}).get("name", "repository")
        guides = shared.get("implementation_guides", {})
        
        return {
            "server_info": server_info,
            "repo_name": repo_name,
            "guides": guides
        }
    
    def exec(self, inputs):
        server_info = inputs.get("server_info", {})
        repo_name = inputs.get("repo_name", "repository")
        guides = inputs.get("guides", {})
        
        # Format a success message
        message = f"""
Analysis complete for {repo_name}!

MCP Server is running at {server_info.get('url', 'localhost:8000')}

The server provides {len(guides)} implementation guides:
{', '.join(guides.keys())}

You can access these guides through the MCP server's API.
"""
        return message
    
    def post(self, shared, prep_res, exec_res):
        shared["completion_message"] = exec_res
        return "end"  # End the flow 