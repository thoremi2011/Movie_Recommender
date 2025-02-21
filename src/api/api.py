"""
FastAPI application for movie recommendation inference.
It exposes an endpoint to obtain recommendations based on a query.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager
from typing import List
from src.utils.logger import logger
from src.model.embeddings import load_embedding_model
from src.config.model_config import MODEL_CONFIG

# Import recommendation service
from src.api.recommendation_service import get_movie_recommendations


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle event handler for the FastAPI application.
    Loads models on startup and ensures proper cleanup on shutdown.
    """
    # Load models on startup
    for model_name, config in MODEL_CONFIG.items():
        if config.get("preload", False):
            logger.info(f"Preloading model: {model_name}")
            try:
                # Warm-up: execute a complete recommendation
                logger.info(f"Warming up complete pipeline for model: {model_name}")
                warm_up_query = "Action movie with explosions and car chases"
                _ = get_movie_recommendations(
                    sentence=warm_up_query,
                    model_name=model_name,
                    top_k=5
                )
                logger.info(f"Model {model_name} warmed up successfully")
            except Exception as e:
                logger.error(f"Error preloading model '{model_name}': {e}")

    # 'yield' gives control to the app; once the app stops, the code after
    # yield executes, equivalent to 'shutdown' or final cleanup.
    yield

    # Log application shutdown
    logger.info("The app is shutting down...")

# Define FastAPI application with lifespan
app = FastAPI(title="Movie Recommender API",lifespan=lifespan)


@app.get("/")
async def read_root():
    return {"message": "Welcome to the Movie Recommender API."}

# Request payload model for recommendation
class RecommendRequest(BaseModel):
    sentence: str
    model_name: str
    top_k: int = 5
    date_from: str = "1902-04-17"
    date_to: str = "2021-03-24"
    min_popularity: float = 0.0
    max_popularity: float = 11702.0
    min_rating: float = 0.0
    max_rating: float = 10.0

# Response model for a movie recommendation
class Recommendation(BaseModel):
    title: str
    overview: str
    score: float
    popularity: float
    rating: float

# Response model for the /recommend endpoint (development mode)
class RecommendResponse(BaseModel):
    sentence: str
    recommendations: List[Recommendation]
    model_info: dict  # Extra debug info to verify which model is used.

@app.post("/recommend", response_model=RecommendResponse)
async def recommend(request: RecommendRequest):
    try:
        recommendations = get_movie_recommendations(
            sentence=request.sentence,
            model_name=request.model_name,
            top_k=request.top_k,
            date_from=request.date_from,
            date_to=request.date_to,
            min_popularity=request.min_popularity,
            max_popularity=request.max_popularity,
            min_rating=request.min_rating,
            max_rating=request.max_rating
        )

        # Get the configuration used for the model to verify the selected model
        from src.config.model_config import MODEL_CONFIG
        config = MODEL_CONFIG.get(request.model_name, {})
        model_info = {
            "model_name": request.model_name,
            "model_type": config.get("type", "sentence_transformer"),
            "model_path": config.get("model_path", request.model_name)
        }

        return RecommendResponse(
            sentence=request.sentence,
            recommendations=recommendations,
            model_info=model_info
        )
    except Exception as e:
        logger.error(f"Error in /recommend endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))