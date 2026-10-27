"""Retain provider assertions; never resolve identity from a name match alone."""
import hashlib
import re
from datetime import datetime, timezone

def valid_identifier(scheme,value):
    if not isinstance(value,str): return None
    if scheme=='orcid':
        value=value.removeprefix('https://orcid.org/').removeprefix('http://orcid.org/')
        if not re.fullmatch(r'\d{4}-\d{4}-\d{4}-\d{3}[\dX]',value): return None
        digits=value.replace('-',''); total=0
        for digit in digits[:15]: total=(total+int(digit))*2
        check=(12-total%11)%11
        return value if digits[-1]==('X' if check==10 else str(check)) else None
    if scheme=='openalex':
        value=value.removeprefix('https://openalex.org/')
        return value if re.fullmatch(r'A\d+',value) else None
    if scheme=='semantic_scholar':
        return value if value.isdecimal() else None

def author_records(records,provider,paper_id,retrieved_at):
    output=[]
    for position,raw in enumerate(records or []):
        if not isinstance(raw,dict): continue
        name=' '.join(str(raw.get('name') or '').split())
        if not name: continue
        identifiers=[]
        for scheme,value in (raw.get('identifiers') or {}).items():
            value=valid_identifier(scheme,value)
            if value: identifiers.append({'scheme':scheme,'value':value})
        preferred=next((i for i in identifiers if i['scheme']=='orcid'), identifiers[0] if identifiers else None)
        identity=(preferred['scheme']+':'+preferred['value']) if preferred else f'{provider}:{paper_id}:{position}'
        output.append(dict(author_id=hashlib.sha256(identity.encode()).hexdigest()[:32],name=name,
            identifiers=identifiers,affiliations=list(dict.fromkeys(a.strip() for a in raw.get('affiliations',[]) if isinstance(a,str) and a.strip())),
            provider=provider,related_paper_ids=[],retrieved_at=retrieved_at))
    return output

def discover_scholars(papers):
    from app.schemas.scholarly import Scholar
    scholars={}
    for paper in papers:
        for raw in paper.scholar_records:
            author=Scholar.model_validate(raw)
            if author.author_id not in scholars:
                author.related_paper_ids=[]
                scholars[author.author_id]=author
            target=scholars[author.author_id]
            if paper.id not in target.related_paper_ids: target.related_paper_ids.append(paper.id)
            target.affiliations=list(dict.fromkeys(target.affiliations+author.affiliations))
            for identifier in author.identifiers:
                if identifier not in target.identifiers: target.identifiers.append(identifier)
    return list(scholars.values())
