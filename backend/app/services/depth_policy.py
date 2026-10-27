"""Academic-depth policies affect tasks and analysis, never the retrieved facts."""
from dataclasses import dataclass, replace

@dataclass(frozen=True)
class DepthPolicy:
    key: str
    focus: str
    question: str
    task: str
    outcome: str
    skills: tuple[str, ...]
    excerpts: int
    difficulty: str
    technical_complexity: str = ''
    explanation_style: str = ''
    methodology: tuple[str, ...] = ()
    evidence_requirements: tuple[str, ...] = ()
    learning_recommendations: tuple[str, ...] = ()
    report_heading: str = ''
    gap_review: str = ''
    career_preparation: tuple[str, ...] = ()

    def instruction(self):
        return (self.focus + '. Explanation: ' + self.explanation_style +
            ' Technical complexity: ' + self.technical_complexity +
            ' Methodology: ' + '; '.join(self.methodology) +
            ' Evidence requirements: ' + '; '.join(self.evidence_requirements) +
            ' Gap review: ' + self.gap_review +
            ' Never invent evidence, outcomes, differences or field-wide novelty to meet these requirements.')


def _base_policy(level):
    value = level.strip().lower()
    if any(x in value for x in ('phd', 'ph.d', 'doctoral', 'research scholar')):
        return DepthPolicy('doctoral', 'critical novelty, validity and falsifiability',
            'Which assumptions, datasets and threats to validity constrain a defensible original contribution?',
            'Design a falsifiable study addressing a supported limitation',
            'A preregistered protocol with competing hypotheses, validity threats and a novelty audit; no novelty claim without further review.',
            ('Causal identification', 'Power analysis', 'Preregistration', 'Novelty assessment'), 6, 'Research specialization')
    if 'master' in value or value in ('msc', 'm.sc', 'mtech', 'm.tech'):
        return DepthPolicy('masters', 'critical comparison of methods and robustness',
            'How do study designs, datasets and uncertainty estimates affect agreement between reported results?',
            'Compare research methods and design a robustness evaluation',
            'A comparative methods matrix and reproducible sensitivity-analysis protocol.',
            ('Sensitivity analysis', 'Study design comparison', 'Uncertainty quantification'), 4, 'Advanced')
    if 'mca' in value:
        return DepthPolicy('mca', 'critical applied implementation and evaluation',
            'Which designs, datasets and evaluation methods support a reproducible software implementation?',
            'Implement and evaluate a reproducible research prototype',
            'A tested prototype specification with baseline metrics, data checks and reproducibility instructions.',
            ('Software architecture', 'Baseline evaluation', 'Integration testing'), 3, 'Intermediate')
    return DepthPolicy('undergraduate', 'foundations and guided interpretation',
        'How are the main methods applied and evaluated, and what prerequisite concepts explain them?',
        'Reproduce a guided example and explain its assumptions',
        'An annotated notebook and glossary separating observations from assumptions.',
        ('Scientific vocabulary', 'Descriptive statistics', 'Guided replication'), 1, 'Beginner')


DETAILS = {
    'undergraduate': dict(
        technical_complexity='Introductory concepts and one guided example; define unfamiliar terms.',
        explanation_style='Plain language; separate what the paper reports from what the learner assumes.',
        methodology=('Create a glossary from paper terminology', 'Annotate one source and reproduce a small supervised example'),
        evidence_requirements=('Trace each observation to a cited passage', 'Distinguish an example from a general conclusion'),
        learning_recommendations=('Learn prerequisite vocabulary before algorithms', 'Use introductory course exercises with a worked example'),
        report_heading='Guided interpretation',
        gap_review='Explain a reported limitation in plain language and identify what remains unknown; do not claim novelty.',
        career_preparation=('Build an annotated reading portfolio', 'Demonstrate a supervised introductory project')),
    'mca': dict(
        technical_complexity='Algorithms, interfaces, system architecture, data pipelines and measurable evaluation.',
        explanation_style='Implementation-oriented explanations with inputs, processing steps, outputs and evaluation criteria.',
        methodology=('Specify algorithm inputs and system interfaces', 'Check dataset access, train/test separation and leakage', 'Define baselines, metrics and integration tests'),
        evidence_requirements=('Locate implementation and evaluation details in the sources', 'Mark missing algorithms, datasets or metrics as unknown'),
        learning_recommendations=('Practice implementing and testing algorithms', 'Use verified courses to build a reproducible baseline and data pipeline'),
        report_heading='Implementation and evaluation plan',
        gap_review='Translate supported implementation or evaluation limitations into testable prototype requirements; proposed improvements are not achieved results.',
        career_preparation=('Build a tested software portfolio', 'Document architecture, dataset checks and baseline evaluation')),
    'masters': dict(
        technical_complexity='Comparative study design, uncertainty and sensitivity analysis.',
        explanation_style='Analytical synthesis distinguishing comparable results from differences in design or population.',
        methodology=('Construct a study-design comparison matrix', 'Compare populations, measures and limitations', 'Plan robustness and sensitivity checks'),
        evidence_requirements=('Use multiple distinct studies for cross-paper conclusions', 'Check comparable populations and outcome definitions before comparison'),
        learning_recommendations=('Study research design and uncertainty estimation', 'Extend course exercises into reproducible method comparisons'),
        report_heading='Methodological comparison and robustness',
        gap_review='Assess whether limitations recur across comparable studies; distinguish limited search coverage from a knowledge gap.',
        career_preparation=('Build a reproducible comparative study portfolio', 'Explain methodological choices and sensitivity results')),
    'doctoral': dict(
        technical_complexity='Validity, competing explanations, causal assumptions, reproducibility and experimental design.',
        explanation_style='Critical argument with explicit assumptions, counterevidence and limits on inference.',
        methodology=('Audit internal and external validity', 'Examine opposing findings and competing explanations', 'Specify reproducibility checks and a falsifiable experimental protocol'),
        evidence_requirements=('Seek original methods and full text before strong validity claims', 'Verify comparability of conflicting findings', 'Do not assert novelty without broader literature review'),
        learning_recommendations=('Audit reproducibility and competing hypotheses', 'Use foundational courses only to close prerequisites, then pursue methodological specialization'),
        report_heading='Validity and experimental design audit',
        gap_review='Separate author-reported gaps, supported inferences and speculative directions; test alternative explanations before proposing a contribution.',
        career_preparation=('Develop a reproducibility and validity portfolio', 'Prepare a defensible research proposal with competing hypotheses')),
}


def depth_policy(level):
    base = _base_policy(level)
    return replace(base, **DETAILS[base.key])
