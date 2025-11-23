from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes_resume import router as resume_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(resume_router, prefix="/api", tags=["Resume"])
