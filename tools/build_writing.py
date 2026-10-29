#!/usr/bin/env python3
"""Build the Writing pages for vivianqiao.com.

Source:  content/writing/pieces.json  (one entry per piece, newest first or any order)
         content/writing/<slug>/zh.txt  (Chinese original, if there is one)
         content/writing/<slug>/en.txt  (English version)
Output:  writing/index.html, writing/<slug>/index.html,
         the Writing preview on index.html (between the writing markers), sitemap.xml

Text format, one paragraph per blank-line-separated block:
  ^ text         epigraph line (put "^— Author" on the next line for the attribution)
  ## 1           section break
  > line         a quoted note; consecutive "> " lines stay on separate lines
  ~ text         a small closing line, like "(The End)"
  For pieces with "verse": true, single line breaks are kept.

Run it with:  python3 tools/build_writing.py
"""
import datetime
import html
import json
import math
import os
import re
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'content', 'writing')
OUT = os.path.join(ROOT, 'writing')
SITE = 'https://vivianqiao.com'
# The site's pixel-pet tab icon, same as the home page.
ICON = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 -3 16 16' shape-rendering='crispEdges'%3E%3Cpath fill='%23F3E6CC' d='M2 1h2v1H2zM12 1h2v1h-2zM2 2h12v1H2zM1 3h14v5H1zM2 8h12v1H2zM3 9h10v1H3z'/%3E%3Cpath fill='%23E8949E' d='M2 6h2v1H2zM12 6h2v1h-2z'/%3E%3Cpath fill='%231A0F0C' d='M2 0h2v1H2zM12 0h2v1h-2zM1 1h1v2H1zM4 1h1v1H4zM11 1h1v1h-1zM14 1h1v2h-1zM5 2h6v1H5zM0 3h1v5H0zM15 3h1v5h-1zM4 4h1v2H4zM11 4h1v2h-1zM7 6h2v1H7zM1 8h1v1H1zM14 8h1v1h-1zM2 9h1v1H2zM5 9h6v1H5zM13 9h1v1h-1zM3 10h2v1H3zM11 10h2v1h-2z'/%3E%3C/svg%3E"

KIND = {
    'story': ('Story', '小说'),
    'essay': ('Essay', '随笔'),
    'poem': ('Poem', '诗'),
}
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
          'September', 'October', 'November', 'December']

esc = lambda s: html.escape(s, quote=True)


# ---------------------------------------------------------------- text → html
def tidy(text, lang):
    text = re.sub(r'\s*-{2,}\s*', ' — ', text) if lang == 'zh' else text
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()


def render(text, lang, verse=False):
    out = []
    for block in [b for b in re.split(r'\n\s*\n', text.strip()) if b.strip()]:
        lines = [l.rstrip() for l in block.split('\n') if l.strip()]
        if all(l.startswith('^') for l in lines):
            quote = [tidy(l[1:].strip(), lang) for l in lines if not l.startswith('^—')]
            by = [tidy(l[2:].strip(), lang) for l in lines if l.startswith('^—')]
            inner = ''.join('<p>%s</p>' % esc(q) for q in quote)
            inner += ''.join('<p class="by">— %s</p>' % esc(b) for b in by)
            out.append('<blockquote class="epi">%s</blockquote>' % inner)
        elif lines[0].startswith('## '):
            out.append('<h2 class="sec">%s</h2>' % esc(lines[0][3:].strip()))
        elif all(l.startswith('> ') for l in lines):
            out.append('<blockquote class="note"><p>%s</p></blockquote>' % '<br>'.join(esc(tidy(l[2:], lang)) for l in lines))
        elif lines[0].startswith('~ '):
            out.append('<p class="end">%s</p>' % esc(tidy(lines[0][2:], lang)))
        elif verse:
            out.append('<p>%s</p>' % '<br>'.join(esc(tidy(l, lang)) for l in lines))
        else:
            out.append('<p>%s</p>' % esc(tidy(' '.join(lines), lang)))
    return '\n'.join(out)


def first_paragraph(text, enough):
    """The opening prose, long enough to give a feel for the piece."""
    got = []
    for block in re.split(r'\n\s*\n', text.strip()):
        b = block.strip()
        if b and not b.startswith(('^', '## ', '> ', '~ ')):
            got.append(b)
            if sum(len(g) for g in got) >= enough:
                break
    return '\n'.join(got) if got else ''


def excerpt(text, lang, verse=False):
    p = first_paragraph(text, 60 if lang == 'zh' else 140)
    p = ' / '.join(l.strip() for l in p.split('\n')) if verse else ' '.join(p.split())
    p = tidy(p, lang)
    if lang == 'zh':
        return p if len(p) <= 72 else p[:70].rstrip('，,。. ;；:：') + '…'
    if len(p) <= 170:
        return p
    cut = p[:170].rsplit(' ', 1)[0].rstrip(',;:—')
    return cut + '…'


def minutes(text, lang):
    if lang == 'zh':
        n = len(re.findall(r'[一-鿿]', text))
        return max(1, math.ceil(n / 450))
    n = len(re.findall(r"[A-Za-z0-9'’]+", text))
    return max(1, math.ceil(n / 230))


