"""
Token Management Usage Guide

This module demonstrates how to use the new token management system
with accurate token counting and intelligent text truncation.
"""

from .token_counter import get_token_counter
from .text_truncator import TextTruncator

# Example usage of the token management system


def example_token_counting():
    """Example of accurate token counting"""

    # Get token counter for embedding model
    token_counter = get_token_counter("text-embedding-3-small")

    text = "This is a sample text that we want to count tokens for."
    token_count = token_counter.count_tokens(text)

    print(f"Text: {text}")
    print(f"Token count: {token_count}")

    # Batch token counting
    texts = [
        "First text sample",
        "Second text sample with more content",
        "Third text sample"
    ]

    token_counts = token_counter.count_tokens_batch(texts)
    total_tokens = token_counter.get_total_tokens(texts)

    print(f"Individual counts: {token_counts}")
    print(f"Total tokens: {total_tokens}")


def example_text_truncation():
    """Example of intelligent text truncation"""

    # Initialize truncator for embedding model
    truncator = TextTruncator("text-embedding-3-small")

    # Long text that exceeds token limit
    long_text = "This is a very long text that exceeds the token limit..." * 1000

    # Truncate to fit within limit
    truncated_text, token_count, was_truncated = truncator.truncate_text(
        long_text)

    print(f"Original length: {len(long_text)} chars")
    print(f"Truncated length: {len(truncated_text)} chars")
    print(f"Token count: {token_count}")
    print(f"Was truncated: {was_truncated}")


def example_batch_truncation():
    """Example of batch text truncation with limits"""

    truncator = TextTruncator("text-embedding-3-small")

    texts = [
        "Short text",
        "Medium length text with some more content",
        "Very long text that definitely exceeds the normal token limits" * 100
    ]

    # Truncate batch with individual and total limits
    truncated_texts, token_counts, total_tokens = truncator.truncate_texts_batch(
        texts,
        max_tokens_per_text=1000,  # Individual limit
        max_total_tokens=2500      # Total batch limit
    )

    print(f"Original texts: {len(texts)}")
    print(f"Truncated texts: {len(truncated_texts)}")
    print(f"Token counts: {token_counts}")
    print(f"Total tokens: {total_tokens}")


def example_integration_with_embeddings():
    """Example of using token management with embedding operations"""

    # This shows how to integrate with existing embedding code
    texts = ["Sample text 1", "Sample text 2", "Very long text..." * 500]

    # Initialize truncator for the embedding model
    truncator = TextTruncator("text-embedding-3-small")

    # Validate and truncate texts before embedding
    processed_texts = []

    for text in texts:
        # Validate if text is within limits
        is_valid, token_count = truncator.validate_text_tokens(text)

        if not is_valid:
            # Truncate if needed
            truncated_text, final_tokens, was_truncated = truncator.truncate_text(
                text)
            processed_texts.append(truncated_text)
            print(f"Truncated text: {token_count} -> {final_tokens} tokens")
        else:
            processed_texts.append(text)
            print(f"Text OK: {token_count} tokens")

    # Now processed_texts can be safely sent to embedding API
    return processed_texts


if __name__ == "__main__":
    print("=== Token Counting Example ===")
    example_token_counting()

    print("\n=== Text Truncation Example ===")
    example_text_truncation()

    print("\n=== Batch Truncation Example ===")
    example_batch_truncation()

    print("\n=== Integration Example ===")
    example_integration_with_embeddings()
