import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError
from app.api.auth_routes import router as auth_router
from app.api.research_routes import router as research_router
from app.db.database import Base, engine

try:
    Base.metadata.create_all(bind=engine)
except SQLAlchemyError as error:
    print(f"Research database startup skipped: {error}")

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
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
app.include_router(research_router, prefix="/api/research", tags=["Research"])


@app.get("/")
def health_check():
    return {"message": "Autonomous Research Agent API is running"}
