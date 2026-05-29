from typing import Protocol


class LLMPort(Protocol):
    def generate_answer(self, prompt: str) -> str:
        ...