def date_en(d, short=False):
    m = MONTHS[d.month - 1]
    return ('%s %d' % (m[:3], d.year)) if short else ('%s %d, %d' % (m, d.day, d.year))


def date_zh(d):
    return '%d年%d月%d日' % (d.year, d.month, d.day)


def both(en, zh, tag='span', cls=''):
    """Two versions of a phrase; CSS shows the one for the current language."""
    c = (' ' + cls) if cls else ''
    return '<%s class="le%s">%s</%s><%s class="lz%s" lang="zh-Hans">%s</%s>' % (tag, c, en, tag, tag, c, zh, tag)


def moods(night, light, train):
    return '<span class="mv n">%s</span><span class="mv l">%s</span><span class="mv t">%s</span>' % (night, light, train)


# ---------------------------------------------------------------- shared chrome
FONTS = ('https://fonts.googleapis.com/css2?family=Gilda+Display&family=Lato:wght@400;700'
         '&family=Cormorant+Garamond:ital,wght@0,600;1,600&family=Nunito+Sans:opsz,wght@6..12,400..700'
         '&family=Jost:wght@300;400;500&family=Noto+Serif+SC:wght@400;600&family=Noto+Sans+SC:wght@400;500&display=swap')

PREPAINT = """<script>
(function(){
  var d=document.documentElement,m='night',ok=/^(night|light|train)$/,l=null;
  try{var s=localStorage.getItem('vq-mode');if(ok.test(s))m=s;}catch(e){}
  var h=location.hash.slice(1);if(ok.test(h))m=h;
  d.setAttribute('data-mode',m);
  var q=/[?&]lang=(zh|en)\\b/.exec(location.search);if(q)l=q[1];
  if(!l){try{l=localStorage.getItem('vq-lang');}catch(e){}}
  if(l!=='zh'&&l!=='en')l=/^zh/i.test(navigator.language||'')?'zh':'en';
  d.setAttribute('data-lang',l);d.setAttribute('lang',l==='zh'?'zh-Hans':'en');
})();
</script>"""

SWITCH = """<nav class="switch" aria-label="Choose a mode">
  <button type="button" data-set="night" aria-pressed="true"><svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M14.5 2.5a9.5 9.5 0 1 0 7 15.9A8 8 0 0 1 14.5 2.5z"/></svg>Night</button>
  <button type="button" data-set="light" aria-pressed="false"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4.5" fill="currentColor"/><g stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M12 1.8v2.6M12 19.6v2.6M1.8 12h2.6M19.6 12h2.6M4.8 4.8l1.8 1.8M17.4 17.4l1.8 1.8M4.8 19.2l1.8-1.8M17.4 6.6l1.8-1.8"/></g></svg>Light</button>
  <button type="button" data-set="train" aria-pressed="false"><svg viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="2.5" width="14" height="15" rx="3.5" fill="none" stroke="currentColor" stroke-width="2.2"/><path fill="currentColor" d="M7.5 6h9v4.5h-9z"/><circle cx="9" cy="14" r="1.3" fill="currentColor"/><circle cx="15" cy="14" r="1.3" fill="currentColor"/><path d="M8 21l2-3.4M16 21l-2-3.4" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></svg>Train</button>
</nav>"""

LANG = """<div class="lang" role="group" aria-label="Language / 语言">
  <button type="button" data-lang-set="zh" aria-pressed="false" lang="zh-Hans">中文</button>
  <button type="button" data-lang-set="en" aria-pressed="true" lang="en">English</button>
</div>"""

PET_D = ('<path class="pb" d="M2 1h2v1h-2z M12 1h2v1h-2z M2 2h12v1h-12z M1 3h14v5h-14z M2 8h12v1h-12z M3 9h10v1h-10z"/>'
         '<path class="pc" d="M2 6h2v1h-2z M12 6h2v1h-2z"/>'
         '<path class="pl" d="M2 0h2v1h-2z M12 0h2v1h-2z M1 1h1v2h-1z M4 1h1v1h-1z M11 1h1v1h-1z M14 1h1v2h-1z M5 2h6v1h-6z M0 3h1v5h-1z M15 3h1v5h-1z M3 5h3v1h-3z M10 5h3v1h-3z M7 6h2v1h-2z M1 8h1v1h-1z M14 8h1v1h-1z M2 9h1v1h-1z M5 9h6v1h-6z M13 9h1v1h-1z M3 10h2v1h-2z M11 10h2v1h-2z"/>')
PET_HEART = '<path class="ph" d="M6 -9h2v1h-2z M9 -9h2v1h-2z M5 -8h7v2h-7z M6 -6h5v1h-5z M7 -5h3v1h-3z M8 -4h1v1h-1z"/>'
PET = ('<svg class="pet" viewBox="-1 -10 18 22" shape-rendering="crispEdges" role="button" tabindex="0" aria-label="Boop the pet">'
       '<g class="bod">' + PET_D + '</g><g class="heart">' + PET_HEART + '</g></svg>')


