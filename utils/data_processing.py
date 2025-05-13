"""
Data processing utilities for Repository Analysis to MCP Server system.
"""

import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Union

from .llm import call_llm
from .monitoring import log_execution_time

def format_for_mcp(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Formats repository analysis data for MCP server.
    
    Args:
        data: Repository analysis data
        
    Returns:
        MCP-formatted data package
    """
    repo_name = data.get("basic_info", {}).get("name", "repository")
    repo_url = data.get("basic_info", {}).get("url", "")
    
    # Create basic MCP package
    mcp_package = {
        "name": f"{repo_name}-mcp",
        "version": "1.0.0",
        "description": f"MCP server for {repo_name} repository",
        "repository": repo_url,
        "server_info": {
            "host": "localhost",
            "port": 8000
        },
        "tools": [],
        "implementation_guides": {},
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "source_repo": repo_url
        }
    }
    
    # Add tools based on features
    features = data.get("detailed_analysis", {}).get("feature_map", {})
    for feature_name, feature_details in features.items():
        tool = {
            "name": f"get_{feature_name.lower().replace(' ', '_')}",
            "description": f"Get information about {feature_name}",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "detail_level": {
                        "type": "string",
                        "enum": ["basic", "detailed"],
                        "description": "Level of detail to return"
                    }
                }
            }
        }
        mcp_package["tools"].append(tool)
    
    # Add implementation guides
    if "implementation_guides" in data:
        mcp_package["implementation_guides"] = data["implementation_guides"]
    
    return mcp_package

@log_execution_time("generate_guides")
def generate_implementation_guides_from_analysis(analysis: Dict[str, Any], 
                                               tech_stack: List[str]) -> Dict[str, Any]:
    """
    Creates detailed implementation guides from repository analysis tailored to user's tech stack.
    
    Args:
        analysis: Repository analysis data
        tech_stack: User's technology stack
        
    Returns:
        Dictionary of implementation guides by feature
    """
    guides = {}
    
    # Extract repository info
    repo_name = analysis.get("repository", {}).get("name", "Unknown Repository")
    
    # Get features from the analysis
    feature_map = analysis.get("feature_map", {})
    
    for feature_name, feature_details in feature_map.items():
        # Prepare file references for the guide
        matching_files = feature_details.get("matching_files", [])
        file_references = []
        
        for file_ref in matching_files:
            if isinstance(file_ref, dict):
                for fname, desc in file_ref.items():
                    file_references.append(f"- `{fname}`: {desc}")
            elif isinstance(file_ref, str):
                file_references.append(f"- `{file_ref}`")
        
        # Generate implementation guide using LLM
        prompt = f"""
Create an implementation guide for "{feature_name}" feature based on the repository {repo_name}.

FEATURE DETAILS:
Implementation Score: {feature_details.get('implementation_score', 'N/A')}
Adaptation Needed: {feature_details.get('adaptation_needed', 'N/A')}

MATCHING FILES:
{'\n'.join(file_references)}

USER'S TECH STACK:
{', '.join(tech_stack)}

Please create a detailed implementation guide with the following sections:
1. Overview - Summary of the feature and how it works
2. Core Concepts - Key concepts to understand
3. Step-by-Step Implementation - Detailed steps to implement this feature
4. Code Examples - Sample code for implementation
5. Integration with User's Tech Stack - How to integrate with {', '.join(tech_stack)}
6. Troubleshooting - Common issues and solutions

Format your response in YAML with these exact sections.
"""
        response = call_llm(prompt, max_tokens=2000)
        
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
            import yaml
            guide_content = yaml.safe_load(yaml_content)
            guides[feature_name] = guide_content
        except Exception as e:
            print(f"Error parsing guide for {feature_name}: {str(e)}")
            # Create a basic guide if parsing fails
            guides[feature_name] = {
                "overview": f"Implementation guide for {feature_name}",
                "core_concepts": ["Feature implementation"],
                "step_by_step_implementation": ["Refer to repository documentation"],
                "code_examples": "# Example code not available",
                "integration_with_tech_stack": f"Integration with {', '.join(tech_stack)}",
                "troubleshooting": ["No troubleshooting information available"]
            }
    
    return guides

def format_repository_list(repositories: List[Dict[str, Any]]) -> str:
    """
    Formats repository list for user display.
    
    Args:
        repositories: List of repository dictionaries
        
    Returns:
        Formatted string for display
    """
    if not repositories:
        return "No repositories found."
    
    formatted_list = "Found repositories:\n\n"
    
    for i, repo in enumerate(repositories):
        # Extract basic information
        name = repo.get("basic_info", {}).get("name", "Unknown Repository")
        description = repo.get("basic_info", {}).get("description", "No description available")
        stars = repo.get("basic_info", {}).get("stars", 0)
        
        # Extract complexity information
        complexity = repo.get("complexity_score", "N/A")
        difficulty = repo.get("implementation_difficulty", "Unknown")
        
        # Format tech stack compatibility if available
        tech_compat = ""
        if "tech_stack_compatibility" in repo:
            compat_score = repo["tech_stack_compatibility"].get("compatibility_score", "N/A")
            compatible_techs = repo["tech_stack_compatibility"].get("compatible_technologies", [])
            tech_compat = f"\n   Tech Compatibility: {compat_score}/10 ({', '.join(compatible_techs[:3])})"
            
            if len(compatible_techs) > 3:
                tech_compat += f" and {len(compatible_techs) - 3} more"
        
        # Format feature implementation if available
        feature_info = ""
        if "feature_map" in repo:
            features = list(repo["feature_map"].keys())
            feature_info = f"\n   Features: {', '.join(features[:3])}"
            
            if len(features) > 3:
                feature_info += f" and {len(features) - 3} more"
        
        # Combine information
        formatted_list += (
            f"{i+1}. {name} ({stars} ★)\n"
            f"   {description}\n"
            f"   Complexity: {complexity}/10, Difficulty: {difficulty}{tech_compat}{feature_info}\n\n"
        )
    
    return formatted_list

def get_user_selection(prompt: str, options: List[Any]) -> Optional[Any]:
    """
    Handles user selection from a list of options.
    
    Args:
        prompt: Prompt to display to user
        options: List of options
        
    Returns:
        Selected option (or None if canceled)
    """
    if not options:
        print("No options available.")
        return None
    
    # Display options
    print(f"\n{prompt}")
    for i, option in enumerate(options):
        # Format option display based on type
        if isinstance(option, dict) and "name" in option:
            display = option["name"]
        elif isinstance(option, dict) and "basic_info" in option:
            display = option["basic_info"].get("name", str(option))
        else:
            display = str(option)
        
        print(f"{i+1}. {display}")
    
    print(f"0. Cancel")
    
    # Get selection
    while True:
        try:
            selection = input("\nEnter selection number: ")
            
            # Check for cancel
            if selection == "0":
                return None
            
            idx = int(selection) - 1
            if 0 <= idx < len(options):
                return options[idx]
            else:
                print(f"Invalid selection. Please enter a number between 0 and {len(options)}.")
        except ValueError:
            print("Please enter a valid number.")

if __name__ == "__main__":
    # Test format_repository_list
    sample_repos = [
        {
            "basic_info": {
                "name": "Repository A",
                "description": "A sample repository for testing",
                "stars": 150
            },
            "complexity_score": 7.5,
            "implementation_difficulty": "Medium",
            "tech_stack_compatibility": {
                "compatibility_score": 8,
                "compatible_technologies": ["Python", "Flask", "MongoDB"]
            },
            "feature_map": {
                "authentication": {},
                "data_processing": {},
                "api_integration": {}
            }
        },
        {
            "basic_info": {
                "name": "Repository B",
                "description": "Another example repository",
                "stars": 75
            },
            "complexity_score": 5.2,
            "implementation_difficulty": "Easy"
        }
    ]
    
    formatted = format_repository_list(sample_repos)
    print(formatted)
    
    # Test user selection
    selection = get_user_selection("Choose a test repository:", ["Repository A", "Repository B", "Repository C"])
    if selection:
        print(f"You selected: {selection}") 