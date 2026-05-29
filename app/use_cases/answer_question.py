import re

class AnswerQuestionUseCase:
    def __init__(self, embedder, knowledge_store, llm, prompt_service, image_service, top_k: int):
        self.embedder = embedder
        self.knowledge_store = knowledge_store
        self.llm = llm
        self.prompt_service = prompt_service
        self.image_service = image_service
        self.top_k = top_k

    def _is_greeting(self, text: str) -> bool:
        if not text: return False
        q = text.strip().lower()
        return q in {"hi", "hello", "hey", "hii", "heyy", "good morning", "good afternoon", "good evening"}

    def _clean_answer_text(self, text: str, contexts=None) -> str:
        if not text: return ""

        # 1. Normalize line endings and remove AI filler
        text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        text = re.sub(r'^(here( is|\'s)?( the)? answer[:\-]?\s*)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'^(based on the (provided )?(context|information)[:,\-]?\s*)', '', text, flags=re.IGNORECASE)

        # The "Zendesk Gap Trick": A newline, a non-breaking space, and another newline.
        # This forces the chat widget to render an actual empty line.
        ZD_GAP = "\n&nbsp;\n"

        heading_map = {
            "overview": "**Overview**", "summary": "**Summary**", "steps": "**Steps**",
            "solution": "**Solution**", "resolution": "**Resolution**", "notes": "**Notes**",
            "important": "**Important**", "source": "**Source**", "sources": "**Sources**",
        }

        lines = []
        for raw_line in text.split("\n"):
            line = raw_line.strip()
            
            if not line:
                if lines and lines[-1] != ZD_GAP:
                    lines.append(ZD_GAP)
                continue

            normalized = line.rstrip(":").strip().lower()
            
            # If line is a heading, ensure a gap before it
            if normalized in heading_map:
                if lines and lines[-1] != ZD_GAP:
                    lines.append(ZD_GAP)
                lines.append(heading_map[normalized])
                continue

            # Standardize bullet points
            line = re.sub(r'^[-*•]\s+', '- ', line)
            line = re.sub(r'^(\d+)[\)\-]\s*', r'\1. ', line)

            # Add spacing before lists for readability
            if re.match(r'^\d+\.\s+', line) or re.match(r'^\-\s+', line):
                if lines and lines[-1] not in ["", ZD_GAP]:
                    lines.append(ZD_GAP)

            lines.append(line)

        # Join lines with a single newline; our ZD_GAP already handles the extra spacing
        cleaned = "\n".join(lines)
        
        # Final cleanup: ensure no triple gaps
        cleaned = re.sub(r'(\n&nbsp;\n){2,}', ZD_GAP, cleaned).strip()

        # Handle Source Reference
        if contexts:
            top = contexts[0] if isinstance(contexts, list) and contexts else {}
            meta = top.get("metadata", {}) or {}
            url = meta.get("url") or top.get("url", "")
            title = meta.get("title") or "Reference article"
            if url:
                cleaned = cleaned.rstrip() + "\n\n&nbsp;\n\n**Expand ➤**\n" + f"[{title}]({url})"


        return cleaned

    def execute(self, question: str, visibility_filters=None, chat_history: str=""):
        if self._is_greeting(question):
            return {"answer": "Hey! How can I help you?", "images": []}

        query_embedding = self.embedder.embed_query(question)
        contexts = self.knowledge_store.query_text_chunks(
            query_embedding=query_embedding, top_k=self.top_k, filters=visibility_filters
        )

        if not contexts:
            return {"answer": "I could not find relevant information.", "images": []}

        prompt = self.prompt_service.build_prompt(question=question, contexts=contexts,chat_history=chat_history)
        answer = self.llm.generate_answer(prompt)
        cleaned_answer = self._clean_answer_text(answer, contexts)

        try:
            images = self.knowledge_store.query_images(
                query_embedding=query_embedding, top_k=3, filters=visibility_filters
            )
            formatted_images = self.image_service.format_images(images)
        except:
            formatted_images = []

        return {"answer": cleaned_answer, "images": formatted_images}
