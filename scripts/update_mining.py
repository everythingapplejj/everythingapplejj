#!/usr/bin/env python3
"""Render timestamped mining cards from the pool's real, formatted telemetry."""
from datetime import datetime, timezone
from html import escape
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ADDRESS = 'bitcoincash:qrkyk3usu33mnzl0luxs8z5crdlus5p5zscpc27v70'
SOURCE = ('https://cwi-themine.com/badge.svg?pool=solo-bch-sha256d&addr='
          'bitcoincash%3Aqrkyk3usu33mnzl0luxs8z5crdlus5p5zscpc27v70')
LABELS = ['HASHRATE', 'WORKERS', 'BEST SHARE', 'BLOCKS', 'AWARDS']
PATTERNS = [r'\d+(?:[.,]\d+)*\s*[kMGTPEZ]?H/s', r'\d[\d,]*',
            r'\d+(?:[.,]\d+)*\s*[kKMGTPEZ]?', r'\d[\d,]*', r'\d+\s*/\s*\d+']


def fetch_metrics():
    result = subprocess.run(
        ['curl', '--fail', '--silent', '--show-error', '--location',
         '--max-time', '30', '--retry', '2', '--retry-delay', '3', SOURCE],
        check=True, capture_output=True, text=True)
    if len(result.stdout) > 100_000:
        raise ValueError('Unexpectedly large pool response')
    root = ET.fromstring(result.stdout)
    if root.tag != '{http://www.w3.org/2000/svg}svg':
        raise ValueError('The pool did not return an SVG')
    texts = [''.join(e.itertext()).strip() for e in root.iter()
             if e.tag == '{http://www.w3.org/2000/svg}text']
    metrics = []
    for label, pattern in zip(LABELS, PATTERNS):
        if texts.count(label) != 1:
            raise ValueError(f'Pool field missing or ambiguous: {label}')
        value = texts[texts.index(label) + 1]
        if not re.fullmatch(pattern, value) or len(value) > 24:
            raise ValueError(f'Invalid pool field: {label}')
        metrics.append(value)
    return metrics


def render(metrics, timestamp, mobile=False):
    width, height = (480, 340) if mobile else (1000, 206)
    positions = [(28, 99), (258, 99), (28, 184), (258, 184), (28, 269)] if mobile else [(32, 96), (270, 96), (440, 96), (665, 96), (830, 96)]
    footer = f'Fetched {timestamp} UTC'
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
           '<title id="title">BCH solo mining telemetry</title>',
           f'<desc id="desc">Real CWI-theMINE pool data: {escape(", ".join(f"{k}: {v}" for k, v in zip(LABELS, metrics)))}. {escape(footer)}. Scheduled every 15 minutes; scheduling and image caches may delay updates.</desc>',
           f'<rect x=".5" y=".5" width="{width-1}" height="{height-1}" rx="12" fill="#1c1c1c" stroke="#343434"/>',
           '<g font-family="Inter,Arial,sans-serif">',
           '<text x="28" y="36" fill="#ededed" font-size="20" font-weight="600">BCH solo mining</text>',
           f'<text x="{width-28}" y="36" text-anchor="end" fill="#a1a1a1" font-size="13">CWI-theMINE</text>',
           f'<path d="M28 57H{width-28}" stroke="#343434"/>']
    for index, ((x, y), label, value) in enumerate(zip(positions, LABELS, metrics)):
        display = {'HASHRATE':'Hashrate','WORKERS':'Workers','BEST SHARE':'Best share','BLOCKS':'Blocks','AWARDS':'Awards'}[label]
        out += [f'<text x="{x}" y="{y}" fill="#b4b4b4" font-size="14">{display}</text>',
                f'<text x="{x}" y="{y+35}" fill="{"#3ecf8e" if index==0 else "#ededed"}" font-size="{30 if mobile else 32}" font-weight="500">{escape(value)}</text>']
    if mobile:
        out += ['<text x="258" y="269" fill="#b4b4b4" font-size="14">Refresh schedule</text>',
                '<text x="258" y="300" fill="#ededed" font-size="21">Every 15 min</text>']
    else:
        out += [f'<path d="M28 157H{width-28}" stroke="#343434"/>',
                f'<text x="{width-28}" y="184" text-anchor="end" fill="#a1a1a1" font-size="12">Scheduled every 15 min</text>']
    out += [f'<text x="28" y="{322 if mobile else 184}" fill="#a1a1a1" font-size="12">{escape(footer)}</text>', '</g></svg>']
    return '\n'.join(out)


def main():
    metrics = fetch_metrics()
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')
    # Validate both complete outputs before replacing any previous successful data.
    cards = {name: render(metrics, timestamp, mobile) for name, mobile in
             [('mining-telemetry.svg', False), ('mining-telemetry-mobile.svg', True)]}
    for card in cards.values():
        ET.fromstring(card)
    for name, card in cards.items():
        target = ROOT / 'assets' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix('.tmp')
        temporary.write_text(card + '\n', encoding='utf-8')
        temporary.replace(target)
    print(f'Updated mining telemetry at {timestamp} UTC: ' + ', '.join(metrics))


if __name__ == '__main__':
    main()
