"""Real academic adapters, safe diagnostics, bounded retry and provider fallback."""
import hashlib
import json
import logging
import os
import threading
import time
from collections import Counter
from contextvars import ContextVar, copy_context
from concurrent.futures import ThreadPoolExecutor
from email.utils import parsedate_to_datetime
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.core.config import settings
from app.services.paper_normalization import normalize_paper, duplicate, related_to_topic

research_context = ContextVar('research_id', default='')
logger = logging.getLogger('researchos.retrieval')
_gate = threading.Lock()
_next_request = {}
_provider_slots = threading.BoundedSemaphore(settings.provider_concurrency)


class ResearchProviderError(RuntimeError):
    def __init__(self, message='Provider unavailable', code='PROVIDER_UNAVAILABLE', status=None, retry_after=0):
        super().__init__(message)
        self.code, self.status, self.retry_after = code, status, retry_after


class ResearchProvider(Protocol):
    name: str
    def search(self, query: str, limit: int) -> list[dict]: ...


def diagnostic(provider, query):
    # Topics/objectives can contain personal information: correlate without raw text.
    return dict(provider=provider, query='[redacted]', query_hash=hashlib.sha256(query.encode()).hexdigest()[:16],
                http_status=None, returned=0, valid=0, rejected=0, duplicates=0,
                rejection_reasons={}, duration_ms=0, error_code=None, error_type=None)


def log_diagnostic(item):
    logger.info('academic_provider_request', extra={'research_id': research_context.get(), **item})


def reserve_request(name):
    interval = 1.05 if name == 'Semantic Scholar' else .25
    with _gate:
        now = time.monotonic()
        delay = _next_request.get(name, 0) - now
        # Don't block a worker for a long Retry-After; allow other providers.
        if delay > 2:
            raise ResearchProviderError('Provider cooling down', 'RATE_LIMITED', 429, delay)
        _next_request[name] = max(now, _next_request.get(name, 0)) + interval
    if delay > 0:
        time.sleep(delay)


def retry_seconds(value):
    try:
        return max(1, float(value))
    except (ValueError, TypeError):
        try:
            return max(1, parsedate_to_datetime(value).timestamp() - time.time())
        except (ValueError, TypeError, OverflowError):
            return 60


class HTTPAcademicProvider:
    """Each HTTP attempt records raw counts, per-record rejections and safe errors."""
    def search(self, query, limit):
        item = diagnostic(self.name, query)
        self.last_diagnostic = item
        started = time.monotonic()
        reasons = Counter()
        try:
            reserve_request(self.name)
            request = self.request(query, limit)
            with urlopen(request, timeout=settings.provider_timeout) as response:
                status = getattr(response, 'status', 200)
                item['http_status'] = status if isinstance(status, int) else 200
                body = response.read(8_000_001)
                if len(body) > 8_000_000:
                    raise ResearchProviderError('Response too large', 'INVALID_PROVIDER_RESPONSE')
                payload = json.loads(body.decode('utf-8'))
            records = self.records(payload)
            if not isinstance(records, list):
                raise ResearchProviderError('Expected a record list', 'INVALID_PROVIDER_RESPONSE')
            item['returned'] = len(records)
            papers = []
            for record in records:
                try:
                    paper = normalize_paper(self.convert(record), self.name)
                    papers.append(paper)
                except ValueError as error:
                    reason = str(error)
                    reasons[reason if reason in {'missing_title', 'missing_valid_url_or_doi', 'not_eligible_scholarly_work'} else 'malformed_record'] += 1
                except (TypeError, KeyError, AttributeError, IndexError):
                    reasons['malformed_record'] += 1
            item['valid'] = len(papers)
            return papers
        except HTTPError as error:
            item['http_status'] = error.code
            code = 'RATE_LIMITED' if error.code == 429 else 'PROVIDER_UNAVAILABLE'
            cooldown = retry_seconds(error.headers.get('Retry-After')) if error.code in (429, 503) else 0
            if cooldown:
                with _gate:
                    _next_request[self.name] = max(_next_request.get(self.name, 0), time.monotonic() + cooldown)
            item['error_code'], item['error_type'] = code, f'HTTP_{error.code}'
            raise ResearchProviderError('Academic provider request failed', code, error.code, cooldown) from error
        except ResearchProviderError as error:
            item['error_code'], item['error_type'] = error.code, type(error).__name__
            item['http_status'] = error.status or item['http_status']
            raise
        except (URLError, OSError, TimeoutError) as error:
            reason = getattr(error, 'reason', error)
            # Numeric OS errors distinguish blocked sockets/DNS/timeouts without
            # logging URLs, headers, response bodies or credential-bearing text.
            os_code = getattr(reason, 'winerror', None) or getattr(reason, 'errno', None)
            item['error_code'] = 'PROVIDER_UNAVAILABLE'
            item['error_type'] = f'{type(error).__name__}:{type(reason).__name__}:{os_code}'
            raise ResearchProviderError() from error
        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as error:
            item['error_code'], item['error_type'] = 'INVALID_PROVIDER_RESPONSE', type(error).__name__
            raise ResearchProviderError('Invalid response', 'INVALID_PROVIDER_RESPONSE') from error
        finally:
            item['rejected'] = sum(reasons.values())
            item['rejection_reasons'] = dict(reasons)
            item['duration_ms'] = round((time.monotonic() - started) * 1000)
            log_diagnostic(item)


