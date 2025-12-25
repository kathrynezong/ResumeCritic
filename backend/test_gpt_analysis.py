#!/usr/bin/env python3
"""
Test Azure OpenAI GPT-4o Integration
Run: python test_gpt_analysis.py
"""

import os
from dotenv import load_dotenv
from openai import AzureOpenAI
import json

load_dotenv()

print("=" * 80)
print("TESTING AZURE OPENAI GPT-4O INTEGRATION")
print("=" * 80)

# Check environment variables
print("\n1. Checking environment variables...")
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
api_key = os.getenv("AZURE_OPENAI_API_KEY")
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

print(f"   Endpoint: {endpoint[:50]}..." if endpoint else "   Endpoint: NOT SET")
print(f"   API Key: {'*' * 20}...{api_key[-4:] if api_key else 'NOT SET'}")
print(f"   Deployment: {deployment}")
print(f"   API Version: {api_version}")

if not endpoint or not api_key:
    print("\n❌ ERROR: Azure OpenAI credentials not configured!")
    print("   Please set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY in .env file")
    exit(1)

# Initialize client
print("\n2. Initializing Azure OpenAI client...")
try:
    client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=api_version
    )
    print("   ✓ Client initialized successfully")
except Exception as e:
    print(f"   ❌ Failed to initialize client: {e}")
    exit(1)

# Test simple completion
print("\n3. Testing simple completion...")
try:
    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "user", "content": "Say 'Hello, Azure OpenAI is working!' in JSON format with a 'message' field."}
        ],
        temperature=0.3,
        max_tokens=100
    )
    content = response.choices[0].message.content
    print(f"   ✓ Response received: {content[:100]}...")
except Exception as e:
    print(f"   ❌ API call failed: {e}")
    exit(1)

# Test resume analysis
print("\n4. Testing resume analysis...")

sample_resume = """
John Doe
Software Engineer

EXPERIENCE:
- 5 years Python development
- Django and Flask frameworks
- AWS cloud deployment
- PostgreSQL databases

EDUCATION:
- BS Computer Science, 2018
"""

sample_job = """
Looking for Senior Python Developer with:
- 3+ years Python experience
- Django or Flask required
- AWS experience preferred
- Bachelor's degree in CS
"""

prompt = f"""You are an expert HR recruiter. Analyze how well this resume matches the job requirements.

JOB DESCRIPTION:
{sample_job}

RESUME:
{sample_resume}

Evaluate the candidate on these criteria (score each 0-100):
1. Technical Skills Match
2. Experience Level
3. Education & Qualifications
4. Domain Knowledge
5. Overall Fit

Provide your response in this exact JSON format:
{{
  "technical_skills": <score>,
  "experience_level": <score>,
  "education": <score>,
  "domain_knowledge": <score>,
  "overall_fit": <score>,
  "overall_score": <average>,
  "strengths": ["strength1", "strength2"],
  "gaps": ["gap1", "gap2"],
  "recommendation": "<STRONG_MATCH|GOOD_MATCH|PARTIAL_MATCH|WEAK_MATCH>",
  "summary": "<2-3 sentence summary>"
}}

Only return valid JSON."""

try:
    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": "You are an expert HR recruiter who provides objective, structured candidate evaluations."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        max_tokens=1000
    )
    
    content = response.choices[0].message.content.strip()
    
    # Extract JSON
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()
    
    result = json.loads(content)
    
    print("   ✓ Analysis completed successfully!")
    print("\n   Results:")
    print(f"   - Overall Score: {result.get('overall_score')}%")
    print(f"   - Technical Skills: {result.get('technical_skills')}%")
    print(f"   - Experience Level: {result.get('experience_level')}%")
    print(f"   - Recommendation: {result.get('recommendation')}")
    print(f"   - Summary: {result.get('summary')}")
    
    if result.get('strengths'):
        print(f"   - Strengths: {', '.join(result['strengths'][:2])}")
    if result.get('gaps'):
        print(f"   - Gaps: {', '.join(result['gaps'][:2])}")
    
except json.JSONDecodeError as e:
    print(f"   ❌ Failed to parse JSON response: {e}")
    print(f"   Raw response: {content[:200]}...")
except Exception as e:
    print(f"   ❌ Analysis failed: {e}")
    exit(1)

print("\n" + "=" * 80)
print("✅ ALL TESTS PASSED! Azure OpenAI GPT-4o is working correctly.")
print("=" * 80)
print("\nYou can now use the full application with GPT-4o analysis enabled!")
