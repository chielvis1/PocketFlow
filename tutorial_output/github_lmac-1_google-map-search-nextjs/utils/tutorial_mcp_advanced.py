"""
Advanced Tutorial MCP Tools

This module provides advanced tools for code pattern recognition and semantic understanding
to enhance the tutorial documentation MCP server.
"""

import re
import logging
from typing import Dict, List, Any, Optional
from collections import defaultdict

# Configure logging
logger = logging.getLogger("tutorial_mcp_advanced")

class CodePatternRecognizer:
    """
    Recognizes common design patterns in code samples.
    """
    
    def __init__(self):
        # Define patterns to recognize
        self.patterns = {
            "singleton": {
                "description": "Ensures a class has only one instance and provides a global point of access to it.",
                "indicators": [
                    r"private\s+static\s+\w+\s+instance",
                    r"static\s+getInstance\(\)",
                    r"private\s+constructor"
                ]
            },
            "factory": {
                "description": "Creates objects without exposing the instantiation logic to the client.",
                "indicators": [
                    r"create\w+\s*\(",
                    r"factory",
                    r"new\s+\w+\(\)"
                ]
            },
            "observer": {
                "description": "Defines a one-to-many dependency between objects so that when one object changes state, all its dependents are notified.",
                "indicators": [
                    r"addEventListener|on\w+|subscribe",
                    r"notify|emit|dispatch",
                    r"observer|listener|subscriber"
                ]
            },
            "decorator": {
                "description": "Attaches additional responsibilities to an object dynamically.",
                "indicators": [
                    r"@\w+",
                    r"decorator",
                    r"wrap\w+\s*\("
                ]
            },
            "mvc": {
                "description": "Separates an application into three main components: Model, View, and Controller.",
                "indicators": [
                    r"model|view|controller",
                    r"render\s*\(",
                    r"update\w+\s*\("
                ]
            }
        }
    
    def identify_patterns(self, code: str) -> Dict[str, float]:
        """
        Identify design patterns in code.
        
        Args:
            code: Source code to analyze
            
        Returns:
            Dictionary mapping pattern names to confidence scores
        """
        results = {}
        
        for pattern_name, pattern_info in self.patterns.items():
            confidence = 0.0
            matches = 0
            
            for indicator in pattern_info["indicators"]:
                if re.search(indicator, code, re.IGNORECASE):
                    matches += 1
            
            if matches > 0:
                # Calculate confidence based on number of matches
                confidence = matches / len(pattern_info["indicators"])
                results[pattern_name] = confidence
        
        return results

