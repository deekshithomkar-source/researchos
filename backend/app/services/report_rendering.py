"""Shared canonical document traversal; no retrieval or model calls during export."""
import re


def document_blocks(report):
    yield 'title', report.title
    yield 'paragraph', f'{report.academic_level} | {report.output_type.replace("_", " ").title()} | {report.citation_style.upper()}'
    for section in report.sections:
        yield 'heading', section.name
        if not section.complete:
            yield 'paragraph', 'Incomplete evidence coverage.'
        for line in section.content.splitlines():
            line = line.strip()
            if not line:
                continue
            kind = 'subheading' if line.startswith('### ') else 'paragraph'
            line = re.sub(r'^#{1,6}\s+|^>\s?', '', line)
            yield kind, line.replace('**', '').replace('`', '')
    yield 'heading', 'References'
    for citation in report.citations:
        yield 'paragraph', citation.reference
    if report.validation_warnings:
        yield 'heading', 'Editorial validation notes'
        for warning in report.validation_warnings:
            yield 'paragraph', warning
