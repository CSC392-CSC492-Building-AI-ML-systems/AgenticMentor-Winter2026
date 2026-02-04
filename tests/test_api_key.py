"""
Simple test to verify your Gemini API key works.
Run: python tests/test_api_key.py
"""
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ GEMINI_API_KEY not found in .env")
    exit(1)

print(f"Testing API key: {api_key[:10]}...{api_key[-5:]}")
print()

try:
    # Configure the API
    genai.configure(api_key=api_key)
    
    # List available models
    print("Available models:")
    for model in genai.list_models():
        if 'generateContent' in model.supported_generation_methods:
            print(f"  ✅ {model.name}")
    
    print()
    
    # Try a simple generation with an available model
    print("Testing generation...")
    model = genai.GenerativeModel('gemini-flash-latest')
    response = model.generate_content("Say 'Hello'")
    print(f"✅ Response: {response.text}")
    print()
    print("🎉 API key works! Use 'gemini-flash-latest' in your .env file")
    
except Exception as e:
    print(f"Error: {e}")
    print()
    print("Check:")
    print("1. API key is correct in .env")
    print("2. API key has Gemini API access enabled")
    print("3. You have quota remaining")
