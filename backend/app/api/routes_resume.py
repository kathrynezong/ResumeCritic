from fastapi import APIRouter, UploadFile, Form
from fastapi.responses import JSONResponse

router = APIRouter()

@router.post("/analyze")
async def analyze_resume(resume: UploadFile, job_text: str = Form(...)):
    # For now, just return mock data
    resume_name = resume.filename
    return JSONResponse(
        content={
            "resume_file": resume_name,
            "job_description_length": len(job_text),
            "match_score": 78,
            "missing_keywords": ["leadership", "REST APIs", "Kubernetes"]
        }
    )
