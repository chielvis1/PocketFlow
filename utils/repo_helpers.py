import yaml
from typing import Dict, List, Any

def get_content_for_indices(files_data, indices):
    """
    Helper to get content for specific file indices from a list of files.
    
    Args:
        files_data: List of (path, content) tuples
        indices: List of indices to retrieve
        
    Returns:
        Dictionary mapping "idx # path" to content
    """
    content_map = {}
    for i in indices:
        if 0 <= i < len(files_data):
            path, content = files_data[i]
            content_map[f"{i} # {path}"] = content # Use index + path as key for context
    return content_map 