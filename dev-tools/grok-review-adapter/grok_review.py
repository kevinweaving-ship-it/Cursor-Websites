#!/usr/bin/env python3
"""Read-only Grok code-review adapter; opt-in requests only, no GitHub/SSH writes."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request

API_URL = 'https://api.x.ai/v1/responses'
DEFAULT_MODEL = 'grok-build-0.1'
MAX_INPUT_BYTES = 80_000
MAX_OUTPUT_TOKENS = 1200
SYSTEM_PROMPT = (
    'You are an independent, skeptical code reviewer. This is review-only: do not '
    'suggest that you executed tests or modified files. Identify concrete defects, '
    'line references if supplied, regressions and minimal testable fixes. '
    'Explicitly separate verified facts from hypotheses. Never repeat any secret '
    'appearing in the input. Output short sections: Findings, Tests, Unknowns.'
)
# Block recognizable secrets before they leave the machine. This is best-effort:
# the caller must still provide *review-safe* inputs, not private configs/logs.
SECRET_PATTERNS = [
    (re.compile(r'(?i)(authorization\s*:\s*bearer\s+)\S+'), r'\1[REDACTED]'),
    (re.compile(r'(?i)((?:xai|openai|github|gh|api)[_-]?(?:token|key|secret)\s*[:=]\s*[\"\']?)[^\s\"\']+'), r'\1[REDACTED]'),
    (re.compile(r'(?i)\b(?:xai|ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_-]{12,}\b'), '[REDACTED]'),
    (re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----.*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', re.S), '[REDACTED PRIVATE KEY]'),
]


def sanitize_input(text):
    for pattern, repl in SECRET_PATTERNS:
        text = pattern.sub(repl, text)
    return text


def prepare_payload(content, model=DEFAULT_MODEL):
    if len(content.encode('utf-8')) > MAX_INPUT_BYTES:
        raise ValueError('Review input exceeds 80,000 bytes; provide a smaller diff.')
    if not content.strip():
        raise ValueError('Review input must not be empty.')
    return {
        'model': model,
        'input': [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': sanitize_input(content)},
        ],
        'max_output_tokens': MAX_OUTPUT_TOKENS,
        'store': False,
    }


def extract_output(response):
    if isinstance(response.get('output_text'), str) and response['output_text']:
        return response['output_text']
    parts = []
    for item in response.get('output', []):
        if item.get('type') != 'message':
            continue
        for element in item.get('content', []):
            if element.get('type') in ('output_text', 'text'):
                value = element.get('text', '')
                if value:
                    parts.append(value)
    if not parts:
        raise ValueError('xAI response has no readable text output.')
    return '\n'.join(parts)


def call_api(payload, api_key, *, opener=None):
    if not api_key:
        raise ValueError('XAI_API_KEY is not configured.')
    req = urllib.request.Request(
        API_URL,
        json.dumps(payload).encode('utf-8'),
        headers={
            'Authorization': 'Bearer ' + api_key,
            'Content-Type': 'application/json',
        },
        method='POST',
    )
    open_fn = opener or urllib.request.urlopen
    try:
        with open_fn(req, timeout=45) as resp:
            result = json.loads(resp.read(3_000_000).decode('utf-8'))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f'xAI request failed: HTTP {exc.code}') from None
    except urllib.error.URLError:
        raise RuntimeError('xAI connection failed; no response received.') from None
    return extract_output(result)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Opt-in, read-only Grok review adapter')
    parser.add_argument('--input-file', required=True, help='Pre-screened code diff or audit text')
    parser.add_argument('--model', default=DEFAULT_MODEL, help='xAI model ID')
    parser.add_argument('--execute', action='store_true', help='Explicitly authorize ONE billable API request')
    args = parser.parse_args(argv)
    text = Path(args.input_file).read_text(encoding='utf-8')
    payload = prepare_payload(text, args.model)
    if not args.execute:
        print(json.dumps({
            'status': 'DRY_RUN_NO_API_CALL', 'endpoint': API_URL,
            'model': args.model, 'input_bytes': len(text.encode('utf-8')),
            'review_mode': 'READ_ONLY', 'requires': 'XAI_API_KEY and --execute',
        }, indent=2))
        return 0
    try:
        print(call_api(payload, os.environ.get('XAI_API_KEY', '')))
        return 0
    except (ValueError, RuntimeError) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
