import os
from dotenv import load_dotenv
from backend.utils.mock_review import get_mock_review

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.models.schemas import ReviewRequest, ReviewResponse
from backend.orchestrator.graph import run_review
from backend.utils.github import fetch_pr_diff

app = FastAPI(
    title="Multi-Agent Code Review API",
    description="AI-powered code review using specialized agents (Security, Performance, Logic, Style)",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"status": "running", "message": "Multi-Agent Code Review API v1.0"}


@app.get("/health")
async def health():
    api_key_set = bool(os.getenv("GEMINI_API_KEY"))
    return {"status": "healthy", "gemini_api_key_configured": api_key_set}


@app.post("/review", response_model=ReviewResponse)
async def review_code(request: ReviewRequest):
    """
    Submit code or a GitHub PR URL for multi-agent review.
    - Provide `code` directly, OR
    - Provide `github_pr_url` to fetch from GitHub
    """
    if not request.code and not request.github_pr_url:
        raise HTTPException(
            status_code=400, detail="Provide either 'code' or 'github_pr_url'."
        )

    code_to_review = request.code

    if request.github_pr_url:
        try:
            code_to_review = await fetch_pr_diff(request.github_pr_url)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=502, detail=f"Failed to fetch PR from GitHub: {str(e)}"
            )

    if not code_to_review or len(code_to_review.strip()) < 10:
        raise HTTPException(status_code=400, detail="Code is too short to review.")

    # Truncate to avoid token limits (Gemini Flash handles ~1M tokens but let's be safe)
    code_to_review = code_to_review[:2000]

    # try:
    #     result = await run_review(code_to_review)
    #     return result
    # except Exception as e:
    #     raise HTTPException(status_code=500, detail=f"Review failed: {str(e)}")

    try:
        # DEMO MODE — returns instant mock data when Gemini quota is exhausted
        if os.getenv("DEMO_MODE", "false").lower() == "true":
            result = get_mock_review()
        else:
            result = await run_review(code_to_review)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Review failed: {str(e)}")