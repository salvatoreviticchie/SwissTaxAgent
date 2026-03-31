"""
Document agent — retrieves relevant chunks from Pinecone and answers questions
about uploaded tax documents.
"""

from retrieval.pinecone_retriever import PineconeRetriever


class DocumentAgent:
    def __init__(self, pinecone_index, openrouter_client, model: str):
        self.retriever = PineconeRetriever(pinecone_index)
        self.client = openrouter_client
        self.model = model

    def run(self, query: str, history: list) -> str:
        chunks = self.retriever.retrieve(query, top_k=5)

        if not chunks:
            return (
                "I could not find relevant information in the uploaded documents. "
                "Please make sure you have uploaded your tax documents."
            )

        context = "\n\n---\n\n".join(chunks)
        system_prompt = (
            "You are a Swiss tax expert (Canton Vaud, ICC/IFD). "
            "Use ONLY the context below to answer. "
            "If the answer is not in the context, say so.\n\n"
            f"Context:\n{context}"
        )

        messages = [{"role": "system", "content": system_prompt}]
        messages += history[:-1]
        messages.append({"role": "user", "content": query})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()
