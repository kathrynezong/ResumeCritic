from fastapi import APIRouter, UploadFile, Form, HTTPException
import re
import pdfplumber
from io import BytesIO
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import google.genai as genai
import os
from dotenv import load_dotenv
import json

load_dotenv()

router = APIRouter()

# Load semantic similarity model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Initialize Google Gemini client
try:
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        client = genai.Client(api_key=api_key)
        gemini_model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        LLM_ENABLED = True
    else:
        client = None
        gemini_model_name = None
        LLM_ENABLED = False
except Exception as e:
    print(f"Gemini not configured: {e}")
    client = None
    gemini_model_name = None
    LLM_ENABLED = False

# Known programming languages and technologies
# Combined list of all technical terms (single words and multi-word phrases)
TECHNICAL_TERMS = {
    # Programming languages
    "python", "java", "javascript", "typescript", "c++", "c#", "cpp", "c",
    "go", "golang", "rust", "ruby", "php", "swift", "kotlin", "scala",
    "r", "matlab", "perl", "shell", "bash", "powershell", "sql",
    
    # Frameworks and libraries
    "react", "angular", "vue", "django", "flask", "fastapi", "express", "spring",
    "node", "nodejs", "tensorflow", "pytorch", "keras", "pandas", "numpy",
    "scikit-learn", "opencv", "matplotlib", "seaborn",
    
    # Technologies and platforms
    "aws", "azure", "gcp", "docker", "kubernetes", "k8s", "jenkins", "git",
    "github", "gitlab", "bitbucket", "jira", "confluence",
    "linux", "unix", "windows", "android", "ios", "macos",
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "cassandra",
    "kafka", "rabbitmq", "nginx", "apache",
    
    # Embedded and hardware
    "rtos", "hal", "ecu", "can", "lin", "spi", "i2c", "uart", "usb",
    "embedded", "microcontroller", "fpga", "arm", "cortex", "x86",
    "firmware", "bootloader", "device driver",
    "embedded linux", "embedded software", "real-time operating system",
    "hardware abstraction layer", "kernel space", "user space",
    
    # Automotive and protocols
    "autosar", "misra", "iso26262", "aspice", "functional safety",
    "adas", "v2x", "obd", "diagnostics", "automotive communication",
    
    # Development practices
    "agile", "scrum", "kanban", "devops", "cicd", "tdd", "bdd",
    "unit testing", "integration testing", "test automation",
    "code review", "version control", "continuous integration", "continuous deployment",
    "test driven development", "behavior driven development", "agile methodology",
    "version control system", "source code management", "build automation",
    "configuration management", "release management", "technical documentation",
    
    # Cloud and architecture
    "microservices", "api", "rest", "graphql", "grpc", "soap",
    "serverless", "lambda", "containerization", "orchestration",
    "software architecture", "design patterns", "object oriented",
    "software development", "full stack", "back end", "front end",
    "system design", "distributed system", "cloud computing", "edge computing",
    
    # Acronyms and abbreviations
    "sdk", "ide", "orm", "mvc", "crud", "iot", "pcb",
    "tcp", "udp", "http", "https", "ssh",
    
    # Data and ML
    "machine learning", "deep learning", "neural network", "nlp",
    "computer vision", "data analysis", "data science", "big data",
    "etl", "data pipeline", "data warehouse",
    
    # Security
    "encryption", "authentication", "authorization", "oauth", "jwt",
    "penetration testing", "vulnerability assessment", "cybersecurity",
    
    # Education and concepts
    "data structure", "algorithm", "computer science", "electrical engineering",
    "computer engineering", "software engineering",
    "performance optimization", "memory management", "multithreading", "concurrency",
}

def extract_keywords(text: str):
    """
    Extract technical keywords - simplified regex-based extraction
    """
    if not text or not text.strip():
        return set()
    
    keywords = set()
    text_lower = text.lower()
    
    # Extract technical terms (handles both single words and multi-word phrases)
    for term in TECHNICAL_TERMS:
        if ' ' in term or '-' in term:
            # Multi-word terms: allow spaces or hyphens
            pattern = re.escape(term).replace(r'\ ', r'[\s\-]+')
            if re.search(pattern, text_lower):
                keywords.add(term)
        else:
            # Single-word terms: use word boundaries
            pattern = r'\b' + re.escape(term) + r'\b'
            if re.search(pattern, text_lower):
                keywords.add(term)
    
    # Extract special patterns
    special_patterns = {
        r'\bc\+\+\b': 'c++',
        r'\bc#\b': 'c#',
        r'\b\.net\b': '.net',
        r'\bnode\.js\b': 'nodejs',
    }
    for pattern, term in special_patterns.items():
        if re.search(pattern, text_lower):
            keywords.add(term)
    
    # Extract acronyms (2-5 uppercase letters)
    # Only match uppercase to avoid false positives like "can" (verb)
    acronyms = re.findall(r'\b[A-Z]{2,5}\b', text)
    for acro in acronyms:
        acro_lower = acro.lower()
        # Check if the acronym is in our technical terms list
        if acro_lower in TECHNICAL_TERMS:
            keywords.add(acro_lower)
    
    return keywords

