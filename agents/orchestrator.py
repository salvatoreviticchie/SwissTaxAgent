"""
Orchestrator agent — routes user queries to the appropriate specialist agent.
"""

from agents.document_agent import DocumentAgent
from agents.web_agent import WebAgent
from memory.session_memory import SessionMemory


class Orchestrator:
    def __init__(self, pinecone_index, pinecone_client, openrouter_client, model: str = "google/gemma-3-27b-it:free"):
        self.model = model
        self.client = openrouter_client
        self.document_agent = DocumentAgent(pinecone_index, pinecone_client, openrouter_client, model)
        self.web_agent = WebAgent(openrouter_client, model)
        self.memory = SessionMemory()

    def run(self, user_query: str) -> str:
        self.memory.add_message("user", user_query)
        route = self._route(user_query)

        if route == "document":
            response = self.document_agent.run(user_query, self.memory.get_history())
        elif route == "web":
            response = self.web_agent.run(user_query, self.memory.get_history())
        else:
            response = self._direct_answer(user_query)

        self.memory.add_message("assistant", response)
        return response

    def _route(self, query: str) -> str:
        system_prompt = (
            "You are a routing assistant for a Swiss tax AI. "
            "Given a user question, decide which agent should handle it:\n"
            "- 'document': questions about specific figures, deductions, forms, instructions, rates\n"
            "- 'web': questions requiring live deadlines, current-year news, or AFC announcements\n"
            "- 'direct': greetings or very general questions\n"
            "Reply with ONLY one word: document, web, or direct."
        )
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
            max_tokens=10,
            temperature=0,
        )
        return response.choices[0].message.content.strip().lower()

    def _direct_answer(self, query: str) -> str:
        system_prompt = (
            "You are a Swiss tax expert specialising in Canton Vaud (ICC and IFD). "
            "Answer clearly and accurately. If unsure, say so."
        )
        messages = [{"role": "system", "content": system_prompt}]
        messages += self.memory.get_history()[:-1]
        messages.append({"role": "user", "content": query})
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
