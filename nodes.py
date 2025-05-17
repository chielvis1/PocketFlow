"""
Node definitions for Repository Analysis.

This file contains the nodes used in the repository analysis flow.
"""

from pocketflow import Node
from typing import Dict, Any, Optional, Tuple, List, Union
from urllib.parse import urlparse
import os
import json
import sys
import subprocess

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
        # Safely call repository analysis and catch exceptions
        try:
            from utils.github import analyze_repository
            analysis_result = analyze_repository(repo_url)
            return analysis_result
        except Exception as e:
            # Return error instead of raising to keep flow in error transition
            return {"error": f"Error during repository analysis: {e}"}
    
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
        
        # Safely call LLM and catch errors
        try:
            analysis = call_llm(prompt)
            return {
                "llm_analysis": analysis,
                "repo_data": validated_repo
            }
        except Exception as e:
            # Non-fatal LLM error; flow can continue
            return {"error": f"LLM analysis error: {e}"}
    
    def post(self, shared, prep_res, exec_res):
        """Store LLM analysis results."""
        # If LLM failed, log and continue without failing the analysis flow
        if isinstance(exec_res, dict) and exec_res.get("error"):
            print(f"LLM analysis failed (non-fatal): {exec_res['error']}")
            # Skip storing llm_analysis, proceed with default
            return "default"
        
        # Store successful LLM analysis
        shared["llm_analysis"] = exec_res.get("llm_analysis")
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

class FetchRepo(Node):
    """Fetches a repository from GitHub or a local directory."""
    
    def prep(self, shared):
        # Set current stage
        shared["current_stage"] = "fetch"
        
        repo_url = shared.get("repo_url")
        local_dir = shared.get("local_dir")
        project_name = shared.get("project_name")

        if not project_name:
            if repo_url:
                project_name = repo_url.split('/')[-1].replace('.git', '')
            else:
                project_name = os.path.basename(os.path.abspath(local_dir))
            shared["project_name"] = project_name
        
        # Ensure include/exclude patterns are in shared store
        if "include_patterns" not in shared:
            shared["include_patterns"] = {
                "*.py", "*.js", "*.jsx", "*.ts", "*.tsx", "*.go", "*.java",
                "*.c", "*.cc", "*.cpp", "*.h", "*.md", "*.rst", "Dockerfile",
                "Makefile", "*.yaml", "*.yml"
            }
            
        if "exclude_patterns" not in shared:
            shared["exclude_patterns"] = {
                "venv/*", ".venv/*", "*test*", "tests/*", "docs/*", "examples/*",
                "dist/*", "build/*", "node_modules/*", ".git/*", ".github/*"
            }
            
        if "max_file_size" not in shared:
            shared["max_file_size"] = 100000  # 100KB default
        
        include_patterns = shared["include_patterns"]
        exclude_patterns = shared["exclude_patterns"]
        max_file_size = shared["max_file_size"]
        
        return {
            "repo_url": repo_url,
            "local_dir": local_dir,
            "token": shared.get("github_token"),
            "include_patterns": include_patterns,
            "exclude_patterns": exclude_patterns,
            "max_file_size": max_file_size,
            "use_relative_paths": True
        }
    
    def exec(self, prep_res):
        if not prep_res["repo_url"] and not prep_res["local_dir"]:
            return {"error": "No repository URL or local directory provided"}
            
        try:
            if prep_res["repo_url"]:
                print(f"Crawling repository: {prep_res['repo_url']}...")
                from utils.crawl_github_files import crawl_github_files
                result = crawl_github_files(
                    repo_url=prep_res["repo_url"],
                    token=prep_res["token"],
                    include_patterns=prep_res["include_patterns"],
                    exclude_patterns=prep_res["exclude_patterns"],
                    max_file_size=prep_res["max_file_size"],
                    use_relative_paths=prep_res["use_relative_paths"]
                )
            else:
                print(f"Crawling directory: {prep_res['local_dir']}...")
                from utils.crawl_local_files import crawl_local_files
                result = crawl_local_files(
                    directory=prep_res["local_dir"],
                    include_patterns=prep_res["include_patterns"],
                    exclude_patterns=prep_res["exclude_patterns"],
                    max_file_size=prep_res["max_file_size"],
                    use_relative_paths=prep_res["use_relative_paths"]
                )

            # Validate result structure
            if not isinstance(result, dict):
                return {"error": f"Invalid result from crawler: expected dict, got {type(result)}"}
                
            if "files" not in result:
                return {"error": "No 'files' key in crawler result"}
                
            # Convert to list of (path, content) tuples for consistent handling
            files_dict = result.get("files", {})
            if not files_dict:
                return {"error": "No files found in repository"}
                
            files_list = list(files_dict.items())
            print(f"Fetched {len(files_list)} files.")
            
            # Add repository stats to the result
            return {
                "files": files_list,
                "file_count": len(files_list),
                "stats": result.get("stats", {})
            }
        except Exception as e:
            return {"error": f"Error fetching repository: {str(e)}"}
    
    def post(self, shared, prep_res, exec_res):
        if "error" in exec_res:
            shared["error"] = exec_res["error"]
            return "error"
            
        # Store files in shared with the correct key
        shared["files"] = exec_res["files"]
        # Also store in repository_files key which is expected by subsequent nodes
        shared["repository_files"] = dict(exec_res["files"])
        
        # Store additional metadata
        shared["file_count"] = exec_res["file_count"]
        if "stats" in exec_res:
            shared["repo_stats"] = exec_res["stats"]
            
        print(f"Repository fetched successfully with {exec_res['file_count']} files.")
        return "default"
    
    def exec_fallback(self, prep_res, exc):
        error_msg = f"Error fetching repository: {str(exc)}"
        print(error_msg)
        return {"error": error_msg}