def scene_pet(x, y, s, body, cheek, line, heart, open_eyes=False):
    eyes = 'M4 4h1v2h-1z M11 4h1v2h-1z' if open_eyes else 'M3 5h3v1h-3z M10 5h3v1h-3z'
    d_line = ('M2 0h2v1h-2z M12 0h2v1h-2z M1 1h1v2h-1z M4 1h1v1h-1z M11 1h1v1h-1z M14 1h1v2h-1z M5 2h6v1h-6z '
              'M0 3h1v5h-1z M15 3h1v5h-1z ' + eyes + ' M7 6h2v1h-2z M1 8h1v1h-1z M14 8h1v1h-1z M2 9h1v1h-1z '
              'M5 9h6v1h-6z M13 9h1v1h-1z M3 10h2v1h-2z M11 10h2v1h-2z')
    return ('<g transform="translate(%s,%s) scale(%s)"><g class="pet"><rect x="-6" y="-12" width="28" height="26" fill="transparent"/>'
            '<g class="bod"><path fill="%s" d="M2 1h2v1h-2z M12 1h2v1h-2z M2 2h12v1h-12z M1 3h14v5h-14z M2 8h12v1h-12z M3 9h10v1h-10z"/>'
            '<path fill="%s" d="M2 6h2v1h-2z M12 6h2v1h-2z"/><path fill="%s" d="%s"/></g>'
            '<g class="heart"><path fill="%s" d="M6 -9h2v1h-2z M9 -9h2v1h-2z M5 -8h7v2h-7z M6 -6h5v1h-5z M7 -5h3v1h-3z M8 -4h1v1h-1z"/></g></g></g>'
            % (x, y, s, body, cheek, line, d_line, heart))


SCENE_NIGHT = """<svg viewBox="0 0 1440 420" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
<defs><radialGradient id="wglow"><stop offset="0" stop-color="#E7B566" stop-opacity="0.55"/><stop offset="1" stop-color="#E7B566" stop-opacity="0"/></radialGradient><pattern id="wbottles" width="34" height="70" patternUnits="userSpaceOnUse"><rect width="34" height="70" fill="#1E100C"/><rect x="6" y="22" width="10" height="44" fill="#5A1E22"/><rect x="9" y="8" width="4" height="16" fill="#5A1E22"/><rect x="20" y="28" width="9" height="38" fill="#2E4A2E"/><rect x="23" y="16" width="3" height="14" fill="#2E4A2E"/><rect x="8" y="32" width="2" height="18" fill="#C08A3E" opacity="0.55"/></pattern></defs>
<rect width="1440" height="420" fill="#3A1F18"/>
<g fill="#2A1712"><rect x="180" width="6" height="262"/><rect x="360" width="6" height="262"/><rect x="1080" width="6" height="262"/><rect x="1260" width="6" height="262"/></g>
<rect x="380" y="30" width="680" height="214" fill="#1E100C"/>
<rect x="390" y="40" width="660" height="70" fill="url(#wbottles)"/>
<rect x="390" y="124" width="660" height="70" fill="url(#wbottles)"/>
<g fill="#4A2A1E"><rect x="380" y="110" width="680" height="8"/><rect x="380" y="194" width="680" height="8"/></g>
<g class="lamp" style="transform-origin:600px 0px"><ellipse class="lampglow" cx="600" cy="196" rx="170" ry="110" fill="url(#wglow)"/><line x1="600" y1="0" x2="600" y2="96" stroke="#120B09" stroke-width="3"/><polygon points="580,96 620,96 634,124 566,124" fill="#C08A3E"/><circle cx="600" cy="128" r="7" fill="#FBE3A6"/></g>
<g class="lamp" style="transform-origin:880px 0px;animation-delay:-2.6s"><ellipse class="lampglow" cx="880" cy="190" rx="160" ry="104" fill="url(#wglow)" style="animation-delay:-1.8s"/><line x1="880" y1="0" x2="880" y2="86" stroke="#120B09" stroke-width="3"/><polygon points="860,86 900,86 914,114 846,114" fill="#C08A3E"/><circle cx="880" cy="118" r="7" fill="#FBE3A6"/></g>
<rect x="0" y="262" width="1440" height="38" fill="#2A1712"/>
<rect x="0" y="262" width="1440" height="3" fill="#4A2A1E"/>
<g fill="#E7B566" opacity="0.22"><ellipse cx="600" cy="282" rx="150" ry="13"/><ellipse cx="880" cy="282" rx="130" ry="12"/></g>
<rect x="0" y="300" width="1440" height="5" fill="#7A4A2A"/>
<rect x="0" y="305" width="1440" height="115" fill="#5A1E22"/>
<g fill="#4A171B"><rect x="120" y="305" width="4" height="115"/><rect x="300" y="305" width="4" height="115"/><rect x="480" y="305" width="4" height="115"/><rect x="660" y="305" width="4" height="115"/><rect x="840" y="305" width="4" height="115"/><rect x="1020" y="305" width="4" height="115"/><rect x="1200" y="305" width="4" height="115"/><rect x="1380" y="305" width="4" height="115"/></g>
<rect x="0" y="372" width="1440" height="8" fill="#C08A3E"/>
<polygon points="640,294 752,294 752,272 652,268" fill="#EADBC0"/>
<polygon points="752,294 864,294 852,268 752,272" fill="#F3E6CC"/>
<rect x="751" y="271" width="2" height="23" fill="#B9A68A"/>
<g fill="#B9A68A"><rect x="662" y="276" width="78" height="1.6"/><rect x="660" y="281" width="82" height="1.6"/><rect x="658" y="286" width="60" height="1.6"/><rect x="764" y="276" width="78" height="1.6"/><rect x="764" y="281" width="70" height="1.6"/></g>
<g transform="rotate(-7 820 286)"><rect x="782" y="284" width="58" height="4" rx="2" fill="#1A0F0C"/><rect x="836" y="284" width="9" height="4" fill="#C08A3E"/></g>
<polygon points="985,256 1013,256 1008,278 990,278" fill="#7A2433"/><polygon points="983,240 1015,240 1013,258 985,258" fill="none" stroke="#EADBC0" stroke-width="2" opacity="0.6"/><rect x="998" y="278" width="2" height="12" fill="#EADBC0"/><ellipse cx="999" cy="291" rx="10" ry="3" fill="#EADBC0"/>
<ellipse cx="470" cy="290" rx="26" ry="6" fill="#2B2422"/><rect x="452" y="280" width="42" height="7" rx="3" fill="#6B3A20"/><rect x="492" y="280" width="5" height="7" fill="#E2603A"/>
<path class="smoke" d="M496 278 C 516 244, 476 222, 504 184 S 524 124, 492 78" stroke="#9A8E86" stroke-width="7" fill="none" opacity="0.32" stroke-linecap="round"/>
""" + scene_pet(1100, 264, 2.4, '#EADBC0', '#C8706C', '#1A0F0C', '#E8949E') + """
<rect width="1440" height="420" fill="#6E625B" opacity="0.07"/>
</svg>"""

