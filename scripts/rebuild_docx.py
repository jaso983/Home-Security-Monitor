"""使用 python-docx 从 md 源文件重建三个 .docx 文档，修复格式问题。

解决的问题：
- 所有段落均为 Normal 样式，标题没有 Heading 层级
- 编号重复（如两个"3."）
- 标题和正文无法区分
"""

import os
import re
from docx import Document
from docx.shared import Pt, Cm, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

DOCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs")

# Font/size constants
TITLE_FONT = "SimHei"
TITLE_SIZE = Pt(36)
SUBTITLE_SIZE = Pt(22)
INFO_FONT = "SimSun"
INFO_SIZE = Pt(15)
HEADING1_SIZE = Pt(16)  # 三号
HEADING2_SIZE = Pt(14)  # 四号
HEADING3_SIZE = Pt(12)  # 小四
BODY_SIZE = Pt(12)       # 小四
TABLE_HEADER_SIZE = Pt(12)
TABLE_CELL_SIZE = Pt(10.5)  # 五号
CODE_FONT = "Consolas"


def set_run_font(run, font_name, size, bold=None):
    """设置 run 的字体属性，同时设置中文字体（eastAsia）。"""
    run.font.name = font_name
    run.font.size = size
    if bold is not None:
        run.font.bold = bold
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = rPr.makeelement(qn("w:rFonts"), {})
        rPr.insert(0, rFonts)
    rFonts.set(qn("w:eastAsia"), font_name)


def add_cover_page(doc, subtitle_text):
    """添加封面页，格式与原模板一致。"""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Emu(198120)
    run = p.add_run("软件工程课程设计报告书")
    set_run_font(run, TITLE_FONT, TITLE_SIZE)

    for _ in range(2):
        doc.add_paragraph()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(subtitle_text)
    set_run_font(run, TITLE_FONT, SUBTITLE_SIZE, bold=True)

    for _ in range(2):
        doc.add_paragraph()

    fields = [
        "学  院", "专  业", "组长姓名", "组  员",
        "指导教师", "课程编号", "课程学分", "起始日期",
    ]
    for field in fields:
        p = doc.add_paragraph()
        run = p.add_run(field)
        set_run_font(run, INFO_FONT, INFO_SIZE, bold=True)

    doc.add_page_break()


def add_evaluation_table(doc):
    """添加教师评语表。"""
    table = doc.add_table(rows=3, cols=2)
    table.style = "Table Grid"

    cells_data = [
        ("教\n师\n评\n语", "\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n教师签名：\n日期："),
        ("成\n绩\n评\n定", "\n\n\n\n\n"),
        ("备\n注", "\n\n"),
    ]
    for i, (left, right) in enumerate(cells_data):
        table.rows[i].cells[0].text = left
        table.rows[i].cells[1].text = right
        for cell in table.rows[i].cells:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    set_run_font(run, INFO_FONT, INFO_SIZE, bold=True)


def setup_heading_styles(doc):
    """配置 Heading 1/2/3 样式的字体。"""
    for style_name, font_size in [
        ("Heading 1", HEADING1_SIZE),
        ("Heading 2", HEADING2_SIZE),
        ("Heading 3", HEADING3_SIZE),
    ]:
        style = doc.styles[style_name]
        style.font.name = TITLE_FONT
        style.font.size = font_size
        style.font.bold = True
        style.font.color.rgb = None
        rPr = style.element.find(qn("w:rPr"))
        if rPr is None:
            rPr = style.element.makeelement(qn("w:rPr"), {})
            style.element.insert(0, rPr)
        rFonts = rPr.find(qn("w:rFonts"))
        if rFonts is None:
            rFonts = rPr.makeelement(qn("w:rFonts"), {})
            rPr.insert(0, rFonts)
        rFonts.set(qn("w:eastAsia"), TITLE_FONT)


def setup_body_style(doc):
    """配置 Normal 样式：宋体小四，首行缩进2字符。"""
    style = doc.styles["Normal"]
    style.font.name = INFO_FONT
    style.font.size = BODY_SIZE
    style.font.bold = False
    rPr = style.element.find(qn("w:rPr"))
    if rPr is None:
        rPr = style.element.makeelement(qn("w:rPr"), {})
        style.element.insert(0, rPr)
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = rPr.makeelement(qn("w:rFonts"), {})
        rPr.insert(0, rFonts)
    rFonts.set(qn("w:eastAsia"), INFO_FONT)
    pf = style.paragraph_format
    pf.first_line_indent = Pt(24)


def add_table_from_md(doc, headers, rows):
    """从 md 表格数据生成 docx 表格。"""
    col_count = len(headers)
    table = doc.add_table(rows=1 + len(rows), cols=col_count)
    table.style = "Table Grid"

    for j, h in enumerate(headers):
        cell = table.rows[0].cells[j]
        cell.text = ""
        p = cell.paragraphs[0]
        run = p.add_run(h)
        set_run_font(run, INFO_FONT, TABLE_HEADER_SIZE, bold=True)

    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = table.rows[i + 1].cells[j]
            cell.text = ""
            p = cell.paragraphs[0]
            run = p.add_run(val)
            set_run_font(run, INFO_FONT, TABLE_CELL_SIZE)

    doc.add_paragraph()


def strip_md_formatting(text):
    """去除 md 格式标记。"""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
    return text


