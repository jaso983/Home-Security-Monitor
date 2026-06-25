"""添加模型对比数据到三个docx文档（两栏对比：YOLOv8n通用预训练 vs Home-fire自训练）。"""

import os
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

DOCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs")

COMPARISON_DATA = [
    ["指标", "YOLOv8n 通用预训练 (COCO)", "Home-fire 自训练 (epoch 80)"],
    ["类别", "80类（不含fire/smoke）", "2类 (fire/smoke)"],
    ["模型大小", "~6 MB", "~6 MB"],
    ["mAP@50", "~0（无相关类别）", "0.930"],
    ["mAP@50-95", "—", "0.575"],
    ["Precision", "—", "0.923"],
    ["Recall", "—", "0.883"],
]

ANALYSIS_TEXT = (
    "YOLOv8n COCO 预训练模型不包含 fire/smoke 类别（80 类为 person/car/dog 等通用目标），"
    "在 Home-fire 测试集上 mAP 接近 0，无法直接用于家庭火灾检测。"
    "Home-fire 自训练模型针对室内家庭火灾场景进行迁移学习："
    "类别聚焦 fire/smoke 2 类，AdamW 优化器 + 余弦学习率衰减 + close_mosaic + 硬负样本挖掘，"
    "100 epochs 训练后 mAP50 达 0.930，满足家庭安防监控实际需求。"
)

TRAINING_PROGRESS = [
    ["Epoch", "cls_loss", "Precision", "Recall", "mAP50", "mAP50-95"],
    ["1", "5.27", "0.242", "0.214", "0.130", "0.044"],
    ["20", "2.90", "0.788", "0.708", "0.768", "0.385"],
    ["40", "2.37", "0.867", "0.804", "0.869", "0.457"],
    ["60", "1.98", "0.912", "0.827", "0.901", "0.537"],
    ["80 (最优)", "1.65", "0.923", "0.883", "0.930", "0.575"],
    ["100", "1.15", "0.913", "0.877", "0.926", "0.583"],
]


def add_table_after(doc, heading_text, table_data):
    """在指定标题后添加表格。"""
    target_para = None
    for para in doc.paragraphs:
        if heading_text in para.text:
            target_para = para
            break

    if target_para is None:
        print(f"  警告: 未找到标题 '{heading_text}'，跳过")
        return

    table = doc.add_table(rows=len(table_data), cols=len(table_data[0]))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    for i, row_data in enumerate(table_data):
        for j, cell_text in enumerate(row_data):
            cell = table.cell(i, j)
            cell.text = cell_text
            for paragraph in cell.paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in paragraph.runs:
                    run.font.size = Pt(10)
                    if i == 0:
                        run.font.bold = True

    target_element = target_para._element
    table_element = table._tbl
    target_element.addnext(table_element)
    print(f"  已添加表格到 '{heading_text}' 之后")


def add_paragraph_after(doc, heading_text, text):
    """在指定标题后添加段落。"""
    target_para = None
    for para in doc.paragraphs:
        if heading_text in para.text:
            target_para = para
            break

    if target_para is None:
        print(f"  警告: 未找到标题 '{heading_text}'，跳过")
        return

    new_para = doc.add_paragraph(text)
    for run in new_para.runs:
        run.font.size = Pt(11)
    target_para._element.addnext(new_para._element)
    print(f"  已添加段落到 '{heading_text}' 之后")


def update_course_report():
    """更新课程设计报告书。"""
    path = os.path.join(DOCS_DIR, "课程设计报告书.docx")
    if not os.path.exists(path):
        print(f"文件不存在: {path}")
        return

    doc = Document(path)

    for para in doc.paragraphs:
        if "模型对比" in para.text:
            add_paragraph_after(doc, para.text,
                "训练过程中关键指标变化：")
            add_table_after(doc, "训练过程中关键指标变化", TRAINING_PROGRESS)
            add_paragraph_after(doc, "训练过程中关键指标变化",
                "YOLOv8n 通用预训练模型与 Home-fire 自训练模型对比：")
            add_table_after(doc, "YOLOv8n 通用预训练模型与 Home-fire 自训练模型对比", COMPARISON_DATA)
            add_paragraph_after(doc, "YOLOv8n 通用预训练模型与 Home-fire 自训练模型对比", ANALYSIS_TEXT)
            break

    doc.save(path)
    print(f"已保存: {path}")


def update_design_doc():
    """更新设计文档。"""
    path = os.path.join(DOCS_DIR, "设计文档.docx")
    if not os.path.exists(path):
        print(f"文件不存在: {path}")
        return

    doc = Document(path)

    for para in doc.paragraphs:
        if "训练数据选择分析" in para.text:
            add_paragraph_after(doc, para.text,
                "YOLOv8n 通用预训练模型与 Home-fire 自训练模型对比：")
            add_table_after(doc, "YOLOv8n 通用预训练模型与 Home-fire 自训练模型对比", COMPARISON_DATA)
            break

    doc.save(path)
    print(f"已保存: {path}")


def update_test_doc():
    """更新测试文档。"""
    path = os.path.join(DOCS_DIR, "测试文档.docx")
    if not os.path.exists(path):
        print(f"文件不存在: {path}")
        return

    doc = Document(path)

    for para in doc.paragraphs:
        if "训练数据选择对比" in para.text:
            add_paragraph_after(doc, para.text,
                "YOLOv8n 通用预训练模型与 Home-fire 自训练模型对比：")
            add_table_after(doc, "YOLOv8n 通用预训练模型与 Home-fire 自训练模型对比", COMPARISON_DATA)
            break

    doc.save(path)
    print(f"已保存: {path}")


if __name__ == "__main__":
    print("更新课程设计报告书...")
    update_course_report()
    print("\n更新设计文档...")
    update_design_doc()
    print("\n更新测试文档...")
    update_test_doc()
    print("\n完成！")
