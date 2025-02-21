from abc import ABC, abstractmethod
import numpy as np

# Base class for embedding model wrappers.
class BaseEmbeddingModel(ABC):
    @abstractmethod
    def encode(self, sentences: list, show_progress_bar: bool = True):
        """
        Given a list of sentences, return their embeddings.
        """
        pass

# Helper function to select pipeline components based on the model configuration.
def _get_pipeline_components(model_name: str):
    from src.config.model_config import MODEL_CONFIG
    config = MODEL_CONFIG.get(model_name, {})

    # Select text preprocessor.
    if config.get("preprocessing", "default") == "custom":
        from src.preprocessing.custom_text_preprocessing import preprocess_custom as text_preprocessor
    else:
        text_preprocessor = lambda x: x

    # Select tokenizer.
    if config.get("tokenizer", "huggingface") == "custom":
        from src.preprocessing.custom_tokenizer import CustomTokenizer
        tokenizer_obj = CustomTokenizer()
    else:
        from transformers import AutoTokenizer
        tokenizer_obj = AutoTokenizer.from_pretrained(config.get("tokenizer_model", model_name))

    # Select pooling function.
    if config.get("pooling", "default") == "mean":
        from src.preprocessing.custom_pooling import mean_pooling as pooling_fn
    else:
        pooling_fn = None

    return text_preprocessor, tokenizer_obj, pooling_fn, config

# Wrapper for sentence-transformers models.
class SentenceTransformerWrapper(BaseEmbeddingModel):
    def __init__(self, model_name_or_path: str):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name_or_path)
        # Forzar inicialización de CUDA si está disponible
        import torch
        if torch.cuda.is_available():
            self.model.to('cuda')
            # Forzar inicialización de CUDA
            torch.cuda.init()
    
    def encode(self, sentences: list, show_progress_bar: bool = True):
        # Ensure all sentences are strings and handle None/NaN values
        cleaned_sentences = [str(text) if text is not None and not isinstance(text, float) else "" for text in sentences]
        return self.model.encode(cleaned_sentences, show_progress_bar=show_progress_bar)

# Wrapper for BERT models.
class BertEmbeddingWrapper(BaseEmbeddingModel):
    def __init__(self, model_name_or_path: str):
        from transformers import AutoTokenizer, AutoModel
        import torch
        self.tokenizer = AutoTokenizer.from_pretrained(model_name_or_path)
        self.model = AutoModel.from_pretrained(model_name_or_path)
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model.to(self.device)
    
    def encode(self, sentences: list, show_progress_bar: bool = True):
        import torch
        # Ensure all sentences are strings and handle None/NaN values
        cleaned_sentences = [str(text) if text is not None else "" for text in sentences]
        
        # Tokenize the texts
        encoded_input = self.tokenizer(
            cleaned_sentences,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors='pt'
        ).to(self.device)

        # Get model output
        with torch.no_grad():
            outputs = self.model(**encoded_input)
            
        # Mean Pooling - Take attention mask into account for correct averaging
        attention_mask = encoded_input['attention_mask']
        token_embeddings = outputs.last_hidden_state
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        embeddings = torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

        return embeddings.cpu().numpy()

# Wrapper for ONNX models.
class OnnxEmbeddingWrapper(BaseEmbeddingModel):
    def __init__(self, model_path: str, model_name: str):
        import onnxruntime
        self.session = onnxruntime.InferenceSession(model_path)
        # Use pipeline components (text preprocessor, tokenizer, pooling function).
        self.text_preprocessor, self.tokenizer, self.pooling_fn, _ = _get_pipeline_components(model_name)

    def encode(self, sentences: list, show_progress_bar: bool = True):
        if self.tokenizer is None:
            raise ValueError("Tokenizer is not set for OnnxEmbeddingWrapper.")
        # Preprocess sentences and tokenize.
        processed = [self.text_preprocessor(sentence) for sentence in sentences]
        inputs = self.tokenizer(processed, return_tensors="np", padding=True, truncation=True)
        # Prepare inputs for ONNX; assume the first input is "input_ids".
        input_name = self.session.get_inputs()[0].name
        ort_inputs = {input_name: inputs["input_ids"]}
        if len(self.session.get_inputs()) > 1 and "attention_mask" in inputs:
            ort_inputs[self.session.get_inputs()[1].name] = inputs["attention_mask"]
        outputs = self.session.run(None, ort_inputs)
        embeddings = outputs[0]
        # Optionally apply pooling if available.
        if self.pooling_fn is not None and "attention_mask" in inputs:
            embeddings = self.pooling_fn(embeddings, inputs["attention_mask"])
        return embeddings

# Wrapper for models served via a SageMaker endpoint.
class SageMakerEmbeddingWrapper(BaseEmbeddingModel):
    def __init__(self, endpoint_name: str, model_name: str):
        import boto3
        self.endpoint_name = endpoint_name
        self.client = boto3.client('sagemaker-runtime')
        # Use pipeline components from configuration.
        self.text_preprocessor, self.tokenizer, self.pooling_fn, _ = _get_pipeline_components(model_name)

    def encode(self, sentences: list, show_progress_bar: bool = True):
        import json
        if self.tokenizer is None:
            raise ValueError("Tokenizer is not set for SageMakerEmbeddingWrapper.")
        # Preprocess and tokenize the input sentences.
        processed = [self.text_preprocessor(sentence) for sentence in sentences]
        inputs = self.tokenizer(processed, return_tensors="np", padding=True, truncation=True)
        payload = json.dumps({"instances": inputs["input_ids"].tolist()})
        response = self.client.invoke_endpoint(
            EndpointName=self.endpoint_name,
            Body=payload,
            ContentType='application/json'
        )
        result = response['Body'].read().decode('utf-8')
        embeddings = json.loads(result)
        # Optionally apply pooling.
        if self.pooling_fn is not None and "attention_mask" in inputs:
            embeddings = self.pooling_fn(embeddings, inputs["attention_mask"])
        return embeddings 