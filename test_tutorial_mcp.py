#!/usr/bin/env python3
"""
Test script for Tutorial MCP Server

This script tests the functionality of the Tutorial MCP Server implementation.
"""

import os
import sys
import json
import argparse
import tempfile
from pathlib import Path

def create_test_tutorial():
    """
    Create a temporary tutorial directory with test files.
    
    Returns:
        Path to the temporary tutorial directory
    """
    # Create temporary directory
    temp_dir = tempfile.mkdtemp(prefix="tutorial_test_")
    tutorial_dir = Path(temp_dir)
    
    # Create index file
    with open(tutorial_dir / "index.md", "w") as f:
        f.write("""# Tutorial Index
        
This is a test tutorial for the MCP server.

## Chapters

1. [Introduction](chapter_01__Introduction.md)
2. [Getting Started](chapter_02__Getting_Started.md)
""")
    
    # Create chapter 1
    with open(tutorial_dir / "chapter_01__Introduction.md", "w") as f:
        f.write("""# Introduction

This is the introduction chapter.

## What is this tutorial about?

This tutorial demonstrates how to build a React application.

```javascript
// Example component
const MyComponent = () => {
  return <div>Hello World</div>;
};

export default MyComponent;
```
""")
    
    # Create chapter 2
    with open(tutorial_dir / "chapter_02__Getting_Started.md", "w") as f:
        f.write("""# Getting Started

Let's get started with our React application.

## Creating a component

Here's how to create a React component:

```typescript
// User component
interface UserProps {
  name: string;
  age: number;
}

export const User: React.FC<UserProps> = ({ name, age }) => {
  return (
    <div>
      <h2>{name}</h2>
      <p>Age: {age}</p>
    </div>
  );
};

// Singleton pattern example
export class UserStore {
  private static instance: UserStore;
  
  private constructor() {
    // Private constructor
  }
  
  public static getInstance(): UserStore {
    if (!UserStore.instance) {
      UserStore.instance = new UserStore();
    }
    return UserStore.instance;
  }
  
  getUsers() {
    return [{ name: 'John', age: 30 }];
  }
}
```
""")
    
    print(f"Created test tutorial in {tutorial_dir}")
    return tutorial_dir

def run_tests(tutorial_dir):
    """
    Run tests on the Tutorial MCP Server.
    
    Args:
        tutorial_dir: Path to the tutorial directory
    """
    # Add parent directory to path to import utils
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Import tutorial MCP server
    try:
        from utils.tutorial_mcp import TutorialMCPServer
        
        # Create tutorial MCP server instance
        tutorial_mcp = TutorialMCPServer(tutorial_dir)
        
        # Test document retrieval tools
        print("\n=== Testing Document Retrieval Tools ===")
        
        print("\nTesting chapter_index():")
        result = tutorial_mcp.chapter_index()
        print(f"Success: {'error' not in result}")
        
        print("\nTesting get_chapter(1):")
        result = tutorial_mcp.get_chapter(1)
        print(f"Success: {'error' not in result}")
        
        print("\nTesting get_complete_tutorial():")
        result = tutorial_mcp.get_complete_tutorial()
        print(f"Success: {'error' not in result}")
        
        # Test document structure analysis tools
        print("\n=== Testing Document Structure Analysis Tools ===")
        
        print("\nTesting analyze_document_structure(1):")
        result = tutorial_mcp.analyze_document_structure(1)
        print(f"Success: {'error' not in result}")
        print(f"Found {len(result['headings'])} headings")
        print(f"Found {len(result['sections'])} sections")
        print(f"Found {len(result['codeBlocks'])} code blocks")
        
        print("\nTesting extract_code_samples(2):")
        result = tutorial_mcp.extract_code_samples(2)
        print(f"Success: {'error' not in result}")
        print(f"Found {result['count']} code samples")
        
        print("\nTesting generate_document_outline():")
        result = tutorial_mcp.generate_document_outline()
        print(f"Success: {'error' not in result}")
        print(f"Found {len(result['outline'])} chapters in outline")
        
        # Test blueprint extraction tools
        print("\n=== Testing Blueprint Extraction Tools ===")
        
        print("\nTesting extract_component_diagrams():")
        result = tutorial_mcp.extract_component_diagrams()
        print(f"Success: {'error' not in result}")
        print(f"Found {len(result['components'])} components")
        
        # Add more tests for advanced features if available
        try:
            # Test data flow extraction
            print("\nTesting extract_data_flow():")
            result = tutorial_mcp.extract_data_flow()
            print(f"Success: {'error' not in result}")
            
            # Test API interface extraction
            print("\nTesting extract_api_interfaces():")
            result = tutorial_mcp.extract_api_interfaces()
            print(f"Success: {'error' not in result}")
            print(f"Found {result.get('count', 0)} interfaces")
        except AttributeError:
            print("Advanced blueprint extraction tools not available")
        
        print("\nAll tests completed successfully!")
        
    except ImportError as e:
        print(f"Error importing TutorialMCPServer: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error during tests: {e}")
        sys.exit(1)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Test the Tutorial MCP Server implementation")
    
    parser.add_argument(
        "--tutorial-dir",
        type=str,
        help="Directory containing tutorial markdown files (if not provided, a temporary directory will be created)"
    )
    
    return parser.parse_args()

def main():
    """Main entry point"""
    args = parse_arguments()
    
    # Use provided tutorial directory or create a temporary one
    tutorial_dir = args.tutorial_dir
    temp_dir = None
    
    if not tutorial_dir:
        temp_dir = create_test_tutorial()
        tutorial_dir = temp_dir
    
    # Run tests
    run_tests(tutorial_dir)
    
    # Clean up if we created a temporary directory
    if temp_dir:
        import shutil
        shutil.rmtree(temp_dir)
        print(f"Cleaned up temporary directory: {temp_dir}")

if __name__ == "__main__":
    main() 