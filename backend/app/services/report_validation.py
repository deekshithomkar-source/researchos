"""Audit factual claims against retained evidence without semantic invention."""
from app.schemas.analysis import ReportClaim


def audit_claims(result):
    evidence = {e.evidence_id: e for e in result.evidence}
    sources = {p.id: p for p in result.sources}
    claims = []
    for item in [*result.key_findings, *result.gaps]:
        passages = [evidence[e] for e in item.evidence_ids if e in evidence]
        supported = bool(passages) and len(passages) == len(item.evidence_ids)
        supported = supported and set(item.paper_ids) == {e.paper_id for e in passages}
        supported = supported and any(item.statement == e.text for e in passages)
        for passage in passages:
            paper = sources.get(passage.paper_id)
            text = (paper.full_text.text if passage.locator == 'full_text' and paper.full_text else paper.abstract) if paper else ''
            supported = supported and text[passage.start:passage.end] == passage.text
        claims.append(ReportClaim(claim_id=getattr(item, 'finding_id', None) or item.gap_id,
            statement=item.statement, evidence_ids=item.evidence_ids, paper_ids=item.paper_ids,
            support='supported_excerpt' if supported else 'unsupported',
            warning=None if supported else 'Claim is not an exact traceable excerpt; editorial verification required.'))
    return claims
