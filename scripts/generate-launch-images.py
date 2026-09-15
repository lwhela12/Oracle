"""Generate solid-color iPhone launch screens and their static HTML links.

Run from the repository root after changing the launch color or device sizes.
Uses only the standard library; iOS needs correctly sized PNG startup images.
"""
from pathlib import Path
import struct
import zlib

ROOT = Path(__file__).resolve().parents[1]
COLOR = bytes.fromhex('101017')
# Logical screen width, height and pixel ratio; include display-zoom sizes.
SCREENS = [(320, 568, 2), (375, 667, 2), (414, 736, 3), (375, 812, 3),
           (414, 896, 2), (414, 896, 3), (390, 844, 3), (428, 926, 3),
           (393, 852, 3), (430, 932, 3), (402, 874, 3), (440, 956, 3),
           (420, 912, 3)]


def chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))


def png(width, height):
    header = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    pixels = (b'\0' + COLOR * width) * height
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', header) + chunk(b'IDAT', zlib.compress(pixels, 9)) + chunk(b'IEND', b'')


output = ROOT / 'static' / 'launch'
output.mkdir(exist_ok=True)
links = ['    <!-- Generated iPhone launch screens: scripts/generate-launch-images.py -->']
for width, height, ratio in SCREENS:
    for orientation in ('portrait', 'landscape'):
        w, h = (width * ratio, height * ratio) if orientation == 'portrait' else (height * ratio, width * ratio)
        filename = f'dark-{w}x{h}.png'
        (output / filename).write_bytes(png(w, h))
        media = f'(device-width: {width}px) and (device-height: {height}px) and (-webkit-device-pixel-ratio: {ratio}) and (orientation: {orientation})'
        links.append(f'    <link rel="apple-touch-startup-image" href="/static/launch/{filename}" media="{media}">')
links.append('    <!-- End generated launch screens -->')
page = ROOT / 'static' / 'index.html'
html = page.read_text()
start = '    <!-- Generated iPhone launch screens: scripts/generate-launch-images.py -->'
end = '    <!-- End generated launch screens -->'
if start in html:
    before, rest = html.split(start, 1)
    _, after = rest.split(end, 1)
    html = before + '\n'.join(links) + after
else:
    html = html.replace('    <!-- External Libraries -->', '\n'.join(links) + '\n\n    <!-- External Libraries -->')
page.write_text(html)
