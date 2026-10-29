# vivianqiao.com

The secret land of Vivian Qiao. A static site: `index.html` plus the Writing pages in `writing/`. Nothing to build on deploy.

## Writing

The essays and stories live as plain text in `content/writing/`:

- `pieces.json` lists every piece: slug, Chinese and English titles, date, kind (`story`, `essay`, `poem`) and the original WeChat link.
- `<slug>/zh.txt` is the Chinese original and `<slug>/en.txt` the English version. Paragraphs are separated by a blank line. `^ ` starts an epigraph (`^— ` for its attribution), `## 1` is a section break, `> ` lines are a quoted note, and `~ ` is a small closing line.

After editing any of those, regenerate the pages:

```
python3 tools/build_writing.py
```

That rewrites `writing/index.html`, `writing/<slug>/index.html`, the Writing preview on the home page, and `sitemap.xml`. Commit the generated files along with the text.
