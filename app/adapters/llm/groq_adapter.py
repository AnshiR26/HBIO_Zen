from groq import Groq
from app.config.settings import GROQ_API_KEY, LLM_MODEL


class GroqAdapter:
    def __init__(self, api_key: str = GROQ_API_KEY, model: str = LLM_MODEL):
        self.api_key = api_key
        self.model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            self._client = Groq(api_key=self.api_key)
        return self._client

    def generate_answer(self, prompt: str) -> str:
        client = self._get_client()
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You answer only from provided document context."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        return response.choices[0].message.content.strip()