"""
Pinecone retriever — embeds the query via Pinecone Inference and retrieves top-k chunks.
Uses the same embedding approach as RAGDATABASE (llama-text-embed-v2, 1024d).
"""

from pinecone import Pinecone

EMBEDDING_MODEL = "llama-text-embed-v2"


class PineconeRetriever:
    def __init__(self, index, namespace: str = "swiss-tax"):
        self.index = index
        self.namespace = namespace
        # pc instance needed for inference API
        self._pc: Pinecone | None = None

    def set_pc(self, pc: Pinecone) -> None:
        self._pc = pc

    def _embed(self, text: str) -> list[float]:
        response = self._pc.inference.embed(
            model=EMBEDDING_MODEL,
            inputs=[text],
            parameters={"input_type": "query", "truncate": "END"},
        )
        return response.data[0]["values"]

    def retrieve(self, query: str, top_k: int = 5) -> list[str]:
        """Return a list of text chunks most relevant to the query."""
        if self._pc is None:
            raise RuntimeError("Call set_pc(pc) before retrieve()")
        vector = self._embed(query)
        results = self.index.query(
            vector=vector,
            top_k=top_k,
            namespace=self.namespace,
            include_metadata=True,
        )
        chunks = []
        for match in results.get("matches", []):
            text = match.get("metadata", {}).get("text", "")
            source = match.get("metadata", {}).get("source", "")
            if text:
                chunks.append(f"[{source}]\n{text}" if source else text)
        return chunks

    def upsert_chunks(self, chunks: list[dict], pc: Pinecone | None = None) -> None:
        """
        Embed and upsert document chunks into Pinecone.
        Each chunk: {"id": str, "text": str, "metadata": dict}
        """
        _pc = pc or self._pc
        if _pc is None:
            raise RuntimeError("Provide pc argument or call set_pc(pc) first")

        BATCH = 96
        texts = [c["text"] for c in chunks]

        # Embed in batches
        all_vectors: list[list[float]] = []
        for i in range(0, len(texts), BATCH):
            batch = texts[i: i + BATCH]
            response = _pc.inference.embed(
                model=EMBEDDING_MODEL,
                inputs=batch,
                parameters={"input_type": "passage", "truncate": "END"},
            )
            all_vectors.extend([item["values"] for item in response.data])

        # Build upsert records
        records = [
            {
                "id": chunk["id"],
                "values": vector,
                "metadata": {**chunk.get("metadata", {}), "text": chunk["text"]},
            }
            for chunk, vector in zip(chunks, all_vectors)
        ]

        # Upsert in batches of 100
        for i in range(0, len(records), 100):
            self.index.upsert(vectors=records[i: i + 100], namespace=self.namespace)
