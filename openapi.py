from dataclasses import dataclass

@dataclass
class Page:
    PageNum: int
    Content: str
    Embedding: list

def page_embeddings(p: Page, client):
    response = client.embeddings.create(
        input=p.Content,
        model="text-embedding-3-small"
    )

    p.Embedding = response.data[0].embedding

def query_embedding(query, client):
    response = client.embeddings.create(
        input=query,
        model="text-embedding-3-small"
    )

    return response.data[0].embedding