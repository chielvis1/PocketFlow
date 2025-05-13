#!/usr/bin/env python3
"""
Test script that demonstrates the dynamic LLM provider and model selection.
"""

import os
import sys
from typing import Optional

# Add parent directory to path so we can import utils
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from utils.llm import call_llm, stream_llm, setup_llm_provider

def print_with_border(text: str) -> None:
    """Print text with a decorative border."""
    width = max(len(line) for line in text.split('\n')) + 4
    border = "=" * width
    print(f"\n{border}")
    for line in text.split('\n'):
        print(f"| {line.ljust(width - 4)} |")
    print(f"{border}\n")

def callback_fn(token: str) -> None:
    """Callback function for streaming LLM output."""
    print(token, end='', flush=True)

def main() -> None:
    """Main function to test dynamic LLM selection."""
    print_with_border("Dynamic LLM Selection Test")
    
    print("This test will walk you through the dynamic LLM provider and model selection.")
    print("You'll be prompted to select a provider and model, then the LLM will be used to answer questions.")
    print("\nYou will need API keys for the providers you want to test.")
    
    # Step 1: Test simple call_llm with full interactive setup
    print_with_border("Test 1: Provider and Model Setup")
    print("First, let's select a provider and model...")
    
    try:
        # Use our setup function that handles the full workflow
        provider, api_key, model = setup_llm_provider()
        print(f"\nSelected provider: {provider}")
        print(f"Selected model: {model}")
        
        print("\nNow testing with a simple prompt:")
        response = call_llm(
            prompt="What is the meaning of life? Keep your answer under 100 words.",
            provider=provider,
            api_key=api_key,
            model=model
        )
        
        print("\nResponse:")
        print_with_border(response)
    except Exception as e:
        print(f"Error: {str(e)}")
        return
    
    # Step 2: Test streaming with a different prompt
    print_with_border("Test 2: Streaming LLM Call")
    print("Testing stream_llm with the same provider and model...")
    print("This will stream the response token by token...\n")
    
    try:
        print("\nResponse (streaming):")
        
        stream_llm(
            prompt="Generate a short haiku about artificial intelligence.",
            callback_fn=callback_fn,
            provider=provider,
            api_key=api_key,
            model=model
        )
        print("\n")
    except Exception as e:
        print(f"\nError: {str(e)}")
    
    # Step 3: Test with explicit model and provider
    print_with_border("Test 3: Using Explicit Provider and Model")
    print("This test simulates using command-line arguments to specify provider/model.")
    
    try:
        # Ask user for explicit provider and model (simulating CLI args)
        cli_provider = input("\nSpecify provider (empty to use previously selected): ")
        cli_model = input("Specify model (empty to use previously selected): ")
        
        # Use previously selected values if empty
        if not cli_provider:
            cli_provider = provider
            print(f"Using previously selected provider: {provider}")
        
        if not cli_model:
            cli_model = model
            print(f"Using previously selected model: {model}")
        
        response = call_llm(
            prompt="What are three benefits of using LLMs in software development?",
            provider=cli_provider,
            api_key=api_key,
            model=cli_model
        )
        
        print("\nResponse:")
        print_with_border(response)
    except Exception as e:
        print(f"Error: {str(e)}")
    
    print_with_border("Tests Completed")
    print("The dynamic LLM selection tests are complete.")
    print("You have successfully tested the LLM utilities with dynamic provider and model selection.")

if __name__ == "__main__":
    main() 