# Additional tutorial generation nodes...
# These are typically found in the original nodes.py but can be added as needed

class IdentifyAbstractions(Node):
    """Identifies key abstractions, patterns, and concepts in the repository."""
    
    def prep(self, shared):
        print(f"IdentifyAbstractions prep - repository_files type: {type(shared.get('repository_files'))}")
        print(f"IdentifyAbstractions prep - repository_files item count: {len(shared.get('repository_files', {}))}")
        
        repo_files = shared.get("repository_files")
        if not repo_files:
            print("ERROR: repository_files is empty or not set!")
            
        return repo_files
    
    def exec(self, files):
        print(f"IdentifyAbstractions exec - files type: {type(files)}")
        
        if not files:
            return {"error": "No repository files provided"}
        
        from utils.llm import call_llm
        
        # Extract content sample and key files
        file_paths = list(files.keys())
        print(f"IdentifyAbstractions exec - file paths: {file_paths[:5]}...")
        
        sample_content = []
        
        # Extract first 500 characters from each file safely
        for path in file_paths[:10]:
            file_content = files[path]
            # Handle different content types safely
            if isinstance(file_content, str):
                sample = file_content[:500]
            elif isinstance(file_content, dict) and "content" in file_content:
                sample = file_content["content"][:500]
            else:
                # For any other type, convert to string first then slice
                sample = str(file_content)[:500]
            
            sample_content.append(f"File: {path}\n{sample}...")
            
        sample_text = "\n".join(sample_content)
        
        print("IdentifyAbstractions exec - calling LLM")
        
        prompt = f"""
        Analyze the following files from a repository and identify key abstractions, patterns, and concepts:
        
        {sample_text}
        
        Please identify the key abstractions, patterns, and software concepts present in this codebase.
        Focus on the main architectural elements, design patterns, and core domain models.
        """
        
        analysis = call_llm(prompt)
        return {"abstractions": analysis, "file_count": len(files)}
    
    def post(self, shared, prep_res, exec_res):
        print(f"IdentifyAbstractions post - exec_res keys: {exec_res.keys() if isinstance(exec_res, dict) else 'not a dict'}")
        
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
        
        # Safely truncate long texts
        if isinstance(abstractions, str):
            abstractions_summary = abstractions[:500]
        else:
            abstractions_summary = str(abstractions)[:500]
            
        if isinstance(relationships, str):
            relationships_summary = relationships[:500]
        else:
            relationships_summary = str(relationships)[:500]
        
        # Function to sanitize filenames
        def sanitize_filename(title, chapter_number):
            """
            Convert a chapter title to a valid filename.
            
            Args:
                title: The chapter title
                chapter_number: The chapter number
                
            Returns:
                A sanitized filename
            """
            import re
            import unicodedata
            
            # Normalize unicode characters
            normalized = unicodedata.normalize('NFKD', title)
            # Remove accents
            normalized = ''.join([c for c in normalized if not unicodedata.combining(c)])
            
            # Replace spaces and special characters with underscores
            sanitized = re.sub(r'[^\w\-\.]', '_', normalized)
            
            # Replace multiple consecutive underscores with a single one
            sanitized = re.sub(r'_+', '_', sanitized)
            
            # Remove common markdown/code file extensions that might be in the title
            sanitized = re.sub(r'\.(md|py|js|jsx|ts|tsx|json|yaml|yml)$', '', sanitized, flags=re.IGNORECASE)
            
            # Remove trailing underscores
            sanitized = sanitized.rstrip('_')
            
            # Ensure filename starts with chapter number
            if not sanitized.startswith(f"chapter_{chapter_number:02d}"):
                sanitized = f"chapter_{chapter_number:02d}_{sanitized}"
            
            # If the sanitized name somehow became empty, use a default
            if sanitized == "" or sanitized.isspace():
                sanitized = f"chapter_{chapter_number:02d}"
            
            # Ensure filename isn't too long for file systems (most limit around 255)
            if len(sanitized) > 200:
                sanitized = sanitized[:197] + "..."
            
            # Final check for trailing underscores
            sanitized = sanitized.rstrip('_')
            
            return sanitized + ".md"
        
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
            - Abstractions: {abstractions_summary}...
            - Relationships: {relationships_summary}...
            
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
            sanitized_title = sanitize_filename(title, i)
            filename = sanitized_title
            filepath = os.path.join(output_dir, filename)
            
            try:
                with open(filepath, 'w') as f:
                    f.write(f"# Chapter {i}: {title}\n\n")
                    f.write(chapter_content)
                print(f"Written chapter {i}: {filename}")
            except Exception as e:
                print(f"Error writing chapter {i}: {e}")
                return {"error": f"Failed to write chapter {i}: {str(e)}"}
            
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
        # Set current stage
        shared["current_stage"] = "combine"
        
        return (
            shared.get("chapters"),
            shared.get("tutorial_output_dir", "tutorial"),
            shared.get("language", "english")
        )
    
    def exec(self, inputs):
        chapters, output_dir, language = inputs
        
        # Ensure output directory is specified
        if not output_dir:
            return {"error": "Missing output directory"}
        # Warn if there are no chapters but continue to generate index
        if not chapters:
            print("Warning: No chapters to combine, generating empty tutorial index.")
        
        import os
        import shutil
        
        # Ensure the output directory exists
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            return {"error": f"Failed to create output directory: {str(e)}"}
        
        # Create the index page with table of contents
        index_content = f"# Tutorial - {language.capitalize()}\n\n"
        index_content += "## Table of Contents\n\n"
        
        try:
            # Sort chapters by number to ensure correct order
            sorted_chapters = sorted(chapters, key=lambda x: x.get("number", 0))
            
            # Validate that we have chapters
            if not sorted_chapters:
                return {"error": "No chapters available to combine"}
            
            # Build the table of contents
            for chapter in sorted_chapters:
                # Extract relative path for linking
                filename = os.path.basename(chapter.get("filename", ""))
                if not filename:
                    print(f"Warning: Chapter {chapter.get('number', '?')} has no filename")
                    continue
                    
                index_content += f"{chapter['number']}. [{chapter['title']}]({filename})\n"
            
            # Create backup of existing index if it exists
            index_path = os.path.join(output_dir, "index.md")
            if os.path.exists(index_path):
                backup_path = os.path.join(output_dir, "index.md.bak")
                try:
                    shutil.copy2(index_path, backup_path)
                    print(f"Created backup of existing index at {backup_path}")
                except Exception as e:
                    print(f"Warning: Could not create backup of index: {e}")
            
            # Write the index file
            try:
                with open(index_path, 'w') as f:
                    f.write(index_content)
                print(f"Written index file to {index_path}")
            except Exception as e:
                return {"error": f"Failed to write index file: {str(e)}"}
            
            # Create a combined version of all chapters
            combined_content = index_content + "\n\n"
            combined_content += "---\n\n"
            
            chapter_read_errors = []
            for chapter in sorted_chapters:
                try:
                    chapter_path = chapter.get("path")
                    if not chapter_path or not os.path.exists(chapter_path):
                        print(f"Warning: Chapter file not found at {chapter_path}")
                        chapter_read_errors.append(f"Missing file for chapter {chapter.get('number', '?')}: {chapter_path}")
                        continue
                        
                    with open(chapter_path, 'r') as f:
                        chapter_text = f.read()
                    combined_content += chapter_text + "\n\n---\n\n"
                except Exception as e:
                    error_msg = f"Could not read chapter {chapter.get('number', '?')}: {str(e)}"
                    print(f"Warning: {error_msg}")
                    chapter_read_errors.append(error_msg)
                    # Continue with other chapters instead of failing completely
            
            # Write the combined file
            combined_path = os.path.join(output_dir, "complete_tutorial.md")
            try:
                with open(combined_path, 'w') as f:
                    f.write(combined_content)
                print(f"Written combined tutorial to {combined_path}")
            except Exception as e:
                return {"error": f"Failed to write combined tutorial: {str(e)}"}
            
            # Report any chapter read errors but don't fail the whole process
            if chapter_read_errors:
                print(f"Completed with {len(chapter_read_errors)} chapter read errors")
                
            return {
                "index_path": index_path,
                "combined_path": combined_path,
                "chapter_count": len(sorted_chapters),
                "chapter_read_errors": chapter_read_errors
            }
        except Exception as e:
            error_msg = f"Error combining tutorial: {str(e)}"
            print(f"ERROR: {error_msg}")
            return {"error": error_msg}
    
    def post(self, shared, prep_res, exec_res):
        if "error" in exec_res:
            shared["error"] = exec_res["error"]
            return "error"
        
        shared["tutorial_index"] = exec_res.get("index_path")
        shared["tutorial_combined"] = exec_res.get("combined_path")
        import os
        # Set the directory where the tutorial files were written
        shared["final_output_dir"] = os.path.dirname(exec_res.get("index_path", ""))
        # Record total number of chapters generated
        shared["tutorial_total_chapters"] = exec_res.get("chapter_count", 0)
        # Store chapter read errors if any
        if "chapter_read_errors" in exec_res and exec_res["chapter_read_errors"]:
            shared["chapter_read_errors"] = exec_res["chapter_read_errors"]
        
        print(f"Completed tutorial generation with {exec_res.get('chapter_count', 0)} chapters.")
        return "default"
        
    def exec_fallback(self, prep_res, exc):
        return {"error": f"Exception in CombineTutorial: {str(exc)}"}

