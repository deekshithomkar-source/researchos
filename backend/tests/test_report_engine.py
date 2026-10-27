"""Document contracts, evidence auditing and authenticated binary exports."""
import io
import json
import unittest
from docx import Document
from app.schemas.research import ResearchRequest, ResearchResult
from app.agents.evidence_analysis import EvidenceExtractor, SupportedGapDetector, extract_findings
from app.services.result_modules import canonical_result
from app.services.report_validation import audit_claims
from app.services.report_docx import DocxReportRenderer
from app.services.report_pdf import PdfReportRenderer
from app.services.citations import CitationGenerator
from app.models.research import ResearchRun
from test_analysis import analysis_paper
import test_foundation


def fixture_result():
    result = ResearchResult(sources=[analysis_paper()])
    result.evidence = EvidenceExtractor().extract(result.sources)
    result.key_findings = extract_findings(result.evidence)
    result.gaps, result.gap_assessment = SupportedGapDetector().analyze(result.evidence)
    return result


class ReportEngineTests(unittest.TestCase):
    def test_settings_change_documents_without_changing_evidence(self):
        structures, depths, citations = {}, {}, {}
        for output in ('academic_report', 'literature_review', 'project_proposal', 'comparative_analysis'):
            for level in ('MCA', 'PhD'):
                for style in ('apa', 'ieee'):
                    request = ResearchRequest(topic='Deep learning', academic_level=level, report_type=output, citation_style=style)
                    report = canonical_result(request, fixture_result()).report
                    structures[output] = tuple(s.name for s in report.sections)
                    depths[level] = next(s.content for s in report.sections if s.name == 'Methodology')
                    citations[style] = report.citations[0].label
                    self.assertTrue(all(c.support == 'supported_excerpt' for c in report.claims))
                    self.assertIn(report.citations[0].label, report.markdown)
                    self.assertIn('## References', report.markdown)
                    self.assertIn('Abstract', structures[output])
                    self.assertIn('Conclusion', structures[output])
        self.assertEqual(len(set(structures.values())), 4)
        self.assertNotEqual(depths['MCA'], depths['PhD'])
        self.assertTrue(citations['apa'].startswith('('))
        self.assertEqual(citations['ieee'], '[1]')

    def test_unsupported_claim_is_flagged(self):
        result = fixture_result()
        result.key_findings[0].statement = 'Invented effect size 99 percent.'
        self.assertEqual(audit_claims(result)[0].support, 'unsupported')
        self.assertIsNotNone(audit_claims(result)[0].warning)
        report = canonical_result(ResearchRequest(topic='Deep learning'), result).report
        self.assertTrue(report.validation_warnings)
        self.assertNotIn('Invented effect size', report.markdown)
        self.assertEqual(report.claims[0].support, 'unsupported')

    def test_export_binaries_share_canonical_sections(self):
        report = canonical_result(ResearchRequest(topic='Deep learning'), fixture_result()).report
        docx = DocxReportRenderer().render(report)
        paragraphs = '\n'.join(p.text for p in Document(io.BytesIO(docx)).paragraphs)
        for section in report.sections:
            self.assertIn(section.name, paragraphs)
        self.assertIn(report.citations[0].reference, paragraphs)
        pdf = PdfReportRenderer().render(report)
        self.assertTrue(pdf.startswith(b'%PDF-'))
        self.assertTrue(pdf.rstrip().endswith(b'%%EOF'))
        self.assertIn(b'/Type /Page', pdf)

    def test_apa_same_author_year_suffixes_are_stable(self):
        first = analysis_paper()
        second = first.model_copy(update={'id':'other', 'title':'A different study'})
        one = CitationGenerator().generate([first, second], 'apa')
        two = CitationGenerator().generate([second, first], 'apa')
        self.assertEqual({c.paper_id:c.label for c in one}, {c.paper_id:c.label for c in two})
        self.assertEqual(len({c.label for c in one}), 2)

    def test_exports_require_completed_owned_run_and_preserve_snapshot(self):
        fixture = test_foundation.FoundationTests(); fixture.setUp()
        try:
            fixture.signup(); run = fixture.submit()
            url = '/api/research/' + run['research_id'] + '/report/export/'
            self.assertEqual(fixture.client.get(url+'pdf').status_code, 409)
            snapshot = fixture_result().model_dump_json()
            with fixture.sessions() as db:
                row = db.get(ResearchRun, run['id']); row.status='completed'; row.result_json=snapshot; db.commit()
            for format in ('pdf','docx'):
                response = fixture.client.get(url+format)
                self.assertEqual(response.status_code, 200, response.text[:100] if response.status_code != 200 else '')
                self.assertIn('attachment;', response.headers['content-disposition'])
                self.assertTrue(response.content.startswith(b'%PDF-' if format == 'pdf' else b'PK'))
            self.assertEqual(fixture.client.get(url+'exe').status_code, 422)
            with fixture.sessions() as db:
                self.assertEqual(db.get(ResearchRun,run['id']).result_json,snapshot)
            fixture.client.post('/api/auth/signout'); fixture.signup(email='not-owner@example.com')
            self.assertEqual(fixture.client.get(url+'pdf').status_code, 404)
        finally:
            fixture.tearDown()