class FunctionExtractor:
    """
    Extracts function signatures and categorizes them.
    """
    
    def extract_functions(self, code: str, language: str) -> List[Dict[str, Any]]:
        """
        Extract function signatures from code.
        
        Args:
            code: Source code to analyze
            language: Programming language
            
        Returns:
            List of function dictionaries with name, params, return type, etc.
        """
        functions = []
        
        if language in ["javascript", "typescript"]:
            # Pattern for JS/TS functions
            func_patterns = [
                # Regular functions
                r"(async\s+)?function\s+(\w+)\s*\((.*?)\)(\s*:\s*(\w+))?\s*\{",
                # Arrow functions with name (const foo = ...)
                r"(const|let|var)\s+(\w+)\s*=\s*(async\s*)?\((.*?)\)(\s*:\s*(\w+))?\s*=>"
            ]
            
            for pattern in func_patterns:
                for match in re.finditer(pattern, code):
                    if pattern.startswith("(const|let|var)"):
                        # Arrow function
                        is_async = match.group(3) is not None
                        name = match.group(2)
                        params = match.group(4) or ""
                        return_type = match.group(6) or "any"
                    else:
                        # Regular function
                        is_async = match.group(1) is not None
                        name = match.group(2)
                        params = match.group(3) or ""
                        return_type = match.group(5) or "any"
                    
                    functions.append({
                        "name": name,
                        "params": self._parse_params(params, language),
                        "return_type": return_type,
                        "is_async": is_async,
                        "type": "function"
                    })
        
        elif language in ["python"]:
            # Pattern for Python functions
            func_pattern = r"def\s+(\w+)\s*\((.*?)\)(\s*->\s*(\w+))?\s*:"
            
            for match in re.finditer(func_pattern, code):
                name = match.group(1)
                params = match.group(2) or ""
                return_type = match.group(4) or "Any"
                
                functions.append({
                    "name": name,
                    "params": self._parse_params(params, language),
                    "return_type": return_type,
                    "is_async": "async" in code[:match.start()].splitlines()[-1] if match.start() > 0 else False,
                    "type": "function"
                })
        
        return functions
    
    def _parse_params(self, params_str: str, language: str) -> List[Dict[str, str]]:
        """
        Parse function parameters.
        
        Args:
            params_str: Parameter string
            language: Programming language
            
        Returns:
            List of parameter dictionaries with name and type
        """
        if not params_str.strip():
            return []
        
        params = []
        
        if language in ["javascript", "typescript"]:
            # Split by commas, but respect nested structures
            param_list = []
            current = ""
            depth = 0
            
            for char in params_str:
                if char in "{[(":
                    depth += 1
                elif char in "}])":
                    depth -= 1
                
                if char == "," and depth == 0:
                    param_list.append(current.strip())
                    current = ""
                else:
                    current += char
            
            if current.strip():
                param_list.append(current.strip())
            
            # Process each parameter
            for param in param_list:
                parts = param.split(":")
                name = parts[0].strip()
                param_type = parts[1].strip() if len(parts) > 1 else "any"
                
                params.append({
                    "name": name,
                    "type": param_type
                })
        
        elif language in ["python"]:
            # Split by commas, but respect nested structures
            param_list = []
            current = ""
            depth = 0
            
            for char in params_str:
                if char in "{[(":
                    depth += 1
                elif char in "}])":
                    depth -= 1
                
                if char == "," and depth == 0:
                    param_list.append(current.strip())
                    current = ""
                else:
                    current += char
            
            if current.strip():
                param_list.append(current.strip())
            
            # Process each parameter
            for param in param_list:
                parts = param.split(":")
                name = parts[0].strip()
                param_type = parts[1].strip() if len(parts) > 1 else "Any"
                
                params.append({
                    "name": name,
                    "type": param_type
                })
        
        return params

