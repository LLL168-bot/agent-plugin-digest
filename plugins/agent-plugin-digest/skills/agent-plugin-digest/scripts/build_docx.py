#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render items.json into a portable Word digest with clickable hyperlinks."""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _config import load, utf8_stdio  # noqa: E402

from docx import Document  # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH  # noqa: E402
from docx.opc.constants import RELATIONSHIP_TYPE as RT  # noqa: E402
from docx.oxml import OxmlElement  # noqa: E402
from docx.oxml.ns import qn  # noqa: E402
from docx.shared import Cm, Pt, RGBColor  # noqa: E402


def default_font():
    if sys.platform.startswith("win"):
        return "Microsoft YaHei"
    if sys.platform == "darwin":
        return "PingFang SC"
    return "Noto Sans CJK SC"


def setup(doc, font_name):
    normal = doc.styles["Normal"]
    normal.font.name = font_name
    normal.font.size = Pt(10.5)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), font_name)
    normal.paragraph_format.space_after = Pt(4)
    normal.paragraph_format.line_spacing = 1.3
    for section in doc.sections:
        section.top_margin = Cm(2.2)
        section.bottom_margin = Cm(2.2)
        section.left_margin = Cm(2.4)
        section.right_margin = Cm(2.4)


def add_hyperlink(paragraph, url):
    rel_id = paragraph.part.relate_to(url, RT.HYPERLINK, is_external=True)
    link = OxmlElement("w:hyperlink")
    link.set(qn("r:id"), rel_id)
    run = OxmlElement("w:r")
    props = OxmlElement("w:rPr")
    color = OxmlElement("w:color")
    color.set(qn("w:val"), "0563C1")
    props.append(color)
    underline = OxmlElement("w:u")
    underline.set(qn("w:val"), "single")
    props.append(underline)
    size = OxmlElement("w:sz")
    size.set(qn("w:val"), "21")
    props.append(size)
    run.append(props)
    text = OxmlElement("w:t")
    text.text = url
    text.set(qn("xml:space"), "preserve")
    run.append(text)
    link.append(run)
    paragraph._p.append(link)


def validate(payload, expected_total=None, intro_range=None):
    sections = payload.get("sections") or []
    if not sections:
        raise SystemExit("items.json has no sections")
    total = 0
    urls = set()
    for section in sections:
        items = section.get("items") or []
        if not items:
            raise SystemExit(f"empty section: {section.get('title')}")
        for item in items:
            for key in ("name", "intro", "url"):
                if not str(item.get(key, "")).strip():
                    raise SystemExit(f"missing field {key}: {item}")
            if not str(item["url"]).startswith(("http://", "https://")):
                raise SystemExit(f"invalid url: {item['url']}")
            if item["url"] in urls:
                raise SystemExit(f"duplicate url: {item['url']}")
            urls.add(item["url"])
            total += 1
            if intro_range:
                low, high = intro_range
                length = len(str(item["intro"]))
                if length < low or length > high:
                    print(f"WARN: intro length {length} outside {low}-{high}: {item['name']}", file=sys.stderr)
    if expected_total and total != expected_total:
        raise SystemExit(f"item count {total} != expected {expected_total}")
    return total


def build(payload, out_path, output_cfg, batch):
    doc = Document()
    setup(doc, output_cfg.get("font") or default_font())
    labels = output_cfg.get("labels") or {}

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run(payload.get("title") or "Agent 插件 / Skill 清单")
    run.bold = True
    run.font.size = Pt(18)

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    default_subtitle = output_cfg.get("subtitle_pattern", "").format(
        date=dt.date.today().isoformat(),
        total=sum(len(section.get("items", [])) for section in payload.get("sections", [])),
        batch=batch,
    )
    sub_run = subtitle.add_run(payload.get("subtitle") or default_subtitle)
    sub_run.font.size = Pt(11)
    sub_run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

    if payload.get("note") and output_cfg.get("include_data_note", True):
        note = doc.add_paragraph()
        note.paragraph_format.space_before = Pt(10)
        note.add_run(labels.get("data_note", "数据说明：")).bold = True
        note.add_run(payload["note"])

    for section in payload["sections"]:
        doc.add_heading(section["title"], level=1)
        for index, item in enumerate(section["items"], 1):
            head = doc.add_paragraph()
            head.paragraph_format.space_before = Pt(8)
            head.paragraph_format.space_after = Pt(2)
            name_run = head.add_run(f"{index}. {item['name']}")
            name_run.bold = True
            name_run.font.size = Pt(11)

            intro = doc.add_paragraph()
            intro.add_run(labels.get("intro", "项目介绍：")).bold = True
            intro.add_run(item["intro"])

            link = doc.add_paragraph()
            link.add_run(labels.get("link", "项目链接：")).bold = True
            add_hyperlink(link, item["url"])

    if payload.get("footer_note"):
        footer = doc.add_paragraph()
        footer.paragraph_format.space_before = Pt(14)
        footer.add_run(labels.get("notes", "备注：")).bold = True
        footer.add_run(payload["footer_note"])

    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out_path))


def resolve_output(args, cfg, total, batch):
    if args.out:
        return Path(args.out)
    out_dir = Path(args.out_dir or cfg["dir"])
    pattern = args.pattern or cfg["filename_pattern"]
    filename = pattern.format(date=dt.date.today().isoformat(), total=total, batch=batch)
    return out_dir / filename


def main():
    utf8_stdio()
    parser = argparse.ArgumentParser(description="Render items.json to a Word document")
    parser.add_argument("--input", required=True)
    parser.add_argument("--config", default="")
    parser.add_argument("--out", default="", help="explicit output path")
    parser.add_argument("--out-dir", default="")
    parser.add_argument("--pattern", default="")
    parser.add_argument("--batch", type=int, default=0)
    parser.add_argument("--expected-total", type=int, default=0)
    args = parser.parse_args()

    data = load(args.config or None)
    output_cfg = data["output"]
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    intro_range = (output_cfg["intro_min_chars"], output_cfg["intro_max_chars"])
    total = validate(payload, args.expected_total or None, intro_range)
    batch = payload.get("batch") or args.batch or 1

    out_path = resolve_output(args, output_cfg, total, batch)
    build(payload, out_path, output_cfg, batch)
    print(f"wrote {total} items -> {out_path}")


if __name__ == "__main__":
    main()
