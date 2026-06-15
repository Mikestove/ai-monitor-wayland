#!/usr/bin/env python3
"""Render icon.svg to PNG sizes needed by electron-builder."""
import subprocess
import sys
from pathlib import Path

here = Path(__file__).parent
svg = here / 'icon.svg'
sizes = [16, 32, 48, 64, 128, 256, 512]

for size in sizes:
    out = here / f'{size}x{size}.png'
    result = subprocess.run(
        ['inkscape', '--export-type=png', f'--export-filename={out}',
         f'--export-width={size}', f'--export-height={size}', str(svg)],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f'  {out.name}')
    else:
        print(f'  FAILED {size}px: {result.stderr.strip()}', file=sys.stderr)

print('Done.')
