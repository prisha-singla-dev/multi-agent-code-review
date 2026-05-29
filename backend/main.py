import os
import logging
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.models.schemas import ReviewRequest, ReviewResponse
from backend.orchestrator.graph import run_review
from backend.utils.github import fetch_pr_diff
from backend.utils.mock_review import get_mock_review
from backend.webhook import router as webhook_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

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

# Mount webhook router
app.include_router(webhook_router, tags=["Webhooks"])


@app.get("/")
async def root():
    return {"status": "running", "message": "Multi-Agent Code Review API v1.0"}


@app.get("/health")
async def health():
    api_key_set = bool(os.getenv("GEMINI_API_KEY"))
    return {
        "status": "healthy",
        "gemini_api_key_configured": api_key_set,
        "demo_mode": DEMO_MODE,
    }


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

    logger.info("Review requested. Demo mode: %s", DEMO_MODE)

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

    # Truncate to avoid token limits
    code_to_review = code_to_review[:800]

    try:
        if DEMO_MODE:
            result = get_mock_review()
        else:
            result = await run_review(code_to_review)
        return result
    except Exception as e:
        logger.exception("Review pipeline failed")
        raise HTTPException(status_code=500, detail=f"Review failed: {str(e)}")