SCENE_LIGHT = """<svg viewBox="0 0 1440 420" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
<rect width="1440" height="420" fill="#A9B9CC"/>
<rect y="210" width="1440" height="58" fill="#E9B9A2"/>
<rect y="268" width="1440" height="38" fill="#F6D2B0"/>
<g class="cloud"><polygon points="760,102 900,86 1010,100 960,114 800,118" fill="#F8E6D6"/><polygon points="1120,196 1250,184 1340,198 1280,210 1150,212" fill="#F3D9C6"/></g>
<circle class="sun" cx="880" cy="300" r="40" fill="#FBE6C4"/>
<polygon points="0,306 0,278 120,254 260,272 380,250 500,296 540,306" fill="#8C8FA6"/>
<rect x="170" y="244" width="46" height="30" fill="#F1EADB"/><polygon points="164,246 193,226 222,246" fill="#A8432F"/>
<polygon points="1100,306 1180,282 1260,270 1340,276 1440,268 1440,306" fill="#7A7D96"/>
<circle class="lantern" cx="1290" cy="190" r="26" fill="#FFF2C6" opacity="0.3"/>
<polygon points="1278,276 1302,276 1298,198 1282,198" fill="#F4EDE0"/>
<polygon points="1290,198 1298,198 1302,276 1290,276" fill="#B9C2C6"/>
<rect x="1276" y="194" width="28" height="5" fill="#2B2D30"/>
<rect x="1280" y="180" width="20" height="14" fill="#F7E3A0"/>
<polygon points="1277,180 1290,166 1303,180" fill="#A8432F"/>
<rect y="306" width="1440" height="114" fill="#5F86A2"/>
<rect y="306" width="1440" height="10" fill="#7395AF"/>
<g fill="#7FA0B8"><rect y="330" width="1440" height="3"/><rect y="352" width="1440" height="3"/></g>
<g class="glint" fill="#F6D2B0" opacity="0.85"><rect x="826" y="312" width="108" height="5"/><rect x="840" y="326" width="80" height="4"/><rect x="852" y="340" width="56" height="4"/><rect x="862" y="354" width="36" height="3"/></g>
<g class="bob"><line x1="620" y1="270" x2="620" y2="320" stroke="#3A2A22" stroke-width="3"/><rect x="560" y="304" width="32" height="16" fill="#F1EADB"/><polygon points="540,320 668,320 656,336 552,336" fill="#2F5E7A"/></g>
<g stroke="#3A3A44" stroke-width="3" fill="none" stroke-linecap="round"><g class="gull"><path class="flap" d="M980 170 l12 8 l12 -8"/></g><g class="gull g2"><path class="flap" style="animation-delay:-.3s" d="M1030 196 l9 6 l9 -6"/></g></g>
<rect y="376" width="1440" height="44" fill="#8A6A4E"/>
<rect y="372" width="1440" height="6" fill="#B08A64"/>
<g transform="rotate(-3 420 366)"><rect x="370" y="356" width="104" height="16" fill="#FBF7EE"/></g>
<rect x="364" y="362" width="108" height="11" fill="#F4EDE0"/>
<g fill="#A9B9CC"><rect x="376" y="365" width="70" height="1.5"/><rect x="376" y="369" width="58" height="1.5"/></g>
<rect x="498" y="350" width="20" height="22" fill="#2F5E7A"/><rect x="502" y="344" width="12" height="7" fill="#1E2A33"/>
<g transform="rotate(-24 548 350)"><rect x="540" y="330" width="4" height="40" fill="#1E2A33"/><rect x="540" y="366" width="4" height="6" fill="#C8504A"/></g>
""" + scene_pet(610, 348, 2.2, '#FFFFFF', '#E8949E', '#1E2A33', '#C8504A', open_eyes=True) + """
</svg>"""

