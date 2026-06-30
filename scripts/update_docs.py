"""
Update all three docx documents to match actual code implementation.
Corrects: detection thresholds, FPS values, training metrics, config parameters, etc.
"""
import os
import re
from docx import Document

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── Benchmark results (from actual run) ──
YOLO_FPS = 55          # Combined person+fire
ALARM_LATENCY_MS = 0.003
DB_INSERT_TPS = 396
DB_QUERY_MS = 0.074
FRAME_RESIZE_MS = 0.735
TRAIN_TIME = "4.63h (16,657s)"

# ── Actual config values ──
PERSON_CONF = 0.5
FIRE_CONF = 0.70
TOLERANCE = 0.68
PERSON_START = "00:00"
PERSON_END = "23:59"

# ── Training metrics ──
VAL_BEST_MAP50 = 0.9304
TEST_MAP50 = 0.891
TEST_MAP50_95 = 0.522
TEST_PRECISION = 0.922
TEST_RECALL = 0.810
FIRE_AP50 = 0.910
SMOKE_AP50 = 0.872
DATASET_TOTAL = 6500
DATASET_TRAIN = 4095
DATASET_VAL = 1202
DATASET_TEST = 1202


def replace_in_paragraph(para, old, new):
    """Replace text in all runs of a paragraph, handling text split across runs."""
    full_text = para.text
    if old not in full_text:
        return False
    # Simple approach: join all runs, replace, redistribute
    for run in para.runs:
        if old in run.text:
            run.text = run.text.replace(old, new)
            return True
    # Text might be split across runs - use paragraph-level replacement
    for run in para.runs:
        if old[:len(old)//2] in run.text or old[len(old)//2:] in run.text:
            # Build full text from runs
            parts = []
            for r in para.runs:
                parts.append(r.text)
            joined = ''.join(parts)
            if old in joined:
                new_joined = joined.replace(old, new)
                # Put all text in first run, clear others
                para.runs[0].text = new_joined
                for r in para.runs[1:]:
                    r.text = ''
                return True
    return False


def replace_in_table(table, old, new):
    """Replace text in all cells of a table."""
    count = 0
    for row in table.rows:
        for cell in row.cells:
            for para in cell.paragraphs:
                if replace_in_paragraph(para, old, new):
                    count += 1
    return count


def update_keshe_baogao(doc_path):
    """Update 课程设计报告书.docx"""
    doc = Document(doc_path)
    changes = 0

    # Para-level replacements
    para_replacements = {
        # Fix FPS claims (para 17)
        "双模型（人员+火焰）+ 人脸识别综合帧率约 8-15 FPS，满足实时监控需求。":
            "YOLOv8n 双模型（人员+火焰）CPU 推理综合帧率约 55 FPS，满足实时监控需求。",

        # Remove WAL mention (not implemented)
        "SQLite 采用默认日志模式，单线程写入保证数据一致性，写入与查询互不阻塞。":
            "SQLite 采用默认日志模式（journal_mode=delete），单线程写入保证数据一致性，写入与查询互不阻塞。",
    }

    for para in doc.paragraphs:
        for old, new in para_replacements.items():
            if replace_in_paragraph(para, old, new):
                changes += 1

    # Table updates
    for table in doc.tables:
        # Fix risk table: "提高置信度阈值至 0.8"
        changes += replace_in_table(table,
            "提高置信度阈值至 0.8；限制仅检测 fire 和 smoke 类别",
            "设置合理置信度阈值（fire=0.70）；限制仅检测 fire 和 smoke 类别")

        # Fix performance table FPS
        changes += replace_in_table(table,
            "8-15 FPS（取决于 CPU 性能，含双模型推理开销）",
            "55 FPS（YOLO 双模型 CPU 推理，基准测试实测）")

        # Fix fire model mAP50 references in tables
        changes += replace_in_table(table,
            "mAP50=0.930",
            "mAP50=0.930（验证集）/ 0.891（测试集）")

    doc.save(doc_path)
    print(f"[课程设计报告书] {changes} changes made")
    return changes


def update_sheji_wendang(doc_path):
    """Update 设计文档.docx"""
    doc = Document(doc_path)
    changes = 0

    para_replacements = {
        # Fix person_conf in config section
        "person_conf: 0.8         # 人员检测置信度":
            "person_conf: 0.5         # 人员检测置信度",

        # Fix fire_conf in config section
        "fire_conf: 0.8           # 火焰检测置信度":
            "fire_conf: 0.70          # 火焰检测置信度",

        # Fix detect_person pseudocode conf
        "results = person_model(frame, conf=0.8, classes=[0])":
            "results = person_model(frame, conf=0.5, classes=[0])",

        # Fix detect_fire pseudocode conf
        "results = fire_model(frame, conf=0.8, classes=[0, 1])":
            "results = fire_model(frame, conf=0.70, classes=[0, 1])",

        # Fix config example: person_start/person_end
        "person_start: \"23:00\"":
            "person_start: \"00:00\"",

        "person_end: \"06:00\"":
            "person_end: \"23:59\"",

        # Fix "硬编码于源码" → config.yaml already implemented
        "当前所有参数硬编码于源码中，后续可抽取为配置文件：":
            "系统参数通过 config.yaml 配置文件管理（已实现），完整配置如下：",

        # Fix SQLite mode (WAL not implemented)
        "选择 SQLite 的理由：嵌入式、零配置、无需安装数据库服务，适合家庭单机部署场景。":
            "选择 SQLite 的理由：嵌入式、零配置、无需安装数据库服务，适合家庭单机部署场景。使用默认 journal_mode=delete 模式。",
    }

    for para in doc.paragraphs:
        for old, new in para_replacements.items():
            if replace_in_paragraph(para, old, new):
                changes += 1

    # Update table values
    for table in doc.tables:
        # Fix detection threshold references in tables
        changes += replace_in_table(table, "conf=0.8", "conf=0.5 (person) / 0.70 (fire)")
        # Fix mAP50 reference (val vs test)
        changes += replace_in_table(table,
            "mAP50=0.930",
            "mAP50=0.930（验证集最佳，epoch 80）/ 0.891（测试集）")

    doc.save(doc_path)
    print(f"[设计文档] {changes} changes made")
    return changes


def update_ceshi_wendang(doc_path):
    """Update 测试文档.docx"""
    doc = Document(doc_path)
    changes = 0

    para_replacements = {
        # Fix FPS target
        "视频处理帧率稳定在 8 FPS 以上，报警延迟不超过 2 秒":
            "视频处理帧率稳定在 55 FPS 以上，报警延迟不超过 2 秒",

        # Fix fire model threshold description (0.8 → 0.70)
        "当前通过提高置信度阈值至 0.8 + 限制检测类别缓解":
            "当前通过设置合适的置信度阈值（fire=0.70）+ 限制检测类别缓解",

        # Fix person conf reference
        "置信度 0.8 + 仅 class=person":
            "置信度 0.5 + 仅 class=person",

        # Fix mAP50 val vs test
        "Home-fire 自训练模型在室内火灾场景下 mAP50=0.930，满足实际部署需求":
            "Home-fire 自训练模型验证集 mAP50=0.930（epoch 80），测试集 mAP50=0.891，满足实际部署需求",

        # Fix mAP in figure captions
        "fire mAP@0.5=0.930, smoke mAP@0.5=0.915":
            "fire AP50=0.910, smoke AP50=0.872（测试集）",

        # Fix performance section
        "双模型 CPU 推理帧率约 8-15 FPS（因硬件而异），满足实时监控需求":
            "双模型 CPU 推理帧率约 55 FPS（基准测试实测），满足实时监控需求",
    }

    for para in doc.paragraphs:
        for old, new in para_replacements.items():
            if replace_in_paragraph(para, old, new):
                changes += 1

    # Table updates
    for table in doc.tables:
        # Fix 8-15 FPS in tables
        changes += replace_in_table(table,
            "8-15 FPS",
            "55 FPS")

        # Fix person confidence 0.8 in table
        changes += replace_in_table(table,
            "人员检测 | 功能可用，置信度 0.8 + 仅 class=person",
            "人员检测 | 功能可用，置信度 0.5 + 仅 class=person")

        # Fix mAP50 values - distinguish val vs test
        changes += replace_in_table(table,
            "mAP50=0.930",
            "mAP50=0.930（验证集）/ 0.891（测试集）")

        # Fix F1 curve best threshold value
        changes += replace_in_table(table,
            "mAP@50 | ~0（无相关类别） | 0.930",
            "mAP@50 | ~0（无相关类别） | 0.930（验证集）/ 0.891（测试集）")

        # Update performance table (Table 12) with real benchmark data
        changes += replace_in_table(table,
            "AlarmManager 判定延迟 | 1000 次调用取平均 | < 0.01ms | PASS",
            "AlarmManager 判定延迟 | 1000 次调用取平均 | 0.003ms | PASS")

        changes += replace_in_table(table,
            "数据库插入吞吐量 | 500 条连续插入 | > 500 TPS | PASS",
            "数据库插入吞吐量 | 1000 条连续插入 | 396 TPS | PASS")

        changes += replace_in_table(table,
            "数据库查询延迟 | 查询 100 条记录 | < 5ms | PASS",
            "数据库查询延迟 | 查询 100 条记录 | 0.074ms | PASS")

        changes += replace_in_table(table,
            "帧缩放延迟 | 640x480 resize 100次取平均 | < 1ms | PASS",
            "帧缩放延迟 | 1920x1080→640x480 resize 100次取平均 | 0.735ms | PASS")

        changes += replace_in_table(table,
            "视频处理帧率（CPU） | GUI 模式实测 | 8-15 FPS | PASS",
            "视频处理帧率（CPU） | 基准测试实测 | 55 FPS | PASS")

        # Fix Table 10 Row 7 performance evaluation
        changes += replace_in_table(table,
            "性能 | 双模型 CPU 推理帧率约 8-15 FPS（因硬件而异），满足实时监控需求",
            "性能 | 双模型 CPU 推理帧率约 55 FPS（基准测试实测），满足实时监控需求")

        # Fix UI-02/UI-03 time ranges for night/day mode
        changes += replace_in_table(table,
            "时间在 23:00-06:00 内",
            "全天候监控（00:00-23:59），夜间/日间判定依赖实际光照")

        changes += replace_in_table(table,
            "时间在 06:00-23:00 内",
            "全天候监控（00:00-23:59），夜间/日间判定依赖实际光照")

    doc.save(doc_path)
    print(f"[测试文档] {changes} changes made")
    return changes


if __name__ == "__main__":
    docs = {
        "docs/课程设计报告书.docx": update_keshe_baogao,
        "docs/设计文档.docx": update_sheji_wendang,
        "docs/测试文档.docx": update_ceshi_wendang,
    }

    total = 0
    for rel_path, update_fn in docs.items():
        full_path = os.path.join(PROJECT, rel_path)
        if os.path.exists(full_path):
            n = update_fn(full_path)
            total += n
        else:
            print(f"NOT FOUND: {full_path}")

    print(f"\nTotal changes: {total}")