class OpenAlexProvider(HTTPAcademicProvider):
    name = 'OpenAlex'
    endpoint = 'https://api.openalex.org/works'

    def request(self, query, limit):
        headers = {'Accept': 'application/json', 'User-Agent': 'ResearchOS/1.0'}
        if os.getenv('OPENALEX_API_KEY'):
            headers['Authorization'] = 'Bearer ' + os.environ['OPENALEX_API_KEY']
        return Request(self.endpoint + '?' + urlencode({'search': query, 'per-page': limit}), headers=headers)

    def records(self, payload):
        return payload['results']

    def convert(self, work):
        positions = {}
        index = work.get('abstract_inverted_index') or {}
        if isinstance(index, dict):
            for word, offsets in index.items():
                if isinstance(offsets, list):
                    for offset in offsets:
                        if isinstance(offset, int) and offset >= 0:
                            positions[offset] = word
        location = work.get('primary_location') or {}
        source = location.get('source') or {}
        return dict(id=work.get('id'), title=work.get('display_name') or work.get('title'),
                    authors=[(a.get('author') or {}).get('display_name') for a in (work.get('authorships') or [])],
                    author_metadata=[dict(name=(a.get('author') or {}).get('display_name'), identifiers={'openalex':(a.get('author') or {}).get('id'),'orcid':(a.get('author') or {}).get('orcid')}, affiliations=[i.get('display_name') for i in a.get('institutions',[]) if isinstance(i,dict)]) for a in (work.get('authorships') or [])],
                    year=work.get('publication_year'), abstract=' '.join(positions[p] for p in sorted(positions)),
                    doi=work.get('doi'), url=location.get('landing_page_url') or work.get('id'),
                    venue=source.get('display_name'), citation_count=work.get('cited_by_count'),
                    open_access_pdf=location.get('pdf_url'), source_type=work.get('type'),
                    is_retracted=work.get('is_retracted', False))


class CrossrefProvider(HTTPAcademicProvider):
    name = 'Crossref'
    endpoint = 'https://api.crossref.org/works'

    def request(self, query, limit):
        params = {'query.bibliographic': query, 'rows': limit}
        if os.getenv('RESEARCH_CONTACT_EMAIL'):
            params['mailto'] = os.environ['RESEARCH_CONTACT_EMAIL']
        return Request(self.endpoint + '?' + urlencode(params),
                       headers={'Accept': 'application/json', 'User-Agent': 'ResearchOS/1.1'})

    def records(self, payload):
        return payload['message']['items']

    def convert(self, work):
        date = work.get('published') or work.get('published-print') or work.get('published-online') or work.get('issued') or {}
        parts = date.get('date-parts') or []
        title = work.get('title') or []
        venue = work.get('container-title') or []
        return dict(id=work.get('DOI') or work.get('URL'), title=title[0] if isinstance(title, list) and title else title,
                    authors=[a.get('name') or ' '.join(p for p in (a.get('given'), a.get('family')) if isinstance(p, str)) for a in (work.get('author') or [])],
                    year=parts[0][0] if parts and parts[0] else None,
                    abstract=work.get('abstract'), doi=work.get('DOI'), url=work.get('URL'),
                    author_metadata=[dict(name=a.get('name') or ' '.join(p for p in (a.get('given'),a.get('family')) if isinstance(p,str)), identifiers={'orcid':a.get('ORCID')},affiliations=[i.get('name') for i in a.get('affiliation',[]) if isinstance(i,dict)]) for a in (work.get('author') or [])],
                    author_details=work.get('author'), volume=work.get('volume'), issue=work.get('issue'), pages=work.get('page'),
                    venue=venue[0] if isinstance(venue, list) and venue else venue,
                    citation_count=work.get('is-referenced-by-count'), source_type=work.get('type'))


