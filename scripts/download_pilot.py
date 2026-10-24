"""Download a fixed research catalog once; never overwrite raw or retry blocks.

Usage: python scripts/download_pilot.py [--provider football_data_co_uk|vaastav_fpl]
No credentials, scraping, model fitting, or target-distribution analysis.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'research' / 'download_manifest.json'
MAX_BYTES = 32 * 1024 * 1024


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--provider', choices=['football_data_co_uk', 'vaastav_fpl'])
    parser.add_argument('--catalog', choices=['pilot_sources', 'team_sources', 'player_sources'], default='pilot_sources')
    args = parser.parse_args()
    specs = json.loads((ROOT / 'research' / f'{args.catalog}.json').read_text(encoding='utf-8'))
    records = json.loads(MANIFEST.read_text(encoding='utf-8')) if MANIFEST.exists() else {}
    failed = False
    blocked_providers: set[str] = set()
    for spec in specs:
        if args.provider and spec['provider'] != args.provider:
            continue
        path = (ROOT / spec['path']).resolve()
        if not path.is_relative_to(ROOT):
            raise ValueError('Destination must remain inside project')
        if path.exists():
            expected = records.get(spec['id'], {}).get('sha256')
            if expected is None or expected != sha256(path):
                raise ValueError(f"Unverified or changed cache: {spec['id']}")
            print(f"CACHED {spec['id']}")
            continue
        if records.get(spec['id'], {}).get('status') == 'unavailable' and spec.get('optional'):
            print(f"UNAVAILABLE_CACHED {spec['id']}")
            continue
        if spec['provider'] in blocked_providers:
            print(f"SKIPPED {spec['id']}: provider failed earlier in this run")
            continue
        record = dict(spec, attempted_at_utc=datetime.now(timezone.utc).isoformat())
        temp = path.with_suffix('.download')
        try:
            request = urllib.request.Request(spec['url'], headers={'User-Agent': 'UniversityResearchPilot/0.1'})
            with urllib.request.urlopen(request, timeout=45) as response:
                raw = response.read(MAX_BYTES + 1)
                if len(raw) > MAX_BYTES:
                    raise ValueError('Size limit exceeded')
                if not raw.strip() or raw.lstrip().startswith(b'<') or b',' not in raw.splitlines()[0]:
                    raise ValueError('Response is not a plausible CSV')
                record.update(status='downloaded', http_status=response.status,
                              final_url=response.url, bytes=len(raw),
                              etag=response.headers.get('ETag'),
                              last_modified=response.headers.get('Last-Modified'),
                              retrieved_at_utc=datetime.now(timezone.utc).isoformat(),
                              sha256=hashlib.sha256(raw).hexdigest())
            path.parent.mkdir(parents=True, exist_ok=True)
            temp.write_bytes(raw)
            temp.replace(path)
            print(f"DOWNLOADED {spec['id']} {len(raw)} bytes")
        except (OSError, ValueError, urllib.error.URLError) as exc:
            if isinstance(exc, urllib.error.HTTPError) and exc.code == 404 and spec.get('optional'):
                record.update(status='unavailable', http_status=404, error=str(exc))
                print(f"UNAVAILABLE {spec['id']}: HTTP 404")
            else:
                record.update(status='failed', error=str(exc))
                failed = True
                blocked_providers.add(spec['provider'])
                print(f"FAILED {spec['id']}: {exc}")
            if temp.exists():
                temp.unlink()
        records[spec['id']] = record
        MANIFEST.write_text(json.dumps(records, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