class DependencyAnalyzer:
    """
    Analyzes dependencies between components and modules.
    """
    
    def analyze_dependencies(self, code_blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze dependencies between components.
        
        Args:
            code_blocks: List of code blocks with language and code
            
        Returns:
            Dictionary with dependency graph
        """
        # Extract imports and component usage
        imports = {}
        component_usage = defaultdict(list)
        
        for block in code_blocks:
            if block["language"] not in ["javascript", "typescript", "jsx", "tsx"]:
                continue
            
            code = block["code"]
            
            # Extract imports
            import_pattern = r"import\s+(?:{(.*?)}|(\w+))\s+from\s+['\"](.+?)['\"]"
            for match in re.finditer(import_pattern, code):
                named_imports = match.group(1)
                default_import = match.group(2)
                source = match.group(3)
                
                if named_imports:
                    for named_import in named_imports.split(","):
                        imports[named_import.strip()] = source
                
                if default_import:
                    imports[default_import] = source
            
            # Extract component usage in JSX
            jsx_pattern = r"<(\w+)"
            for match in re.finditer(jsx_pattern, code):
                component = match.group(1)
                if component[0].isupper():  # React components start with uppercase
                    # Find the context (parent component)
                    context = self._find_component_context(code, match.start())
                    if context:
                        component_usage[context].append(component)
        
        # Build dependency graph
        graph = {
            "nodes": [],
            "edges": []
        }
        
        # Add nodes
        for component in set(list(imports.keys()) + [item for sublist in component_usage.values() for item in sublist] + list(component_usage.keys())):
            graph["nodes"].append({
                "id": component,
                "source": imports.get(component, "local")
            })
        
        # Add edges
        for parent, children in component_usage.items():
            for child in children:
                graph["edges"].append({
                    "source": parent,
                    "target": child
                })
        
        return graph
    
    def _find_component_context(self, code: str, position: int) -> Optional[str]:
        """
        Find the component context (parent component) for a given position in code.
        
        Args:
            code: Source code
            position: Position in code
            
        Returns:
            Component name or None
        """
        # Look for the nearest function or class declaration before the position
        component_pattern = r"(function|class|const)\s+(\w+)"
        for match in re.finditer(component_pattern, code[:position]):
            component_name = match.group(2)
            if component_name[0].isupper():  # React components start with uppercase
                return component_name
        
        return None

class SemanticAnalyzer:
    """
    Provides semantic understanding of documentation.
    """
    
    def extract_technical_terms(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract technical terms from content.
        
        Args:
            content: Markdown content
            
        Returns:
            List of technical terms with context
        """
        # Define patterns for technical terms
        tech_patterns = [
            # React/JS terms
            r'\b(React|Component|Hook|useState|useEffect|Redux|Context|Props|JSX)\b',
            # Programming concepts
            r'\b(Algorithm|Function|Class|Object|Interface|Type|API|REST|GraphQL)\b',
            # Design patterns
            r'\b(Singleton|Factory|Observer|Decorator|MVC|MVVM)\b'
        ]
        
        terms = []
        
        for pattern in tech_patterns:
            for match in re.finditer(pattern, content):
                term = match.group(1)
                
                # Get context (surrounding text)
                start = max(0, match.start() - 50)
                end = min(len(content), match.end() + 50)
                context = content[start:end]
                
                terms.append({
                    "term": term,
                    "context": context.strip(),
                    "position": match.start()
                })
        
        return terms
    
    def generate_glossary(self, content: str) -> Dict[str, str]:
        """
        Generate a technical glossary from content.
        
        Args:
            content: Markdown content
            
        Returns:
            Dictionary mapping terms to definitions
        """
        # Extract technical terms
        terms = self.extract_technical_terms(content)
        
        # Group by term
        term_groups = defaultdict(list)
        for term_entry in terms:
            term_groups[term_entry["term"]].append(term_entry["context"])
        
        # Generate definitions (simplified implementation)
        glossary = {}
        for term, contexts in term_groups.items():
            # Use the most representative context as definition
            # In a real implementation, we would use an LLM to generate a proper definition
            glossary[term] = contexts[0]
        
        return glossary

# Helper function to create advanced tools
def register_advanced_tools(mcp, tutorial_mcp):
    """
    Register advanced tools for code pattern recognition and semantic understanding.
    
    Args:
        mcp: FastMCP server instance
        tutorial_mcp: TutorialMCPServer instance
    """
    # Create tool instances
    pattern_recognizer = CodePatternRecognizer()
    function_extractor = FunctionExtractor()
    dependency_analyzer = DependencyAnalyzer()
    semantic_analyzer = SemanticAnalyzer()
    
    # Register code pattern recognition tools
    @mcp.tool(name="identify_design_patterns")
    def identify_design_patterns(chapter_num: int):
        """Detects common software design patterns in code samples"""
        try:
            # Get code samples
            code_samples_result = tutorial_mcp.extract_code_samples(chapter_num)
            if "error" in code_samples_result:
                return code_samples_result
            
            code_samples = code_samples_result["samples"]
            
            # Filter to only code samples
            code_samples = [sample for sample in code_samples 
                           if sample["language"] in ["javascript", "typescript", "jsx", "tsx", "python"]]
            
            # Analyze patterns in each sample
            results = []
            for sample in code_samples:
                patterns = pattern_recognizer.identify_patterns(sample["code"])
                if patterns:
                    results.append({
                        "language": sample["language"],
                        "patterns": patterns
                    })
            
            return {
                "results": results,
                "count": len(results)
            }
        except Exception as e:
            logger.error(f"Error identifying design patterns: {str(e)}")
            return {"error": str(e)}
    
    @mcp.tool(name="extract_function_signatures")
    def extract_function_signatures(chapter_num: int):
        """Parses and categorizes function definitions"""
        try:
            # Get code samples
            code_samples_result = tutorial_mcp.extract_code_samples(chapter_num)
            if "error" in code_samples_result:
                return code_samples_result
            
            code_samples = code_samples_result["samples"]
            
            # Extract functions from each sample
            results = []
            for sample in code_samples:
                if sample["language"] in ["javascript", "typescript", "jsx", "tsx", "python"]:
                    functions = function_extractor.extract_functions(sample["code"], sample["language"])
                    if functions:
                        results.append({
                            "language": sample["language"],
                            "functions": functions
                        })
            
            return {
                "results": results,
                "count": sum(len(r["functions"]) for r in results)
            }
        except Exception as e:
            logger.error(f"Error extracting function signatures: {str(e)}")
            return {"error": str(e)}
    
    @mcp.tool(name="analyze_dependencies")
    def analyze_dependencies():
        """Maps relationships between components/modules"""
        try:
            # Get all chapters
            chapters = tutorial_mcp._get_all_chapters()
            
            # Extract code blocks from all chapters
            all_code_blocks = []
            for chapter in chapters:
                code_blocks = tutorial_mcp._extract_code_blocks(chapter["content"])
                all_code_blocks.extend(code_blocks)
            
            # Analyze dependencies
            dependency_graph = dependency_analyzer.analyze_dependencies(all_code_blocks)
            
            return {
                "graph": dependency_graph,
                "nodeCount": len(dependency_graph["nodes"]),
                "edgeCount": len(dependency_graph["edges"])
            }
        except Exception as e:
            logger.error(f"Error analyzing dependencies: {str(e)}")
            return {"error": str(e)}
    
    # Register semantic understanding tools
    @mcp.tool(name="technical_glossary")
    def technical_glossary():
        """Extracts and defines technical terms used in the documentation"""
        try:
            # Get complete tutorial content
            tutorial_result = tutorial_mcp.get_complete_tutorial()
            if "error" in tutorial_result:
                return tutorial_result
            
            content = tutorial_result["content"]
            
            # Generate glossary
            glossary = semantic_analyzer.generate_glossary(content)
            
            return {
                "glossary": glossary,
                "count": len(glossary)
            }
        except Exception as e:
            logger.error(f"Error generating technical glossary: {str(e)}")
            return {"error": str(e)}
    
    @mcp.tool(name="search_by_concept")
    def search_by_concept(concept: str):
        """Allows searching by technical concepts rather than just keywords"""
        try:
            # Get all chapters
            chapters = tutorial_mcp._get_all_chapters()
            
            # Simple concept search (in a real implementation, we would use embeddings)
            results = []
            for chapter in chapters:
                # Check if concept appears in chapter
                if re.search(r'\b' + re.escape(concept) + r'\b', chapter["content"], re.IGNORECASE):
                    # Extract surrounding context
                    matches = []
                    for match in re.finditer(r'\b' + re.escape(concept) + r'\b', chapter["content"], re.IGNORECASE):
                        start = max(0, match.start() - 100)
                        end = min(len(chapter["content"]), match.end() + 100)
                        context = chapter["content"][start:end]
                        matches.append({
                            "context": context.strip(),
                            "position": match.start()
                        })
                    
                    results.append({
                        "chapter": chapter["number"],
                        "filename": chapter["filename"],
                        "matches": matches,
                        "matchCount": len(matches)
                    })
            
            return {
                "results": results,
                "totalMatches": sum(r["matchCount"] for r in results)
            }
        except Exception as e:
            logger.error(f"Error searching by concept: {str(e)}")
            return {"error": str(e)}
    
    @mcp.tool(name="related_concepts")
    def related_concepts(concept: str):
        """Finds related technical concepts within documentation"""
        try:
            # Get technical glossary
            glossary_result = technical_glossary()
            if "error" in glossary_result:
                return glossary_result
            
            glossary = glossary_result["glossary"]
            
            # Find related concepts (simplified implementation)
            # In a real implementation, we would use embeddings or an LLM
            related = []
            for term, definition in glossary.items():
                if term.lower() != concept.lower() and (
                    concept.lower() in definition.lower() or
                    concept.lower() in term.lower() or
                    term.lower() in concept.lower()
                ):
                    related.append({
                        "term": term,
                        "definition": definition,
                        "relevance": 0.5  # Simplified relevance score
                    })
            
            # Sort by relevance
            related.sort(key=lambda x: x["relevance"], reverse=True)
            
            return {
                "concept": concept,
                "related": related,
                "count": len(related)
            }
        except Exception as e:
            logger.error(f"Error finding related concepts: {str(e)}")
            return {"error": str(e)}
    
    logger.info("Registered advanced tools for code pattern recognition and semantic understanding") 