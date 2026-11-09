"""Fill the Apart submission template with paper/submission.md.

  python3 paper/build_docx.py TEMPLATE.docx FIGDIR OUT.docx
FIGDIR holds the PNG figures named in submission.md (% FIGURE: name.png | caption).
Keeps the template's title block, author table, abstract box, styles and page setup; drops its guidance text.
"""

from __future__ import annotations

import re
import struct
import sys
import zipfile
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
FONT = '<w:rFonts w:ascii="Old Standard TT" w:cs="Old Standard TT" w:eastAsia="Old Standard TT" w:hAnsi="Old Standard TT"/>'
MONO = '<w:rFonts w:ascii="Courier New" w:cs="Courier New" w:eastAsia="Courier New" w:hAnsi="Courier New"/>'
TEXT_W = 9360  # 6.5 in in twips


def runs(text: str, base: str = "", size: int | None = None) -> str:
    """Markdown inline (**bold**, *italic*, `code`) -> w:r elements."""
    out = []
    sz = f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>' if size else ""
    for tok in re.split(r"(\*\*.+?\*\*|`[^`]+`|(?<![\w*])\*[^*]+?\*(?![\w*]))", text):
        if not tok:
            continue
        font, fmt = FONT, base
        if tok.startswith("**"):
            tok, fmt = tok[2:-2], base + '<w:b w:val="1"/><w:bCs w:val="1"/>'
        elif tok.startswith("`"):
            tok, font = tok[1:-1], MONO
            msz = (size or 22) - 3
            sz_ = f'<w:sz w:val="{msz}"/><w:szCs w:val="{msz}"/>'
            out.append(f'<w:r><w:rPr>{font}{fmt}{sz_}</w:rPr><w:t xml:space="preserve">{escape(tok, quote=False)}</w:t></w:r>')
            continue
        elif tok.startswith("*") and tok.endswith("*") and len(tok) > 2:
            tok, fmt = tok[1:-1], base + '<w:i w:val="1"/><w:iCs w:val="1"/>'
        out.append(f'<w:r><w:rPr>{font}{fmt}{sz}</w:rPr><w:t xml:space="preserve">{escape(tok, quote=False)}</w:t></w:r>')
    return "".join(out)


def para(text, *, jc="both", after=120, before=0, ind="", num=None, base="", size=None, keep=False):
    ppr = []
    if num:
        ppr.append(f'<w:numPr><w:ilvl w:val="{num[1]}"/><w:numId w:val="{num[0]}"/></w:numPr>')
    if keep:
        ppr.append('<w:keepNext w:val="1"/>')
    ppr.append(f'<w:spacing w:before="{before}" w:after="{after}" w:line="264" w:lineRule="auto"/>')
    if ind:
        ppr.append(ind)
    ppr.append(f'<w:jc w:val="{jc}"/>')
    return f'<w:p><w:pPr>{"".join(ppr)}</w:pPr>{runs(text, base, size)}</w:p>'


def heading2(text):
    rpr = f'{FONT}<w:b w:val="1"/><w:bCs w:val="1"/><w:color w:val="434343"/><w:sz w:val="28"/><w:szCs w:val="28"/>'
    return (f'<w:p><w:pPr><w:pStyle w:val="Heading2"/><w:keepNext w:val="1"/><w:spacing w:after="60" w:before="240" w:line="360" w:lineRule="auto"/>'
            f'<w:rPr>{rpr}</w:rPr></w:pPr><w:r><w:rPr>{rpr}</w:rPr><w:t xml:space="preserve">{escape(text, quote=False)}</w:t></w:r></w:p>')


def heading3(text):
    rpr = f'{FONT}<w:b w:val="1"/><w:bCs w:val="1"/><w:color w:val="434343"/><w:sz w:val="24"/><w:szCs w:val="24"/>'
    return (f'<w:p><w:pPr><w:pStyle w:val="Heading3"/><w:keepNext w:val="1"/><w:spacing w:after="60" w:before="160"/>'
            f'<w:rPr>{rpr}</w:rPr></w:pPr><w:r><w:rPr>{rpr}</w:rPr><w:t xml:space="preserve">{escape(text, quote=False)}</w:t></w:r></w:p>')


