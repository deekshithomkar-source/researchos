"""Bounded open-access body retrieval. No arbitrary publisher/PDF fetching or paywall access."""
import json
import re
import time
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError
from xml.etree import ElementTree
from app.schemas.scholarly import FullText, RetrievalMetadata
from app.services.paper_normalization import normalize_doi
from app.services.research_provider import reserve_request, ResearchProviderError, _gate, _next_request, retry_seconds

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): return None

def read(url):
    reserve_request('Europe PMC')
    with build_opener(NoRedirect).open(Request(url,headers={'User-Agent':'ResearchOS/1.2'}),timeout=6) as response:
        data=response.read(2_000_001)
        if len(data)>2_000_000: raise ValueError('Oversized response')
        return data

def parse_open_fulltext(body,doi,url):
    text=body.decode('utf-8')
    if '<!ENTITY' in text.upper(): raise ValueError('XML entities forbidden')
    root=ElementTree.fromstring(text)
    article_dois=[normalize_doi(e.text) for e in root.findall('.//article-id') if e.get('pub-id-type')=='doi']
    if normalize_doi(doi) not in article_dois: raise ValueError('Full text DOI mismatch')
    licenses=[]
    for element in root.findall('.//license'):
        licenses.extend(str(v) for node in element.iter() for k,v in node.attrib.items() if k.endswith('href'))
        licenses.extend(re.findall(r'https?://[^\s<>]+',' '.join(element.itertext())))
    license_url=next((u for u in licenses if re.fullmatch(r'https?://creativecommons\.org/(?:licenses/by(?:-sa)?/\d\.\d/|publicdomain/zero/1\.0/)',u)),None)
    if not license_url: raise ValueError('No supported reuse license')
    paragraphs=[' '.join(''.join(p.itertext()).split()) for p in root.findall('./body//p')]
    full='\n\n'.join(p for p in paragraphs if p)
    if not full: raise ValueError('No article body')
    return FullText(text=full[:100000],url=url,license_url=license_url,
        retrieved_at=datetime.now(timezone.utc).isoformat(),truncated=len(full)>100000)

class FullTextService:
    def __init__(self,enabled=False,max_papers=2): self.enabled,self.max_papers=enabled,max_papers
    def enrich(self,papers):
        diagnostics=[]
        if not self.enabled: return diagnostics
        for paper in [p for p in papers if p.doi][:self.max_papers]:
            started=time.monotonic(); status='NO_OPEN_FULL_TEXT'; http_status=None
            try:
                url='https://www.ebi.ac.uk/europepmc/webservices/rest/search?'+urlencode({'query':'DOI:"'+paper.doi+'"','format':'json','pageSize':3})
                payload=json.loads(read(url));http_status=200
                for row in payload.get('resultList',{}).get('result',[]):
                    pmcid=row.get('pmcid','')
                    if row.get('isOpenAccess')!='Y' or normalize_doi(row.get('doi'))!=paper.doi or not re.fullmatch(r'PMC\d+',pmcid): continue
                    url=f'https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML'
                    paper.full_text=parse_open_fulltext(read(url),paper.doi,url)
                    status='FULL_TEXT_RETRIEVED';break
            except HTTPError as error:
                http_status=error.code;status='RATE_LIMITED' if error.code==429 else 'PROVIDER_UNAVAILABLE'
                if error.code in (429,503):
                    with _gate: _next_request['Europe PMC']=time.monotonic()+retry_seconds(error.headers.get('Retry-After'))
            except ResearchProviderError as error: status=error.code
            except (ValueError,ElementTree.ParseError): status='UNUSABLE_OR_UNLICENSED_FULL_TEXT'
            except (OSError,TimeoutError): status='PROVIDER_UNAVAILABLE'
            diagnostics.append(RetrievalMetadata(provider='Europe PMC',paper_id=paper.id,status=status,http_status=http_status,duration_ms=round((time.monotonic()-started)*1000)))
            if status in ('RATE_LIMITED','PROVIDER_UNAVAILABLE'): break
        return diagnostics
