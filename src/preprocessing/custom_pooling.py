import numpy as np

def mean_pooling(token_embeddings: np.ndarray, attention_mask: np.ndarray = None) -> np.ndarray:
    """
    Applies mean pooling over token embeddings.
    
    If an attention mask is provided, averages only over valid tokens.
    
    Args:
        token_embeddings: A numpy array of shape (batch_size, sequence_length, embedding_dim)
        attention_mask: An optional numpy array of shape (batch_size, sequence_length)
                       indicating which tokens should be included in pooling.
    
    Returns:
        A numpy array of shape (batch_size, embedding_dim) containing the pooled embeddings.
    """
    if attention_mask is not None:
        # Expand mask to match dimensions of token embeddings
        mask = attention_mask[..., None]
        sum_embeddings = np.sum(token_embeddings * mask, axis=1)
        sum_mask = np.clip(mask.sum(axis=1), a_min=1e-9, a_max=None)
        pooled_embeddings = sum_embeddings / sum_mask
    else:
        pooled_embeddings = np.mean(token_embeddings, axis=1)
    return pooled_embeddings 