def compute_semantic_similarity(text1: str, text2: str) -> float:
    """
    Compute semantic similarity between two texts using sentence transformers
    Returns similarity score between 0 and 1
    """
    if not text1.strip() or not text2.strip():
        return 0.0
    
    embeddings = model.encode([text1, text2])
    similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
    return float(similarity)

def analyze_with_gpt(resume_text: str, job_text: str) -> dict:
    """
    Use Google Gemini to analyze resume-job fit with consistent criteria
    Returns structured analysis with score and feedback
    """
    if not LLM_ENABLED or not client or not gemini_model_name:
        return {"enabled": False, "error": "Gemini analysis not configured"}
    
    prompt = f"""You are an expert HR recruiter. Analyze how well this resume matches the job requirements.

JOB DESCRIPTION:
{job_text}

RESUME:
{resume_text}

Evaluate the candidate on these criteria (score each 0-100):
1. Technical Skills Match: Required technical skills and tools
2. Experience Level: Years and type of experience required
3. Education & Qualifications: Degree and certifications
4. Domain Knowledge: Industry-specific knowledge
5. Overall Fit: Cultural fit and soft skills

Provide your response in this exact JSON format (keep all text concise - max 50 chars per strength/gap, 150 chars for summary):
{{
  "technical_skills": <score 0-100>,
  "experience_level": <score 0-100>,
  "education": <score 0-100>,
  "domain_knowledge": <score 0-100>,
  "overall_fit": <score 0-100>,
  "overall_score": <average score 0-100>,
  "strengths": ["strength1", "strength2", "strength3"],
  "gaps": ["gap1", "gap2", "gap3"],
  "recommendation": "<STRONG_MATCH|GOOD_MATCH|PARTIAL_MATCH|WEAK_MATCH>",
  "summary": "<2-3 sentence summary, max 150 characters>"
}}

IMPORTANT: Return ONLY valid JSON. No markdown, no code blocks, no explanations. Start with {{ and end with }}. Keep all strings short."""
    
    try:
        response = client.models.generate_content(
            model=gemini_model_name,
            contents=prompt,
            config={
                "temperature": 0.3,
                "max_output_tokens": 2000,  # Increased to handle longer responses
            }
        )
        
        # Get the full response text - handle different response formats
        if hasattr(response, 'text'):
            content = response.text.strip()
        elif hasattr(response, 'candidates') and len(response.candidates) > 0:
            # Alternative response format
            content = response.candidates[0].content.parts[0].text.strip()
        elif hasattr(response, 'content'):
            content = response.content.strip()
        else:
            # Try to convert to string
            content = str(response).strip()
        
        # Debug: Check if response seems truncated
        if len(content) < 100:
            print(f"Warning: Response seems very short ({len(content)} chars)")
        
        # Extract JSON from response - handle various formats
        if "```json" in content:
            # Extract content between ```json and ```
            parts = content.split("```json")
            if len(parts) > 1:
                content = parts[1].split("```")[0].strip()
        elif "```" in content:
            # Extract content between ``` and ```
            parts = content.split("```")
            if len(parts) > 1:
                content = parts[1].split("```")[0].strip()
        
        # Try to find JSON object boundaries if not already extracted
        if not content.startswith("{"):
            start_idx = content.find("{")
            if start_idx != -1:
                content = content[start_idx:]
        
        # Find the matching closing brace - handle nested objects and strings properly
        brace_count = 0
        in_string = False
        escape_next = False
        end_idx = -1
        
        for i, char in enumerate(content):
            if escape_next:
                escape_next = False
                continue
            
            if char == "\\":
                escape_next = True
                continue
            
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            
            if not in_string:
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i + 1
                        break
        
        if end_idx != -1:
            content = content[:end_idx]
        else:
            # If we couldn't find the end, the JSON might be incomplete
            # Try to close it manually by adding missing closing braces/brackets
            open_braces = content.count('{') - content.count('}')
            open_brackets = content.count('[') - content.count(']')
            
            # If we're in the middle of a string, try to close it
            if in_string:
                content += '"'
                in_string = False
            
            # Close any open arrays
            for _ in range(open_brackets):
                content += ']'
            
            # Close any open objects
            for _ in range(open_braces):
                content += '}'
        
        # Clean up any trailing commas or whitespace before parsing
        content = content.rstrip().rstrip(',')
        
        # Parse JSON
        result = json.loads(content)
        result["enabled"] = True
        return result
        
    except json.JSONDecodeError as e:
        print(f"Gemini JSON parsing error: {e}")
        print(f"Response content (first 2000 chars): {content[:2000]}")
        print(f"Response length: {len(content)}")
        print(f"Last 200 chars: {content[-200:]}")
        
        # Try to fix common JSON issues
        try:
            import re
            # Remove trailing commas
            fixed_content = re.sub(r',\s*}', '}', content)
            fixed_content = re.sub(r',\s*]', ']', fixed_content)
            
            # If response seems truncated, try to close it
            open_braces = fixed_content.count('{') - fixed_content.count('}')
            open_brackets = fixed_content.count('[') - fixed_content.count(']')
            
            # Close incomplete strings at the end
            if fixed_content.rstrip().endswith('"') == False and '"' in fixed_content:
                # Find last unclosed quote
                last_quote = fixed_content.rfind('"')
                if last_quote > len(fixed_content) - 50:  # Near the end
                    # Check if it's an open string
                    before_quote = fixed_content[:last_quote]
                    if before_quote.count('"') % 2 == 1:  # Odd number means unclosed
                        fixed_content = fixed_content[:last_quote] + '"' + fixed_content[last_quote+1:]
            
            # Close arrays and objects
            for _ in range(open_brackets):
                fixed_content += ']'
            for _ in range(open_braces):
                fixed_content += '}'
            
            result = json.loads(fixed_content)
            result["enabled"] = True
            return result
        except Exception as fix_error:
            print(f"Failed to fix JSON: {fix_error}")
            return {"enabled": False, "error": f"Failed to parse AI response (truncated?): {str(e)}"}
    except Exception as e:
        print(f"Gemini analysis error: {e}")
        return {"enabled": False, "error": str(e)}

