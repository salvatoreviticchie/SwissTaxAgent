"""
Pinecone retriever — embeds the query and retrieves top-k relevant chunks.
"""

from pinecone import Pinecone


class PineconeRetriever:
    def __init__(self, index, namespace: str = "swiss-tax"):
        self.index = index
        self.namespace = namespace

    def retrieve(self, query: str, top_k: int = 5) -> list[str]:
        """Return a list of text chunks most relevant to the query."""
        # Use Pinecone inference embeddings (same approach as RAGDATABASE)
        results = self.index.query(
            inputs={"text": query},
            top_k=top_k,
            namespace=self.namespace,
            include_metadata=True,
        )
        chunks = []
        for match in results.get("matches", []):
            text = match.get("metadata", {}).get("text", "")
            if text:
                chunks.append(text)
        return chunks

    def upsert_chunks(self, chunks: list[dict]) -> None:
        """
        Upsert document chunks into Pinecone.
        Each chunk: {"id": str, "text": str, "metadata": dict}
        """
        records = [
            {
                "id": chunk["id"],
                "inputs": {"text": chunk["text"]},
                "metadata": {**chunk.get("metadata", {}), "text": chunk["text"]},
            }
            for chunk in chunks
        ]
        self.index.upsert_records(records, namespace=self.namespace)
