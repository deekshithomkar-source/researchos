import json


def to_json_text(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def from_json_text(value: str):
    return json.loads(value)