class SemanticScholarProvider(HTTPAcademicProvider):
    name = 'Semantic Scholar'
    endpoint = 'https://api.semanticscholar.org/graph/v1/paper/search'

    def request(self, query, limit):
        fields = 'paperId,title,abstract,year,authors,venue,url,citationCount,externalIds,openAccessPdf,publicationTypes'
        headers = {'Accept': 'application/json', 'User-Agent': 'ResearchOS/1.1'}
        if os.getenv('SEMANTIC_SCHOLAR_API_KEY'):
            headers['x-api-key'] = os.environ['SEMANTIC_SCHOLAR_API_KEY']
        return Request(self.endpoint + '?' + urlencode({'query': query, 'limit': limit, 'fields': fields}), headers=headers)

    def records(self, payload):
        return payload['data']

    def convert(self, paper):
        return dict(id=paper.get('paperId'), title=paper.get('title'),
                    authors=[a.get('name') for a in (paper.get('authors') or [])],
                    author_metadata=[dict(name=a.get('name'),identifiers={'semantic_scholar':a.get('authorId')},affiliations=a.get('affiliations') or []) for a in (paper.get('authors') or [])],
                    year=paper.get('year'), abstract=paper.get('abstract'),
                    doi=(paper.get('externalIds') or {}).get('DOI'), url=paper.get('url'),
                    venue=paper.get('venue'), citation_count=paper.get('citationCount'),
                    open_access_pdf=(paper.get('openAccessPdf') or {}).get('url'),
                    source_type=next(iter(paper.get('publicationTypes') or []), None))


