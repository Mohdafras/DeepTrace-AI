"""Dependency-free SVG evaluation plots with exact CSV data alongside each plot.

Curves: single series; x/y axes 0..1; keyboard and pointer crosshair inspection.
Matrix: literal counts and explicit actual/predicted axes, not color-only.
"""
from html import escape
import json
from pathlib import Path

STYLE = '''<style>
:root{--surface:#fcfcfb;--ink:#0b0b0b;--muted:#52514e;--grid:#d9d9d5;--series:#2a78d6;--low:#cde2fb}
@media(prefers-color-scheme:dark){:root:not([data-theme="light"]){--surface:#1a1a19;--ink:#f0efec;--muted:#c3c2b7;--grid:#444440;--series:#3987e5;--low:#104281}}
:root[data-theme="dark"]{--surface:#1a1a19;--ink:#f0efec;--muted:#c3c2b7;--grid:#444440;--series:#3987e5;--low:#104281}
text{font-family:system-ui,sans-serif;fill:var(--ink);font-size:14px} .muted{fill:var(--muted)}
.axis{stroke:var(--grid);stroke-width:1}.curve{fill:none;stroke:var(--series);stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
@media(forced-colors:active),print{.curve{stroke:CanvasText}}
</style>'''


def shell(title, contents, description):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 720 520" role="img" '
            'aria-labelledby="title desc">' + f'<title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>' + STYLE +
            '<rect width="720" height="520" fill="var(--surface)"/>' +
            f'<text x="72" y="36" font-size="20" font-weight="600">{escape(title)}</text>' + contents + '</svg>')


def curve(path, title, x, y, xlabel, ylabel, csv_name):
    points = list(zip(map(float, x), map(float, y)))
    # Keep the plot small while preserving the full unrounded data in CSV.
    stride = max(1, len(points)//1600)
    plotted = points[::stride]
    if plotted[-1] != points[-1]:
        plotted.append(points[-1])
    line = " ".join(f"{80+px*580:.3f},{400-py*330:.3f}" for px,py in plotted)
    parts = []
    for tick in (0, .2, .4, .6, .8, 1):
        xx, yy = 80+tick*580, 400-tick*330
        parts += [f'<line class="axis" x1="{xx}" x2="{xx}" y1="70" y2="400"/>',
                  f'<line class="axis" x1="80" x2="660" y1="{yy}" y2="{yy}"/>',
                  f'<text class="muted" x="{xx}" y="424" text-anchor="middle">{tick:g}</text>',
                  f'<text class="muted" x="64" y="{yy+5}" text-anchor="end">{tick:g}</text>']
    parts += [f'<polyline class="curve" points="{line}"/>',
              f'<text x="370" y="453" text-anchor="middle">{escape(xlabel)}</text>',
              f'<text x="22" y="235" text-anchor="middle" transform="rotate(-90 22 235)">{escape(ylabel)}</text>',
              '<line id="crosshair" x1="80" x2="80" y1="70" y2="400" stroke="var(--muted)" visibility="hidden"/>',
              '<circle id="point" r="4" fill="var(--series)" stroke="var(--surface)" stroke-width="2" visibility="hidden"/>',
              '<text id="tooltip" x="80" y="59" class="muted">Hover or use Left/Right arrows to inspect the curve.</text>',
              f'<a href="{escape(csv_name)}"><text x="80" y="490" text-decoration="underline">Exact data table (CSV)</text></a>',
              '<rect id="hit" x="72" y="65" width="600" height="345" fill="transparent" tabindex="0" role="slider" aria-label="Inspect curve points"/>']
    script = '''<script><![CDATA[
const points=POINTS; const hit=document.getElementById('hit'), cross=document.getElementById('crosshair'), dot=document.getElementById('point'), tip=document.getElementById('tooltip'); let active=0;
function show(i){active=Math.max(0,Math.min(points.length-1,i));const [x,y]=points[active];const px=80+x*580,py=400-y*330;cross.setAttribute('x1',px);cross.setAttribute('x2',px);cross.setAttribute('visibility','visible');dot.setAttribute('cx',px);dot.setAttribute('cy',py);dot.setAttribute('visibility','visible');tip.textContent='x: '+x.toFixed(5)+' / y: '+y.toFixed(5);hit.setAttribute('aria-valuenow',active);hit.setAttribute('aria-valuetext',tip.textContent);}
hit.setAttribute('aria-valuemin','0');hit.setAttribute('aria-valuemax',points.length-1);
hit.addEventListener('pointermove',e=>{const svg=hit.ownerSVGElement,p=svg.createSVGPoint();p.x=e.clientX;p.y=e.clientY;const q=p.matrixTransform(svg.getScreenCTM().inverse());const x=(q.x-80)/580;let i=0,best=Infinity;points.forEach((p,j)=>{let d=Math.abs(p[0]-x);if(d<best){best=d;i=j;}});show(i);});
hit.addEventListener('focus',()=>show(active));hit.addEventListener('keydown',e=>{if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();show(active+(e.key==='ArrowLeft'?-1:1));}});
]]></script>'''.replace('POINTS', json.dumps(plotted, allow_nan=False))
    Path(path).write_text(shell(title, ''.join(parts)+script, 'Fake is the positive class. Full exact curve coordinates are in the linked CSV; plotted coordinates may be subsampled for display.'), encoding='utf-8')


def confusion(path, title, matrix, csv_name):
    maximum = max(max(row) for row in matrix) or 1
    parts = ['<text x="390" y="75" text-anchor="middle">Predicted class</text>',
             '<text x="286" y="105" text-anchor="middle">Fake</text><text x="496" y="105" text-anchor="middle">Real</text>',
             '<text x="44" y="285" text-anchor="middle" transform="rotate(-90 44 285)">Actual class</text>']
    for i, actual in enumerate(('Fake','Real')):
        parts.append(f'<text x="140" y="{205+i*156}" text-anchor="end">{actual}</text>')
        for j, predicted in enumerate(('Fake','Real')):
            value=matrix[i][j]
            x,y=182+j*210,125+i*156
            parts.append(f'<g tabindex="0"><title>Actual {actual}, predicted {predicted}: {value:,}</title><rect x="{x}" y="{y}" width="208" height="154" fill="var(--low)"/><rect x="{x+8}" y="{y+8}" width="{192*value/maximum}" height="8" rx="4" fill="var(--series)"/><text x="{x+104}" y="{y+85}" text-anchor="middle" font-size="28">{value:,}</text></g>')
    parts += [f'<a href="{escape(csv_name)}"><text x="182" y="487" text-decoration="underline">Exact counts (CSV); rows actual, columns predicted</text></a>']
    Path(path).write_text(shell(title, ''.join(parts), 'Every cell prints its count; a blue meter also encodes count relative to the largest cell. Fake is the positive class.'), encoding='utf-8')
