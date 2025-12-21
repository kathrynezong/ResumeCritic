from fastapi import APIRouter, UploadFile, Form, HTTPException
import re
import PyPDF2
import pdfplumber
from io import BytesIO
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from openai import AzureOpenAI
import os
from dotenv import load_dotenv
import json

load_dotenv()

router = APIRouter()

# Load semantic similarity model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Initialize Azure OpenAI client
try:
    azure_client = AzureOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    )
    AZURE_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
    GPT_ENABLED = True
except Exception as e:
    print(f"Azure OpenAI not configured: {e}")
    azure_client = None
    GPT_ENABLED = False

# Known programming languages and technologies
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
    
    # Automotive and protocols
    "autosar", "misra", "iso26262", "aspice", "functional safety",
    "adas", "v2x", "obd", "diagnostics",
    
    # Development practices
    "agile", "scrum", "kanban", "devops", "cicd", "tdd", "bdd",
    "unit testing", "integration testing", "test automation",
    "code review", "version control", "continuous integration",
    
    # Cloud and architecture
    "microservices", "api", "rest", "graphql", "grpc", "soap",
    "serverless", "lambda", "containerization", "orchestration",
    
    # Data and ML
    "machine learning", "deep learning", "neural network", "nlp",
    "computer vision", "data analysis", "data science", "big data",
    "etl", "data pipeline", "data warehouse",
    
    # Security
    "encryption", "authentication", "authorization", "oauth", "jwt",
    "penetration testing", "vulnerability assessment", "cybersecurity",
}

# Multi-word technical terms and patterns
TECHNICAL_PHRASES = {
    "embedded linux", "embedded software", "real-time operating system",
    "hardware abstraction layer", "device driver", "kernel space", "user space",
    "automotive communication", "functional safety", "software architecture",
    "design patterns", "object oriented", "continuous integration", "continuous deployment",
    "test driven development", "behavior driven development", "agile methodology",
    "version control system", "source code management", "build automation",
    "configuration management", "release management", "technical documentation",
    "software development", "full stack", "back end", "front end",
    "data structure", "algorithm", "computer science", "electrical engineering",
    "computer engineering", "software engineering", "system design",
    "performance optimization", "memory management", "multithreading", "concurrency",
    "distributed system", "cloud computing", "edge computing",
}

# Words to completely ignore
IGNORE_WORDS = {
    # Generic business/job terms
    "job", "position", "role", "opportunity", "career", "company", "team",
    "candidate", "employee", "work", "experience", "year", "responsibility",
    "skill", "ability", "requirement", "qualification", "education", "degree",
    "communication", "collaboration", "customer", "client", "business",
    "management", "leadership", "project", "problem", "solution", "quality",
    
    # Generic descriptive words
    "good", "great", "excellent", "strong", "effective", "efficient", "successful",
    "innovative", "creative", "dynamic", "passionate", "motivated", "detail",
    
    # Common verbs/actions
    "develop", "create", "build", "design", "implement", "maintain", "improve",
    "work", "collaborate", "communicate", "manage", "lead", "support", "provide",
    "ensure", "help", "make", "take", "give", "use", "need", "want",
    
    # Time/location
    "time", "day", "week", "month", "year", "location", "office", "remote",
    "canada", "usa", "united states",
    
    # Compensation
    "salary", "pay", "compensation", "benefit", "bonus", "stock",
    
    # Other filler
    "etc", "including", "such", "other", "various", "multiple", "related",
    "completion", "term", "application", "performance", "next", "chapter",
}

def extract_keywords(text: str):
    """
    Extract technical keywords - simplified regex-based extraction
    """
    if not text or not text.strip():
        return set()
    
    keywords = set()
    text_lower = text.lower()
    
    # Extract exact technical terms
    for term in TECHNICAL_TERMS:
        if ' ' in term or '-' in term:
            pattern = re.escape(term).replace(r'\ ', r'[\s\-]+')
            if re.search(pattern, text_lower):
                keywords.add(term)
        else:
            pattern = r'\b' + re.escape(term) + r'\b'
            if re.search(pattern, text_lower):
                keywords.add(term)
    
    # Extract multi-word technical phrases
    for phrase in TECHNICAL_PHRASES:
        pattern = re.escape(phrase).replace(r'\ ', r'[\s\-]+')
        if re.search(pattern, text_lower):
            keywords.add(phrase)
    
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
    
    # Extract acronyms
    acronyms = re.findall(r'\b[A-Z]{2,5}\b', text)
    known_acronyms = {'api', 'sdk', 'ide', 'orm', 'mvc', 'crud', 'cicd', 
                      'aws', 'gcp', 'sql', 'rest', 'grpc', 'iot', 'pcb', 
                      'fpga', 'rtos', 'hal', 'can', 'uart', 'spi', 'i2c',
                      'tcp', 'udp', 'http', 'ssh', 'jwt', 'oauth', 'tdd'}
    
    for acro in acronyms:
        acro_lower = acro.lower()
        if acro_lower in known_acronyms or acro_lower in TECHNICAL_TERMS:
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
    Use GPT-4o to analyze resume-job fit with consistent criteria
    Returns structured analysis with score and feedback
    """
    if not GPT_ENABLED or not azure_client:
        return {"enabled": False, "error": "GPT analysis not configured"}
    
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

Provide your response in this exact JSON format:
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
  "summary": "<2-3 sentence summary>"
}}

Be objective and specific. Only return valid JSON."""
    
    try:
        response = azure_client.chat.completions.create(
            model=AZURE_DEPLOYMENT,
            messages=[
                {"role": "system", "content": "You are an expert HR recruiter who provides objective, structured candidate evaluations."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        content = response.choices[0].message.content.strip()
        
        # Extract JSON from response
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        result = json.loads(content)
        result["enabled"] = True
        return result
        
    except Exception as e:
        print(f"GPT analysis error: {e}")
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
    Extract text from PDF file content.
    Tries pdfplumber first (better for complex PDFs), falls back to PyPDF2.
    """
    text = ""
    
    # Try pdfplumber first (better text extraction)
    try:
        with pdfplumber.open(BytesIO(file_content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"pdfplumber failed: {e}, trying PyPDF2...")
        # Fallback to PyPDF2
        try:
            pdf_file = BytesIO(file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        except Exception as e2:
            print(f"PyPDF2 also failed: {e2}")
            raise HTTPException(
                status_code=400,
                detail=f"Could not extract text from PDF: {str(e2)}"
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
        # try:
        #     resume_text = file_content.decode("utf-8", errors="ignore")
        # except:
        #     try:
        #         resume_text = extract_text_from_pdf(file_content)
        #     except:
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
    
    # GPT-4o analysis
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