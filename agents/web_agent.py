"""
Web agent — fetches up-to-date Swiss tax information from official sources.
"""

import httpx
from bs4 import BeautifulSoup


OFFICIAL_SOURCES = [
    "https://www.vd.ch/themes/etat-droit-finances/impots/",
    "https://www.estv.admin.ch/estv/fr/home.html",
]


class WebAgent:
    def __init__(self, openrouter_client, model: str):
        self.client = openrouter_client
        self.model = model

    def run(self, query: str, history: list) -> str:
        fetched_text = self._fetch_sources()

        system_prompt = (
            "You are a Swiss tax expert (Canton Vaud, ICC/IFD). "
            "Use the web content below to answer the user's question. "
            "Cite the source URL when relevant.\n\n"
            f"Web content:\n{fetched_text[:6000]}"
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

    def _fetch_sources(self) -> str:
        texts = []
        for url in OFFICIAL_SOURCES:
            try:
                resp = httpx.get(url, timeout=10, follow_redirects=True)
                soup = BeautifulSoup(resp.text, "html.parser")
                texts.append(f"[{url}]\n{soup.get_text(separator=' ', strip=True)[:2000]}")
            except Exception:
                continue
        return "\n\n".join(texts) if texts else "No web content available."