class ResilientResearchProvider:
    name = 'OpenAlex / Crossref / Semantic Scholar'

    def __init__(self, primary=None, secondary=None, *, providers=None):
        self.providers = providers if providers is not None else (
            [primary, secondary] if primary is not None or secondary is not None else
            [OpenAlexProvider(), CrossrefProvider(), SemanticScholarProvider()])
        self.providers = [p for p in self.providers if p is not None]
        self.last_warning = None
        self.last_diagnostics = []
        self.last_status = None

    def search(self, query, limit):
        return self.search_many([query], limit, query)

    def search_many(self, queries, limit, topic):
        deadline = time.monotonic() + settings.search_budget_seconds
        def discover(provider):
            child = ResilientResearchProvider(providers=[provider])
            remaining = max(0, deadline - time.monotonic())
            if not _provider_slots.acquire(timeout=remaining):
                item = diagnostic(provider.name, queries[0] if queries else '')
                item.update(error_code='PROVIDER_UNAVAILABLE', error_type='ConcurrencyBudgetExceeded')
                child.last_diagnostics = [item]
                log_diagnostic(item)
                return [], child
            try:
                return child._search_sequential(queries, limit, topic, deadline), child
            except Exception as error:
                item = diagnostic(provider.name, queries[0] if queries else '')
                item.update(error_code='PROVIDER_UNAVAILABLE', error_type=type(error).__name__)
                child.last_diagnostics.append(item)
                log_diagnostic(item)
                return [], child
            finally:
                _provider_slots.release()
        # Each provider owns its mutable diagnostics. Submission order determines
        # merge order so completion timing never changes source identity/citations.
        with ThreadPoolExecutor(max_workers=settings.provider_concurrency) as pool:
            futures = [pool.submit(copy_context().run, discover, provider) for provider in self.providers]
            batches = [future.result() for future in futures]
        papers, diagnostics = [], []
        for batch, child in batches:
            diagnostics.extend(child.last_diagnostics)
            for paper in batch:
                match = next((other for other in papers if duplicate(paper, [other])), None)
                if match is None:
                    paper['origins'] = [{'provider': paper['provider'], 'provider_paper_id': paper['id'], 'url': paper['url']}]
                    papers.append(paper)
                else:
                    match.setdefault('origins', []).append({'provider': paper['provider'], 'provider_paper_id': paper['id'], 'url': paper['url']})
                    authors=match.get('scholar_records',[])+paper.get('scholar_records',[])
                    if not match.get('abstract') and paper.get('abstract'):
                        # Keep evidence provenance with the provider that supplied it.
                        origins = match['origins']
                        match.update(paper)
                        match['origins'] = origins
                    merged_authors={}
                    for author in authors:
                        existing=merged_authors.get(author['author_id'])
                        if existing:
                            existing['affiliations']=list(dict.fromkeys(existing.get('affiliations',[])+author.get('affiliations',[])))
                            for identifier in author.get('identifiers',[]):
                                if identifier not in existing['identifiers']: existing['identifiers'].append(identifier)
                        else: merged_authors[author['author_id']]=dict(author)
                    match['scholar_records']=list(merged_authors.values())
                    match['author_identifiers']=[i for a in merged_authors.values() for i in a.get('identifiers',[])]
        self._finish(papers, diagnostics, limit)
        return papers  # Rank the complete bounded candidate pool before truncation.

    def _search_sequential(self, queries, limit, topic, deadline=None):
        papers, diagnostics, disabled = [], [], set()
        deadline = deadline or (time.monotonic() + settings.search_budget_seconds)
        for query in queries[:5]:
            for provider in self.providers:
                if provider.name in disabled:
                    continue
                for attempt in range(settings.provider_attempts):
                    if time.monotonic() >= deadline:
                        item = diagnostic(provider.name, query)
                        item.update(error_code='PROVIDER_UNAVAILABLE', error_type='SearchBudgetExceeded')
                        diagnostics.append(item)
                        log_diagnostic(item)
                        break
                    started = time.monotonic()
                    item = diagnostic(provider.name, query)
                    try:
                        records = provider.search(query, limit)
                        item = dict(getattr(provider, 'last_diagnostic', item))
                        item['rejection_reasons'] = dict(item['rejection_reasons'])
                        if not isinstance(records, list):
                            raise ResearchProviderError('Expected records', 'INVALID_PROVIDER_RESPONSE')
                        if not isinstance(provider, HTTPAcademicProvider):
                            item.update(returned=len(records), valid=0)
                        reasons = Counter(item['rejection_reasons'])
                        valid = 0
                        for record in records:
                            try:
                                paper = normalize_paper(record, provider.name)
                                if not related_to_topic(paper, topic):
                                    reasons['unrelated_to_topic'] += 1
                                    continue
                                valid += 1
                                if duplicate(paper, papers):
                                    item['duplicates'] += 1
                                else:
                                    papers.append(paper)
                            except (ValueError, TypeError, AttributeError):
                                reasons['invalid_normalized_record'] += 1
                        item.update(valid=valid, rejected=sum(reasons.values()), rejection_reasons=dict(reasons))
                        if not records and item['returned']:
                            item['error_code'] = 'INVALID_PROVIDER_RESPONSE'
                        break
                    except Exception as error:  # Provider boundary: preserve prior evidence on unexpected adapter failures.
                        item = dict(getattr(provider, 'last_diagnostic', item))
                        item['error_code'] = getattr(error, 'code', 'PROVIDER_UNAVAILABLE')
                        item['error_type'] = item.get('error_type') or type(error).__name__
                        item['http_status'] = getattr(error, 'status', None) or item['http_status']
                        stop = (item['error_code'] in ('RATE_LIMITED', 'INVALID_PROVIDER_RESPONSE') or
                                item['http_status'] in (400, 401, 403, 404) or getattr(error, 'retry_after', 0) > 0)
                        if stop or attempt + 1 == settings.provider_attempts:
                            disabled.add(provider.name)
                            break
                        time.sleep(.25 * (attempt + 1))
                    finally:
                        item['duration_ms'] = round((time.monotonic() - started) * 1000)
                        diagnostics.append(item)
                        logger.info('academic_provider_evaluation', extra={'research_id': research_context.get(), **item})
                if len(papers) >= limit or time.monotonic() >= deadline:
                    break
            if len(papers) >= limit or time.monotonic() >= deadline:
                break
        self._finish(papers, diagnostics, limit)
        return papers[:limit]

    def _finish(self, papers, diagnostics, limit):
        errors = {d['error_code'] for d in diagnostics if d['error_code']}
        if papers:
            self.last_status = 'PARTIAL_RESULTS' if len(papers) < limit or errors else 'SUCCESS'
        elif errors:
            self.last_status = next(code for code in ('RATE_LIMITED', 'PROVIDER_UNAVAILABLE', 'INVALID_PROVIDER_RESPONSE') if code in errors)
        elif any(d['returned'] for d in diagnostics):
            self.last_status = 'INSUFFICIENT_EVIDENCE'
        else:
            self.last_status = 'NO_RESULTS'
        warnings = [f"{d['provider']}: {d['error_code']}" for d in diagnostics if d['error_code']]
        if len(papers) < limit:
            warnings.append(f'Retrieved {len(papers)} of {limit} requested sources. No substitute evidence was generated.')
        self.last_warning = ' '.join(dict.fromkeys(warnings)) or None
        self.last_diagnostics = diagnostics

