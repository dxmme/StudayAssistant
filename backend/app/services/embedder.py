from app.core.config import settings


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts via OpenAI. Raises ValueError if API key is missing."""
    if not settings.openai_api_key:
        raise ValueError(
            "OPENAI_API_KEY is not configured. Set it in backend/.env to enable ingest."
        )
    from openai import OpenAI  # lazy import — not installed in base env

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.embeddings.create(model=settings.embedding_model, input=texts)
    return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]
