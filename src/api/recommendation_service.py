from src.model.embeddings import load_embedding_model, generate_embeddings
from src.config.model_config import MODEL_CONFIG, load_model_config
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import pandas as pd
from src.model.model_wrappers import BaseEmbeddingModel
from fastapi import HTTPException
from src.utils.logger import logger
from typing import List
import boto3
from urllib.parse import urlparse
import os
from src.utils.s3_utils import read_from_s3

# Cache for dataframe and embeddings
_CACHE = {}

def clear_cache():
    """Clears the embeddings cache"""
    global _CACHE
    _CACHE.clear()
    logger.info("Cache cleared")

def _load_data(model_name: str):
    """
    Load movie data and embeddings from storage and cache them in memory.
    
    Args:
        model_name: Name of the model to load embeddings for
    
    Returns:
        tuple: (DataFrame with movie data, numpy array of embeddings)
    
    Raises:
        ValueError: If model configuration or embeddings path is not found
    """
    try:
        logger.info(f"Requesting data for model: {model_name}")
        logger.info(f"Current _CACHE state: {list(_CACHE.keys())}")
        
        # Load DataFrame if not in cache
        if 'df' not in _CACHE:
            logger.info("Loading movies DataFrame...")
            csv_path = os.getenv("MOVIES_CSV_PATH", "data/processed/movies_processed.csv")
            if csv_path.startswith('s3://'):
                _CACHE['df'] = read_from_s3(csv_path)
            else:
                _CACHE['df'] = pd.read_csv(csv_path)
            logger.info("DataFrame loaded successfully")
        
        # Load embeddings for this model
        if model_name not in _CACHE:
            logger.info(f"Embeddings not found in cache for {model_name}, loading...")
            config = MODEL_CONFIG.get(model_name)
            if not config:
                raise ValueError(f"No configuration found for model {model_name}")
            
            embeddings_path = config.get("embeddings_path")
            if not embeddings_path:
                raise ValueError(f"Embeddings path not specified for model {model_name}")
            
            if embeddings_path.startswith('s3://'):
                _CACHE[model_name] = read_from_s3(embeddings_path)
            else:
                _CACHE[model_name] = np.load(embeddings_path)
            logger.info(f"Embeddings loaded successfully for {model_name}")
        
        return _CACHE['df'], _CACHE[model_name]
    except Exception as e:
        logger.error(f"Error in _load_data: {str(e)}")
        # Clear cache in case of error
        if model_name in _CACHE:
            del _CACHE[model_name]
        raise

def get_movie_recommendations(sentence: str, model_name: str = "paraphrase-MiniLM-L6-v2", 
                            top_k: int = 5, exclude_movies: list = None, **kwargs):
    """Get movie recommendations based on a query."""
    # Get updated configuration without depending on previously imported variable
    current_config = load_model_config()
    logger.info(f"Available models in MODEL_CONFIG: {current_config.keys()}")
    if model_name not in current_config:
        raise ValueError(f"Model {model_name} does not exist in configuration")
    
    try:
        logger.info(f"Applying filters with parameters:")
        logger.info(f"- Date range: {kwargs.get('date_from')} to {kwargs.get('date_to')}")
        logger.info(f"- Popularity range: {kwargs.get('min_popularity')} to {kwargs.get('max_popularity')}")
        logger.info(f"- Rating range: {kwargs.get('min_rating')} to {kwargs.get('max_rating')}")
        
        # Load data and embeddings
        df, movie_embeddings = _load_data(model_name)
        
        # Generate embedding for query
        model = load_embedding_model(model_name)
        logger.info(f"Model loaded: {model.__class__.__name__}")

        # Generate query embedding
        query_embedding = generate_embeddings(model, [sentence], show_progress_bar=False)
        
        # Apply filters
        mask = (
            (df['release_date'] >= kwargs.get('date_from')) &
            (df['release_date'] <= kwargs.get('date_to')) &
            (df['popularity'] >= kwargs.get('min_popularity')) &
            (df['popularity'] <= kwargs.get('max_popularity')) &
            (df['vote_average'] >= kwargs.get('min_rating')) &
            (df['vote_average'] <= kwargs.get('max_rating'))
        )
        
        # Exclude movies if specified
        if exclude_movies:
            mask = mask & ~df['title'].isin(exclude_movies)
            
        # Get indices that meet the filters
        filtered_indices = df[mask].index
        logger.info(f"Total movies before filtering: {len(df)}")
        logger.info(f"Movies after filtering: {len(filtered_indices)}")
        
        if len(filtered_indices) == 0:
            logger.warning(f"No movies match the filter criteria with current parameters")
            return []
        
        # Calculate cosine similarity with filtered embeddings
        similarity_scores = cosine_similarity(query_embedding, movie_embeddings[filtered_indices])[0]
        
        # Get indices of top_k movies within filtered ones
        top_k = min(top_k, len(filtered_indices))
        top_indices = np.argsort(-similarity_scores)[:top_k]
        
        # Log selected movies with their scores
        logger.info(f"Selected top {top_k} movies from {len(filtered_indices)} filtered movies")
        
        # Build recommendations list
        recommendations = []
        for idx in top_indices:
            # Get original DataFrame index
            original_idx = filtered_indices[idx]
            movie_title = df.iloc[original_idx]["title"]
            movie_overview = df.iloc[original_idx]["overview"]
            popularity = df.iloc[original_idx]["popularity"]
            rating = df.iloc[original_idx]["vote_average"]
            
            logger.info(f"Selected movie: {movie_title} (popularity: {popularity:.2f}, rating: {rating:.2f})")
            
            recommendations.append({
                "title": movie_title,
                "overview": movie_overview,
                "score": float(similarity_scores[idx]),
                "popularity": float(popularity),
                "rating": float(rating)
            })
        
        return recommendations
    except Exception as e:
        logger.error(f"Error in get_movie_recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def get_movie_df():
    """
    Returns the movies DataFrame loaded in _CACHE or loads it if needed.
    """
    if 'df' not in _CACHE:
        csv_path = os.getenv("MOVIES_CSV_PATH", "data/processed/movies_processed.csv")
        if csv_path.startswith("s3://"):
            _CACHE['df'] = read_from_s3(csv_path)
        else:
            _CACHE['df'] = pd.read_csv(csv_path)
    return _CACHE['df'] 