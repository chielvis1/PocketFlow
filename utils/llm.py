"""
LLM integration utilities for Repository Analysis to MCP Server system.
"""

import os
import json
import yaml
from functools import lru_cache
from typing import Dict, List, Any, Optional, Callable, Union, Tuple

# Global configuration storage
_CURRENT_CONFIG = {}

def choose_provider() -> str:
    """
    Prompt user to choose an LLM provider.
    
    Returns:
        The selected provider name
    """
    providers = [
        "google", # Google Gemini
        "openai", # OpenAI (GPT models)
        "anthropic", # Anthropic (Claude models)
        "openrouter" # OpenRouter (aggregator)
    ]
    
    print("\nAvailable LLM providers:")
    for i, provider in enumerate(providers):
        print(f"{i+1}. {provider.capitalize()}")
    
    while True:
        try:
            choice = input(f"\nSelect a provider (1-{len(providers)}): ")
            provider_idx = int(choice) - 1
            if 0 <= provider_idx < len(providers):
                return providers[provider_idx]
            else:
                print(f"Please enter a number between 1 and {len(providers)}")
        except ValueError:
            print("Please enter a valid number")

def get_api_key(provider: str) -> str:
    """
    Get API key for the selected provider from environment or user input.
    
    Args:
        provider: The name of the LLM provider
    
    Returns:
        The API key
    """
    env_var_map = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "google": "GOOGLE_API_KEY",
        "openrouter": "OPENROUTER_API_KEY"
    }
    
    env_var = env_var_map.get(provider)
    if not env_var:
        raise ValueError(f"Unknown provider: {provider}")
    
    api_key = os.environ.get(env_var)
    if not api_key:
        while not api_key:
            api_key = input(f"Enter your {provider.capitalize()} API key: ")
            if not api_key:
                print("API key cannot be empty. Please enter a valid API key.")
        os.environ[env_var] = api_key  # Store temporarily for this session
    
    return api_key

def verify_api_key(provider: str, api_key: str) -> bool:
    """
    Verify that the API key is valid for the specified provider.
    
    Args:
        provider: The LLM provider name
        api_key: The API key to verify
        
    Returns:
        True if the API key is valid, otherwise raises an exception
    """
    try:
        if provider == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            # Simple API call to verify the key
            client.models.list(limit=1)
            
        elif provider == "anthropic":
            from anthropic import Anthropic
            client = Anthropic(api_key=api_key)
            # Simple API call to verify the key
            client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=10,
                messages=[{"role": "user", "content": "Hello"}]
            )
            
        elif provider == "google":
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                # Simple API call to verify the key
                genai.list_models()
            except ImportError:
                # If Google Generative AI package is not available, make a simple HTTP request
                import requests
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                }
                response = requests.get(
                    "https://generativelanguage.googleapis.com/v1/models",
                    headers=headers
                )
                if response.status_code != 200:
                    raise ValueError(f"API key validation failed with status code: {response.status_code}")
                
        elif provider == "openrouter":
            import requests
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            response = requests.get("https://openrouter.ai/api/v1/models", headers=headers)
            if response.status_code != 200:
                raise ValueError(f"API key validation failed with status code: {response.status_code}")
            
        else:
            raise ValueError(f"Unknown provider: {provider}")
            
        return True
        
    except Exception as e:
        # Re-raise with more context
        raise ValueError(f"API key verification failed for {provider}: {str(e)}")

