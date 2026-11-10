# -*- coding: utf-8 -*-
"""提取 PPTX/DOCX 大纲，输出到 tools/ 结果文件"""
import sys, json, io
from pathlib import Path

ROOT = Path(r"D:\数据文件\上课\信电导论")
OUT = ROOT / "开发板" / "_outline"
OUT.mkdir(exist_ok=True)

def pptx_outline(p: Path):
    from pptx import Presentation
    prs = Presentation(str(p))
    lines = [f"# {p.name}  (共 {len(prs.slides)} 页)"]
    for i, slide in enumerate(prs.slides, 1):
        texts = []
        for sh in slide.shapes:
            if sh.has_text_frame:
                t = " ".join(x.strip() for x in sh.text_frame.text.split("\n") if x.strip())
                if t:
                    texts.append(t)
            if sh.has_table:
                for r in sh.table.rows:
                    texts.append(" | ".join(c.text.strip() for c in r.cells))
        pic = sum(1 for sh in slide.shapes if sh.shape_type == 13)
        lines.append(f"\n## Slide {i}" + (f"  [{pic} 图]" if pic else ""))
        for t in texts:
            lines.append(f"- {t[:400]}")
    return "\n".join(lines)

def docx_outline(p: Path, limit=1200):
    import docx
    d = docx.Document(str(p))
    lines = [f"# {p.name}  段落 {len(d.paragraphs)} / 表格 {len(d.tables)} / 图片 {len(d.inline_shapes)}"]
    n = 0
    for para in d.paragraphs:
        t = para.text.strip()
        if not t:
            continue
        style = para.style.name if para.style else ""
        if style.startswith("Heading") or style.startswith("标题"):
            lines.append(f"\n[{style}] {t}")
        else:
            lines.append(f"- {t[:300]}")
        n += 1
        if n >= limit:
            lines.append("...(截断)")
            break
    for ti, tb in enumerate(d.tables[:5], 1):
        lines.append(f"\n[表{ti}] {len(tb.rows)}x{len(tb.columns)}")
        for r in tb.rows[:6]:
            lines.append("  | " + " | ".join(c.text.strip()[:40] for c in r.cells))
    return "\n".join(lines)

targets = [p for p in ROOT.rglob("*") if p.suffix.lower() in (".pptx", ".docx") and p.is_file()]
for p in targets:
    try:
        txt = pptx_outline(p) if p.suffix.lower() == ".pptx" else docx_outline(p)
        f = OUT / (p.stem + ".outline.md")
        f.write_text(txt, encoding="utf-8")
        print(f"[OK] {p.name} -> {f.name}  ({len(txt)} chars)")
    except Exception as e:
        print(f"[ERR] {p.name}: {type(e).__name__}: {e}")