def extract_or_groups(text: str, all_keywords: set) -> list:
    """
    Extract groups of keywords connected by "or" (e.g., "Python or Java").
    Returns a list of sets, where each set contains alternative keywords.
    """
    or_groups = []
    text_lower = text.lower()
    
    # Pattern to match "X or Y" or "X, Y, or Z" where X, Y, Z are technical terms
    # Look for patterns like: "Python or Java", "C++ or C", "Linux/Android or RTOS"
    or_patterns = [
        r'\b(\w+(?:\s+\w+)?)\s+or\s+(\w+(?:\s+\w+)?)',  # "X or Y"
        r'\b(\w+(?:\s+\w+)?)\s*/\s*(\w+(?:\s+\w+)?)\s+or\s+(\w+(?:\s+\w+)?)',  # "X/Y or Z"
        r'\b(\w+(?:\s+\w+)?)\s*,\s*(\w+(?:\s+\w+)?)\s*,\s*or\s+(\w+(?:\s+\w+)?)',  # "X, Y, or Z"
    ]
    
    for pattern in or_patterns:
        for match in re.finditer(pattern, text_lower):
            groups = match.groups()
            # Filter to only include keywords that are in our known technical terms
            group_keywords = set()
            for g in groups:
                if g:
                    # Clean and normalize the keyword
                    clean_kw = g.strip().lower()
                    # Check if it's a known technical term or matches one
                    if clean_kw in all_keywords:
                        group_keywords.add(clean_kw)
                    else:
                        # Try to find a match in all_keywords (fuzzy match)
                        for kw in all_keywords:
                            if clean_kw in kw or kw in clean_kw:
                                group_keywords.add(kw)
                                break
            
            # Only add groups with 2+ valid keywords
            if len(group_keywords) >= 2:
                or_groups.append(group_keywords)
    
    # Also look for common "or" patterns with known technical terms
    # Find sentences/phrases with "or" and check if they contain multiple technical keywords
    sentences = re.split(r'[.!?;]', text_lower)
    for sentence in sentences:
        if ' or ' in sentence or '/ or ' in sentence:
            # Extract all technical keywords from this sentence
            sentence_keywords = {kw for kw in all_keywords if kw in sentence}
            if len(sentence_keywords) >= 2:
                # Check if they're connected by "or"
                # Simple heuristic: if sentence has "or" and multiple keywords, they might be alternatives
                words = sentence.split()
                if 'or' in words:
                    or_groups.append(sentence_keywords)
    
    # Remove duplicates and subsets
    unique_groups = []
    for group in or_groups:
        # Check if this group is a subset of another group
        is_subset = False
        for existing_group in unique_groups:
            if group.issubset(existing_group):
                is_subset = True
                break
            if existing_group.issubset(group):
                # Replace the smaller group with the larger one
                unique_groups.remove(existing_group)
                unique_groups.append(group)
                is_subset = True
                break
        if not is_subset and group not in unique_groups:
            unique_groups.append(group)
    
    return unique_groups

