# Project Overview

## Project Title
ResearchOS: An Autonomous Research Agent for Academic Intelligence

## Problem Statement
Students waste time collecting information from multiple sources, arranging notes, preparing summaries, and converting research into a report format. This project automates the research workflow.

## Proposed Solution
The system accepts a topic, creates purpose-specific research questions, retrieves
scholarly metadata, deduplicates and evaluates sources, maps evidence to questions,
generates a cited report, and saves the research history.

## Modules

1. Research Input Module
2. Planning Agent
3. Scholarly Search Provider
4. Source Verification Agent
5. Evidence Summarizer
6. Report Generator Agent
7. Research History Module
8. Source Review and Export Dashboard

## Current MVP

- Academic report, literature review, and project proposal outputs
- Semantic Scholar metadata and abstract retrieval
- Honest offline demo fallback
- Source deduplication and credibility signals
- APA and IEEE reference formatting
- Markdown report export

## Known Limitations

- Synthesis currently works from abstracts and metadata, not complete papers.
- Quality scoring is heuristic and does not replace peer-review assessment.
- Reports require human review before academic submission.

## Future Scope

- Permission-aware PDF ingestion
- Optional LLM synthesis with claim-level citations
- PDF/DOCX export
- Literature survey table
- Plagiarism checker
- Student login
- Teacher review dashboard