def list_available_models(provider: str, api_key: str) -> List[Dict[str, Any]]:
    """
    List available models from the selected provider.
    
    Args:
        provider: The name of the LLM provider
        api_key: The API key for the provider
    
    Returns:
        List of available models with metadata
    """
    try:
        if provider == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            models = client.models.list()
            # Filter chat models
            return [
                {"id": m.id, "name": m.id, "description": ""}
                for m in models.data if m.id.startswith(("gpt-", "text-"))
            ]
            
        elif provider == "anthropic":
            # Anthropic doesn't have a list_models API, so we provide some known models
            models = [
                {"id": "claude-3-haiku-20240307", "name": "Claude 3 Haiku", "description": "Fast and efficient model for tasks requiring quick responses"},
                {"id": "claude-3-sonnet-20240229", "name": "Claude 3 Sonnet", "description": "Balanced model offering a strong blend of intelligence and speed"},
                {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus", "description": "Most powerful model for complex and nuanced tasks"},
                {"id": "claude-2.1", "name": "Claude 2.1", "description": "Previous generation model"},
                {"id": "claude-2.0", "name": "Claude 2.0", "description": "Previous generation model"},
                {"id": "claude-instant-1.2", "name": "Claude Instant 1.2", "description": "Faster and more affordable Claude model"}
            ]
            return models
            
        elif provider == "google":
            # Always provide these models for Google to ensure we have a working fallback
            # This will be used when the API fails to list models or when the package is not installed
            fallback_models = [
                {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro", "description": "Latest flagship Gemini model with advanced reasoning"},
                {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "description": "Gemini model optimized for speed and efficiency"},
                {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro", "description": "Previous generation Gemini model with 1M context window"},
                {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash", "description": "Previous generation fast Gemini model"},
                {"id": "gemini-1.0-pro", "name": "Gemini 1.0 Pro", "description": "Legacy Gemini model"}
            ]
            
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                
                # Get available models from Google Generative AI
                try:
                    models_response = genai.list_models()
                    
                    # Filter for Gemini models and format the response
                    api_models = [
                        {
                            "id": model.name, 
                            "name": model.name.split('/')[-1] if '/' in model.name else model.name, 
                            "description": model.description if hasattr(model, 'description') else ""
                        }
                        for model in models_response if "gemini" in model.name.lower()
                    ]
                    
                    # If we successfully got models from the API, return those
                    if api_models:
                        return api_models
                    # Otherwise fall back to our predefined list
                    print("No Gemini models found via API, using predefined list.")
                    return fallback_models
                except Exception as e:
                    print(f"Error listing Google models: {str(e)}. Using predefined models.")
                    return fallback_models
            except ImportError:
                # Package not available, use fallback
                print("Google Generative AI package not available. Using fallback model list.")
                return fallback_models
                
        elif provider == "openrouter":
            import requests
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            response = requests.get("https://openrouter.ai/api/v1/models", headers=headers)
            if response.status_code != 200:
                raise ValueError(f"Failed to fetch models from OpenRouter: {response.status_code}")
                
            models = response.json().get("data", [])
            return [
                {"id": m["id"], "name": m.get("name", m["id"]), "description": m.get("description", "")}
                for m in models
            ]
            
        else:
            raise ValueError(f"Unknown provider: {provider}")
            
    except Exception as e:
        print(f"Error listing models: {str(e)}")
        # Return a minimal set of fallback models based on the provider
        fallback_models = {
            "openai": [
                {"id": "gpt-4o", "name": "GPT-4o", "description": "Latest OpenAI GPT-4o model"},
                {"id": "gpt-4-turbo", "name": "GPT-4 Turbo", "description": "OpenAI GPT-4 Turbo model"},
                {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "description": "OpenAI GPT-3.5 Turbo model"}
            ],
            "anthropic": [
                {"id": "claude-3-haiku-20240307", "name": "Claude 3 Haiku", "description": "Fast and efficient model"},
                {"id": "claude-3-sonnet-20240229", "name": "Claude 3 Sonnet", "description": "Balanced model"},
                {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus", "description": "Most powerful model"}
            ],
            "google": [
                {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro", "description": "Latest flagship Gemini model with advanced reasoning"},
                {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro", "description": "Previous generation Gemini model with 1M context window"},
                {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash", "description": "Previous generation fast Gemini model"}
            ],
            "openrouter": [
                {"id": "openai/gpt-4o", "name": "OpenAI GPT-4o", "description": "Access to GPT-4o via OpenRouter"},
                {"id": "anthropic/claude-3-opus", "name": "Anthropic Claude 3 Opus", "description": "Access to Claude 3 Opus via OpenRouter"}
            ]
        }
        
        return fallback_models.get(provider, [])

def extract_keywords_and_techstack(query: str, model: Optional[str] = None, provider: Optional[str] = None) -> Dict[str, Any]:
    """
    Extracts relevant keywords, tech stack, and context from user queries.
    
    Args:
        query: User's natural language query
        model: The model to use (if None, will use a default or last configured model)
        provider: The provider to use (if None, will use a default or last configured provider)
        
    Returns:
        Dictionary containing:
          - original_query (str): Original query text
          - keywords (list): List of extracted keywords
          - tech_stack (list): Technologies mentioned or implied
          - context (str): Interpreted context of the query
          - features (list): Desired features the user is looking for
    """
    prompt = f"""
Please analyze this query and extract the following information:

Query: "{query}"

Please extract:
1. Keywords - the main general concepts in the query
2. Tech Stack - specific technologies mentioned or implied
3. Features - specific functionality the user is looking for
4. Context - the overall goal/purpose of the query

Output in YAML format:
```yaml
keywords:
  - keyword1
  - keyword2
tech_stack:
  - technology1
  - technology2
features:
  - feature1
  - feature2
context: A brief description of the overall goal
```
"""
    
    result = call_llm(prompt=prompt, model=model, provider=provider, temperature=0.1)
    
    try:
        # Extract YAML part from response
        yaml_str = result
        if "```yaml" in result:
            yaml_str = result.split("```yaml")[1].split("```")[0].strip()
        elif "```" in result:
            yaml_str = result.split("```")[1].split("```")[0].strip()
        
        # Parse YAML
        import yaml
        parsed_data = yaml.safe_load(yaml_str)
        
        # Ensure all required fields exist
        parsed_data["original_query"] = query
        parsed_data.setdefault("keywords", [])
        parsed_data.setdefault("tech_stack", [])
        parsed_data.setdefault("features", [])
        parsed_data.setdefault("context", "")
        
        return parsed_data
    except Exception as e:
        print(f"Error parsing LLM response: {str(e)}")
        # Return a default structure on failure
        return {
            "original_query": query,
            "keywords": [],
            "tech_stack": [],
            "features": [],
            "context": ""
        }

def analyze_repository_with_llm(repo_data: Dict[str, Any], keywords: List[str], tech_stack: List[str], features: List[str], 
                              model: Optional[str] = None, provider: Optional[str] = None) -> Dict[str, Any]:
    """
    Performs in-depth analysis of repository contents using an LLM.
    
    Args:
        repo_data: Repository data (files, structure, etc.)
        keywords: Keywords from user query
        tech_stack: Technologies from user query
        features: Features the user is looking for
        model: The model to use (if None, will use a default or last configured model)
        provider: The provider to use (if None, will use a default or last configured provider)
        
    Returns:
        Detailed analysis dictionary with feature mapping, patterns, etc.
    """
    # Format repo data for the prompt
    repo_summary = f"Repository: {repo_data.get('name', 'Unknown')}\n"
    repo_summary += f"Description: {repo_data.get('description', 'No description')}\n"
    repo_summary += f"Language: {repo_data.get('language', 'Unknown')}\n"
    repo_summary += f"Stars: {repo_data.get('stars', 0)}\n\n"
    
    # Add file structure if available
    if "file_structure" in repo_data:
        repo_summary += "File Structure:\n"
        for file in repo_data["file_structure"][:20]:  # Limit to first 20 files
            repo_summary += f"- {file}\n"
    
    # Add code samples if available
    if "code_samples" in repo_data:
        repo_summary += "\nCode Samples:\n"
        for sample in repo_data["code_samples"][:3]:  # Limit to first 3 samples
            repo_summary += f"File: {sample.get('file', 'Unknown')}\n"
            repo_summary += f"```\n{sample.get('content', '')[:500]}...\n```\n\n"
    
    prompt = f"""
Please analyze this repository in relation to the user's requirements:

USER REQUIREMENTS:
Keywords: {', '.join(keywords)}
Tech Stack: {', '.join(tech_stack)}
Features: {', '.join(features)}

REPOSITORY INFORMATION:
{repo_summary}

Please provide a detailed analysis including:
1. Feature compatibility: How well does this repository address the user's required features?
2. Tech stack compatibility: How well does it align with the user's tech stack?
3. Code quality: Assessment of code organization, documentation, and maintainability
4. Key patterns: Important architectural or design patterns used
5. Implementation guide: Key concepts needed to understand and use this codebase

Output in YAML format:
```yaml
feature_compatibility:
  score: 0-10
  details: Explanation of how the repository addresses features
tech_compatibility:
  score: 0-10
  details: Compatibility with user's tech stack
code_quality:
  score: 0-10
  details: Assessment of code quality
key_patterns:
  - pattern1: Description
  - pattern2: Description
implementation_guide:
  key_concepts:
    - concept1: Explanation
    - concept2: Explanation
  learning_resources:
    - resource1
    - resource2
```
"""
    
    result = call_llm(prompt=prompt, model=model, provider=provider, temperature=0.2, max_tokens=2000)
    
    try:
        # Extract YAML part from response
        yaml_str = result
        if "```yaml" in result:
            yaml_str = result.split("```yaml")[1].split("```")[0].strip()
        elif "```" in result:
            yaml_str = result.split("```")[1].split("```")[0].strip()
        
        # Parse YAML
        import yaml
        analysis = yaml.safe_load(yaml_str)
        
        # Add the original query and repository data for reference
        analysis["keywords"] = keywords
        analysis["tech_stack"] = tech_stack
        analysis["features"] = features
        analysis["repository"] = {
            "name": repo_data.get("name", ""),
            "description": repo_data.get("description", ""),
            "url": repo_data.get("url", "")
        }
        
        return analysis
    except Exception as e:
        print(f"Error parsing LLM response: {str(e)}")
        # Return a default structure on failure
        return {
            "error": f"Failed to analyze repository: {str(e)}",
            "repository": {
                "name": repo_data.get("name", ""),
                "url": repo_data.get("url", "")
            }
        }

def prompt_model_selection(models: List[Dict[str, Any]]) -> str:
    """
    Prompt the user to select a model from the list of available models.
    
    Args:
        models: List of available models with metadata
        
    Returns:
        Selected model ID
    """
    # Ensure we have at least one model
    if not models:
        raise ValueError("No models available to select from")
        
    # Default to first model if only one is available
    if len(models) == 1:
        print(f"\nOnly one model available: {models[0]['name']}")
        print(f"Automatically selecting: {models[0]['id']}")
        return models[0]['id']
    
    print("\nAvailable models:")
    for i, model in enumerate(models):
        # Format description to be more readable
        description = model.get("description", "")
        if len(description) > 60:
            description = description[:57] + "..."
            
        print(f"{i+1}. {model['name']}")
        if description:
            print(f"   {description}")
    
    while True:
        try:
            choice = input(f"\nEnter the number of the model you want to use (1-{len(models)}): ")
            
            # Check if user wants to exit
            if choice.lower() in ('q', 'quit', 'exit'):
                raise KeyboardInterrupt("User requested to exit model selection")
                
            # Handle default case (empty input)
            if not choice.strip():
                print(f"Using default model: {models[0]['name']}")
                return models[0]['id']
                
            # Parse numeric choice
            index = int(choice) - 1
            if 0 <= index < len(models):
                return models[index]["id"]
            else:
                print(f"Please enter a valid number between 1 and {len(models)}")
        except ValueError:
            print("Please enter a valid number")
        except (KeyboardInterrupt, EOFError):
            # Handle Ctrl+C or Ctrl+D
            print("\nCancelling model selection...")
            # Default to first model when interrupted
            print(f"Using default model: {models[0]['name']}")
            return models[0]['id']

def choose_model(models: List[Dict[str, Any]]) -> str:
    """
    Prompt user to select a model from the available options.
    
    Args:
        models: List of available models with metadata
        
    Returns:
        Selected model ID
    """
    return prompt_model_selection(models)

def setup_llm_provider() -> Tuple[str, str, str]:
    """
    Interactive setup for LLM provider, including provider selection, API key entry, and model selection.
    
    Returns:
        Tuple of (provider_name, api_key, model_name)
    """
    # Step 1: Choose LLM Provider
    provider = choose_provider()
    print(f"\nSelected provider: {provider}")
    
    # Step 2: Get API Key
    api_key = get_api_key(provider)
    if not api_key:
        raise ValueError("API key is required")
    
    # Step 3: Verify API Key
    print(f"\nVerifying API key...")
    try:
        verify_api_key(provider, api_key)
        print("API key verified successfully!")
    except Exception as e:
        raise ValueError(f"API key verification failed: {str(e)}")
    
    # Step 4: List Available Models
    print(f"\nRetrieving available models...")
    try:
        models = list_available_models(provider, api_key)
        if not models:
            raise ValueError(f"No models available for {provider}")
    except Exception as e:
        raise ValueError(f"Error listing models: {str(e)}")
    
    # Step 5: Choose Model
    model = choose_model(models)
    print(f"\nSelected model: {model}")
    
    # Return the selected provider, API key, and model
    return provider, api_key, model

def setup_llm_provider_with_params(provider=None, model=None, api_key=None) -> Tuple[str, str, str]:
    """
    Set up LLM provider with specified parameters, with minimal interactive prompting.
    Will only prompt for values that are not provided.
    
    Args:
        provider: The name of the LLM provider (e.g., 'openai', 'google', 'anthropic', 'openrouter')
        model: The name of the model to use
        api_key: The API key to use (if None, will look in environment or prompt user)
        
    Returns:
        Tuple of (provider_name, api_key, model_name)
    """
    global _CURRENT_CONFIG
    
    # Step 1: Get provider (use provided, or prompt)
    if not provider:
        provider = choose_provider()
    print(f"Using provider: {provider}")
    
    # Step 2: Get API key (use provided, environment, or prompt)
    if not api_key:
        api_key = get_api_key(provider)
    if not api_key:
        raise ValueError("API key is required")
    
    # Step 3: Verify API key
    try:
        verify_api_key(provider, api_key)
    except Exception as e:
        raise ValueError(f"API key verification failed: {str(e)}")
    
    # Step 4: Get model (use provided, or prompt from available models)
    if not model:
        try:
            models = list_available_models(provider, api_key)
            if not models:
                raise ValueError(f"No models available for {provider}")
            model = choose_model(models)
        except Exception as e:
            raise ValueError(f"Error selecting model: {str(e)}")
    print(f"Using model: {model}")
    
    # Update configuration
    _CURRENT_CONFIG = {
        "provider": provider,
        "api_key": api_key,
        "model": model
    }
    
    return provider, api_key, model

def call_llm(prompt: str, model: Optional[str] = None, 
             provider: Optional[str] = None, api_key: Optional[str] = None,
             temperature: float = 0.7, max_tokens: Optional[int] = None) -> str:
    """
    Call an LLM with the given prompt.
    
    Args:
        prompt: The prompt to send to the LLM
        model: The model to use (if None, will use a default or last configured model)
        provider: The provider to use (if None, will use a default or last configured provider)
        api_key: The API key to use (if None, will use a default or last configured API key)
        temperature: Controls randomness (lower is more deterministic)
        max_tokens: Maximum number of tokens to generate
        
    Returns:
        The LLM's response text
    """
    global _CURRENT_CONFIG
    
    # Use configured values if not provided
    if not provider and not model and not api_key:
        if not _CURRENT_CONFIG:
            # If no configuration exists, prompt the user to set one up
            try:
                provider, api_key, model = setup_llm_provider()
                _CURRENT_CONFIG = {
                    "provider": provider,
                    "api_key": api_key,
                    "model": model
                }
            except Exception as e:
                raise RuntimeError(f"Failed to set up LLM provider: {str(e)}")
        else:
            provider = _CURRENT_CONFIG["provider"]
            api_key = _CURRENT_CONFIG["api_key"]
            model = _CURRENT_CONFIG["model"]
    else:
        # If any parameter was explicitly provided, use it
        provider = provider or _CURRENT_CONFIG.get("provider")
        api_key = api_key or _CURRENT_CONFIG.get("api_key")
        model = model or _CURRENT_CONFIG.get("model")
        
        # Update the current configuration
        if provider and api_key and model:
            _CURRENT_CONFIG = {
                "provider": provider,
                "api_key": api_key,
                "model": model
            }
    
    # Validate we have all required parameters
    if not provider:
        raise ValueError("Provider is required")
    if not api_key:
        raise ValueError("API key is required")
    if not model:
        raise ValueError("Model is required")
    
    try:
        if provider == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
            
        elif provider == "anthropic":
            from anthropic import Anthropic
            client = Anthropic(api_key=api_key)
            response = client.messages.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens or 4096
            )
            return response.content[0].text
            
        elif provider == "google":
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                
                try:
                    model_obj = genai.GenerativeModel(
                        model_name=model,
                        generation_config={
                            "temperature": temperature,
                            "max_output_tokens": max_tokens,
                        }
                    )
                    response = model_obj.generate_content(prompt)
                    return response.text
                except Exception as api_error:
                    error_message = str(api_error)
                    if "Invalid API key" in error_message:
                        raise ValueError(f"Invalid Google API key: {error_message}")
                    elif "not found" in error_message and "model" in error_message.lower():
                        raise ValueError(f"Model '{model}' not found or not accessible: {error_message}")
                    else:
                        raise RuntimeError(f"Error calling Google Gemini API: {error_message}")
            except ImportError:
                raise ImportError("Google Generative AI package is not installed or not accessible. Please install it with 'pip install google-generativeai'")
            except Exception as e:
                raise RuntimeError(f"Unexpected error with Google Gemini: {str(e)}")
                
        elif provider == "openrouter":
            import requests
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature
            }
            if max_tokens:
                data["max_tokens"] = max_tokens
                
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data
            )
            if response.status_code != 200:
                raise ValueError(f"OpenRouter API request failed with status code: {response.status_code}")
                
            result = response.json()
            return result["choices"][0]["message"]["content"]
            
        else:
            raise ValueError(f"Unknown provider: {provider}")
            
    except Exception as e:
        raise RuntimeError(f"LLM call failed: {str(e)}")

def stream_llm(prompt: str, callback_fn: Callable[[str], None], 
               model: Optional[str] = None, provider: Optional[str] = None, 
               api_key: Optional[str] = None, temperature: float = 0.7,
               max_tokens: Optional[int] = None) -> str:
    """
    Stream from an LLM with the given prompt, calling callback_fn with each chunk.
    
    Args:
        prompt: The prompt to send to the LLM
        callback_fn: Function to call with each chunk of the response
        model: The model to use (if None, will use a default or last configured model)
        provider: The provider to use (if None, will use a default or last configured provider)
        api_key: The API key to use (if None, will use a default or last configured API key)
        temperature: Controls randomness (lower is more deterministic)
        max_tokens: Maximum number of tokens to generate
        
    Returns:
        The full LLM response text
    """
    global _CURRENT_CONFIG
    
    # Use configured values if not provided
    if not provider and not model and not api_key:
        if not _CURRENT_CONFIG:
            # If no configuration exists, prompt the user to set one up
            try:
                provider, api_key, model = setup_llm_provider()
                _CURRENT_CONFIG = {
                    "provider": provider,
                    "api_key": api_key,
                    "model": model
                }
            except Exception as e:
                raise RuntimeError(f"Failed to set up LLM provider: {str(e)}")
        else:
            provider = _CURRENT_CONFIG["provider"]
            api_key = _CURRENT_CONFIG["api_key"]
            model = _CURRENT_CONFIG["model"]
    else:
        # If any parameter was explicitly provided, use it
        provider = provider or _CURRENT_CONFIG.get("provider")
        api_key = api_key or _CURRENT_CONFIG.get("api_key")
        model = model or _CURRENT_CONFIG.get("model")
        
        # Update the current configuration
        if provider and api_key and model:
            _CURRENT_CONFIG = {
                "provider": provider,
                "api_key": api_key,
                "model": model
            }
    
    # Validate we have all required parameters
    if not provider:
        raise ValueError("Provider is required")
    if not api_key:
        raise ValueError("API key is required")
    if not model:
        raise ValueError("Model is required")
    
    full_response = ""
    
    try:
        if provider == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            stream = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    callback_fn(content)
                    full_response += content
                    
        elif provider == "anthropic":
            from anthropic import Anthropic
            client = Anthropic(api_key=api_key)
            stream = client.messages.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens or 4096,
                stream=True
            )
            
            for chunk in stream:
                if chunk.delta.text:
                    callback_fn(chunk.delta.text)
                    full_response += chunk.delta.text
                    
        elif provider == "google":
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                
                model_obj = genai.GenerativeModel(
                    model_name=model,
                    generation_config={
                        "temperature": temperature,
                        "max_output_tokens": max_tokens
                    }
                )
                
                response = model_obj.generate_content(
                    prompt,
                    stream=True
                )
                
                for chunk in response:
                    if hasattr(chunk, 'text') and chunk.text:
                        callback_fn(chunk.text)
                        full_response += chunk.text
                        
            except ImportError:
                raise RuntimeError("Google Generative AI package is not installed. Please install it with 'pip install google-generativeai'")
                
        elif provider == "openrouter":
            # OpenRouter doesn't support streaming directly in the Python API,
            # So we'll use the requests library and handle the SSE stream ourselves
            import requests
            import json
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream"
            }
            
            data = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "stream": True
            }
            
            if max_tokens:
                data["max_tokens"] = max_tokens
                
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data,
                stream=True
            )
            
            if response.status_code != 200:
                raise ValueError(f"OpenRouter API request failed with status code: {response.status_code}")
                
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data = line[6:]  # Remove the 'data: ' prefix
                        if data == "[DONE]":
                            break
                        try:
                            json_data = json.loads(data)
                            content = json_data['choices'][0]['delta'].get('content', '')
                            if content:
                                callback_fn(content)
                                full_response += content
                        except json.JSONDecodeError:
                            pass  # Ignore invalid JSON
                            
        else:
            raise ValueError(f"Unknown provider: {provider}")
            
    except Exception as e:
        raise RuntimeError(f"LLM streaming failed: {str(e)}")
        
    return full_response

if __name__ == "__main__":
    # Test the functions
    print("Testing LLM call...")
    test_prompt = "What is the meaning of life in one sentence?"
    response = call_llm(test_prompt, max_tokens=50)
    print(f"Response: {response}") 