def preprocess_custom(text: str) -> str:
    """
    Custom preprocessing routine.
    This function lowercases the text and removes punctuation.
    Adjust this as needed for your specific model requirements.
    """
    import re
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation
    return text