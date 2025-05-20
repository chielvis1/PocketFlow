"""
Tutorial Documentation MCP Server

This module implements a Model Context Protocol (MCP) server for serving tutorial documentation
in a machine-readable format, optimized for reverse engineering software blueprints.
"""

import os
import re
import json
from typing import Dict, List, Any, Optional, Union
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("tutorial_mcp")

class TutorialMCPServer:
    """
    MCP server for tutorial documentation with blueprint extraction capabilities.
    
    This server provides tools for:
    1. Document retrieval
    2. Document structure analysis
    3. Blueprint extraction
    4. Code pattern recognition
    5. Semantic understanding
    """
    
    def __init__(self, tutorial_dir: str):
        """
        Initialize the tutorial MCP server.
        
        Args:
            tutorial_dir: Directory containing tutorial markdown files
        """
        self.tutorial_dir = Path(tutorial_dir)
        if not self.tutorial_dir.exists():
            raise FileNotFoundError(f"Tutorial directory not found: {tutorial_dir}")
        
        self.index_file = self.tutorial_dir / "index.md"
        if not self.index_file.exists():
            raise FileNotFoundError(f"Index file not found: {self.index_file}")
        
        # Cache for parsed content
        self._cache = {
            "chapters": {},
            "structure": {},
            "components": None
        }
        
        logger.info(f"Initialized TutorialMCPServer with tutorial directory: {tutorial_dir}")
    
    def _load_chapter(self, chapter_num: int) -> str:
        """
        Load a chapter's content by number.
        
        Args:
            chapter_num: Chapter number
            
        Returns:
            Chapter content as string
        """
        # Check cache first
        if chapter_num in self._cache["chapters"]:
            return self._cache["chapters"][chapter_num]
        
        # Find chapter file based on naming convention
        chapter_pattern = f"chapter_{chapter_num:02d}__*.md"
        chapter_files = list(self.tutorial_dir.glob(chapter_pattern))
        
        if not chapter_files:
            raise FileNotFoundError(f"Chapter {chapter_num} not found")
        
        # Read content
        with open(chapter_files[0], 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Cache content
        self._cache["chapters"][chapter_num] = content
        return content
    
    def _get_all_chapters(self) -> List[Dict[str, Any]]:
        """
        Get all chapters with their content.
        
        Returns:
            List of chapter dictionaries with number, filename, and content
        """
        chapter_files = sorted(self.tutorial_dir.glob("chapter_*__*.md"))
        chapters = []
        
        for file_path in chapter_files:
            # Extract chapter number from filename
            match = re.match(r"chapter_(\d+)__", file_path.name)
            if match:
                chapter_num = int(match.group(1))
                
                # Get content (from cache if available)
                if chapter_num in self._cache["chapters"]:
                    content = self._cache["chapters"][chapter_num]
                else:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        self._cache["chapters"][chapter_num] = content
                
                chapters.append({
                    "number": chapter_num,
                    "filename": file_path.name,
                    "content": content
                })
        
        return chapters
    
    def _extract_headings(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract all headings with their levels and positions.
        
        Args:
            content: Markdown content
            
        Returns:
            List of heading dictionaries with level, text, and line number
        """
        heading_pattern = r'^(#{1,6})\s+(.+?)$'
        headings = []
        
        for i, line in enumerate(content.split('\n')):
            match = re.match(heading_pattern, line)
            if match:
                level = len(match.group(1))
                text = match.group(2)
                headings.append({
                    "level": level,
                    "text": text,
                    "line": i
                })
                
        return headings
    
    def _extract_sections(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract sections based on headings.
        
        Args:
            content: Markdown content
            
        Returns:
            List of section dictionaries with heading, content, and subsections
        """
        headings = self._extract_headings(content)
        if not headings:
            return []
        
        lines = content.split('\n')
        sections = []
        
        for i, heading in enumerate(headings):
            # Determine section end line
            end_line = len(lines)
            if i < len(headings) - 1:
                end_line = headings[i+1]["line"]
            
            # Extract section content
            section_content = '\n'.join(lines[heading["line"]+1:end_line])
            
            sections.append({
                "heading": heading,
                "content": section_content.strip()
            })
        
        return sections
    
    def _extract_code_blocks(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract code blocks with language information.
        
        Args:
            content: Markdown content
            
        Returns:
            List of code block dictionaries with language and code
        """
        code_block_pattern = r'```(\w+)?\n(.*?)\n```'
        code_blocks = []
        
        for match in re.finditer(code_block_pattern, content, re.DOTALL):
            language = match.group(1) or "text"
            code = match.group(2)
            code_blocks.append({
                "language": language,
                "code": code
            })
                
        return code_blocks
    
    def _extract_components(self, content: str) -> Dict[str, Dict[str, Any]]:
        """
        Extract React component definitions.
        
        Args:
            content: Markdown content or code
            
        Returns:
            Dictionary of component names to component info
        """
        # Pattern for React functional components
        func_component_pattern = r'(export\s+)?const\s+(\w+)\s*:\s*React\.FC.*?='
        # Pattern for React class components
        class_component_pattern = r'(export\s+)?class\s+(\w+)\s+extends\s+React\.Component'
        
        components = {}
        
        # Find functional components
        for match in re.finditer(func_component_pattern, content):
            name = match.group(2)
            components[name] = {"type": "functional"}
            
        # Find class components
        for match in re.finditer(class_component_pattern, content):
            name = match.group(2)
            components[name] = {"type": "class"}
            
        return components
    
    def _build_component_graph(self, components: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build a component relationship graph.
        
        Args:
            components: Dictionary of component definitions
            
        Returns:
            Component graph with nodes and edges
        """
        # This is a simplified implementation
        # In a real system, we would analyze imports and JSX usage
        
        graph = {
            "nodes": [],
            "edges": []
        }
        
        # Add nodes
        for name, info in components.items():
            graph["nodes"].append({
                "id": name,
                "type": info["type"]
            })
        
        # For now, we're not adding edges
        # A more complete implementation would analyze component usage
        
        return graph
    
    # Document Retrieval Tools
    
    def chapter_index(self) -> Dict[str, Any]:
        """
        Returns the tutorial index markdown.
        
        Returns:
            Dictionary with index content
        """
        try:
            with open(self.index_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                "content": content,
                "format": "markdown"
            }
        except Exception as e:
            logger.error(f"Error retrieving chapter index: {str(e)}")
            return {"error": str(e)}
    
    def get_chapter(self, n: int) -> Dict[str, Any]:
        """
        Returns one chapter's markdown by number.
        
        Args:
            n: Chapter number
            
        Returns:
            Dictionary with chapter content
        """
        try:
            content = self._load_chapter(n)
            return {
                "content": content,
                "format": "markdown",
                "chapter_number": n
            }
        except FileNotFoundError:
            logger.error(f"Chapter {n} not found")
            return {"error": f"Chapter {n} not found"}
        except Exception as e:
            logger.error(f"Error retrieving chapter {n}: {str(e)}")
            return {"error": str(e)}
    
    def get_complete_tutorial(self) -> Dict[str, Any]:
        """
        Returns the complete tutorial markdown.
        
        Returns:
            Dictionary with complete tutorial content
        """
        try:
            # Get index content
            with open(self.index_file, 'r', encoding='utf-8') as f:
                index_content = f.read()
            
            # Get all chapters
            chapters = self._get_all_chapters()
            
            # Combine content
            chapter_contents = [chapter["content"] for chapter in sorted(chapters, key=lambda x: x["number"])]
            complete_content = index_content + "\n\n" + "\n\n".join(chapter_contents)
            
            return {
                "content": complete_content,
                "format": "markdown"
            }
        except Exception as e:
            logger.error(f"Error retrieving complete tutorial: {str(e)}")
            return {"error": str(e)}
    
    # Document Structure Analysis Tools
    
    def analyze_document_structure(self, chapter_num: int) -> Dict[str, Any]:
        """
        Analyzes document structure of a specific chapter.
        
        Args:
            chapter_num: Chapter number
            
        Returns:
            Dictionary with document structure
        """
        try:
            # Check cache
            if chapter_num in self._cache["structure"]:
                return self._cache["structure"][chapter_num]
            
            # Load chapter content
            chapter_content = self._load_chapter(chapter_num)
            
            # Parse markdown structure
            structure = {
                "headings": self._extract_headings(chapter_content),
                "sections": self._extract_sections(chapter_content),
                "codeBlocks": self._extract_code_blocks(chapter_content)
            }
            
            # Cache result
            self._cache["structure"][chapter_num] = structure
            
            return structure
        except Exception as e:
            logger.error(f"Error analyzing document structure for chapter {chapter_num}: {str(e)}")
            return {"error": str(e)}
    
    def extract_code_samples(self, chapter_num: int, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Extracts code samples from a chapter with optional language filtering.
        
        Args:
            chapter_num: Chapter number
            language: Filter by programming language
            
        Returns:
            Dictionary with code samples
        """
        try:
            # Load chapter content
            chapter_content = self._load_chapter(chapter_num)
            
            # Extract code blocks with language info
            code_blocks = self._extract_code_blocks(chapter_content)
            
            # Filter by language if specified
            if language:
                code_blocks = [block for block in code_blocks if block["language"] == language]
            
            return {
                "samples": code_blocks,
                "count": len(code_blocks)
            }
        except Exception as e:
            logger.error(f"Error extracting code samples from chapter {chapter_num}: {str(e)}")
            return {"error": str(e)}
    
    def generate_document_outline(self) -> Dict[str, Any]:
        """
        Creates hierarchical representation of document structure.
        
        Returns:
            Dictionary with document outline
        """
        try:
            # Get all chapters
            chapters = self._get_all_chapters()
            
            # Extract headings from each chapter
            outline = []
            for chapter in sorted(chapters, key=lambda x: x["number"]):
                chapter_headings = self._extract_headings(chapter["content"])
                
                outline.append({
                    "chapter": chapter["number"],
                    "filename": chapter["filename"],
                    "headings": chapter_headings
                })
            
            return {
                "outline": outline
            }
        except Exception as e:
            logger.error(f"Error generating document outline: {str(e)}")
            return {"error": str(e)}
    
    # Blueprint Extraction Tools
    
    def extract_component_diagrams(self) -> Dict[str, Any]:
        """
        Identifies React component hierarchies from documentation.
        
        Returns:
            Dictionary with component diagrams
        """
        try:
            # Check cache
            if self._cache["components"] is not None:
                return self._cache["components"]
            
            # Analyze all chapters to find component relationships
            components = {}
            for chapter in self._get_all_chapters():
                # Extract code blocks
                code_blocks = self._extract_code_blocks(chapter["content"])
                
                # Extract components from each code block
                for block in code_blocks:
                    if block["language"] in ["javascript", "typescript", "jsx", "tsx"]:
                        chapter_components = self._extract_components(block["code"])
                        components.update(chapter_components)
            
            # Build relationship graph
            component_graph = self._build_component_graph(components)
            
            result = {
                "components": components,
                "graph": component_graph
            }
            
            # Cache result
            self._cache["components"] = result
            
            return result
        except Exception as e:
            logger.error(f"Error extracting component diagrams: {str(e)}")
            return {"error": str(e)}
    
    def extract_data_flow(self) -> Dict[str, Any]:
        """
        Analyzes and visualizes data flow between components.
        
        Returns:
            Dictionary with data flow information
        """
        try:
            # Get component diagrams first
            component_result = self.extract_component_diagrams()
            if "error" in component_result:
                return component_result
            
            components = component_result["components"]
            
            # Analyze data flow (simplified implementation)
            # In a real implementation, we would analyze props passing between components
            data_flows = []
            
            # For now, we'll just return a placeholder
            # A more complete implementation would analyze props and state
            
            return {
                "dataFlows": data_flows,
                "components": list(components.keys())
            }
        except Exception as e:
            logger.error(f"Error extracting data flow: {str(e)}")
            return {"error": str(e)}
    
    def extract_api_interfaces(self) -> Dict[str, Any]:
        """
        Identifies API interfaces and data structures.
        
        Returns:
            Dictionary with API interfaces
        """
        try:
            # Get all chapters
            chapters = self._get_all_chapters()
            
            # Look for interface/type definitions in TypeScript code
            interfaces = []
            
            for chapter in chapters:
                code_blocks = self._extract_code_blocks(chapter["content"])
                
                for block in code_blocks:
                    if block["language"] in ["typescript", "tsx"]:
                        # Look for interface definitions
                        interface_pattern = r'(export\s+)?interface\s+(\w+)(\s+extends\s+(\w+))?\s*\{([^}]*)\}'
                        for match in re.finditer(interface_pattern, block["code"], re.DOTALL):
                            name = match.group(2)
                            extends = match.group(4)
                            body = match.group(5).strip()
                            
                            interfaces.append({
                                "name": name,
                                "extends": extends,
                                "body": body,
                                "type": "interface",
                                "chapter": chapter["number"]
                            })
                        
                        # Look for type definitions
                        type_pattern = r'(export\s+)?type\s+(\w+)(\s*<[^>]*>)?\s*=\s*([^;]*);'
                        for match in re.finditer(type_pattern, block["code"], re.DOTALL):
                            name = match.group(2)
                            generics = match.group(3)
                            definition = match.group(4).strip()
                            
                            interfaces.append({
                                "name": name,
                                "generics": generics,
                                "definition": definition,
                                "type": "type",
                                "chapter": chapter["number"]
                            })
            
            return {
                "interfaces": interfaces,
                "count": len(interfaces)
            }
        except Exception as e:
            logger.error(f"Error extracting API interfaces: {str(e)}")
            return {"error": str(e)}

# Create FastMCP server wrapper
def create_tutorial_mcp_server(tutorial_dir: str):
    """
    Create and configure a FastMCP server for tutorial documentation.
    
    Args:
        tutorial_dir: Directory containing tutorial markdown files
        
    Returns:
        Configured FastMCP server instance
    """
    try:
        from fastmcp import FastMCP
        
        # Create tutorial MCP implementation
        tutorial_mcp = TutorialMCPServer(tutorial_dir)
        
        # Create FastMCP server
        mcp = FastMCP("tutorial_mcp_server")
        
        # Register document retrieval tools
        @mcp.tool(name="chapter_index")
        def chapter_index():
            """Returns the tutorial index markdown"""
            return tutorial_mcp.chapter_index()
        
        @mcp.tool(name="get_chapter")
        def get_chapter(n: int):
            """Returns one chapter's markdown by number"""
            return tutorial_mcp.get_chapter(n)
        
        @mcp.tool(name="get_complete_tutorial")
        def get_complete_tutorial():
            """Returns the complete tutorial markdown"""
            return tutorial_mcp.get_complete_tutorial()
        
        # Register document structure analysis tools
        @mcp.tool(name="analyze_document_structure")
        def analyze_document_structure(chapter_num: int):
            """Analyzes document structure and returns hierarchical representation"""
            return tutorial_mcp.analyze_document_structure(chapter_num)
        
        @mcp.tool(name="extract_code_samples")
        def extract_code_samples(chapter_num: int, language: Optional[str] = None):
            """Extracts code samples with language identification"""
            return tutorial_mcp.extract_code_samples(chapter_num, language)
        
        @mcp.tool(name="generate_document_outline")
        def generate_document_outline():
            """Creates hierarchical representation of document structure"""
            return tutorial_mcp.generate_document_outline()
        
        # Register blueprint extraction tools
        @mcp.tool(name="extract_component_diagrams")
        def extract_component_diagrams():
            """Identifies React component hierarchies from documentation"""
            return tutorial_mcp.extract_component_diagrams()
        
        @mcp.tool(name="extract_data_flow")
        def extract_data_flow():
            """Analyzes and visualizes data flow between components"""
            return tutorial_mcp.extract_data_flow()
        
        @mcp.tool(name="extract_api_interfaces")
        def extract_api_interfaces():
            """Identifies API interfaces and data structures"""
            return tutorial_mcp.extract_api_interfaces()
        
        # Register advanced tools if available
        try:
            from .tutorial_mcp_advanced import register_advanced_tools
            register_advanced_tools(mcp, tutorial_mcp)
            logger.info("Advanced tools registered successfully")
        except ImportError:
            logger.warning("Advanced tools module not available, skipping registration")
        
        logger.info("Tutorial MCP server created successfully")
        return mcp
        
    except ImportError:
        logger.warning("FastMCP not available, using mock implementation")
        from .mcp import MockMCPServer
        
        # Create a mock server with basic functionality
        tools = [
            {"name": "chapter_index", "description": "Returns the tutorial index markdown"},
            {"name": "get_chapter", "description": "Returns one chapter's markdown by number"},
            {"name": "get_complete_tutorial", "description": "Returns the complete tutorial markdown"},
            {"name": "analyze_document_structure", "description": "Analyzes document structure"},
            {"name": "extract_code_samples", "description": "Extracts code samples"},
            {"name": "generate_document_outline", "description": "Creates document outline"},
            {"name": "extract_component_diagrams", "description": "Identifies React component hierarchies"},
            {"name": "extract_data_flow", "description": "Analyzes data flow between components"},
            {"name": "extract_api_interfaces", "description": "Identifies API interfaces"}
        ]
        
        # Create tutorial MCP implementation for the mock server to use
        tutorial_mcp = TutorialMCPServer(tutorial_dir)
        
        # Create mock server with custom handlers
        mock_server = MockMCPServer("tutorial_mcp_server", tools, {})
        
        # Override tool handlers with actual implementations
        mock_server.tool_handlers["chapter_index"] = tutorial_mcp.chapter_index
        mock_server.tool_handlers["get_chapter"] = tutorial_mcp.get_chapter
        mock_server.tool_handlers["get_complete_tutorial"] = tutorial_mcp.get_complete_tutorial
        mock_server.tool_handlers["analyze_document_structure"] = tutorial_mcp.analyze_document_structure
        mock_server.tool_handlers["extract_code_samples"] = tutorial_mcp.extract_code_samples
        mock_server.tool_handlers["generate_document_outline"] = tutorial_mcp.generate_document_outline
        mock_server.tool_handlers["extract_component_diagrams"] = tutorial_mcp.extract_component_diagrams
        mock_server.tool_handlers["extract_data_flow"] = tutorial_mcp.extract_data_flow
        mock_server.tool_handlers["extract_api_interfaces"] = tutorial_mcp.extract_api_interfaces
        
        # Try to register advanced tools if available
        try:
            from .tutorial_mcp_advanced import register_advanced_tools
            register_advanced_tools(mock_server, tutorial_mcp)
            logger.info("Advanced tools registered with mock server")
        except ImportError:
            logger.warning("Advanced tools module not available, skipping registration")
        
        return mock_server

def start_tutorial_mcp_server(tutorial_dir: str, host: str = "localhost", port: int = 8000, debug: bool = False):
    """
    Create and start a tutorial MCP server.
    
    Args:
        tutorial_dir: Directory containing tutorial markdown files
        host: Host to bind to
        port: Port to listen on
        debug: Enable debug logging
        
    Returns:
        Server information
    """
    # Create server
    mcp_server = create_tutorial_mcp_server(tutorial_dir)
    
    # Start server
    from .mcp import start_mcp_server
    server_info = start_mcp_server(mcp_server, host, port, debug=debug)
    
    return server_info 