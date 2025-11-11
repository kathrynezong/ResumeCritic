from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import routes_resume

app = FastAPI(title="ResumeCritic API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_resume.router, prefix="/api", tags=["Resume"])

@app.get("/")
def root():
    return {"message": "ResumeCritic backend running!"}