_passes = ''.join('<rect class="vq-pass" style="animation-delay:%.2fs" x="%d" y="92" width="70" height="126" fill="#E8913A"/>' % (i * 0.12, 40 + i * 180)
                  for i in range(8))
SCENE_TRAIN = """<svg viewBox="0 0 1440 360" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
<g class="rock">
<rect width="1440" height="360" fill="#0A0E0E"/>
<rect width="1440" height="44" fill="#1C2827"/>
<g opacity="0.5"><rect y="38" width="1440" height="6" fill="#DDEBDF" class="vq-hum"/></g>
<rect y="80" width="1440" height="150" fill="#07090B"/>
""" + _passes + """
<g fill="#1C2624"><rect y="76" width="1440" height="8"/><rect y="226" width="1440" height="8"/><rect x="352" y="80" width="10" height="150"/><rect x="712" y="80" width="10" height="150"/><rect x="1072" y="80" width="10" height="150"/></g>
<g fill="none" stroke-linecap="round">
<g class="strap"><line x1="200" y1="44" x2="200" y2="96" stroke="#3A4A47" stroke-width="4"/><circle cx="200" cy="104" r="8" stroke="#5A6A64" stroke-width="3"/></g>
<g class="strap" style="animation-delay:-.6s"><line x1="540" y1="44" x2="540" y2="96" stroke="#3A4A47" stroke-width="4"/><circle cx="540" cy="104" r="8" stroke="#5A6A64" stroke-width="3"/></g>
<g class="strap" style="animation-delay:-1.2s"><line x1="900" y1="44" x2="900" y2="96" stroke="#3A4A47" stroke-width="4"/><circle cx="900" cy="104" r="8" stroke="#5A6A64" stroke-width="3"/></g>
<g class="strap" style="animation-delay:-1.8s"><line x1="1240" y1="44" x2="1240" y2="96" stroke="#3A4A47" stroke-width="4"/><circle cx="1240" cy="104" r="8" stroke="#5A6A64" stroke-width="3"/></g>
</g>
<rect y="234" width="1440" height="126" fill="#24302D"/>
<g fill="#3B1416"><rect x="0" y="262" width="300" height="98" rx="14"/><rect x="520" y="262" width="400" height="98" rx="14"/><rect x="1140" y="262" width="300" height="98" rx="14"/></g>
<g fill="#4E1C1F"><rect x="0" y="262" width="300" height="12" rx="6"/><rect x="520" y="262" width="400" height="12" rx="6"/><rect x="1140" y="262" width="300" height="12" rx="6"/></g>
<g opacity="0.16"><ellipse cx="410" cy="252" rx="120" ry="40" fill="#E8913A" class="vq-hum"/></g>
<rect x="330" y="282" width="160" height="10" fill="#1C2624"/>
<polygon points="352,282 408,282 408,270 358,266" fill="#D9D4C4" opacity="0.92"/>
<polygon points="408,282 464,282 458,266 408,270" fill="#F1E8D4" opacity="0.92"/>
<rect x="407" y="268" width="2" height="14" fill="#8E897C"/>
""" + scene_pet(820, 234, 2.6, '#D9D4C4', '#C8706C', '#0A0E0E', '#E8913A') + """
</g>
</svg>"""


def head(title, desc, url, depth, extra=''):
    up = '../' * depth
    return """<!doctype html>
<html lang="en" data-lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{url}">
<meta property="og:site_name" content="Vivian Qiao">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}">
<meta property="og:type" content="{ogtype}">
<meta name="theme-color" content="#3A1F18">
<link rel="icon" href="{icon}">
{prepaint}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{fonts}">
<link rel="stylesheet" href="{up}writing/assets/writing.css">
{extra}
</head>""".format(title=esc(title), desc=esc(desc), url=url, up=up, icon=ICON, prepaint=PREPAINT,
                  fonts=esc(FONTS), extra=extra, ogtype='article' if depth == 2 else 'website')


def foot(depth):
    up = '../' * depth
    return """<footer class="site-foot">
<div class="wrap"><span>© 2026 Vivian Qiao · SaltyMalty</span><span><a href="{up}">vivianqiao.com</a> · Weihai → New York</span></div>
</footer>
<script src="{up}writing/assets/writing.js"></script>
</body>
</html>
""".format(up=up)


