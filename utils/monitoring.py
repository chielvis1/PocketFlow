"""
Monitoring utilities for Repository Analysis to MCP Server system.
"""

import time
import logging
import functools
from typing import Dict, Any, Optional, Callable, Union

# Global counter dictionary for metrics
_counters = {}

def log_execution_time(operation_name: Optional[str] = None) -> Callable:
    """
    Decorator for timing node execution.
    
    Args:
        operation_name: Name of operation
        
    Returns:
        Decorated function that logs execution time
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate operation name if not provided
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            # Log start
            start_time = time.time()
            logging.debug(f"Starting {op_name}")
            
            try:
                # Execute function
                result = func(*args, **kwargs)
                
                # Calculate execution time
                execution_time = time.time() - start_time
                
                # Log completion
                logging.info(f"Completed {op_name} in {execution_time:.2f} seconds")
                
                # Track metric
                increment_counter(f"{op_name}_count")
                increment_counter(f"{op_name}_time_total", value=execution_time)
                
                # If result is a dict, add execution metadata
                if isinstance(result, dict):
                    result.setdefault("_metadata", {}).update({
                        "execution_time": execution_time,
                        "operation": op_name
                    })
                
                return result
            except Exception as e:
                # Log failure and execution time
                execution_time = time.time() - start_time
                logging.error(f"Failed {op_name} after {execution_time:.2f} seconds: {str(e)}")
                
                # Track failure metric
                increment_counter(f"{op_name}_errors")
                
                # Re-raise the exception
                raise
        
        return wrapper
    
    # Handle case when decorator is used without parentheses
    if callable(operation_name):
        func = operation_name
        operation_name = None
        return decorator(func)
    
    return decorator

def configure_logging(level: Union[str, int], format_string: Optional[str] = None) -> logging.Logger:
    """
    Configures structured logging for the system.
    
    Args:
        level: Logging level 
        format_string: Custom log format
        
    Returns:
        Configured logger
    """
    # Convert string level to numeric if needed
    if isinstance(level, str):
        level = getattr(logging, level.upper())
    
    # Use default format if not specified
    if not format_string:
        format_string = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        format=format_string,
        handlers=[
            logging.StreamHandler(),  # Console handler
            logging.FileHandler("repo_analyzer.log")  # File handler
        ]
    )
    
    # Create logger for this application
    logger = logging.getLogger("repo_analyzer")
    logger.setLevel(level)
    
    # Add filter to include correlation ID if available
    class ContextFilter(logging.Filter):
        def filter(self, record):
            record.correlation_id = getattr(record, 'correlation_id', '-')
            return True
    
    logger.addFilter(ContextFilter())
    
    return logger

def increment_counter(name: str, value: float = 1, tags: Optional[Dict[str, str]] = None) -> None:
    """
    Tracks metric counters for monitoring.
    
    Args:
        name: Counter name
        value: Value to increment by
        tags: Metadata tags
    """
    # Initialize counter if not exists
    if name not in _counters:
        _counters[name] = 0
    
    # Increment counter
    _counters[name] += value
    
    # Log the increment
    tag_str = ""
    if tags:
        tag_str = ", ".join(f"{k}={v}" for k, v in tags.items())
        tag_str = f" with tags {tag_str}"
    
    logging.debug(f"Incremented counter {name} by {value}{tag_str}, new value: {_counters[name]}")

def get_counter(name: str) -> float:
    """
    Get current value of a counter.
    
    Args:
        name: Counter name
        
    Returns:
        Current counter value
    """
    return _counters.get(name, 0)

def get_all_counters() -> Dict[str, float]:
    """
    Get all counters.
    
    Returns:
        Dictionary of all counters
    """
    return _counters.copy()

def reset_counter(name: str) -> None:
    """
    Reset a counter to zero.
    
    Args:
        name: Counter name
    """
    if name in _counters:
        _counters[name] = 0
        logging.debug(f"Reset counter {name} to 0")

def reset_all_counters() -> None:
    """
    Reset all counters to zero.
    """
    for name in _counters:
        _counters[name] = 0
    logging.debug(f"Reset all {len(_counters)} counters to 0")

if __name__ == "__main__":
    # Configure logging
    logger = configure_logging("INFO")
    
    # Test the execution time decorator
    @log_execution_time("test_operation")
    def test_function(duration):
        """Test function that sleeps for specified duration"""
        time.sleep(duration)
        return {"status": "success", "duration": duration}
    
    # Test counter functions
    print("Testing metrics...")
    increment_counter("api_calls", tags={"method": "GET", "endpoint": "/search"})
    increment_counter("api_calls", tags={"method": "POST", "endpoint": "/analyze"})
    increment_counter("items_processed", 5)
    
    print("Current counters:", get_all_counters())
    
    # Test execution time decorator
    print("\nTesting execution time decorator...")
    result = test_function(0.5)
    print(f"Function result: {result}")
    
    # Show final counter values
    print("\nFinal counter values:", get_all_counters()) 