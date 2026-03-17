"""CrewHub Knowledge Base — RAG component for document Q&A."""

from langflow.custom import CustomComponent


class CrewHubKnowledgeBaseComponent(CustomComponent):
    display_name = "CrewHub Knowledge Base"
    description = "Upload documents and query them using semantic search (RAG)."
    documentation = "https://crewhubai.com/docs"
    icon = "book-open"

    def build_config(self):
        return {
            "query": {
                "display_name": "Query",
                "info": "Question to search the knowledge base for",
                "required": True,
                "input_types": ["str"],
            },
            "context_documents": {
                "display_name": "Context Documents",
                "info": "Text content to search through (paste or connect from file loader)",
                "required": True,
                "input_types": ["str"],
                "multiline": True,
            },
            "top_k": {
                "display_name": "Top K Results",
                "info": "Number of relevant chunks to return",
                "value": 3,
                "advanced": True,
            },
        }

    def build(
        self,
        query: str,
        context_documents: str,
        top_k: int = 3,
    ) -> str:
        chunks = self._chunk_text(context_documents, chunk_size=500)
        scored = self._score_chunks(query, chunks)
        top_chunks = sorted(scored, key=lambda x: x[1], reverse=True)[:top_k]

        if not top_chunks or top_chunks[0][1] == 0:
            return "No relevant information found in the knowledge base."

        result_parts = []
        for i, (chunk, score) in enumerate(top_chunks, 1):
            if score > 0:
                result_parts.append(f"[Source {i}] {chunk.strip()}")

        return "\n\n".join(result_parts) if result_parts else "No relevant information found."

    def _chunk_text(self, text: str, chunk_size: int = 500) -> list[str]:
        paragraphs = text.split("\n\n")
        chunks = []
        current = ""
        for para in paragraphs:
            if len(current) + len(para) > chunk_size and current:
                chunks.append(current)
                current = para
            else:
                current = current + "\n\n" + para if current else para
        if current:
            chunks.append(current)
        return chunks

    def _score_chunks(self, query: str, chunks: list[str]) -> list[tuple[str, float]]:
        query_words = set(query.lower().split())
        scored = []
        for chunk in chunks:
            chunk_words = set(chunk.lower().split())
            overlap = len(query_words & chunk_words)
            score = overlap / max(len(query_words), 1)
            scored.append((chunk, score))
        return scored