# ---------------------------------------------------------------- load
def load():
    pieces = json.load(open(os.path.join(SRC, 'pieces.json'), encoding='utf-8'))
    for p in pieces:
        d = os.path.join(SRC, p['slug'])
        p['d'] = datetime.date.fromisoformat(p['date'])
        p['original'] = p.get('original', 'zh')
        p['zh_text'] = open(os.path.join(d, 'zh.txt'), encoding='utf-8').read() if os.path.exists(os.path.join(d, 'zh.txt')) else None
        p['en_text'] = open(os.path.join(d, 'en.txt'), encoding='utf-8').read()
        verse = p.get('verse', False)
        p['ex_en'] = excerpt(p['en_text'], 'en', verse)
        p['ex_zh'] = excerpt(p['zh_text'], 'zh', verse) if p['zh_text'] else p['ex_en']
        p['min_en'] = minutes(p['en_text'], 'en')
        p['min_zh'] = minutes(p['zh_text'], 'zh') if p['zh_text'] else p['min_en']
    pieces.sort(key=lambda p: p['d'], reverse=True)
    return pieces


def title_html(p, lang, tag, cls):
    """Title in one language; English-original pieces keep their English title everywhere."""
    if lang == 'zh' and p['original'] == 'zh':
        return '<%s class="%s zh-t" lang="zh-Hans">%s</%s>' % (tag, cls, esc(p['zh']), tag)
    return '<%s class="%s" lang="en">%s</%s>' % (tag, cls, esc(p['en']), tag)


def kind_line(p):
    en, zh = KIND[p['kind']]
    if p.get('parts') == 2:
        en, zh = en + ' in two parts', zh + ' · 上下篇'
    return en, zh


# ---------------------------------------------------------------- article page
def build_piece(p, newer, older):
    verse = p.get('verse', False)
    k_en, k_zh = kind_line(p)
    label = both('%s · %s' % (k_en, date_en(p['d'])), '%s · %s' % (k_zh, date_zh(p['d'])))
    zh_orig = p['original'] == 'zh'

    if zh_orig:
        h1 = (title_html(p, 'zh', 'h1', 'lz') + title_html(p, 'en', 'h1', 'le'))
        sub = ('<p class="art-sub lz">%s</p>' % esc(p['en']) +
               '<p class="art-sub le zh-t" lang="zh-Hans">%s</p>' % esc(p['zh']))
    else:
        h1 = '<h1 lang="en">%s</h1>' % esc(p['en'])
        sub = ''

    rev = ''
    if p.get('revised'):
        if isinstance(p['revised'], str):
            rd = datetime.date.fromisoformat(p['revised'])
            rev = '<span>%s</span>' % both('Revised ' + date_en(rd), '修改于' + date_zh(rd))
        else:
            rev = '<span>%s</span>' % both('Revised after publishing', '发表后修改')

    links = p.get('links', [])
    if len(links) == 2:
        wechat = both('WeChat: <a href="%s" rel="noopener" target="_blank">part one ↗</a> <a href="%s" rel="noopener" target="_blank">part two ↗</a>' % (links[0], links[1]),
                      '首发于微信公众号：<a href="%s" rel="noopener" target="_blank">上 ↗</a> <a href="%s" rel="noopener" target="_blank">下 ↗</a>' % (links[0], links[1]))
    elif links:
        wechat = both('<a href="%s" rel="noopener" target="_blank">First published on WeChat ↗</a>' % links[0],
                      '<a href="%s" rel="noopener" target="_blank">首发于微信公众号 ↗</a>' % links[0])
    else:
        wechat = ''

    time_ = both('%d min read' % p['min_en'], '约 %d 分钟' % p['min_zh']) if zh_orig else '<span>%s</span>' % both('%d min read' % p['min_en'], '约 %d 分钟' % p['min_en'])

    facts = '<div class="facts"><span>%s</span>%s<span>%s</span></div>' % (time_, rev, wechat)
    langbox = LANG if zh_orig else ''

    vcls = ' verse' if verse else ''
    if zh_orig:
        body = ('<div class="prose zh lz%s" lang="zh-Hans">\n%s\n</div>\n' % (vcls, render(p['zh_text'], 'zh', verse)) +
                '<div class="prose en le%s" lang="en">\n%s\n</div>' % (vcls, render(p['en_text'], 'en', verse)))
        swap = ('<button type="button" class="swap le" data-lang-set="zh" data-to-top lang="zh-Hans">阅读中文版 →</button>'
                '<button type="button" class="swap lz" data-lang-set="en" data-to-top lang="en">Read it in English →</button>')
    else:
        body = '<div class="prose en%s" lang="en">\n%s\n</div>' % (vcls, render(p['en_text'], 'en', verse))
        swap = '<span></span>'

    def pn_link(q, cls, k_en, k_zh):
        if not q:
            return ''
        t_en = esc(q['en'])
        t_zh = esc(q['zh']) if q['original'] == 'zh' else t_en
        return ('<a class="%s" href="../%s/"><span class="k">%s</span>%s</a>' %
                (cls, q['slug'], both(k_en, k_zh),
                 '<span class="t le">%s</span><span class="t lz zh-t" lang="zh-Hans">%s</span>' % (t_en, t_zh)))
    pn = '<nav class="pn" aria-label="More writing">%s%s</nav>' % (
        pn_link(newer, 'newer', '← Newer', '← 较新'), pn_link(older, 'older', 'Older →', '较早 →'))

    url = '%s/writing/%s/' % (SITE, p['slug'])
    t_en = '%s · Vivian Qiao' % p['en']
    t_zh = '%s · Vivian Qiao' % (p['zh'] if zh_orig else p['en'])
    desc = p['ex_en']
    ld = {
        '@context': 'https://schema.org', '@type': 'Article',
        'headline': p['en'], 'alternativeHeadline': p['zh'] if zh_orig else None,
        'datePublished': p['date'], 'inLanguage': ['zh-Hans', 'en'] if zh_orig else 'en',
        'url': url, 'genre': KIND[p['kind']][0],
        'author': {'@type': 'Person', 'name': 'Vivian Qiao', 'alternateName': 'SaltyMalty', 'url': SITE + '/'},
    }
    ld = {k: v for k, v in ld.items() if v is not None}
    extra = '<script type="application/ld+json">%s</script>' % json.dumps(ld, ensure_ascii=False)

    page = head(t_en, desc, url, 2, extra)
    page = page.replace('<html lang="en" data-lang="en">',
                        '<html lang="en" data-lang="en" data-title-en="%s" data-title-zh="%s">' % (esc(t_en), esc(t_zh)), 1)
    page += """
<body>
<div class="progress" aria-hidden="true"></div>
{switch}
<header class="read art-top">
<a class="back" href="../">{back}</a>
</header>
<main>
<article>
<header class="read art-head">
<p class="label">{label}</p>
{h1}
{sub}
<div class="art-meta">{facts}{langbox}</div>
</header>
<div class="read">
{body}
<div class="after">{swap}{pet}</div>
{pn}
</div>
</article>
</main>
""".format(switch=SWITCH, back=both('← All writing', '← 全部文字'), label=label, h1=h1, sub=sub,
           facts=facts, langbox=langbox, body=body, swap=swap, pet=PET, pn=pn)
    page += foot(2)
    d = os.path.join(OUT, p['slug'])
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, 'index.html'), 'w', encoding='utf-8').write(page)