# Add new node for MCP server spec and code generation
class GenerateMCPServerNode(Node):
    """
    Node to generate an MCP server spec and server code based on the generated tutorial.
    """
    def prep(self, shared):
        return {
            "output_dir": shared.get("tutorial_output_dir"),
            "tutorial_index": shared.get("tutorial_index", os.path.join(shared.get("tutorial_output_dir"), "index.md")),
            "features": shared.get("features", [])
        }

    def exec(self, inputs):
        from utils.llm import call_llm
        import yaml
        output_dir = inputs["output_dir"]
        tutorial_index = inputs["tutorial_index"]
        features = inputs["features"]

        prompt = f"""
Generate a YAML specification and Python MCP server code that:
- Serves files from {output_dir}
- Exposes an endpoint /index to return the contents of {tutorial_index}
- Exposes endpoints for each chapter file in {output_dir} with path parameters (e.g., /chapter/1)
- Includes a 'features' section listing: {features}

First output the YAML spec in ```yaml ... ``` then the Python server code in ```python ... ``` format.
"""
        raw_output = call_llm(prompt)

        yaml_str = ""
        code_str = ""
        if "```yaml" in raw_output:
            yaml_str = raw_output.split("```yaml")[1].split("```", 1)[0].strip()
        if "```python" in raw_output:
            code_str = raw_output.split("```python")[1].split("```", 1)[0].strip()

        raw_spec = yaml.safe_load(yaml_str)
        server_name = raw_spec.get("name") or os.path.basename(output_dir.rstrip('/'))
        version = raw_spec.get("version", "1.0.0")
        host = raw_spec.get("host", "localhost")
        port = raw_spec.get("port", 8000)
        mcp_spec = {
            "name": server_name,
            "version": version,
            "transport": raw_spec.get("transport", "stdio"),
            "host": host,
            "port": port,
            "health": raw_spec.get("health", "/health"),
            "specEndpoint": raw_spec.get("specEndpoint", "/mcp_spec"),
            "tools": [
                {
                    "name": "chapter_index",
                    "description": f"Returns the tutorial index markdown",
                    "method": "GET",
                    "endpoint": "/index",
                    "outputSchema": {"type": "string"}
                },
                {
                    "name": "get_chapter",
                    "description": "Returns one chapter's markdown by number",
                    "method": "GET",
                    "endpoint": "/chapter/{n}",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"n": {"type": "integer", "description": "Chapter number"}},
                        "required": ["n"]
                    },
                    "outputSchema": {"type": "string"}
                }
            ],
            # Optional examples for LLM guidance
            "examples": [
                {"tool": "get_chapter", "args": {"n": 1}}
            ]
        }
        spec = mcp_spec
        code = code_str

        spec_path = os.path.join(output_dir, "mcp_spec.yaml")
        with open(spec_path, "w") as f:
            yaml.dump(spec, f)
        server_path = os.path.join(output_dir, "simple_mcp_server.py")
        with open(server_path, 'w') as f:
            f.write(code)

        # Return spec and server code path for post-processing
        return {"mcp_spec": spec, "mcp_server_code": server_path}

    def post(self, shared, prep_res, exec_res):
        # Handle errors from exec
        if isinstance(exec_res, dict) and exec_res.get("error"):
            shared["error"] = exec_res.get("error")
            return "error"
        # Store MCP spec and server code path
        shared["mcp_spec"] = exec_res.get("mcp_spec")
        shared["mcp_server_code"] = exec_res.get("mcp_server_code")
        return "default"

