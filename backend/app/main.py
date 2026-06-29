import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.research_routes import router as research_router
from app.db.database import Base, engine

Base.metadata.create_all(bind=engine)

allowed_origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if origin.strip()
]

app = FastAPI(
    title="ResearchOS API",
    description="Traceable academic research planning, source retrieval, verification, and reporting.",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(research_router, prefix="/api/research", tags=["Research"])


@app.get("/")
def health_check():
    return {"message": "Autonomous Research Agent API is running"}
