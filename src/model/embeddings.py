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

# Diccionario global para almacenar los modelos cargados en memoria.
LOADED_MODELS = {}

def _get_available_ram_gb() -> float:
    """
    Retorna la memoria RAM disponible (en GB) usando psutil.virtual_memory().
    """
    mem = psutil.virtual_memory()
    return mem.available / (1024**3)

def _free_memory(required_ram_gb: float):
    """
    Libera modelos de LOADED_MODELS (del mayor uso de RAM al menor) 
    hasta que haya memoria suficiente para 'required_ram_gb'.
    Si tras eliminar todos los modelos no se puede liberar suficiente memoria, 
    lanza MemoryError.
    """
    # Ordena los modelos en memoria en orden descendente de uso RAM 
    # (sacado del 'RAM' en MODEL_CONFIG).
    loaded_model_names = sorted(
        LOADED_MODELS.keys(),
        key=lambda name: float(MODEL_CONFIG.get(name, {}).get("RAM", 0.0)),
        reverse=True
    )
    
    while True:
        available_ram_gb = _get_available_ram_gb()
        if available_ram_gb >= required_ram_gb:
            # Ya hay memoria suficiente.
            return

        if not loaded_model_names:
            # No quedan modelos que liberar y todavía no hay memoria.
            raise MemoryError(
                f"No hay suficiente memoria para cargar el nuevo modelo. "
                f"Se requieren ~{required_ram_gb:.2f}GB, "
                f"y no se pudo liberar más memoria."
            )
        # Elimina el modelo de mayor RAM.
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
    # Primero verificamos si el modelo ya está cargado en memoria (caché).
    if model_name in LOADED_MODELS:
        return LOADED_MODELS[model_name]

    config = MODEL_CONFIG.get(model_name, {})
    model_type = config.get("type", "sentence_transformer").lower()
    model_path = config.get("model_path", model_name)
    
    # Comprobamos la RAM libre, si el campo "RAM" existe en el JSON y, si no hay suficiente,
    # intentamos liberar modelos del caché.
    required_ram_gb = float(config.get("RAM", 0.0))  # GB estimados que requiere el modelo
    if required_ram_gb > 0.0:
        available_ram_gb = _get_available_ram_gb()
        if available_ram_gb < required_ram_gb:
            # Intenta liberar memoria removiendo modelos de la caché.
            _free_memory(required_ram_gb)
            # Tras liberar, se comprueba de nuevo la memoria.
            if _get_available_ram_gb() < required_ram_gb:
                raise MemoryError(
                    f"No hay suficiente memoria para cargar el modelo '{model_name}'. "
                    f"Se requieren ~{required_ram_gb:.2f}GB, pero no se pudo liberar suficiente memoria."
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
    
    # Guardamos el modelo para uso posterior.
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
