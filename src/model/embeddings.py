"""Module for loading an embedding model and generating sentence embeddings."""

from src.config.model_config import MODEL_CONFIG
from src.model.model_wrappers import (
    BaseEmbeddingModel,
    SentenceTransformerWrapper,
    BertEmbeddingWrapper,
    OnnxEmbeddingWrapper,
    SageMakerEmbeddingWrapper,
)
from src.utils.s3_utils import download_model_from_s3
import psutil

# Global dictionary to store loaded models in memory
LOADED_MODELS = {}

def _get_available_ram_gb() -> float:
    """
    Returns available RAM (in GB) using psutil.virtual_memory().
    """
    mem = psutil.virtual_memory()
    return mem.available / (1024**3)

def _free_memory(required_ram_gb: float):
    """
    Frees models from LOADED_MODELS (from highest to lowest RAM usage)
    until there is enough memory for 'required_ram_gb'.
    If after removing all models there is not enough memory available,
    raises MemoryError.
    """
    # Sort loaded models in descending order by RAM usage
    # (taken from 'RAM' in MODEL_CONFIG)
    loaded_model_names = sorted(
        LOADED_MODELS.keys(),
        key=lambda name: float(MODEL_CONFIG.get(name, {}).get("RAM", 0.0)),
        reverse=True
    )
    
    while True:
        available_ram_gb = _get_available_ram_gb()
        if available_ram_gb >= required_ram_gb:
            # There is enough memory
            return

        if not loaded_model_names:
            # No more models to free and still not enough memory
            raise MemoryError(
                f"Not enough memory to load the new model. "
                f"Required ~{required_ram_gb:.2f}GB, "
                f"and could not free more memory."
            )
        # Remove the model with highest RAM usage
        model_to_remove = loaded_model_names.pop(0)
        del LOADED_MODELS[model_to_remove]

def load_embedding_model(model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> BaseEmbeddingModel:
    """
    Loads an embedding model based on the configuration for the specified model_name.
    
    The MODEL_CONFIG determines:
      - The model type ('sagemaker', 's3', 'local', or 'huggingface')
      - The model path.
      
    For 's3' models, the model file is downloaded locally.
    
    Returns:
        A model wrapper instance configured with the appropriate pipeline components.
    """
    # First check if the model is already loaded in memory (cache)
    if model_name in LOADED_MODELS:
        return LOADED_MODELS[model_name]

    config = MODEL_CONFIG.get(model_name, {})
    model_type = config.get("type", "sentence_transformer").lower()
    model_path = config.get("model_path", model_name)
    
    # Check free RAM if "RAM" field exists in JSON and, if not enough,
    # try to free models from cache
    required_ram_gb = float(config.get("RAM", 0.0))  # Estimated GB required by the model
    if required_ram_gb > 0.0:
        available_ram_gb = _get_available_ram_gb()
        if available_ram_gb < required_ram_gb:
            # Try to free memory by removing models from cache
            _free_memory(required_ram_gb)
            # After freeing, check memory again
            if _get_available_ram_gb() < required_ram_gb:
                raise MemoryError(
                    f"Not enough memory to load model '{model_name}'. "
                    f"Required ~{required_ram_gb:.2f}GB, but could not free enough memory."
                )

    if model_type == "s3":
        model_path = download_model_from_s3(model_path)
        model_wrapper = OnnxEmbeddingWrapper(model_path, model_name)
    elif model_type == "sagemaker":
        model_wrapper = SageMakerEmbeddingWrapper(model_path, model_name)
    elif model_type == "local":
        model_wrapper = OnnxEmbeddingWrapper(model_path, model_name)
    elif model_type == "sentence_transformer":
        model_wrapper = SentenceTransformerWrapper(model_path)
    elif model_type == "bert":
        model_wrapper = BertEmbeddingWrapper(model_path)
    else:
        raise ValueError(f"Unsupported model type: {model_type}")
    
    # Save model for later use
    LOADED_MODELS[model_name] = model_wrapper
    
    return model_wrapper

def generate_embeddings(model: BaseEmbeddingModel, sentences: list, show_progress_bar: bool = True):
    """
    Generates embeddings for a list of sentences using the provided model wrapper.
    
    Args:
        model: A model wrapper instance.
        sentences: A list of strings (e.g., movie descriptions).
        show_progress_bar: Whether to show a progress bar during encoding.
    
    Returns:
        A numpy array of embeddings.
    """
    return model.encode(sentences, show_progress_bar=show_progress_bar)
