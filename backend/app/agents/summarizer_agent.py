import re


class SummarizerAgent:
    def summarize(self, topic: str, sources: list[dict]) -> str:
        if not sources:
            return f"No usable evidence was retrieved for {topic}."

        demo_only = all(source.get("is_demo") for source in sources)
        evidence_note = (
            "This is an offline demonstration and must not be treated as a cited literature review."
            if demo_only
            else f"This synthesis is based on {len(sources)} scholarly records."
        )
        insights = []
        for source in sources[:5]:
            sentence = _first_useful_sentence(
                source.get("abstract") or source.get("snippet") or ""
            )
            if sentence:
                insights.append(sentence)

        return (
            f"{evidence_note} The collected evidence frames “{topic}” through its "
            f"foundations, applications, implementation concerns, and open research questions. "
            f"{' '.join(insights)}"
        ).strip()


def _first_useful_sentence(text: str) -> str:
    clean_text = " ".join(text.split())
    if not clean_text:
        return ""
    sentence = re.split(r"(?<=[.!?])\s+", clean_text)[0]
    if len(sentence) > 300:
        sentence = f"{sentence[:300].rsplit(' ', 1)[0]}..."
    return sentence
