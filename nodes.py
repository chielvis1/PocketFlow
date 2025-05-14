"""
Node definitions for Repository Analysis.

This file contains the nodes used in the repository analysis flow.
"""

from pocketflow import Node
from typing import Dict, Any, Optional, Tuple, List, Union
from urllib.parse import urlparse

class ParseRepositoryURLNode(Node):
    """
    Node to parse and validate a GitHub repository URL.
    """
    def prep(self, shared):
        """Get repository URL from shared data."""
        return shared.get("repo_url")
    
    def exec(self, repo_url):
        """Validate GitHub repository URL."""
        if not repo_url:
            return None
            
        from urllib.parse import urlparse
        parsed_url = urlparse(repo_url)
        
        # Check if URL is valid and is a GitHub URL
        if not parsed_url.netloc or 'github.com' not in parsed_url.netloc:
            return {"error": "Invalid GitHub URL", "url": repo_url}
            
        # Extract username and repo name
        path_parts = parsed_url.path.strip('/').split('/')
        if len(path_parts) < 2:
            return {"error": "Invalid GitHub repository format", "url": repo_url}
            
        return {
            "url": repo_url,
            "username": path_parts[0],
            "repo_name": path_parts[1],
            "is_valid": True
        }
    
    def post(self, shared, prep_res, exec_res):
        """Process validated repository URL."""
        if not exec_res:
            shared["error"] = "No repository URL provided"
            return "error"
            
        if "error" in exec_res:
            shared["error"] = exec_res["error"]
            return "error"
            
        shared["validated_repo"] = exec_res
        return "default"

class AnalyzeRepositoryNode(Node):
    """
    Node for analyzing a GitHub repository.
    """
    def prep(self, shared):
        """Prepare repository URL from shared data."""
        return shared.get("validated_repo", {}).get("url")
    
    def exec(self, repo_url):
        """Analyze GitHub repository."""
        if not repo_url:
            return {"error": "No valid repository URL provided"}
            
        from utils.github import analyze_repository
        return analyze_repository(repo_url)
    
    def post(self, shared, prep_res, exec_res):
        """Process repository analysis results."""
        if not exec_res:
            shared["error"] = "Failed to analyze repository"
            return "analysis_error"
            
        if "error" in exec_res:
            shared["error"] = exec_res["error"]
            return "analysis_error"
            
        shared["repo_analysis"] = exec_res
        return "default"

class AnalyzeWithLLMNode(Node):
    """
    Node to analyze repository data with an LLM.
    """
    def prep(self, shared):
        """Prepare repository analysis data for LLM."""
        return shared.get("repo_analysis"), shared.get("validated_repo")
    
    def exec(self, inputs):
        """Analyze repository with LLM."""
        repo_analysis, validated_repo = inputs
        
        if not repo_analysis or not validated_repo:
            return {"error": "Missing repository data for analysis"}
            
        from utils.llm import call_llm
        
        # Prepare a prompt for the LLM to analyze the repository
        prompt = f"""
        Analyze this GitHub repository structure and provide insights:
        
        Repository: {validated_repo['url']}
        Owner: {validated_repo['username']}
        Name: {validated_repo['repo_name']}
        
        Repository Analysis:
        {repo_analysis}
        
        Please provide:
        1. A summary of the repository's purpose
        2. The main technologies/frameworks used
        3. The overall architecture
        4. Key components and their relationships
        5. Recommendations for someone wanting to understand this codebase
        """
        
        analysis = call_llm(prompt)
        return {
            "llm_analysis": analysis,
            "repo_data": validated_repo
        }
    
    def post(self, shared, prep_res, exec_res):
        """Store LLM analysis results."""
        if "error" in exec_res:
            shared["error"] = exec_res["error"]
            return "error"
            
        shared["llm_analysis"] = exec_res["llm_analysis"]
        return "default"

class AnalysisErrorNode(Node):
    """
    Node to handle repository analysis errors.
    """
    def prep(self, shared):
        """Get error information."""
        return shared.get("error", "Unknown error")
    
    def exec(self, error_message):
        """Format error message for display."""
        return f"Error analyzing repository: {error_message}"
    
    def post(self, shared, prep_res, exec_res):
        """Store formatted error message."""
        shared["formatted_error"] = exec_res
        print(exec_res)
        return "default"

