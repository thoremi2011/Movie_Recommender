# Hot-Swappable Model Architecture

This is how I’ve structured a flexible and maintainable architecture that enables dynamic model loading and seamless integration of new models.

## Overview

The system is designed to handle multiple embedding models that can:
- Be dynamically loaded at runtime
- Be swapped without restarting the application (**as long as no custom preprocessing, tokenization, or pooling is required**)
- Be cached to improve performance
- Be automatically managed in terms of memory

## Architecture Components

### 1. Model Configuration
Model configurations are stored in either a local JSON file or AWS SSM Parameter Store.

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
To ensure consistency, I use a wrapper pattern that standardizes the interface for different types of models. Each wrapper follows the `BaseEmbeddingModel` structure:
```python
class BaseEmbeddingModel(ABC):
    @abstractmethod
    def encode(self, sentences: list) -> np.ndarray:
        """Convert sentences to embeddings"""
        pass
```
Implemented wrappers:
- `SentenceTransformerWrapper` for Hugging Face models
- `OnnxEmbeddingWrapper` for ONNX models (compatible with TensorFlow and PyTorch)
- `BertEmbeddingWrapper` for BERT-based models
- `SageMakerEmbeddingWrapper` for models deployed on SageMaker

### 3. SageMaker Integration Details

The `SageMakerEmbeddingWrapper` allows inference via SageMaker endpoints while keeping preprocessing and pooling local.

1. **Preprocessing Pipeline**:
   ```python
   class SageMakerEmbeddingWrapper(BaseEmbeddingModel):
       def encode(self, sentences: list) -> np.ndarray:
           processed = [self.text_preprocessor(sentence) for sentence in sentences]
           inputs = self.tokenizer(
               processed, 
               return_tensors="np", 
               padding=True, 
               truncation=True
           )
   ```

2. **SageMaker Inference**:
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
   ```python
   if self.pooling_fn is not None and "attention_mask" in inputs:
       sentence_embeddings = self.pooling_fn(
           token_embeddings, 
           inputs["attention_mask"]
       )
   ```

This setup ensures:
- Minimal data transfer (only tokenized inputs are sent)
- Consistent preprocessing across different environments
- Flexibility in pooling strategies
- Heavy compute (model inference) stays within SageMaker

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
To optimize memory usage, the system:
- Tracks RAM consumption per model
- Unloads models dynamically when free memory is low
- Prioritizes model unloading based on memory footprint
- Caches frequently used models

Example function:
```python
def free_memory(required_ram_gb: float):
    """Frees models from highest to lowest RAM usage until enough memory is available"""
```

### 5. Model Loading Pipeline
The pipeline for handling models follows this sequence:
1. **Load Configuration**:
   ```python
   config = load_model_config()  # From JSON or SSM
   ```
2. **Initialize Model**:
   ```python
   model = load_embedding_model(model_name)  # Handles caching automatically
   ```
3. **Generate Embeddings**:
   ```python
   embeddings = generate_embeddings(model, sentences)
   ```

## Integration and Model Expansion

### Adding New Models
Adding new models is simple:

- **For Supported Architectures**:  
  Just update the JSON configuration (or SSM Parameter Store) with model details—no code modifications required.

- **For New Model Types**:  
  Implement a new wrapper based on `BaseEmbeddingModel` and extend `load_embedding_model()` to support it.

Example:
```python
class NewModelWrapper(BaseEmbeddingModel):
    def encode(self, sentences: list) -> np.ndarray:
        return embeddings
```
Once added, the model can be loaded dynamically without restarting the application.

## Additional Aspects

### Supported Model Sources
- Local storage
- Hugging Face Hub
- S3 storage
- SageMaker endpoints
- ONNX format models

### Error Handling
To ensure robustness, the system manages:
- Model loading failures
- Memory allocation constraints
- Configuration errors
- API endpoint failures

### Logging and Monitoring
The system logs:
- Model loading/unloading events
- Memory management actions
- Configuration updates
- Performance metrics