# ---------------------------------------------------------------- archive page
def build_archive(pieces):
    years = {}
    for p in pieces:
        years.setdefault(p['d'].year, []).append(p)
    blocks = []
    for y in sorted(years, reverse=True):
        items = []
        for p in years[y]:
            k_en, k_zh = kind_line(p)
            zh_orig = p['original'] == 'zh'
            meta = ('<span class="e-meta"><span>%s</span><span class="chip">%s</span><span>%s</span></span>' %
                    (both(date_en(p['d']).replace(', %d' % y, ''), '%d月%d日' % (p['d'].month, p['d'].day)),
                     both(k_en.split(' ')[0], k_zh.split(' ')[0]),
                     both('%d min' % p['min_en'], '约 %d 分钟' % p['min_zh'])))
            if zh_orig:
                titles = (title_html(p, 'zh', 'h3', 'e-title lz') + title_html(p, 'en', 'h3', 'e-title le') +
                          '<p class="e-alt lz">%s</p><p class="e-alt le zh-t" lang="zh-Hans">%s</p>' % (esc(p['en']), esc(p['zh'])))
                ex = '<p class="e-ex lz zh-t" lang="zh-Hans">%s</p><p class="e-ex le">%s</p>' % (esc(p['ex_zh']), esc(p['ex_en']))
            else:
                titles = '<h3 class="e-title" lang="en">%s</h3>' % esc(p['en'])
                ex = '<p class="e-ex" lang="en">%s</p>' % esc(p['ex_en'])
            items.append('<li class="entry"><a href="%s/">%s%s%s</a></li>' % (p['slug'], meta, titles, ex))
        blocks.append('<section class="year" aria-label="%d"><h2>%d</h2><ul class="entries">%s</ul></section>' % (y, y, '\n'.join(items)))

    n_zh = sum(1 for p in pieces if p['original'] == 'zh')
    first, last = pieces[-1]['d'].year, pieces[0]['d'].year
    intro_en = ('Short stories, essays and a couple of poems, written as SaltyMalty between %d and %d. ' % (first, last)) + moods(
        'Pull up a stool.', 'Read them by the window.', 'Something for the long ride.')
    intro_zh = ('%d 至 %d 年间以 SaltyMalty 为笔名写下的小说、随笔和几首诗。' % (first, last)) + moods(
        '找个吧台位坐下吧。', '就着窗边的光慢慢读。', '留给漫长的夜车。')

    hero_title = """<div class="hero-title"><div class="wrap">
<a class="back" href="../">{back}</a>
<p class="label">{label}</p>
<h1>{h1}</h1>
</div></div>""".format(back=both('← The secret land', '← 回到首页'),
                       label=moods(both('After hours · the back bar', '打烊之后 · 吧台'),
                                   both('Letters in bottles', '漂流瓶里的信'),
                                   both('Reading car', '阅读车厢')),
                       h1='<span class="le">Writing</span><span class="lz zh-t" lang="zh-Hans">文字</span>')

    def hero(mid, svg):
        return '<div class="mode" id="%s"><section class="hero">%s<div class="scene">%s</div></section></div>' % (mid, hero_title, svg)

    url = SITE + '/writing/'
    desc = ('Stories, essays and poems by Vivian Qiao, written as SaltyMalty. %d pieces, %d–%d.' % (len(pieces), first, last))
    ld = {'@context': 'https://schema.org', '@type': 'CollectionPage', 'name': 'Writing · Vivian Qiao', 'url': url,
          'inLanguage': ['zh-Hans', 'en'],
          'author': {'@type': 'Person', 'name': 'Vivian Qiao', 'alternateName': 'SaltyMalty', 'url': SITE + '/'},
          'hasPart': [{'@type': 'Article', 'headline': p['en'], 'url': '%s%s/' % (url, p['slug']), 'datePublished': p['date']} for p in pieces]}
    page = head('Writing · Vivian Qiao', desc, url, 1,
                '<script type="application/ld+json">%s</script>' % json.dumps(ld, ensure_ascii=False))
    page = page.replace('<html lang="en" data-lang="en">',
                        '<html lang="en" data-lang="en" data-title-en="Writing · Vivian Qiao" data-title-zh="文字 · Vivian Qiao">', 1)
    page += """
<body>
{switch}
{night}{light}{train}
<main class="wrap">
<div class="intro-row">
<p class="intro le">{intro_en}</p>
<p class="intro lz zh-t" lang="zh-Hans">{intro_zh}</p>
{lang}
</div>
{blocks}
</main>
""".format(switch=SWITCH, night=hero('night', SCENE_NIGHT), light=hero('light', SCENE_LIGHT), train=hero('train', SCENE_TRAIN),
           intro_en=intro_en, intro_zh=intro_zh, lang=LANG, blocks='\n'.join(blocks))
    page += foot(1)
    open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8').write(page)


