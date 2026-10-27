import json
import unittest
from types import SimpleNamespace
from app.services.intelligence import build_intelligence
from app.services.intelligence_modules import courses_module
from app.agents.evidence_analysis import gap_categories
from test_intelligence import resources


class SpecializedModuleTests(unittest.TestCase):
    def build(self, topic='AI in healthcare', level='MCA', discover=resources):
        return build_intelligence(SimpleNamespace(topic=topic, objective='Compare methods',
            academic_level=level, research_id='fixture', report_type='academic_report'),
            {'sources': [{'id': 'p1', 'title': 'Fixture study'}],
             'key_findings': [{'finding_id': 'f1', 'paper_ids': ['p1']},
                              {'finding_id': 'invalid', 'paper_ids': ['unknown']}], 'gaps': []}, discover)

    def test_topic_and_level_matrix(self):
        for topic in ('AI in healthcare', 'Cybersecurity', 'Medieval history'):
            outcomes = set()
            for level in ('Undergraduate', 'MCA', "Master's", 'PhD'):
                value = self.build(topic, level)
                outcomes.add(value['projects'][1]['expected_outcome'])
                self.assertEqual(value['projects'][1]['finding_ids'], ['f1'])
                self.assertEqual(value['projects'][1]['topic'], topic)
                self.assertIn(topic, value['career_paths'][0]['title'])
                self.assertEqual(value['next_steps'][0]['kind'], 'paper')
                self.assertEqual([s['priority'] for s in value['next_steps']], list(range(1,len(value['next_steps'])+1)))
            self.assertEqual(len(outcomes), 4)
        values = [self.build(topic) for topic in ('AI in healthcare', 'Cybersecurity', 'Medieval history')]
        self.assertEqual(len({json.dumps(v['skills']['Technical']) for v in values}), 3)
        self.assertEqual(len({v['suggested_internship_roles'][1]['title'] for v in values}), 3)

    def test_invalid_courses_do_not_replace_or_break_other_modules(self):
        def discovery(terms):
            value = resources(terms)
            value['courses'] = {'status': 'verified', 'items': [{'title': 'Incomplete course'}]}
            return value
        value = self.build(discover=discovery)
        self.assertEqual(value['resources']['courses']['status'], 'invalid_response')
        self.assertEqual(value['resources']['courses']['items'], [])
        self.assertTrue(value['projects'])
        self.assertFalse(any(s['kind'] == 'course' for s in value['next_steps']))

    def test_discovery_outage_preserves_generated_guidance(self):
        def failure(terms): raise TimeoutError('provider timeout')
        value = self.build(discover=failure)
        self.assertTrue(value['skills'])
        self.assertTrue(value['career_paths'])
        self.assertTrue(all(v['status'] == 'provider_unavailable' and not v['items'] for v in value['resources'].values()))

    def test_course_reason_and_level_derive_from_metadata(self):
        item = dict(id='fixture', title='Fixture course', provider='MIT', difficulty='Beginner',
                    skills=['Python'], url='https://ocw.mit.edu/courses/fixture/',
                    checked_at='2026-01-01T00:00:00Z', classification_basis='Suggested classification')
        course = courses_module([item], SimpleNamespace(topic='Healthcare', academic_level='MCA'))[0]
        self.assertEqual(course['level'], 'Beginner')
        self.assertIn('Healthcare', course['reason_for_recommendation'])
        self.assertIn('MCA', course['reason_for_recommendation'])

    def test_population_gaps_require_explicit_language(self):
        self.assertIn('understudied_population', gap_categories('Underrepresented populations need further study.'))
        self.assertNotIn('understudied_population', gap_categories('The study included 200 patients.'))
        self.assertNotIn('understudied_population', gap_categories('No underrepresented populations were identified.'))