def parse_md_file(filepath):
    """解析 md 文件，返回结构化内容列表。"""
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    elements = []
    i = 0
    in_code_block = False
    code_lines = []
    table_lines = []

    while i < len(lines):
        line = lines[i].rstrip("\n")
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code_block:
                elements.append({"type": "code", "lines": code_lines})
                code_lines = []
                in_code_block = False
            else:
                in_code_block = True
            i += 1
            continue

        if in_code_block:
            code_lines.append(line)
            i += 1
            continue

        if stripped.startswith("#### "):
            elements.append({"type": "heading3", "text": strip_md_formatting(stripped[5:])})
            i += 1
            continue
        if stripped.startswith("### "):
            elements.append({"type": "heading2", "text": strip_md_formatting(stripped[4:])})
            i += 1
            continue
        if stripped.startswith("## "):
            elements.append({"type": "heading1", "text": strip_md_formatting(stripped[3:])})
            i += 1
            continue
        if stripped.startswith("# "):
            i += 1
            continue

        if stripped == "---":
            elements.append({"type": "separator"})
            i += 1
            continue

        if stripped.startswith("|") and "|" in stripped[1:]:
            table_lines.append(stripped)
            i += 1
            continue
        else:
            if table_lines:
                headers, rows = parse_table_lines(table_lines)
                elements.append({"type": "table", "headers": headers, "rows": rows})
                table_lines = []

        if re.match(r"^\d+\.\s", stripped) or stripped.startswith("- ") or stripped.startswith("* "):
            elements.append({"type": "list", "text": strip_md_formatting(stripped)})
            i += 1
            continue

        if stripped == "":
            i += 1
            continue

        elements.append({"type": "body", "text": strip_md_formatting(stripped)})
        i += 1

    if table_lines:
        headers, rows = parse_table_lines(table_lines)
        elements.append({"type": "table", "headers": headers, "rows": rows})

    return elements


def parse_table_lines(table_lines):
    """从 md 表格行解析出 headers 和 rows。"""
    data_lines = [l for l in table_lines if not re.match(r"^\|[\s\-:]+\|", l)]
    if len(data_lines) < 1:
        return [], []
    headers = [cell.strip() for cell in data_lines[0].split("|") if cell.strip()]
    rows = []
    for line in data_lines[1:]:
        cells = [cell.strip() for cell in line.split("|") if cell.strip()]
        rows.append(cells)
    return headers, rows


def add_elements_to_doc(doc, elements):
    """将解析后的 elements 写入 docx 文档。"""
    for elem in elements:
        t = elem["type"]

        if t == "heading1":
            p = doc.add_heading(elem["text"], level=1)
            for run in p.runs:
                set_run_font(run, TITLE_FONT, HEADING1_SIZE, bold=True)
            p.paragraph_format.first_line_indent = None

        elif t == "heading2":
            p = doc.add_heading(elem["text"], level=2)
            for run in p.runs:
                set_run_font(run, TITLE_FONT, HEADING2_SIZE, bold=True)
            p.paragraph_format.first_line_indent = None

        elif t == "heading3":
            p = doc.add_heading(elem["text"], level=3)
            for run in p.runs:
                set_run_font(run, TITLE_FONT, HEADING3_SIZE, bold=True)
            p.paragraph_format.first_line_indent = None

        elif t == "body":
            p = doc.add_paragraph(elem["text"])
            p.paragraph_format.first_line_indent = Pt(24)

        elif t == "list":
            p = doc.add_paragraph(elem["text"])
            p.paragraph_format.first_line_indent = Pt(24)

        elif t == "table":
            headers = elem["headers"]
            rows = elem["rows"]
            padded_rows = []
            for row in rows:
                if len(row) < len(headers):
                    row = row + [""] * (len(headers) - len(row))
                padded_rows.append(row[:len(headers)])
            add_table_from_md(doc, headers, padded_rows)

        elif t == "code":
            for line in elem["lines"]:
                p = doc.add_paragraph(line)
                p.paragraph_format.first_line_indent = None
                for run in p.runs:
                    set_run_font(run, CODE_FONT, Pt(10))


def build_docx(md_path, subtitle_text):
    """从 md 文件构建 docx 文档。"""
    doc = Document()

    section = doc.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(3.2)
    section.bottom_margin = Cm(3.2)
    section.left_margin = Cm(2.6)
    section.right_margin = Cm(2.6)

    setup_heading_styles(doc)
    setup_body_style(doc)

    add_cover_page(doc, subtitle_text)

    elements = parse_md_file(md_path)
    add_elements_to_doc(doc, elements)

    add_evaluation_table(doc)

    return doc


def main():
    configs = [
        {
            "md_file": "报告文档.md",
            "docx_file": "课程设计报告书.docx",
            "subtitle": "**题目",
        },
        {
            "md_file": "设计文档.md",
            "docx_file": "设计文档.docx",
            "subtitle": "题目***—设计文档",
        },
        {
            "md_file": "测试文档.md",
            "docx_file": "测试文档.docx",
            "subtitle": "题目***—测试文档",
        },
    ]

    for cfg in configs:
        md_path = os.path.join(DOCS_DIR, cfg["md_file"])
        docx_path = os.path.join(DOCS_DIR, cfg["docx_file"])
        doc = build_docx(md_path, cfg["subtitle"])
        doc.save(docx_path)
        print(f"[OK] {cfg['docx_file']} rebuilt from {cfg['md_file']}")

    print("\nAll docs rebuilt successfully.")


if __name__ == "__main__":
    main()
