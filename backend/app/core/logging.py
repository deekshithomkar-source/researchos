import json
import logging


class ResearchJSONFormatter(logging.Formatter):
    def format(self, record):
        result = {'level': record.levelname, 'event': record.getMessage(), 'logger': record.name}
        for key in ('research_id', 'stage', 'progress', 'partial', 'error_type',
                    'agent', 'model', 'status', 'attempts', 'input_tokens', 'output_tokens', 'reserved_tokens', 'cached',
                    'provider', 'query', 'query_hash', 'http_status', 'returned', 'valid',
                    'rejected', 'duplicates', 'rejection_reasons', 'duration_ms', 'error_code'):
            if hasattr(record, key):
                result[key] = getattr(record, key)
        return json.dumps(result)


def configure_logging():
    logger = logging.getLogger('researchos')
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(ResearchJSONFormatter())
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
