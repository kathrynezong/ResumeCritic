"""
routes_resume.py — updated to load technical terms from YAML.
Make sure `pyyaml` is installed (added to requirements.txt).
"""
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
import logging
from starlette.concurrency import run_in_threadpool
import yaml
from pathlib import Path

load_dotenv()
logger = logging.getLogger("resumecritic.api.routes_resume")

router = APIRouter()

# Lazy-loaded globals
_model = None
_client = None
_gemini_model_name = None
_LLM_ENABLED = None
_TECHNICAL_TERMS = None

# Config
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", 5 * 1024 * 1024))  # default 5MB

# Path to YAML file containing technical terms
TERMS_YAML_PATH = Path(__file__).resolve().parents[1] / "core" / "technical_terms.yaml"


def load_technical_terms() -> set:
    """
    Load technical terms from YAML file. Return a set of lowercase terms.
    Cache the result in module-level _TECHNICAL_TERMS.
    """
    global _TECHNICAL_TERMS
    if _TECHNICAL_TERMS is not None:
        return _TECHNICAL_TERMS

    if TERMS_YAML_PATH.exists():
        try:
            with open(TERMS_YAML_PATH, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if isinstance(data, list):
                    # Normalize to lowercase strings
                    _TECHNICAL_TERMS = {str(s).strip().lower() for s in data if s}
                    logger.info("Loaded %d technical terms from YAML", len(_TECHNICAL_TERMS))
                    return _TECHNICAL_TERMS
                else:
                    logger.warning("technical_terms.yaml content is not a list; falling back to built-in terms")
        except Exception as e:
            logger.exception("Failed to load technical_terms.yaml; falling back to built-in terms: %s", e)

    # Fallback minimal set if YAML missing or invalid
    fallback = {
        "python",
        "java",
        "javascript",
        "typescript",
        "c++",
        "c#",
        "sql",
        "react",
        "django",
        "flask",
        "fastapi",
        "aws",
        "docker",
        "kubernetes",
    }
    _TECHNICAL_TERMS = fallback
    logger.warning("Using fallback technical terms (%d items). Create %s to override.", len(fallback), TERMS_YAML_PATH)
    return _TECHNICAL_TERMS


def extract_keywords(text: str):
    """
    Extract technical keywords (single- and multi-word) using the loaded YAML terms.
    """
    if not text or not text.strip():
        return set()

    all_terms = load_technical_terms()
    keywords = set()
    text_lower = text.lower()

    # Extract multi-word and single-word terms
    for term in all_terms:
        if " " in term or "-" in term:
            pattern = re.escape(term).replace(r"\ ", r"[\s\-]+")
            if re.search(pattern, text_lower):
                keywords.add(term)
        else:
            pattern = r"\b" + re.escape(term) + r"\b"
            if re.search(pattern, text_lower):
                keywords.add(term)

    # Special pattern handling (retain previous behavior)
    special_patterns = {
        r"\bc\+\+\b": "c++",
        r"\bc#\b": "c#",
        r"\b\.net\b": ".net",
        r"\bnode\.js\b": "nodejs",
    }
    for pattern, term in special_patterns.items():
        if re.search(pattern, text_lower):
            keywords.add(term)

    # Extract uppercase acronyms and map if present in terms
    acronyms = re.findall(r"\b[A-Z]{2,5}\b", text)
    for acro in acronyms:
        acro_lower = acro.lower()
        if acro_lower in all_terms:
            keywords.add(acro_lower)

    return keywords


def ensure_model():
    global _model
    if _model is None:
        logger.info("Loading sentence-transformers model (this may take a moment)...")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Model loaded.")
    return _model


def compute_semantic_similarity(text1: str, text2: str) -> float:
    if not text1.strip() or not text2.strip():
        return 0.0
    model = ensure_model()
    embeddings = model.encode([text1, text2])
    similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
    return float(similarity)


def extract_or_groups(text: str, all_keywords: set) -> list:
    """
    Same logic as before, but calling load_technical_terms() earlier ensures all_keywords aligns with YAML.
    """
    or_groups = []
    text_lower = text.lower()
    or_patterns = [
        r"\b(\w+(?:\s+\w+)?)\s+or\s+(\w+(?:\s+\w+)?)",
        r"\b(\w+(?:\s+\w+)?)\s*/\s*(\w+(?:\s+\w+)?)\s+or\s+(\w+(?:\s+\w+)?)",
        r"\b(\w+(?:\s+\w+)?)\s*,\s*(\w+(?:\s+\w+)?)\s*,\s*or\s+(\w+(?:\s+\w+)?)",
    ]
    for pattern in or_patterns:
        for match in re.finditer(pattern, text_lower):
            groups = match.groups()
            group_keywords = set()
            for g in groups:
                if g:
                    clean_kw = g.strip().lower()
                    if clean_kw in all_keywords:
                        group_keywords.add(clean_kw)
                    else:
                        for kw in all_keywords:
                            if clean_kw in kw or kw in clean_kw:
                                group_keywords.add(kw)
                                break
            if len(group_keywords) >= 2:
                or_groups.append(group_keywords)
    sentences = re.split(r"[.!?;]", text_lower)
    for sentence in sentences:
        if " or " in sentence or "/ or " in sentence:
            sentence_keywords = {kw for kw in all_keywords if kw in sentence}
            if len(sentence_keywords) >= 2:
                words = sentence.split()
                if "or" in words:
                    or_groups.append(sentence_keywords)
    # dedupe groups
    unique_groups = []
    for group in or_groups:
        is_subset = False
        for existing_group in unique_groups:
            if group.issubset(existing_group):
                is_subset = True
                break
            if existing_group.issubset(group):
                unique_groups.remove(existing_group)
                unique_groups.append(group)
                is_subset = True
                break
        if not is_subset and group not in unique_groups:
            unique_groups.append(group)
    return unique_groups


def match_with_or_groups(resume_keywords: set, job_keywords: set, or_groups: list) -> tuple:
    matched = resume_keywords & job_keywords
    matched_groups = []
    for group in or_groups:
        group_in_resume = any(kw in resume_keywords for kw in group)
        group_in_job = any(kw in job_keywords for kw in group)
        if group_in_job and group_in_resume:
            matched_groups.append(group)
            matched.update(group)
    missing = job_keywords - resume_keywords
    for group in matched_groups:
        missing = missing - group
    return matched, missing, matched_groups


def extract_text_from_pdf(file_content: bytes) -> str:
    text = ""
    try:
        with pdfplumber.open(BytesIO(file_content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        logger.exception("Could not extract text from PDF")
        raise HTTPException(status_code=400, detail=f"Could not extract text from PDF: {str(e)}")
    if not text.strip():
        raise HTTPException(status_code=400, detail="PDF appears to be empty or contains no extractable text")
    return text


@router.post("/analyze")
async def analyze_resume(resume: UploadFile, job_text: str = Form(...)):
    file_content = await resume.read()
    file_extension = resume.filename.split(".")[-1].lower() if resume.filename else ""

    if len(file_content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Uploaded file is too large")

    if file_extension == "pdf":
        resume_text = await run_in_threadpool(extract_text_from_pdf, file_content)
    elif file_extension in ["txt", "text"]:
        resume_text = file_content.decode("utf-8", errors="ignore")
    else:
        raise HTTPException(status_code=400, detail="Could not extract text from file")

    # Keyword-based matching
    all_terms = load_technical_terms()
    resume_kw = extract_keywords(resume_text)
    job_kw = extract_keywords(job_text)
    or_groups = extract_or_groups(job_text, job_kw)
    common, missing, matched_groups = match_with_or_groups(resume_kw, job_kw, or_groups)

    keywords_in_groups = set()
    for group in or_groups:
        keywords_in_groups.update(group)

    adjusted_total = len(job_kw) - len(keywords_in_groups) + len(or_groups)
    matched_regular = len(common - keywords_in_groups)
    total_matched = matched_regular + len(matched_groups)
    keyword_score = int((total_matched / adjusted_total) * 100) if adjusted_total > 0 else 0

    # Semantic similarity score
    semantic_score = compute_semantic_similarity(resume_text, job_text) * 100

    # Gemini LLM analysis (synchronous)
    # NOTE: analyze_with_gpt can be implemented to use ensure_gemini_client() like before
    gpt_analysis = {"enabled": False}
    try:
        client, gemini_model_name, enabled = ensure_gemini_client()
        if enabled:
            # call your existing analyze_with_gpt implementation here
            # keep the previous robust parsing you had in the original file
            from app.api.routes_resume_original_gpt import analyze_with_gpt  # optional split
            gpt_analysis = analyze_with_gpt(resume_text, job_text)
    except Exception:
        # If you keep the analyze_with_gpt in this file, call it directly.
        pass

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