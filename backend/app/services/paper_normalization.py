"""Normalize optional metadata and conservatively deduplicate retrieved works."""
import re
from datetime import datetime, timezone
from app.services.scholar_discovery import author_records
import unicodedata
from difflib import SequenceMatcher
from urllib.parse import urlsplit, unquote

from app.services.search_queries import terms


def clean_text(value):
    return ' '.join(re.sub(r'<[^>]+>', ' ', value if isinstance(value, str) else '').split())


def valid_url(value):
    if not isinstance(value, str) or any(c.isspace() for c in value):
        return None
    try:
        parsed = urlsplit(value)
        return value if parsed.scheme in ('https', 'http') and parsed.hostname and not parsed.username and not parsed.password else None
    except ValueError:
        return None


def normalize_doi(value):
    value = unquote(str(value or '')).strip()
    value = re.sub(r'^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)', '', value, flags=re.I)
    return value.lower() if re.fullmatch(r'10\.\d{4,9}/\S+', value, re.I) else None


def normalize_paper(record, provider):
    title = clean_text(record.get('title'))
    if not title:
        raise ValueError('missing_title')
    doi = normalize_doi(record.get('doi'))
    url = valid_url(record.get('url')) or (f'https://doi.org/{doi}' if doi else None)
    if not url:
        raise ValueError('missing_valid_url_or_doi')
    if record.get('is_retracted') or record.get('source_type') in {'dataset', 'component', 'peer-review'}:
        raise ValueError('not_eligible_scholarly_work')
    abstract = clean_text(record.get('abstract'))
    authors = record.get('authors') or []
    if not isinstance(authors, list):
        authors = []
    year = record.get('year')
    year = year if isinstance(year, int) and 1000 <= year <= 3000 else None
    citations = record.get('citation_count')
    citations = citations if isinstance(citations, int) and citations >= 0 else 0
    retrieved_at=record.get('retrieved_at') or datetime.now(timezone.utc).isoformat()
    scholars=record.get('scholar_records') or author_records(record.get('author_metadata') or [{'name':a} for a in authors],provider,str(record.get('id') or doi or url),retrieved_at)
    return {
        'retrieved_at':retrieved_at, 'scholar_records':scholars,
        'author_identifiers':[i for a in scholars for i in a.get('identifiers',[])],
        'id': str(record.get('id') or doi or url), 'title': title,
        'authors': [clean_text(a) for a in authors if clean_text(a)],
        'year': year, 'abstract': abstract, 'doi': doi, 'url': url,
        'venue': clean_text(record.get('venue')), 'provider': provider,
        'author_details': [dict(given=clean_text(a.get('given')), family=clean_text(a.get('family')))
                           for a in (record.get('author_details') or []) if isinstance(a, dict) and a.get('family')],
        'volume': clean_text(record.get('volume')), 'issue': clean_text(record.get('issue')),
        'pages': clean_text(record.get('pages')),
        'citation_count': citations, 'open_access_pdf': valid_url(record.get('open_access_pdf')),
        'snippet': abstract[:420] if abstract else 'No abstract was supplied by the source.',
        'source_type': record.get('source_type') or 'Scholarly work', 'is_demo': False,
    }


def normalized_title(title):
    return ' '.join(re.findall(r'[^\W_]+', unicodedata.normalize('NFKC', title).casefold()))


def duplicate(paper, existing):
    title = normalized_title(paper['title'])
    for other in existing:
        if paper.get('doi') and normalize_doi(paper['doi']) == normalize_doi(other.get('doi')):
            return True
        candidate = normalized_title(other['title'])
        if title == candidate:
            return True
        # Near-identical long titles only. Avoid merging short or opposing claims.
        if len(title.split()) >= 6 and len(candidate.split()) >= 6:
            if set(re.findall(r'\d+|\bnot\b|\bwithout\b', title)) != set(re.findall(r'\d+|\bnot\b|\bwithout\b', candidate)):
                continue
            if SequenceMatcher(None, title, candidate).ratio() >= .97:
                return True
    return False


def related_to_topic(paper, topic):
    # Broad lexical guard, not a quality score cutoff; absent abstracts are allowed.
    topic_terms = terms(topic)
    evidence_terms = terms(paper['title'] + ' ' + (paper.get('abstract') or ''))
    # A generic AI/ML paper is not evidence about every application domain.
    domains = [
        ({'education', 'educational'}, {'education', 'educational', 'teaching', 'teacher', 'teachers', 'student', 'students', 'university', 'universities', 'pedagogy', 'classroom', 'schools', 'school', 'faculty'}),
        ({'healthcare', 'clinical', 'medicine'}, {'healthcare', 'health', 'clinical', 'medicine', 'medical', 'patient', 'patients', 'hospital', 'diagnosis', 'diagnostic', 'disease'}),
        ({'cybersecurity'}, {'cybersecurity', 'security', 'intrusion', 'attack', 'attacks', 'privacy'}),
    ]
    for triggers, vocabulary in domains:
        if topic_terms & triggers and not evidence_terms & vocabulary:
            return False
    return bool(topic_terms & evidence_terms)