# ---------------------------------------------------------------- home page preview
def build_home_preview(pieces):
    path = os.path.join(ROOT, 'index.html')
    s = open(path, encoding='utf-8').read()
    rows = []
    for p in pieces[:5]:
        zh = '<i lang="zh-Hans">%s</i>' % esc(p['zh']) if p['original'] == 'zh' else ''
        rows.append('<li><a href="writing/%s/"><span class="ix-d">%s</span><span class="ix-t"><b>%s</b>%s</span><span class="ix-k">%s</span></a></li>'
                    % (p['slug'], date_en(p['d'], short=True), esc(p['en']), zh, KIND[p['kind']][0]))
    more = len(pieces) - 5
    block = ('<!-- writing:start (generated by tools/build_writing.py) -->\n'
             '<ol class="ix-list">\n%s\n</ol>\n'
             '<a class="ix-more" href="writing/">+ %d more · Read all →</a>\n'
             '<!-- writing:end -->' % ('\n'.join(rows), more))
    s2, n = re.subn(r'<!-- writing:start.*?<!-- writing:end -->', lambda m: block, s, flags=re.S)
    if n != 1:
        raise SystemExit('index.html is missing the writing markers')
    # Chinese titles on the home page use a tiny Noto Serif SC subset with just those characters.
    chars = ''.join(sorted(set(''.join(p['zh'] for p in pieces[:5] if p['original'] == 'zh'))))
    font = '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@500&amp;text=%s&amp;display=swap">' % urllib.parse.quote(chars)
    s2, n = re.subn(r'<!-- zhfont:start -->.*?<!-- zhfont:end -->', lambda m: '<!-- zhfont:start -->' + font + '<!-- zhfont:end -->', s2, flags=re.S)
    if n != 1:
        raise SystemExit('index.html is missing the zhfont markers')
    count = re.subn(r'(<span class="chip js-wcount">)\d+ pieces(</span>)', lambda m: '%s%d pieces%s' % (m.group(1), len(pieces), m.group(2)), s2)
    s2 = count[0]
    if s2 != s:
        open(path, 'w', encoding='utf-8').write(s2)


def build_sitemap(pieces):
    today = datetime.date.today().isoformat()
    urls = [(SITE + '/', today), (SITE + '/writing/', today)] + [('%s/writing/%s/' % (SITE, p['slug']), p['date']) for p in pieces]
    xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    xml += ['  <url><loc>%s</loc><lastmod>%s</lastmod></url>' % u for u in urls]
    xml.append('</urlset>')
    open(os.path.join(ROOT, 'sitemap.xml'), 'w', encoding='utf-8').write('\n'.join(xml) + '\n')


def main():
    pieces = load()
    for i, p in enumerate(pieces):
        build_piece(p, pieces[i - 1] if i > 0 else None, pieces[i + 1] if i + 1 < len(pieces) else None)
    build_archive(pieces)
    build_home_preview(pieces)
    build_sitemap(pieces)
    print('built %d pieces' % len(pieces))


if __name__ == '__main__':
    main()
