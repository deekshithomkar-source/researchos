from math import log10


class VerifierAgent:
    """Apply transparent, metadata-based quality signals to each source."""

    def evaluate(self, sources: list[dict]) -> list[dict]:
        unique_sources = {}
        for source in sources:
            key = source.get("doi") or source.get("url") or source.get("title", "").lower()
            if not key or key in unique_sources:
                continue
            evaluated = {**source}
            evaluated.update(self._score(source))
            unique_sources[key] = evaluated

        return sorted(
            unique_sources.values(),
            key=lambda item: (item["credibility_score"], item.get("citation_count", 0)),
            reverse=True,
        )

    def _score(self, source: dict) -> dict:
        if source.get("is_demo"):
            return {
                "credibility_score": 0,
                "credibility_label": "Demo only",
                "quality_signals": ["Not a real citation"],
            }

        score = 35
        signals = ["Indexed scholarly record"]
        if source.get("abstract"):
            score += 15
            signals.append("Abstract available")
        if source.get("doi"):
            score += 15
            signals.append("DOI available")
        if source.get("venue") and source["venue"] != "Unknown venue":
            score += 10
            signals.append("Publication venue identified")
        if source.get("year"):
            score += 5
        if source.get("open_access_pdf"):
            score += 5
            signals.append("Open-access copy available")

        citations = source.get("citation_count", 0)
        if citations:
            score += min(15, round(log10(citations + 1) * 6))
            signals.append(f"Cited by {citations} works")

        score = min(score, 100)
        label = "High" if score >= 75 else "Moderate" if score >= 55 else "Basic"
        return {
            "credibility_score": score,
            "credibility_label": label,
            "quality_signals": signals,
        }