# Add other node classes from the original file below...
# Tutorial generation nodes
class FetchRepo(Node):
    """Fetches a repository from GitHub or a local directory."""
    
    def prep(self, shared):
        return shared.get("repo_url"), shared.get("local_dir")
    
    def exec(self, inputs):
        repo_url, local_dir = inputs
        
        if local_dir:
            # Use local repository
            from utils.crawl_local_files import crawl_local_files
            return crawl_local_files(local_dir)
        
        if repo_url:
            # Use GitHub repository
            from utils.crawl_github_files import crawl_github_files
            from utils.github import get_github_token
            
            # Get token from session store
            github_token = get_github_token()
            
            return crawl_github_files(repo_url, token=github_token)
        
        return {"error": "No repository source provided"}
    
    def post(self, shared, prep_res, exec_res):
        if "error" in exec_res:
            shared["error"] = exec_res["error"]
            return "error"
            
        shared["repository_files"] = exec_res
        return "default"

# Additional tutorial generation nodes...
# These are typically found in the original nodes.py but can be added as needed

class IdentifyAbstractions(Node):
    """Identifies key abstractions, patterns, and concepts in the repository."""
    
    def prep(self, shared):
        return shared.get("repository_files")
    
    def exec(self, files):
        if not files:
            return {"error": "No repository files provided"}
        
        from utils.llm import call_llm
        
        # Extract content sample and key files
        file_paths = list(files.keys())
        sample_content = "\n".join([f"File: {path}\n{files[path][:500]}..." for path in file_paths[:10]])
        
        prompt = f"""
        Analyze the following files from a repository and identify key abstractions, patterns, and concepts:
        
        {sample_content}
        
        Please identify the key abstractions, patterns, and software concepts present in this codebase.
        Focus on the main architectural elements, design patterns, and core domain models.
        """
        
        analysis = call_llm(prompt)
        return {"abstractions": analysis, "file_count": len(files)}
    
    def post(self, shared, prep_res, exec_res):
        if "error" in exec_res:
            shared["error"] = exec_res["error"]
            return "error"
            
        shared["abstractions"] = exec_res["abstractions"]
        return "default"

class AnalyzeRelationships(Node):
    """Analyzes relationships between components and creates a structure map."""
    
    def prep(self, shared):
        return shared.get("repository_files"), shared.get("abstractions")
    
    def exec(self, inputs):
        files, abstractions = inputs
        
        if not files or not abstractions:
            return {"error": "Missing repository files or abstractions"}
        
        from utils.llm import call_llm
        
        # Extract core file structure
        file_structure = "\n".join([f"- {path}" for path in list(files.keys())[:50]])
        
        prompt = f"""
        Based on the following file structure and identified abstractions, analyze the relationships
        between components in this codebase:
        
        Identified abstractions:
        {abstractions}
        
        File structure:
        {file_structure}
        
        Please map out how these components relate to each other, focusing on:
        1. Dependencies between modules
        2. Information flow
        3. Hierarchical relationships
        4. Core system interactions
        """
        
        relationships = call_llm(prompt)
        return {"relationships": relationships}
    
    def post(self, shared, prep_res, exec_res):
        if "error" in exec_res:
            shared["error"] = exec_res["error"]
            return "error"
            
        shared["relationships"] = exec_res["relationships"]
        return "default"

class OrderChapters(Node):
    """Creates a logical sequence of chapters for the tutorial."""
    
    def prep(self, shared):
        return shared.get("abstractions"), shared.get("relationships"), shared.get("language", "english")
    
    def exec(self, inputs):
        abstractions, relationships, language = inputs
        
        if not abstractions or not relationships:
            return {"error": "Missing abstractions or relationships"}
        
        from utils.llm import call_llm
        
        prompt = f"""
        Based on the following abstractions and relationships, create a logical sequence of chapters
        for a tutorial in {language}:
        
        Abstractions:
        {abstractions}
        
        Relationships:
        {relationships}
        
        Please outline 5-8 chapters that would form an effective tutorial for understanding this codebase.
        For each chapter, provide:
        1. Title
        2. Brief description of what the chapter covers
        3. Key concepts to be explained
        
        Format as a numbered list of chapters with clear indentation for descriptions.
        """
        
        chapters_outline = call_llm(prompt)
        return {"chapters_outline": chapters_outline}
    
    def post(self, shared, prep_res, exec_res):
        if "error" in exec_res:
            shared["error"] = exec_res["error"]
            return "error"
            
        shared["chapters_outline"] = exec_res["chapters_outline"]
        
        # Extract the number of chapters (approximation based on numbered list)
        import re
        chapter_count = len(re.findall(r'^\d+\.', exec_res["chapters_outline"], re.MULTILINE))
        shared["tutorial_total_chapters"] = chapter_count
        
        return "default"

