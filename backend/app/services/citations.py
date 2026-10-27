"""APA/IEEE references from provider-supplied metadata only."""
import re
from collections import Counter
from app.schemas.analysis import Citation


def initials(given):
    return ' '.join(part[0].upper() + '.' for part in re.findall(r'[^\W\d_]+', given or ''))


def author_names(paper, style):
    details = getattr(paper, 'author_details', None) or []
    if details and all(d.get('family') for d in details):
        if style == 'apa':
            return [f"{d['family']}, {initials(d.get('given'))}".rstrip(', ') for d in details]
        return [f"{initials(d.get('given'))} {d['family']}".strip() for d in details]
    # Do not guess family names from international display names.
    return list(paper.authors)


class CitationGenerator:
    def generate(self, papers, style):
        if style not in ('apa', 'ieee'):
            raise ValueError('Unsupported citation style')
        if style == 'apa':
            papers = sorted(papers, key=lambda p: (tuple(author_names(p, 'apa')), p.year or 0, p.title.casefold(), p.id))
        citations = []
        bases = []
        for paper in papers:
            details = getattr(paper, 'author_details', None) or []
            names = [d['family'] for d in details if d.get('family')] if details else paper.authors
            author = (names[0] + ' et al.' if len(names) >= 3 else ' & '.join(names)) if names else paper.title
            bases.append(f'{author}, {paper.year or "n.d."}')
        counts, occurrences = Counter(bases), Counter()
        for index, paper in enumerate(papers, 1):
            names = author_names(paper, style)
            missing = [key for key, value in [('authors', names), ('year', paper.year), ('venue', paper.venue)] if not value]
            details = getattr(paper, 'author_details', None) or []
            if names and not details:
                missing.append('structured_author_names')
            link = f'https://doi.org/{paper.doi}' if paper.doi else paper.url or ''
            volume, issue, pages = (getattr(paper, key, None) or '' for key in ('volume', 'issue', 'pages'))
            if style == 'apa':
                if len(names) > 20:
                    names = names[:19] + ['…', names[-1]]
                authors = (', '.join(names[:-1]) + ', & ' + names[-1]) if len(names) > 1 else (names[0] if names else '')
                if len(author_names(paper, style)) > 20:
                    authors = ', '.join(names[:-2]) + ', . . . ' + names[-1]
                base = bases[index-1]
                suffix = chr(97 + occurrences[base]) if counts[base] > 1 else ''
                occurrences[base] += 1
                label = '(' + base + suffix + ')'
                date = str(paper.year or 'n.d.') + suffix
                venue = paper.venue
                if volume:
                    venue += f', {volume}' + (f'({issue})' if issue else '')
                if pages:
                    venue += f', {pages}'
                head = f'{authors} ({date}). {paper.title}.' if authors else f'{paper.title}. ({date}).'
                reference = ' '.join(x for x in (head, venue + '.' if venue else '', link) if x)
            else:
                label = f'[{index}]'
                authors = ', '.join(names[:6]) + (', et al.' if len(names) > 6 else '')
                parts = [authors, f'“{paper.title}”', paper.venue,
                         f'vol. {volume}' if volume else '', f'no. {issue}' if issue else '',
                         f'pp. {pages}' if pages else '', str(paper.year) if paper.year else '']
                reference = label + ' ' + ', '.join(p for p in parts if p) + '. ' + link
            citations.append(Citation(paper_id=paper.id, style=style, label=label,
                                      reference=reference.strip(), metadata_missing=missing))
        return sorted(citations, key=lambda c: c.reference.casefold()) if style == 'apa' else citations