class StartMCPServerNode(Node):
    """
    Node to start an MCP server for a generated tutorial, dynamically serving index and chapters.
    """
    def prep(self, shared):
        # Read spec and determine tutorials root
        spec = shared.get("mcp_spec")
        tutorial_root = os.environ.get("TUTORIAL_ROOT") or shared.get("tutorial_output_dir")
        host = spec.get("host", "localhost")
        port = spec.get("port", 8000)
        return spec, tutorial_root, host, port

    def exec(self, inputs):
        # Launch the simple MCP server script generated in the tutorial directory
        spec, tutorial_root, host, port = inputs
        import os
        import time
        script_path = os.path.join(tutorial_root, "simple_mcp_server.py")
        if not os.path.exists(script_path):
            return {"error": f"simple_mcp_server.py not found at {script_path}"}
        # Start the server script with the same Python interpreter
        proc = subprocess.Popen([sys.executable, script_path], cwd=tutorial_root)
        # Give the server a moment to start
        time.sleep(2)
        return {"host": host, "port": port, "process_id": proc.pid, "url": f"http://{host}:{port}", "status": "running"}

    def post(self, shared, prep_res, exec_res):
        # Combine spec and server info for best-practice output
        spec = shared.get('mcp_spec', {})
        server_info = exec_res
        combined = { 'spec': spec, 'server': server_info }
        shared['mcp_server_info'] = combined
        print(json.dumps(combined, indent=2))
        # Keep server running (do not return successor)
        return None