class WriteChapters(Node):
    """Writes the individual tutorial chapters based on the outline."""
    
    def prep(self, shared):
        return (
            shared.get("repository_files"),
            shared.get("abstractions"),
            shared.get("relationships"),
            shared.get("chapters_outline"),
            shared.get("language", "english"),
            shared.get("tutorial_output_dir", "tutorial")
        )
    
    def exec(self, inputs):
        files, abstractions, relationships, chapters_outline, language, output_dir = inputs
        
        if not all([files, chapters_outline, output_dir]):
            return {"error": "Missing required inputs for chapter writing"}
        
        import os
        import re
        from utils.llm import call_llm
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Extract chapter titles for the table of contents
        chapter_titles = re.findall(r'^\d+\.\s+(.*?)$', chapters_outline, re.MULTILINE)
        
        # Write each chapter
        chapters = []
        for i, title in enumerate(chapter_titles, 1):
            # Find the content for this chapter in the outline
            chapter_content_match = re.search(f"{i}\\. {re.escape(title)}(.*?)(?=\\d+\\. |$)", 
                                             chapters_outline, re.DOTALL)
            chapter_description = chapter_content_match.group(1).strip() if chapter_content_match else ""
            
            prompt = f"""
            Write Chapter {i}: {title} for a tutorial in {language}.
            
            Chapter Description:
            {chapter_description}
            
            Repository Context:
            - Abstractions: {abstractions[:500]}...
            - Relationships: {relationships[:500]}...
            
            The chapter should:
            1. Be well-structured with clear headings (use markdown format with # for headers)
            2. Include code examples where relevant
            3. Explain concepts clearly for someone new to this codebase
            4. Be comprehensive yet concise
            5. Include a brief introduction and conclusion
            
            Write the complete chapter in markdown format.
            """
            
            chapter_content = call_llm(prompt)
            
            # Save the chapter to a file
            filename = f"chapter_{i:02d}_{title.lower().replace(' ', '_')}.md"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'w') as f:
                f.write(f"# Chapter {i}: {title}\n\n")
                f.write(chapter_content)
            
            chapters.append({
                "number": i,
                "title": title,
                "filename": filename,
                "path": filepath
            })
        
        return {"chapters": chapters, "chapter_count": len(chapters)}
    
    def post(self, shared, prep_res, exec_res):
        if "error" in exec_res:
            shared["error"] = exec_res["error"]
            return "error"
            
        shared["chapters"] = exec_res["chapters"]
        return "default"

class CombineTutorial(Node):
    """Creates the final tutorial by combining chapters and adding navigation."""
    
    def prep(self, shared):
        return (
            shared.get("chapters"),
            shared.get("tutorial_output_dir", "tutorial"),
            shared.get("language", "english")
        )
    
    def exec(self, inputs):
        chapters, output_dir, language = inputs
        
        if not chapters or not output_dir:
            return {"error": "Missing chapters or output directory"}
        
        import os
        
        # Create the index page with table of contents
        index_content = f"# Tutorial - {language.capitalize()}\n\n"
        index_content += "## Table of Contents\n\n"
        
        for chapter in sorted(chapters, key=lambda x: x["number"]):
            index_content += f"{chapter['number']}. [{chapter['title']}]({chapter['filename']})\n"
        
        # Add navigation links to each chapter
        for i, chapter in enumerate(sorted(chapters, key=lambda x: x["number"])):
            chapter_path = chapter["path"]
            
            with open(chapter_path, 'r') as f:
                chapter_content = f.read()
            
            # Add navigation bar
            nav_bar = "## Navigation\n\n"
            
            if i > 0:
                prev_chapter = chapters[i-1]
                nav_bar += f"[← Previous: {prev_chapter['title']}]({prev_chapter['filename']}) | "
            else:
                nav_bar += "← Previous | "
                
            nav_bar += f"[↑ Table of Contents](index.md)"
            
            if i < len(chapters) - 1:
                next_chapter = chapters[i+1]
                nav_bar += f" | [Next: {next_chapter['title']} →]({next_chapter['filename']})"
            else:
                nav_bar += " | Next →"
            
            with open(chapter_path, 'w') as f:
                f.write(chapter_content + "\n\n" + nav_bar)
        
        # Write the index file
        index_path = os.path.join(output_dir, "index.md")
        with open(index_path, 'w') as f:
            f.write(index_content)
            
        return {"index_path": index_path, "total_chapters": len(chapters)}
    
    def post(self, shared, prep_res, exec_res):
        if "error" in exec_res:
            shared["error"] = exec_res["error"]
            return "error"
            
        shared["tutorial_index"] = exec_res["index_path"]
        shared["tutorial_total_chapters"] = exec_res["total_chapters"]
        
        print(f"\nTutorial successfully generated with {exec_res['total_chapters']} chapters.")
        print(f"Index file created at: {exec_res['index_path']}")
        
        return "default"