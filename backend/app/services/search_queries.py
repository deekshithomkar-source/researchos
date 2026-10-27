"""Bounded lexical query planning; no invented papers or LLM dependency."""
import re

STOP = set('a an the in on of for and or to with using how what which are is research study investigate explore evaluate impact effect'.split())
TERMS = {
    'ai': 'artificial intelligence', 'ml': 'machine learning',
    'healthcare': 'health care clinical medicine',
    'education': 'education learning teaching',
    'cybersecurity': 'cybersecurity information security',
    'blockchain': 'blockchain distributed ledger',
    'indian': 'india indian',
}


def terms(text):
    words = re.findall(r'[^\W_]+', text.lower(), re.UNICODE)
    expanded = ' '.join(TERMS.get(word, word) for word in words)
    return {word for word in expanded.split() if len(word) > 1 and word not in STOP}


def generate_queries(topic, objective=None, academic_level='', questions=()):
    exact = ' '.join(topic.split())
    words = re.findall(r'[^\W_]+', exact, re.UNICODE)
    core = [word for word in words if word.lower() not in STOP]
    broader = ' '.join(core[:6]) or exact
    objective_words = [w for w in re.findall(r'[^\W_]+', objective or '', re.UNICODE)
                       if w.lower() not in STOP and w.lower() not in terms(exact)]
    domain = f"{broader} {' '.join(objective_words[:3])}".strip()
    if domain == broader:
        domain = f'{broader} applications'
    related = ' '.join(TERMS.get(w.lower(), w) for w in core)
    if related == broader:
        related = f'{related} methods'
    # Level controls depth rather than adding restrictive degree names to search.
    depth = 'systematic review' if any(x in academic_level.lower() for x in ('phd', 'doctoral', 'master', 'mca')) else 'review'
    question = questions[0] if questions else f'What evidence exists for {exact}?'
    question_words = [w for w in re.findall(r'[^\W_]+', question, re.UNICODE)
                      if w.lower() not in STOP and w.lower() not in terms(exact)]
    question_query = f"{broader} {' '.join(question_words[:2])} {depth}"
    candidates = [exact, broader, domain, related, ' '.join(question_query.split())]
    return list(dict.fromkeys(candidates))[:5]
