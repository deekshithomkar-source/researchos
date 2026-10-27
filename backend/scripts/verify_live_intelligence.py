"""Opt-in live provider verification. Run from backend; requires internet access."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.resource_discovery import discover_resources

if __name__ == '__main__':
    results = discover_resources(sys.argv[1:] or ['healthcare', 'artificial intelligence'])
    print(json.dumps(results, indent=2))
    if any(value['status'] == 'provider_unavailable' for value in results.values()):
        raise SystemExit(1)
