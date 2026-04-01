"""
Document agent — retrieves relevant chunks from Pinecone and answers questions
about Swiss tax documents (pre-ingested from vd.ch).
"""

from retrieval.pinecone_retriever import PineconeRetriever


class DocumentAgent:
    def __init__(self, pinecone_index, pinecone_client, openrouter_client, model: str):
        self.retriever = PineconeRetriever(pinecone_index, namespace="swiss-tax")
        self.retriever.set_pc(pinecone_client)
        self.client = openrouter_client
        self.model = model

    def run(self, query: str, history: list) -> str:
        chunks = self.retriever.retrieve(query, top_k=5)

        if not chunks:
            return (
                "Je n'ai pas trouvé d'information pertinente dans les documents fiscaux disponibles. "
                "Essayez de reformuler votre question."
            )

        context = "\n\n---\n\n".join(chunks)
        system_prompt = (
            "You are a Swiss tax expert (Canton Vaud, ICC/IFD). "
            "Use ONLY the context below — extracted from official vd.ch documents — to answer. "
            "Always cite the source filename when relevant. "
            "If the answer is not in the context, say so clearly.\n\n"
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