class TutorialErrorHandler(Node):
    """Error handling node for the tutorial generation flow."""
    
    def prep(self, shared):
        """Prepare error information from the shared store."""
        import logging
        import os
        from datetime import datetime
        
        # Configure error logging if not already done
        if not hasattr(TutorialErrorHandler, "logger_initialized"):
            log_dir = "logs"
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, f"tutorial_errors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
            
            # Set up logger
            logger = logging.getLogger("tutorial_error_logger")
            logger.setLevel(logging.INFO)
            handler = logging.FileHandler(log_file)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
            # Add console handler for immediate visibility
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            console_handler.setLevel(logging.ERROR)  # Only ERROR and above to console
            logger.addHandler(console_handler)
            
            TutorialErrorHandler.logger = logger
            TutorialErrorHandler.logger_initialized = True
            TutorialErrorHandler.log_file = log_file
        
        error = shared.get("error")
        if error:
            if hasattr(TutorialErrorHandler, "logger"):
                TutorialErrorHandler.logger.error(f"Error during processing: {error}")
                print(f"Error logged to {TutorialErrorHandler.log_file}")
        
        # Gather comprehensive error context
        error_context = {
            "error": error,
            "current_stage": shared.get("current_stage", "unknown"),
            "retry_count": shared.get("retry_count", {}),
            "repository_url": shared.get("repo_url"),
            "local_dir": shared.get("local_dir"),
            "project_name": shared.get("project_name"),
            "tutorial_output_dir": shared.get("tutorial_output_dir", "tutorial"),
            "chapter_read_errors": shared.get("chapter_read_errors", []),
            "file_count": shared.get("file_count"),
        }
        
        # Log additional context
        if hasattr(TutorialErrorHandler, "logger"):
            TutorialErrorHandler.logger.info(f"Error context: stage={error_context['current_stage']}, retry_count={error_context['retry_count'].get(error_context['current_stage'], 0)}")
            
        return error_context
    
    def exec(self, error_info):
        """Process error and determine the appropriate action."""
        import time
        import logging
        
        error = error_info["error"]
        current_stage = error_info["current_stage"]
        retry_count = error_info.get("retry_count", {})
        
        # Initialize retry count for current stage if not exists
        if current_stage not in retry_count:
            retry_count[current_stage] = 0
        
        # Increment retry count
        retry_count[current_stage] += 1
        
        # Categorize errors for better handling
        error_category = self._categorize_error(error)
        max_retries = self._get_max_retries(error_category, current_stage)
        
        # Log detailed error information
        if hasattr(TutorialErrorHandler, "logger"):
            TutorialErrorHandler.logger.error(
                f"Error in stage '{current_stage}' (attempt {retry_count[current_stage]}/{max_retries}): "
                f"{error} (category: {error_category})"
            )
        
        # Calculate wait time with exponential backoff
        wait_time = self._calculate_backoff(retry_count[current_stage], error_category)
        
        # Handle specific error categories
        if error_category == "file_system":
            return self._handle_file_system_error(error, current_stage, retry_count, error_info)
        
        elif error_category == "api_error":
            return self._handle_api_error(error, current_stage, retry_count, max_retries, wait_time)
        
        elif error_category == "format_error":
            return self._handle_format_error(error, current_stage, retry_count, max_retries)
        
        elif error_category == "content_error":
            return self._handle_content_error(error, current_stage, retry_count, max_retries)
        
        # General retry logic for other errors
        if retry_count[current_stage] <= max_retries:
            if wait_time > 0:
                if hasattr(TutorialErrorHandler, "logger"):
                    TutorialErrorHandler.logger.info(f"Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
                
            return {
                "action": "retry",
                "message": f"Retrying {current_stage} (attempt {retry_count[current_stage]}/{max_retries}).",
                "error_category": error_category,
                "retry_count": retry_count[current_stage]
            }
        
        # If all retries exhausted
        if hasattr(TutorialErrorHandler, "logger"):
            TutorialErrorHandler.logger.error(
                f"All retries exhausted for stage '{current_stage}'. "
                f"Last error: {error}"
            )
            
        return {
            "action": "terminate",
            "message": f"All retries exhausted for {current_stage}. Attempting to salvage partial results.",
            "error_category": error_category
        }
    
    def _categorize_error(self, error):
        """Categorize the error for better handling."""
        if isinstance(error, dict) and "error" in error:
            error_message = error["error"]
        else:
            error_message = str(error)
        
        error_message = error_message.lower()
        
        # File system errors
        if any(term in error_message for term in ["no such file", "directory", "permission denied", "file exists"]):
            return "file_system"
        
        # API-related errors
        if any(term in error_message for term in ["api", "token", "rate limit", "timeout", "connection", "network"]):
            return "api_error"
        
        # Format/parsing errors
        if any(term in error_message for term in ["malformed", "invalid", "format", "syntax", "expected", "parse"]):
            return "format_error"
        
        # Content-related errors
        if any(term in error_message for term in ["content", "empty", "missing", "not found", "null"]):
            return "content_error"
        
        # Default
        return "general_error"
    
    def _get_max_retries(self, error_category, stage):
        """Get maximum retry count based on error category and stage."""
        # Higher retry counts for API errors (rate limiting, etc.)
        if error_category == "api_error":
            return 5
        
        # Format errors in specific stages may need more attempts
        if error_category == "format_error" and stage in ["identify", "analyze"]:
            return 4
        
        # File system errors
        if error_category == "file_system":
            return 3
        
        # Default
        return 3
    
    def _calculate_backoff(self, retry_count, error_category):
        """Calculate wait time with exponential backoff."""
        base_wait = 5  # Base wait time in seconds
        
        # API errors need longer backoff
        if error_category == "api_error":
            base_wait = 10
        
        # Exponential backoff with jitter
        import random
        wait_time = base_wait * (2 ** (retry_count - 1))  # Exponential
        jitter = random.uniform(0.8, 1.2)  # Add 20% jitter
        
        return wait_time * jitter
    
    def _handle_file_system_error(self, error, current_stage, retry_count, error_info):
        """Handle file system errors like missing files, permissions, etc."""
        if isinstance(error, dict) and "error" in error:
            error_message = error["error"]
        else:
            error_message = str(error)
        
        # Specific handling for directory/file issues in the tutorial directory
        if "tutorial" in error_message and "no such file" in error_message.lower():
            # Try to recreate the directory
            output_dir = error_info.get("tutorial_output_dir", "tutorial")
            
            return {
                "action": "recreate_directory",
                "message": f"File system error detected. Will recreate directory: {output_dir}",
                "directory": output_dir,
                "stage": current_stage
            }
        
        # For other file system errors, just retry normally if retries left
        max_retries = self._get_max_retries("file_system", current_stage)
        if retry_count[current_stage] <= max_retries:
            return {
                "action": "retry",
                "message": f"Retrying after file system error (attempt {retry_count[current_stage]}/{max_retries}).",
                "error_category": "file_system"
            }
        
        # If all retries exhausted for file system errors, try to continue from next stage
        next_stage = self._get_next_stage(current_stage)
        if next_stage:
            return {
                "action": next_stage,
                "message": f"Skipping problematic stage {current_stage} and proceeding to {next_stage}."
            }
        
        return {
            "action": "terminate",
            "message": f"All retries exhausted for file system errors in {current_stage}."
        }
    
    def _handle_api_error(self, error, current_stage, retry_count, max_retries, wait_time):
        """Handle API-related errors like rate limits, connection issues, etc."""
        if retry_count[current_stage] <= max_retries:
            if hasattr(TutorialErrorHandler, "logger"):
                TutorialErrorHandler.logger.info(f"API error. Waiting {wait_time}s before retry...")
            
            import time
            time.sleep(wait_time)
            
            return {
                "action": "retry",
                "message": f"Retrying after API error with {wait_time}s wait (attempt {retry_count[current_stage]}/{max_retries}).",
                "error_category": "api_error",
                "wait_time": wait_time
            }
        
        return {
            "action": "terminate",
            "message": f"All retries exhausted for API errors in {current_stage}."
        }
    
    def _handle_format_error(self, error, current_stage, retry_count, max_retries):
        """Handle format/parsing errors by tweaking prompts."""
        if retry_count[current_stage] <= max_retries:
            return {
                "action": "retry_with_better_prompt",
                "message": f"Format error detected. Retrying with enhanced prompt (attempt {retry_count[current_stage]}/{max_retries}).",
                "error_category": "format_error"
            }
        
        return {
            "action": "terminate",
            "message": f"All retries exhausted for format errors in {current_stage}."
        }
    
    def _handle_content_error(self, error, current_stage, retry_count, max_retries):
        """Handle content-related errors like missing or invalid content."""
        if retry_count[current_stage] <= max_retries:
            return {
                "action": "retry",
                "message": f"Content error detected. Retrying (attempt {retry_count[current_stage]}/{max_retries}).",
                "error_category": "content_error"
            }
        
        # For content errors, try skipping to the next stage if possible
        next_stage = self._get_next_stage(current_stage)
        if next_stage:
            return {
                "action": next_stage,
                "message": f"All retries failed for content errors. Skipping to {next_stage}."
            }
        
        return {
            "action": "terminate",
            "message": f"All retries exhausted for content errors in {current_stage}."
        }
    
    def _get_next_stage(self, current_stage):
        """Get the next stage in the flow sequence."""
        stages = ["fetch", "abstractions", "relationships", "chapters", "write", "combine"]
        
        try:
            current_index = stages.index(current_stage)
            if current_index < len(stages) - 1:
                return stages[current_index + 1]
        except ValueError:
            pass
        
        return None
    
    def post(self, shared, prep_res, exec_res):
        """Update shared store and return appropriate action."""
        # Update retry count
        if "retry_count" not in shared:
            shared["retry_count"] = {}
        
        if prep_res and "current_stage" in prep_res:
            current_stage = prep_res["current_stage"]
            if "retry_count" in prep_res and current_stage in prep_res["retry_count"]:
                shared["retry_count"][current_stage] = prep_res["retry_count"][current_stage]
        
        # Handle action based on exec_res
        if exec_res:
            action = exec_res.get("action")
            message = exec_res.get("message", "No message provided")
            
            print(f"Error handler: {message}")
            
            if action == "retry":
                # Standard retry - return to current stage
                wait_time = exec_res.get("wait_time", 0)
                if wait_time > 0:
                    import time
                    print(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                return current_stage
            
            elif action == "retry_with_better_prompt":
                # Set a flag to indicate we need a better prompt
                shared["better_prompt_needed"] = True
                # Store the error category for context
                shared["last_error_category"] = exec_res.get("error_category", "unknown")
                return current_stage
            
            elif action == "recreate_directory":
                # Try to recreate the directory
                try:
                    import os
                    import shutil
                    output_dir = exec_res.get("directory", shared.get("tutorial_output_dir", "tutorial"))
                    if os.path.exists(output_dir):
                        # Rename the problematic directory
                        backup_dir = f"{output_dir}_backup_{shared['retry_count'][current_stage]}"
                        shutil.move(output_dir, backup_dir)
                        print(f"Moved problematic directory to {backup_dir}")
                    
                    # Create a fresh directory
                    os.makedirs(output_dir, exist_ok=True)
                    print(f"Created fresh directory: {output_dir}")
                    
                    # Depending on the stage, we might need to restart from different points
                    if current_stage == "combine":
                        # We have chapters data but need to rewrite files
                        return "write"
                    else:
                        # Go back to the beginning
                        return "fetch"
                except Exception as e:
                    if hasattr(TutorialErrorHandler, "logger"):
                        TutorialErrorHandler.logger.error(f"Error during directory recreation: {e}")
                    print(f"Error during directory recreation: {e}")
                    # If we can't recover, terminate
                    return "terminate"
            
            # If action is a specific stage, go to that stage
            elif action in ["fetch", "abstractions", "relationships", "chapters", "write", "combine"]:
                return action
        
        # Default termination if no specific action or error in handler itself
        return "terminate"