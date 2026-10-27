import re


class SummarizerAgent:
    def summarize(self, topic: str, sources: list[dict]) -> str:
        if not sources:
            return f"No usable evidence was retrieved for {topic}."

        evidence_note = f"Extractive summary of {len(sources)} retrieved scholarly records; this is not a verified claim synthesis."
        insights = []
        for index, source in enumerate(sources[:5], start=1):
            sentence = _first_useful_sentence(
                source.get("abstract") or ""
            )
            if sentence:
                insights.append(f"[{index}] {sentence}")

        if not insights:
            return f"{evidence_note} No abstracts were available; the report contains metadata only."

        return f"{evidence_note} Abstract excerpts: {' '.join(insights) if insights else 'No abstracts available.'}"



def _first_useful_sentence(text: str) -> str:
    clean_text = " ".join(text.split())
    if not clean_text:
        return ""
    sentence = re.split(r"(?<=[.!?])\s+", clean_text)[0]
    if len(sentence) > 300:
        sentence = f"{sentence[:300].rsplit(' ', 1)[0]}..."
    return sentence