def table(rows):
    ncol = len(rows[0])
    lens = [max(len(re.sub(r"[*`]", "", r[c])) for r in rows) for c in range(ncol)]
    lens = [min(max(n, 6), 60) for n in lens]
    widths = [int(TEXT_W * n / sum(lens)) for n in lens]
    widths[-1] += TEXT_W - sum(widths)
    b = '<w:{0} w:val="single" w:sz="4" w:space="0" w:color="999999"/>'
    borders = "".join(b.format(s) for s in ("top", "left", "bottom", "right", "insideH", "insideV"))
    x = [f'<w:tbl><w:tblPr><w:tblW w:w="{TEXT_W}" w:type="dxa"/><w:jc w:val="center"/><w:tblBorders>{borders}</w:tblBorders>'
         f'<w:tblLayout w:type="fixed"/><w:tblCellMar><w:top w:w="40" w:type="dxa"/><w:left w:w="80" w:type="dxa"/>'
         f'<w:bottom w:w="40" w:type="dxa"/><w:right w:w="80" w:type="dxa"/></w:tblCellMar></w:tblPr><w:tblGrid>'
         + "".join(f'<w:gridCol w:w="{w}"/>' for w in widths) + "</w:tblGrid>"]
    for i, r in enumerate(rows):
        hdr = i == 0
        x.append("<w:tr>" + ('<w:trPr><w:tblHeader/><w:cantSplit/></w:trPr>' if hdr else '<w:trPr><w:cantSplit/></w:trPr>'))
        for c, cell in enumerate(r):
            shd = '<w:shd w:val="clear" w:color="auto" w:fill="EFEFEF"/>' if hdr else ""
            base = '<w:b w:val="1"/><w:bCs w:val="1"/>' if hdr else ""
            x.append(f'<w:tc><w:tcPr><w:tcW w:w="{widths[c]}" w:type="dxa"/>{shd}</w:tcPr>'
                     + para(cell, jc="left", after=0, base=base, size=18) + "</w:tc>")
        x.append("</w:tr>")
    x.append("</w:tbl>")
    return "".join(x) + para("", after=60)


def box(text):
    return (f'<w:tbl><w:tblPr><w:tblW w:w="{TEXT_W}" w:type="dxa"/><w:jc w:val="center"/><w:tblBorders>'
            '<w:top w:val="single" w:sz="4" w:space="0" w:color="999999"/><w:left w:val="single" w:sz="4" w:space="0" w:color="999999"/>'
            '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="999999"/><w:right w:val="single" w:sz="4" w:space="0" w:color="999999"/>'
            '</w:tblBorders><w:tblLayout w:type="fixed"/><w:tblCellMar><w:top w:w="100" w:type="dxa"/><w:left w:w="140" w:type="dxa"/>'
            f'<w:bottom w:w="60" w:type="dxa"/><w:right w:w="140" w:type="dxa"/></w:tblCellMar></w:tblPr><w:tblGrid><w:gridCol w:w="{TEXT_W}"/></w:tblGrid>'
            f'<w:tr><w:trPr><w:cantSplit/></w:trPr><w:tc><w:tcPr><w:tcW w:w="{TEXT_W}" w:type="dxa"/><w:shd w:val="clear" w:color="auto" w:fill="F5F5F0"/></w:tcPr>'
            + para(text, after=60, size=20) + "</w:tc></w:tr></w:tbl>" + para("", after=60))


def png_size(path):
    d = Path(path).read_bytes()[:24]
    return struct.unpack(">II", d[16:24])


def figure(rid, n, path, caption, width_in=6.5):
    w, h = png_size(path)
    cx = int(914400 * width_in)
    cy = int(cx * h / w)
    drawing = (f'<w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/>'
               f'<wp:docPr id="{100 + n}" name="Figure {n}"/><a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
               '<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
               '<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
               f'<pic:nvPicPr><pic:cNvPr id="{100 + n}" name="fig{n}.png"/><pic:cNvPicPr/></pic:nvPicPr>'
               f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
               f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
               '</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing>')
    img = f'<w:p><w:pPr><w:keepNext w:val="1"/><w:spacing w:before="120" w:after="60"/><w:jc w:val="center"/></w:pPr><w:r>{drawing}</w:r></w:p>'
    return img + para(caption, jc="both", after=200, base='<w:i w:val="1"/><w:iCs w:val="1"/>', size=19)