def match_with_or_groups(resume_keywords: set, job_keywords: set, or_groups: list) -> tuple:
    """
    Match keywords accounting for "or" groups.
    If any keyword in an "or" group is found, the whole group counts as matched.
    Returns: (matched_keywords, missing_keywords, matched_groups)
    """
    matched = resume_keywords & job_keywords
    matched_groups = []
    
    # Check each "or" group
    for group in or_groups:
        # If any keyword in the group is in resume, the group is matched
        group_in_resume = any(kw in resume_keywords for kw in group)
        group_in_job = any(kw in job_keywords for kw in group)
        
        if group_in_job and group_in_resume:
            # At least one keyword from this group is in both resume and job
            matched_groups.append(group)
            # Add all keywords from the group to matched (even if not all are in resume)
            matched.update(group)
    
    # Remove keywords that are part of matched "or" groups from missing
    missing = job_keywords - resume_keywords
    for group in matched_groups:
        # If the group is matched, remove its keywords from missing
        missing = missing - group
    
    return matched, missing, matched_groups

def extract_text_from_pdf(file_content: bytes) -> str:
    """
    Extract text from PDF file content using pdfplumber.
    """
    text = ""
    
    try:
        with pdfplumber.open(BytesIO(file_content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Could not extract text from PDF: {str(e)}"
        )
    
    if not text.strip():
        raise HTTPException(
            status_code=400,
            detail="PDF appears to be empty or contains no extractable text"
        )
    
    return text

@router.post("/analyze")
async def analyze_resume(resume: UploadFile, job_text: str = Form(...)):
    file_content = await resume.read()
    file_extension = resume.filename.split('.')[-1].lower() if resume.filename else ''
    
    if file_extension == 'pdf':
        resume_text = extract_text_from_pdf(file_content)
    elif file_extension in ['txt', 'text']:
        resume_text = file_content.decode("utf-8", errors="ignore")
    else:
        raise HTTPException(status_code=400, detail="Could not extract text from file")

    # Keyword-based matching
    resume_kw = extract_keywords(resume_text)
    job_kw = extract_keywords(job_text)
    or_groups = extract_or_groups(job_text, job_kw)
    common, missing, matched_groups = match_with_or_groups(resume_kw, job_kw, or_groups)
    
    # Calculate keyword score
    keywords_in_groups = set()
    for group in or_groups:
        keywords_in_groups.update(group)
    
    adjusted_total = len(job_kw) - len(keywords_in_groups) + len(or_groups)
    matched_regular = len(common - keywords_in_groups)
    total_matched = matched_regular + len(matched_groups)
    keyword_score = int((total_matched / adjusted_total) * 100) if adjusted_total > 0 else 0

    # Semantic similarity score
    semantic_score = compute_semantic_similarity(resume_text, job_text) * 100
    
    # Gemini LLM analysis
    gpt_analysis = analyze_with_gpt(resume_text, job_text)
    
    # Combined score (50% semantic, 30% keyword, 20% GPT if available)
    if gpt_analysis.get("enabled"):
        final_score = int(semantic_score * 0.5 + keyword_score * 0.3 + gpt_analysis["overall_score"] * 0.2)
    else:
        final_score = int(semantic_score * 0.7 + keyword_score * 0.3)

    return {
        "match_score": final_score,
        "semantic_score": round(semantic_score, 1),
        "keyword_score": keyword_score,
        "gpt_analysis": gpt_analysis,
        "missing_keywords": sorted(list(missing)),
        "matched_keywords": sorted(list(common)),
        "job_keywords": sorted(list(job_kw)),
        "resume_keywords": sorted(list(resume_kw)),
    }