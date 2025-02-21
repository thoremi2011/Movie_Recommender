import re

class CustomTokenizer:
    def __init__(self, vocab: dict = None, unknown_token: str = "<UNK>"):
        """
        Initialize the custom tokenizer with an optional vocabulary.
        If no vocabulary is provided, a default one is used.
        """
        if vocab is None:
            # Default vocabulary for demonstration purposes
            self.vocab = {
                "<UNK>": 0,
                "this": 1,
                "is": 2,
                "a": 3,
                "custom": 4,
                "tokenizer": 5,
                "example": 6,
            }
        else:
            self.vocab = vocab
        self.unknown_token = unknown_token

    def tokenize(self, text: str) -> list:
        """
        Tokenizes the input text by splitting on whitespace.
        Assumes that any necessary preprocessing (such as lowercasing or punctuation removal)
        has been performed separately.
        """
        tokens = text.split()
        return tokens

    def convert_to_ids(self, text: str) -> list:
        """
        Tokenizes the text and converts tokens into token IDs using the vocabulary.
        """
        tokens = self.tokenize(text)
        token_ids = [self.vocab.get(token, self.vocab.get(self.unknown_token, 0)) for token in tokens]
        return token_ids