def body(md: str, figdir: Path, media: list):
    out, lines, i = [], md.splitlines(), 0
    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if not s or s.startswith(("% TITLE", "% ABSTRACT", "% AUTHORS")):
            i += 1
            continue
        if s.startswith("## "):
            out.append(heading2(s[3:]))
        elif s.startswith("### "):
            out.append(heading3(s[4:]))
        elif s.startswith("% FIGURE:"):
            name, cap = [p.strip() for p in s[len("% FIGURE:"):].split("|", 1)]
            name, _, width = name.partition("@")  # optional "@inches"
            rid = f"rIdFig{len(media) + 1}"
            media.append((rid, name))
            out.append(figure(rid, len(media), figdir / name, cap, float(width or 6.5)))
        elif s.startswith("% BOX:"):
            out.append(box(s[len("% BOX:"):].strip()))
        elif s.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            out.append(table(rows))
            continue
        elif re.match(r"\s*- ", ln):
            lvl = (len(ln) - len(ln.lstrip())) // 2
            out.append(para(re.sub(r"^\s*- ", "", ln), num=(3, lvl), after=60,
                            ind=f'<w:ind w:left="{360 * (lvl + 1) + 360}" w:hanging="360"/>'))
        elif re.match(r"\d+\. ", s):
            out.append(para(re.sub(r"^\d+\. ", "", s), num=(5, 0), after=60, ind='<w:ind w:left="720" w:hanging="360"/>'))
        elif s.startswith("*Table") and s.endswith("*"):
            out.append(para(s, jc="left", after=60, size=19, keep=True))
        else:
            out.append(para(s))
        i += 1
    return "".join(out)


def build(template: Path, figdir: Path, out: Path):
    md = (HERE / "submission.md").read_text()
    title = re.search(r"^% TITLE: (.+)$", md, re.M).group(1).strip()
    abstract = re.search(r"^% ABSTRACT: (.+)$", md, re.M).group(1).strip()
    zin = zipfile.ZipFile(template)
    doc = zin.read("word/document.xml").decode()

    doc = doc.replace(">PROJECT TITLE<", f">{escape(title, quote=False)}<", 1)
    # authors: the template's 2x3 grid; fill slots 1 and 3 of the first row (keeps it centred), drop the second row
    authors = [tuple(x.strip() for x in a.split("|")) for a in re.search(r"^% AUTHORS: (.+)$", md, re.M).group(1).split(";")]
    slots = {0: authors[0], 2: authors[1]} if len(authors) == 2 else dict(enumerate(authors))
    row2 = next(tr for tr in re.findall(r"<w:tr>.*?</w:tr>", doc, re.S) if "Author name 4" in tr and "Author name 1" not in tr)
    doc = doc.replace(row2, "", 1)
    for k in range(3):
        name, aff = slots.get(k, ("", ""))
        doc = doc.replace(f">Author name {k + 1}<", f">{escape(name, quote=False)}<", 1)
        doc = doc.replace(">Affiliation<", f">{escape(aff, quote=False)}<", 1)
    # abstract: replace the guidance paragraph inside the Table4 box
    t4 = re.search(r'<w:tbl><w:tblPr><w:tblStyle w:val="Table4"/>.*?</w:tbl>', doc, re.S)
    t4x = t4.group(0)
    gp = next(p for p in re.findall(r"<w:p[ >].*?</w:p>", t4x, re.S) if "Summarize your project" in p)
    ppr = re.search(r"<w:pPr>.*?</w:pPr>", gp, re.S).group(0).replace('<w:u w:val="single"/>', "")
    t4x = t4x.replace(gp, f"<w:p>{ppr}{runs(abstract)}</w:p>")
    doc = doc[:t4.start()] + t4x + doc[t4.end():]

    # keep the title block (Table1, which nests the author and abstract tables); drop the guidance box (Table5) onward
    cut = doc.index('<w:tbl><w:tblPr><w:tblStyle w:val="Table5"/>')
    sect = re.search(r"<w:sectPr>.*?</w:sectPr>\s*</w:body>", doc, re.S)
    media = []
    new = body(md, figdir, media)
    doc = doc[:cut] + new + sect.group(0) + doc[sect.end():]
    if "xmlns:wp=" not in doc[:3000]:
        doc = doc.replace("<w:document ", '<w:document xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" ', 1)

    rels = zin.read("word/_rels/document.xml.rels").decode()
    rels = rels.replace("</Relationships>", "".join(
        f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/{name}"/>'
        for rid, name in media) + "</Relationships>")
    ct = zin.read("[Content_Types].xml").decode()
    if 'Extension="png"' not in ct:
        ct = ct.replace("<Default ", '<Default ContentType="image/png" Extension="png"/><Default ', 1)

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for item in zin.infolist():
            if item.is_dir() or item.filename.endswith("/"):
                continue
            data = zin.read(item.filename)
            if item.filename == "word/document.xml":
                data = doc.encode()
            elif item.filename == "word/_rels/document.xml.rels":
                data = rels.encode()
            elif item.filename == "[Content_Types].xml":
                data = ct.encode()
            z.writestr(item.filename, data)
        for _, name in media:
            z.write(figdir / name, f"word/media/{name}")
    print(f"wrote {out} ({len(media)} figures)")


if __name__ == "__main__":
    build(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
