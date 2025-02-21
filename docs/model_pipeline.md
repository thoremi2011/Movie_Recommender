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
  "paraphrase-MiniLM-L6-v2": {
      "model_path": "sentence-transformers/paraphrase-MiniLM-L6-v2",
      "embeddings_path": "s3://my-bucket/data/embeddings/embeddings_paraphrase_MiniLM.npy", 
      "type": "sentence_transformer",
      "tokenizer_model": "",
      "preprocces":"",
      "pooling":"",
      "RAM": 0.4,
      "preload": true
    },
  "my_custom_onnx_model_(beta)": {
    "type": "s3",
    "model_path": "s3://my-bucket/path/to/model.onnx",
    "preprocessing": "custom",    
    "tokenizer": "custom",        
    "tokenizer_model": "custom",  
    "pooling": "mean",
    "RAM": 1.0,
    "preload": false
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

### 3. SageMaker Integration Details

The `SageMakerEmbeddingWrapper` handles model inference through SageMaker endpoints while maintaining local control over preprocessing and pooling:

1. **Preprocessing Pipeline**:
   ```python
   class SageMakerEmbeddingWrapper(BaseEmbeddingModel):
       def encode(self, sentences: list) -> np.ndarray:
           # Local preprocessing and tokenization
           processed = [self.text_preprocessor(sentence) for sentence in sentences]
           inputs = self.tokenizer(
               processed, 
               return_tensors="np", 
               padding=True, 
               truncation=True
           )
   ```

2. **SageMaker Inference**:
   - Send tokenized inputs to SageMaker endpoint
   - Receive token-level embeddings back
   ```python
   payload = json.dumps({"instances": inputs["input_ids"].tolist()})
   response = self.client.invoke_endpoint(
       EndpointName=self.endpoint_name,
       Body=payload,
       ContentType='application/json'
   )
   token_embeddings = json.loads(response['Body'].read().decode('utf-8'))
   ```

3. **Post-processing**:
   - Apply local pooling strategy to get sentence embeddings
   ```python
   if self.pooling_fn is not None and "attention_mask" in inputs:
       sentence_embeddings = self.pooling_fn(
           token_embeddings, 
           inputs["attention_mask"]
       )
   ```

This approach:
- Reduces data transfer (only sending tokenized inputs)
- Maintains consistency in preprocessing across environments
- Allows flexible pooling strategies
- Keeps the heavy compute (model inference) in SageMaker

Configuration example:
```json
{
  "my-sagemaker-model_v2_(beta_a2)": {
      "model_path": "sagemaker_endpoint",
      "embeddings_path": "s3://my-bucket/data/embeddings/my-sagemaker-model-embeddings.npy",
      "type": "sagemaker",
      "tokenizer_model": "",
      "preprocces":"",
      "pooling":"",
      "RAM": 0.0,
      "preload": false
    }
}
```

### 4. Memory Management and Optimization
The system efficiently manages memory by:
- Tracking RAM usage per model
- Automatically unloading models when available memory is low using a least-memory-intensive strategy
- Caching frequently used models

Example:
```python
def free_memory(required_ram_gb: float):
    """Frees models from highest to lowest RAM usage until enough memory is available"""
```

### 5. Model Loading Pipeline
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
