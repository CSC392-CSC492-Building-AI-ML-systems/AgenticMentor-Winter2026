"""Test Gemini API connectivity and available models."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv

load_dotenv()


def test_api_key():
    """Test that API key is available."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not found in environment")
        sys.exit(1)

    print(f"API Key found: {api_key[:10]}...")


def test_langchain_model():
    """Test Gemini model with langchain-google-genai."""
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        api_key = os.getenv("GEMINI_API_KEY")
        model_name = os.getenv("MODEL_NAME", "gemini-flash-latest")
        
        print(f"\nTesting {model_name} with langchain-google-genai...")
        
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=0.7,
        )
        
        response = llm.invoke("Say hello in one word")
        print(f"Response: {response.content}")
        print("Test passed!")
        
    except Exception as e:
        print(f"Test failed: {e}")
        sys.exit(1)


def test_model_availability():
    """Test which models are available (using new google.genai package)."""
    try:
        import google.genai as genai
        from google.genai import types
        
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key)
        
        print("\nAvailable models:")
        models = client.models.list()
        for model in models:
            print(f"  - {model.name}")
            
    except ImportError:
        print("\ngoogle-genai package not installed")
        print("Install with: pip install google-genai")
    except Exception as e:
        print(f"Could not list models: {e}")


if __name__ == "__main__":
    print("Testing Gemini API Configuration\n")
    print("=" * 50)
    
    test_api_key()
    test_langchain_model()
    test_model_availability()
    
    print("\n" + "=" * 50)
    print("All tests completed!")