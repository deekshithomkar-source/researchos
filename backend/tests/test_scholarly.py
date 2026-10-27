import json
import unittest
from unittest.mock import patch
from app.services.scholar_discovery import valid_identifier, discover_scholars
from app.services.paper_normalization import normalize_paper, duplicate
from app.services.research_provider import OpenAlexProvider, CrossrefProvider, SemanticScholarProvider
from app.schemas.research import Source, ResearchResult
from app.services.full_text import parse_open_fulltext, FullTextService
from app.agents.evidence_analysis import EvidenceExtractor, validate_traceability
from app.models.scholarly import ResearchAuthor, paper_authors
from app.models.research import ResearchRun
from app.services.research_artifacts import persist_artifacts
import test_foundation
from test_retrieval import known_paper, crossref_record

class ScholarlyTests(unittest.TestCase):
    def test_provider_identifiers_and_affiliations_are_retained(self):
        work={'id':'https://openalex.org/W1','display_name':'Test paper','doi':'https://doi.org/10.1234/test',
              'authorships':[{'author':{'id':'https://openalex.org/A123','display_name':'Recorded Test Author','orcid':'https://orcid.org/0000-0002-1825-0097'},'institutions':[{'display_name':'Fixture University'}]}]}
        paper=Source.model_validate(normalize_paper(OpenAlexProvider().convert(work),'OpenAlex'))
        self.assertEqual(paper.scholar_records[0].affiliations,['Fixture University'])
        self.assertEqual(len(paper.author_identifiers),2)
        self.assertTrue(paper.retrieved_at)
        raw=crossref_record();raw['author'][0]['ORCID']='https://orcid.org/0000-0002-1825-0097'
        cross=normalize_paper(CrossrefProvider().convert(raw),'Crossref')
        self.assertEqual(cross['scholar_records'][0]['identifiers'][0]['scheme'],'orcid')
        s2=normalize_paper(SemanticScholarProvider().convert({'paperId':'abc','title':'Test','url':'https://www.semanticscholar.org/paper/abc','authors':[{'name':'Recorded Test Author','authorId':'123'}]}),'Semantic Scholar')
        self.assertEqual(s2['scholar_records'][0]['identifiers'][0]['value'],'123')

    def test_identifier_validation_never_guesses(self):
        self.assertIsNone(valid_identifier('orcid','0000-0002-1825-0098'))
        self.assertIsNone(valid_identifier('openalex','https://evil.test/A123'))
        self.assertIsNone(valid_identifier('semantic_scholar','name-not-id'))
        p=Source.model_validate(normalize_paper({**known_paper(),'authors':['Same name'],'scholar_records':[]},'Crossref'))
        q=Source.model_validate(normalize_paper({**known_paper(),'id':'different-paper','authors':['Same name'],'scholar_records':[]},'Crossref'))
        self.assertEqual(len(discover_scholars([p,q])),2)

    def test_duplicate_and_second_normalization_preserve_metadata(self):
        original=normalize_paper(known_paper(),'Crossref')
        second=normalize_paper(original,'Crossref')
        self.assertEqual(second['scholar_records'],original['scholar_records'])
        self.assertEqual(second['retrieved_at'],original['retrieved_at'])
        self.assertTrue(duplicate({**second,'doi':'https://doi.org/'+second['doi'].upper()},[original]))

    def xml(self,license='https://creativecommons.org/licenses/by/4.0/',doi='10.1234/test'):
        return f'<article><front><article-id pub-id-type="doi">{doi}</article-id><license><ext-link href="{license}"/></license></front><body><p>We tested a method. Results show improved outcomes.</p></body></article>'.encode()

    def test_full_text_license_identity_and_traceability(self):
        full=parse_open_fulltext(self.xml(),'10.1234/test','https://www.ebi.ac.uk/europepmc/webservices/rest/PMC1/fullTextXML')
        p=Source.model_validate({**known_paper(),'full_text':full})
        result=ResearchResult(sources=[p]);result.evidence=EvidenceExtractor().extract([p])
        self.assertTrue(result.evidence)
        self.assertTrue(all(e.locator=='full_text' for e in result.evidence))
        validate_traceability(result)
        result.evidence[0].text='Unsupported replacement'
        with self.assertRaises(ValueError): validate_traceability(result)
        for raw in (self.xml(license='https://unknown.test/license'),self.xml(doi='10.1234/wrong'),b'<!DOCTYPE x [<!ENTITY x "attack">]><article/>'):
            with self.assertRaises(ValueError): parse_open_fulltext(raw,'10.1234/test','https://www.ebi.ac.uk/test')

    def test_full_text_provider_failure_preserves_abstract(self):
        p=Source.model_validate(known_paper())
        before=p.abstract
        with patch('app.services.full_text.read',side_effect=OSError): diagnostics=FullTextService(enabled=True).enrich([p])
        self.assertEqual(diagnostics[0].status,'PROVIDER_UNAVAILABLE')
        self.assertEqual(p.abstract,before);self.assertIsNone(p.full_text)

    def test_full_text_identity_lookup_is_required(self):
        p=Source.model_validate({**known_paper(),'doi':'10.1234/test'})
        records={'resultList':{'result':[{'pmcid':'PMC1','doi':'10.1234/test','isOpenAccess':'Y'}]}}
        with patch('app.services.full_text.read',side_effect=[json.dumps(records).encode(),self.xml()]):
            self.assertEqual(FullTextService(enabled=True).enrich([p])[0].status,'FULL_TEXT_RETRIEVED')
        self.assertTrue(p.full_text)

    def test_authors_persist_with_paper_links_and_idempotence(self):
        f=test_foundation.FoundationTests();f.setUp()
        try:
            f.signup();created=f.submit();p=Source.model_validate(known_paper());result=ResearchResult(sources=[p],scholars=discover_scholars([p]))
            with f.sessions() as db:
                run=db.get(ResearchRun,created['id'])
                persist_artifacts(db,run,result);db.commit()
                persist_artifacts(db,run,result);db.commit()
                self.assertEqual(db.query(ResearchAuthor).count(),len(result.scholars))
                self.assertEqual(len(db.execute(paper_authors.select()).all()),len(result.scholars))
        finally:f.tearDown()
