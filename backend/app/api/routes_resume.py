from fastapi import APIRouter, UploadFile, Form, HTTPException
import spacy
import re
import PyPDF2
import pdfplumber
from io import BytesIO

router = APIRouter()
nlp = spacy.load("en_core_web_sm")

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
    Extract technical keywords from job postings and resumes.
    Focus on technologies, tools, frameworks, and specific technical skills.
    """
    if not text or not text.strip():
        return set()
    
    keywords = set()
    text_lower = text.lower()
    
    # Extract exact technical terms (single words and multi-word)
    for term in TECHNICAL_TERMS:
        # Handle multi-word terms differently
        if ' ' in term or '-' in term:
            # For multi-word terms, use a more flexible pattern
            pattern = re.escape(term).replace(r'\ ', r'[\s\-]+')
            if re.search(pattern, text_lower):
                keywords.add(term)
        else:
            # For single words, use word boundaries
            pattern = r'\b' + re.escape(term) + r'\b'
            if re.search(pattern, text_lower):
                keywords.add(term)
    
    # Extract multi-word technical phrases
    for phrase in TECHNICAL_PHRASES:
        # Allow for slight variations (hyphens, spaces)
        pattern = re.escape(phrase).replace(r'\ ', r'[\s\-]+')
        if re.search(pattern, text_lower):
            keywords.add(phrase)
    
    # Extract programming languages with special characters
    special_patterns = {
        r'\bc\+\+\b': 'c++',
        r'\bc#\b': 'c#',
        r'\b\.net\b': '.net',
        r'\bnode\.js\b': 'nodejs',
    }
    for pattern, term in special_patterns.items():
        if re.search(pattern, text_lower):
            keywords.add(term)
    
    # Extract version numbers with technologies (e.g., "Python 3.x", "Java 11")
    tech_version_pattern = r'\b(python|java|node|go|rust|ruby|php)\s*\d+(?:\.\d+)?(?:\.\d+)?'
    for match in re.finditer(tech_version_pattern, text_lower):
        tech_name = match.group(1)
        keywords.add(tech_name)
    
    # Extract acronyms (2-5 uppercase letters, technical sounding)
    acronyms = re.findall(r'\b[A-Z]{2,5}\b', text)
    known_acronyms = {'api', 'sdk', 'ide', 'orm', 'mvc', 'mvvm', 'crud', 'cicd', 
                      'aws', 'gcp', 'sql', 'nosql', 'rest', 'soap', 'grpc',
                      'iot', 'pcb', 'fpga', 'dsp', 'rtos', 'hal', 'ecu', 'can',
                      'tcp', 'udp', 'http', 'https', 'ssh', 'ftp', 'smtp',
                      'jwt', 'oauth', 'saml', 'ldap', 'tdd', 'bdd'}
    
    for acro in acronyms:
        acro_lower = acro.lower()
        # Only add if it's a known technical acronym
        if acro_lower in known_acronyms or acro_lower in TECHNICAL_TERMS:
            keywords.add(acro_lower)
    
    # Use spaCy for NLP-based extraction
    doc = nlp(text_lower)
    
    # Extract noun chunks ONLY if they match known technical phrases
    # This is much more conservative - only extract exact matches
    for chunk in doc.noun_chunks:
        chunk_text = chunk.text.strip()
        
        # Skip short or very long chunks
        if len(chunk_text) < 3 or len(chunk_text) > 50:
            continue
        
        # Clean the chunk and lowercase
        clean_chunk = re.sub(r'[^\w\s-]', '', chunk_text.lower().strip())
        
        # ONLY add if it's a known technical phrase (exact match)
        if clean_chunk in TECHNICAL_PHRASES:
            keywords.add(clean_chunk)
    
    # Extract individual technical nouns - ONLY known technical terms
    for token in doc:
        # Skip non-alphabetic, short tokens, and stop words
        if not token.is_alpha or len(token.text) < 3 or token.is_stop:
            continue
        
        lemma = token.lemma_.lower()
        
        # Skip if it's in ignore list
        if lemma in IGNORE_WORDS:
            continue
        
        # ONLY keep nouns and proper nouns that are KNOWN technical terms
        if token.pos_ in {"NOUN", "PROPN"}:
            # Only add if it's a known technical term - no guessing!
            if lemma in TECHNICAL_TERMS:
                keywords.add(lemma)
    
    # Final cleanup - be very strict
    keywords = {
        kw.strip().lower() for kw in keywords 
        if kw.strip() 
        and len(kw.strip()) >= 2
        and kw.strip().lower() not in IGNORE_WORDS
        and not re.match(r'^\d+$', kw.strip())  # Remove pure numbers
        and not any(word in IGNORE_WORDS for word in kw.strip().lower().split())  # Remove if contains ignore words
    }
    
    # Final filter: only keep if it's in our known technical terms/phrases or is a known acronym
    final_keywords = set()
    known_acronyms_lower = {a.lower() for a in known_acronyms}
    
    for kw in keywords:
        kw_lower = kw.lower()
        # Keep if it's a known technical term, phrase, or acronym
        if (kw_lower in TECHNICAL_TERMS or 
            kw_lower in TECHNICAL_PHRASES or 
            kw_lower in known_acronyms_lower):
            final_keywords.add(kw_lower)
    
    return final_keywords

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
    # Read uploaded resume
    file_content = await resume.read()
    
    # Check file type and extract text accordingly
    file_extension = resume.filename.split('.')[-1].lower() if resume.filename else ''
    
    if file_extension == 'pdf':
        resume_text = extract_text_from_pdf(file_content)
    elif file_extension in ['txt', 'text']:
        resume_text = file_content.decode("utf-8", errors="ignore")
    else:
        # Try to decode as text first, if that fails try PDF
        try:
            resume_text = file_content.decode("utf-8", errors="ignore")
        except:
            try:
                resume_text = extract_text_from_pdf(file_content)
            except:
                raise HTTPException(
                    status_code=400,
                    detail="Could not extract text from file. Please upload a PDF or TXT file."
                )

    # Extract keywords using NLP
    resume_kw = extract_keywords(resume_text)
    job_kw = extract_keywords(job_text)
    
    # Extract "or" groups from job posting
    all_technical_terms = TECHNICAL_TERMS | TECHNICAL_PHRASES
    or_groups = extract_or_groups(job_text, job_kw)
    
    # Match keywords accounting for "or" groups
    common, missing, matched_groups = match_with_or_groups(resume_kw, job_kw, or_groups)
    
    # Calculate score: count each "or" group as 1 requirement, not multiple
    # Regular keywords count as 1 each, "or" groups count as 1 total
    total_requirements = len(job_kw)
    # Subtract keywords that are in "or" groups and add back the groups (counted as 1 each)
    keywords_in_groups = set()
    for group in or_groups:
        keywords_in_groups.update(group)
    
    # Adjust total: remove individual keywords that are in groups, add groups
    adjusted_total = total_requirements - len(keywords_in_groups) + len(or_groups)
    
    # Count matched: regular matches + matched groups
    matched_regular = len(common - keywords_in_groups)
    matched_group_count = len(matched_groups)
    total_matched = matched_regular + matched_group_count
    
    score = int((total_matched / adjusted_total) * 100) if adjusted_total > 0 else 0

    print("\n=== Job Keywords ===")
    print(sorted(job_kw))
    print("\n=== Resume Keywords ===")
    print(sorted(resume_kw))
    print("\n=== Common Keywords ===")
    print(sorted(common))
    print("\n=== Missing Keywords ===")
    print(sorted(missing))
    print("\n=== OR Groups Found ===")
    for i, group in enumerate(or_groups, 1):
        print(f"Group {i}: {sorted(group)}")
    print("\n=== Matched OR Groups ===")
    for i, group in enumerate(matched_groups, 1):
        print(f"Group {i}: {sorted(group)}")

    return {
        "match_score": score,
        "missing_keywords": sorted(list(missing)),
        "job_keywords": sorted(list(job_kw)),
        "resume_keywords": sorted(list(resume_kw)),
        "matched_keywords": sorted(list(common)),
        "total_job_keywords": len(job_kw),
        "total_resume_keywords": len(resume_kw),
        "total_matched": len(common),
    }