# Hot-Swappable Model Architecture

This document describes the implementation of a flexible and maintainable architecture that allows for dynamic model loading and seamless integration of new models.

## Overview

The system supports multiple embedding models that can be:
- Dynamically loaded at runtime
- Swapped without restarting the application (**if no custom preprocessing, tokenization, or pooling is required**)
- Cached for improved performance
- Automatically managed in terms of memory

## Architecture Components

### 1. Model Configuration
Models are defined in a configuration that can be loaded from a local JSON file or AWS SSM Parameter Store.

Example configuration:
```json
{
  "all-MiniLM-L6-v2": {
    "type": "sentence_transformer",
    "model_path": "sentence-transformers/all-MiniLM-L6-v2",
    "RAM": 0.5,
    "preload": true
  },
  "custom-onnx-model": {
    "type": "s3",
    "model_path": "s3://my-bucket/models/custom.onnx",
    "RAM": 1.2
  }
}
```

### 2. Model Wrappers and Standardized Interface
A wrapper pattern is used to standardize the interface for different types of models. Each wrapper implements the `BaseEmbeddingModel` interface:
```python
class BaseEmbeddingModel(ABC):
    @abstractmethod
    def encode(self, sentences: list) -> np.ndarray:
        """Convert sentences to embeddings"""
        pass
```
Implemented wrappers include:
- `SentenceTransformerWrapper` for Hugging Face models
- `OnnxEmbeddingWrapper` for ONNX format models (compatible with TensorFlow and PyTorch)
- `BertEmbeddingWrapper` for BERT-specific models
- `SageMakerEmbeddingWrapper` for models deployed on SageMaker

### 3. Memory Management and Optimization
The system efficiently manages memory by:
- Tracking RAM usage per model
- Automatically unloading models when available memory is low using a least-memory-intensive strategy
- Caching frequently used models

Example:
```python
def free_memory(required_ram_gb: float):
    """Frees models from highest to lowest RAM usage until enough memory is available"""
```

### 4. Model Loading Pipeline
The pipeline for loading and using models includes:
1. **Configuration Loading**:
   ```python
   config = load_model_config()  # From JSON or SSM
   ```
2. **Model Initialization**:
   ```python
   model = load_embedding_model(model_name)  # Automatically handles caching
   ```
3. **Embedding Generation**:
   ```python
   embeddings = generate_embeddings(model, sentences)
   ```

## Integration and Model Expansion

### Adding New Models
Integrating new models is straightforward:

- **For Known Architectures**:  
  Simply update the configuration (JSON file or SSM) with the model details (type, path, memory requirements). No code changes are necessary.

- **For New Model Types**:  
  Create a new wrapper that implements the `BaseEmbeddingModel` interface and update the model loading function to handle the new type.

Example:
```python
class NewModelWrapper(BaseEmbeddingModel):
    def encode(self, sentences: list) -> np.ndarray:
        # Custom implementation
        return embeddings
```
After integration, use the reload endpoint to load the updated configuration, making the new model available immediately.

## Additional Aspects

### Supported Model Sources
- Local files
- Hugging Face Hub
- S3 storage
- SageMaker endpoints
- ONNX format models

### Error Handling
The system robustly manages:
- Model loading failures
- Memory allocation issues
- Configuration errors
- API endpoint errors

### Logging and Monitoring
Comprehensive logging tracks:
- Model loading/unloading events
- Memory management decisions
- Configuration changes
- Performance metrics

### Best Practices
- **Memory Management**: Configure RAM requirements and preload flags appropriately in the model configuration.
- **Model Configuration**: Use descriptive model names and include all necessary metadata.
- **Testing**: Regularly verify memory management, hot-swapping functionality, and embedding consistency.

### Future Improvements
Potential enhancements include:
- Model versioning support
- A/B testing capabilities
- Performance metrics collection
- Automated model optimization
