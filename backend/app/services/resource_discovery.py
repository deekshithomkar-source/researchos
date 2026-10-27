"""Bounded resource discovery. Failed verification never produces a recommended URL."""
import json
import re
import threading
import time
from datetime import datetime, timezone
from urllib.parse import urlencode, urlparse, quote
from urllib.request import Request, build_opener, HTTPRedirectHandler
from concurrent.futures import ThreadPoolExecutor

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

def fetch(url, json_response=True):
    if urlparse(url).scheme != 'https' or urlparse(url).hostname not in {'huggingface.co', 'ocw.mit.edu', 'remotive.com'}:
        raise ValueError('Untrusted resource host')
    with build_opener(NoRedirect).open(Request(url, headers={'User-Agent': 'ResearchOS/1.0 resource discovery'}), timeout=6) as response:
        raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError('Oversized provider response')
        text = raw.decode('utf-8')
        return json.loads(text) if json_response else text

COURSES = [
    ('Introduction to Computer Science and Programming in Python', '6-0001-introduction-to-computer-science-and-programming-in-python-fall-2016', 'Beginner', ['Python', 'Programming']),
    ('Introduction to Machine Learning', '6-036-introduction-to-machine-learning-fall-2020', 'Intermediate', ['Machine learning', 'Model evaluation']),
]
_job_lock = threading.Lock()
_job_cache = (0, [])

def discover(kind, terms):
    checked = datetime.now(timezone.utc).isoformat()
    records = []
    try:
        if kind == 'datasets':
            seen = set()
            for term in terms[:2]:
                rows = fetch('https://huggingface.co/api/datasets?' + urlencode({'search': term, 'limit': 3, 'full': 'true'}))
                if not isinstance(rows, list):
                    raise ValueError('Invalid dataset response')
                for row in rows:
                    name = row.get('id', '')
                    if not re.fullmatch(r'[\w.-]+/[\w.-]+', name) or name in seen:
                        continue
                    seen.add(name)
                    url = 'https://huggingface.co/datasets/' + quote(name, safe='/')
                    page = fetch(url, False)
                    if name.lower() not in page.lower():
                        continue
                    card = row.get('cardData') or {}
                    if not isinstance(card, dict):
                        card = {}
                    records.append(dict(id=name, title=name, provider='Hugging Face', url=url,
                        description=card.get('pretty_name') or 'Dataset repository; inspect its dataset card before use.',
                        license=card.get('license'), relevance=f'Repository search matched {term}; suitability requires review.',
                        verification='provider_metadata_and_live_page', checked_at=checked))
        elif kind == 'courses':
            for title, slug, difficulty, skills in COURSES:
                if 'Machine learning' in skills and not re.search(r'\b(learning|artificial|ai|data)\b', ' '.join(terms), re.I):
                    continue
                url = 'https://ocw.mit.edu/courses/' + slug + '/'
                page = fetch(url, False)
                if title.lower() not in page.lower():
                    continue
                records.append(dict(id=slug, title=title, provider='MIT OpenCourseWare', url=url,
                    difficulty=difficulty, skills=skills, duration=None,
                    classification_basis='Suggested difficulty and skill mapping; verified course identity.',
                    verification='live_official_course_page', checked_at=checked))
        else:
            # No vacancies are generated. Only explicit internship records in the current feed qualify.
            global _job_cache
            with _job_lock:
                if time.monotonic() - _job_cache[0] > 21600:
                    payload = fetch('https://remotive.com/api/remote-jobs')
                    if not isinstance(payload.get('jobs'), list):
                        raise ValueError('Invalid jobs response')
                    _job_cache = (time.monotonic(), payload['jobs'])
                jobs = _job_cache[1]
            for row in jobs:
                title = row.get('title', '')
                url = row.get('url', '')
                if not re.search(r'\bintern(ship)?\b', title, re.I) or not any(t.lower() in title.lower() for t in terms):
                    continue
                if urlparse(url).hostname != 'remotive.com':
                    continue
                page = fetch(url, False)
                if title.lower() not in page.lower() or re.search(r'position (is |has been )?(closed|filled)|job has expired', page, re.I):
                    continue
                records.append(dict(id=str(row['id']), title=title, provider='Remotive', company=row.get('company_name'),
                    url=url, location=row.get('candidate_required_location'), checked_at=checked,
                    verification='current_provider_feed_and_live_page', availability_note='Listed at check time; confirm availability with employer.'))
                if len(records) == 3:
                    break
        return {'status': 'verified' if records else 'no_verified_matches', 'items': records, 'checked_at': checked}
    except Exception as error:
        return {'status': 'partial' if records else 'provider_unavailable', 'items': records,
                'checked_at': checked, 'error_type': type(error).__name__}

def discover_resources(terms):
    with ThreadPoolExecutor(max_workers=3) as pool:
        return dict(zip(('datasets', 'courses', 'active_internships'), pool.map(lambda kind: discover(kind, terms), ('datasets', 'courses', 'active_internships'))))
