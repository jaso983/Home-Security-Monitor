"""使用 python-docx 更新三个 .docx 文档，补充模型训练和陌生人识别相关内容。"""

import os
import sys
from docx import Document

DOCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs")


def find_paragraph_index(doc, text_prefix):
    """找到包含指定文本前缀的段落索引，返回第一个匹配。"""
    for i, p in enumerate(doc.paragraphs):
        if p.text.strip().startswith(text_prefix):
            return i
    return None


def insert_paragraph_after(doc, index, text, style="Normal"):
    """在指定索引的段落后插入新段落。"""
    p = doc.paragraphs[index]
    new_p = doc.add_paragraph(text, style=style)
    p._element.addnext(new_p._element)
    return new_p


def update_design_doc():
    """更新设计文档.docx"""
    path = os.path.join(DOCS_DIR, "设计文档.docx")
    doc = Document(path)
    changed = False

    # 1. 更新概要设计 - 模型层描述
    for p in doc.paragraphs:
        if "模型层（Models）：封装YOLO模型加载与推理" in p.text:
            p.text = "模型层（Models）：封装YOLO模型加载与推理，含自训练火焰/烟雾检测模型（基于YOLOv8n迁移学习）。包含yolo_detector.py、face_recognizer.py及YOLO预训练模型。"
            changed = True
            break

    # 2. 更新业务流程 - 加入陌生人识别
    for p in doc.paragraphs:
        if p.text.startswith("读取一帧画面后，判断是否在布防时段"):
            p.text = (
                "读取一帧画面后，判断是否在布防时段（23:00-06:00），"
                "若在布防时段则进行YOLO人员检测（conf=0.8, class=person），"
                "检测到人员后调用FaceRecognizer进行人脸比对：若为陌生人（非家庭成员）则经AlarmManager防抖判定，通过后保存截图并写入数据库；若为家庭成员则不触发报警。"
            )
            changed = True
            break

    # 3. 更新核心业务层模块划分
    for p in doc.paragraphs:
        if p.text.startswith("核心业务层：src/core/alarm_manager.py"):
            p.text = (
                "核心业务层：src/core/alarm_manager.py（AlarmManager报警防抖）、"
                "db_manager.py（DatabaseManager SQLite管理）、"
                "config.py（ConfigReader配置读取）、"
                "logger.py（日志初始化）、"
                "face_recognizer.py（FaceRecognizer陌生人识别）。"
            )
            changed = True
            break

    # 4. 更新模型层模块划分
    for p in doc.paragraphs:
        if p.text.startswith("模型层：src/models/yolo_detector.py"):
            p.text = (
                "模型层：src/models/yolo_detector.py（YoloDetector YOLO推理，含自训练火焰模型）、"
                "face_recognizer.py（人脸识别与陌生人判断）、family_faces/（家庭成员照片目录）。"
            )
            changed = True
            break

    # 5. 更新YoloDetector类描述
    for p in doc.paragraphs:
        if p.text.startswith("3.2 YoloDetector：YOLO检测器"):
            p.text = (
                "3.2 YoloDetector：YOLO检测器，属性含person_model（YOLO，COCO预训练yolov8n）、"
                "fire_model（YOLO，自训练火焰/烟雾模型，基于YOLOv8n迁移学习，classes: 0=fire, 1=smoke）。"
                "方法：detect_person(frame) -> (has_person, annotated_frame)、detect_fire(frame) -> (has_fire, annotated_frame)。"
            )
            changed = True
            break

    # 6. 在YoloDetector描述后添加FaceRecognizer类描述
    yolo_idx = find_paragraph_index(doc, "3.2 YoloDetector：")
    if yolo_idx is not None:
        has_face_desc = any("FaceRecognizer" in p.text for p in doc.paragraphs)
        if not has_face_desc:
            face_text = (
                "3.2.1 FaceRecognizer：人脸识别器，属性含recognizer（LBPHFaceRecognizer）、"
                "face_cascade（OpenCV Haar级联分类器）、known_faces_dir（家庭成员照片目录）。"
                "方法：is_stranger(frame) -> bool（检测画面中人脸并与家庭成员比对，未匹配返回True表示陌生人）、"
                "load_known_faces()（加载家庭成员照片并训练识别器）。"
                "底层使用OpenCV LBPH（Local Binary Patterns Histograms）算法，"
                "通过Haar级联检测人脸位置，LBPH提取纹理特征进行1:N比对，"
                "容差阈值由config.yaml中recognition.tolerance控制。"
            )
            insert_paragraph_after(doc, yolo_idx, face_text)
            changed = True

    # 7. 更新技术选型
    for p in doc.paragraphs:
        if p.text.startswith("5.1 技术选型：AI推理使用YOLOv8n+火焰检测模型"):
            p.text = (
                "5.1 技术选型：AI推理使用YOLOv8n+自训练火焰/烟雾检测模型（迁移学习，50 epochs，mAP50=0.765）；"
                "陌生人识别使用OpenCV LBPHFaceRecognizer（Local Binary Patterns Histograms）；"
                "GUI使用tkinter（Python内置）；数据库使用SQLite3（零配置）；"
                "图像处理使用OpenCV（opencv-contrib-python含face模块）；"
                "模型训练使用ultralytics YOLOv8框架，基于DFire数据集进行迁移学习。"
            )
            changed = True
            break

    # 8. 更新详细设计说明
    for p in doc.paragraphs:
        if p.text.startswith("5.5 详细设计说明："):
            p.text = (
                "5.5 详细设计说明：AlarmManager防抖算法采用last_alarm_time字典记录各事件类型最近触发时间，"
                "冷却期内（默认10秒）抑制重复报警，不同事件类型独立计时。"
                "YoloDetector人员检测使用COCO预训练yolov8n模型（class 0=person），"
                "火焰/烟雾检测使用自训练模型（DFire数据集迁移学习，classes: 0=fire, 1=smoke）。"
                "FaceRecognizer加载家庭成员照片（src/models/family_faces/），"
                "使用OpenCV Haar级联检测人脸、LBPH算法训练识别器、predict()方法判断是否为陌生人。"
                "人员检测流程：检测到person -> FaceRecognizer.is_stranger()判断 -> 陌生人时触发报警，家庭成员不报警。"
            )
            changed = True
            break

    # 9. 在GUI面板接口后添加模型训练章节
    gui_idx = find_paragraph_index(doc, "3.5 GUI面板接口")
    if gui_idx is not None:
        has_training_section = any("模型训练" in p.text for p in doc.paragraphs)
        if not has_training_section:
            training_lines = [
                "3.6 模型训练流程：",
                "（1）数据准备：从Kaggle下载DFire数据集（21,000+张图像，2类：fire/smoke），转换为YOLOv8格式放置于training/data/fire_smoke/目录。",
                "（2）迁移学习：基于COCO预训练yolov8n权重，使用ultralytics YOLOv8框架进行微调（train_fire.py），训练参数：epochs=50, imgsz=640, batch=16, device=cuda:0, patience=20。",
                "（3）训练环境：本地RTX 4060 Laptop GPU (8GB VRAM)，PyTorch 2.6.0+cu124，训练耗时约20分钟。",
                "（4）训练结果：mAP50=0.765, mAP50-95=0.446，classes: {0: 'fire', 1: 'smoke'}。",
                "（5）模型部署：训练完成后将best.pt复制为src/models/fire_model.pt（export_model.py），供YoloDetector加载使用。",
                "（6）训练脚本：training/train_fire.py（训练）、training/export_model.py（部署）、training/README.md（文档）。",
            ]
            insert_pos = gui_idx
            for line in reversed(training_lines):
                insert_paragraph_after(doc, insert_pos, line)
            changed = True

    if changed:
        doc.save(path)
        print(f"[OK] 设计文档.docx updated")
    else:
        print(f"[SKIP] 设计文档.docx no changes needed")


def update_test_doc():
    """更新测试文档.docx"""
    path = os.path.join(DOCS_DIR, "测试文档.docx")
    doc = Document(path)
    changed = False

    # 1. 更新测试目标
    for p in doc.paragraphs:
        if p.text.startswith("1. 功能正确性：验证实时视频流获取"):
            p.text = (
                "1. 功能正确性：验证实时视频流获取、火焰/烟雾检测、陌生人识别与报警、报警防抖合并、历史记录存储五大核心功能均能正确运行。"
            )
            changed = True
            break

    # 2. 更新人员样本
    for p in doc.paragraphs:
        if p.text.startswith("人员样本：测试人员在摄像头前走动"):
            p.text = (
                "人员样本：测试人员在摄像头前走动，用于人员检测测试。家庭成员照片放置于src/models/family_faces/，用于陌生人识别测试。"
            )
            changed = True
            break

    # 3. 更新YD-06
    for p in doc.paragraphs:
        if p.text.startswith("YD-06 误报抑制fog："):
            p.text = (
                "YD-06 误报抑制：非火焰物体（深色物体、蓝色纺织品），预期has_fire=False（自训练模型已过滤fog类别），优先级中。"
            )
            changed = True
            break

    # 4. 在YD-07后添加模型训练测试
    yd07_idx = find_paragraph_index(doc, "YD-07 置信度阈值")
    if yd07_idx is not None:
        has_yd08 = any("YD-08" in p.text for p in doc.paragraphs)
        if not has_yd08:
            training_test_lines = [
                "YD-08 自训练模型加载：启动系统，预期fire_model加载成功，classes={0: 'fire', 1: 'smoke'}，优先级高。",
                "YD-09 模型类别索引：对含火焰图像调用detect_fire()，预期检测框标注为'fire'（class 0），非'fog'或'sol'，优先级高。",
            ]
            for line in reversed(training_test_lines):
                insert_paragraph_after(doc, yd07_idx, line)
            changed = True

    # 5. 在UI-11后添加陌生人识别测试模块
    ui11_idx = find_paragraph_index(doc, "UI-11 摄像头断连恢复")
    if ui11_idx is not None:
        has_fr_test = any("FR-01" in p.text for p in doc.paragraphs)
        if not has_fr_test:
            fr_test_lines = [
                "模块三B：陌生人识别模块（FaceRecognizer）",
                "FR-01 陌生人检测：非家庭成员出现在摄像头前，预期is_stranger()返回True，触发person报警，优先级高。",
                "FR-02 家庭成员识别：家庭成员出现在摄像头前（照片已注册），预期is_stranger()返回False，不触发person报警，优先级高。",
                "FR-03 无人脸画面：空房间或背对摄像头，预期is_stranger()返回True（保守策略：有人但看不到脸=可疑），优先级中。",
                "FR-04 空家庭成员库：family_faces/目录为空时，预期所有检测到的人员均视为陌生人，优先级中。",
                "FR-05 人脸编码缓存：首次运行生成.npy缓存文件，后续启动直接加载缓存，优先级低。",
            ]
            for line in reversed(fr_test_lines):
                insert_paragraph_after(doc, ui11_idx, line)
            changed = True

    # 6. 更新IL-02
    for p in doc.paragraphs:
        if p.text.startswith("IL-02 人员报警全链路："):
            p.text = (
                "IL-02 陌生人报警全链路：夜间时段非家庭成员出现在摄像头前，预期检测到person -> FaceRecognizer判定为陌生人 -> AlarmManager判定通过 -> 截图保存 -> 数据库写入 -> GUI状态更新，优先级高。"
            )
            changed = True
            break

    # 7. 在IL-04后添加IL-05
    il04_idx = find_paragraph_index(doc, "IL-04 双检测共存")
    if il04_idx is not None:
        has_il05 = any("IL-05" in p.text for p in doc.paragraphs)
        if not has_il05:
            il05_lines = [
                "IL-05 家庭成员不报警：夜间时段家庭成员出现在摄像头前，预期检测到person -> FaceRecognizer判定为家人 -> 不触发报警 -> 不写库，优先级高。",
            ]
            for line in reversed(il05_lines):
                insert_paragraph_after(doc, il04_idx, line)
            changed = True

    # 8. 更新测试脚本描述
    for p in doc.paragraphs:
        if p.text.startswith("测试脚本：tests/test_db.py（13个用例）"):
            p.text = (
                "测试脚本：tests/test_db.py（13个用例）、tests/test_alarm.py（7个用例）、tests/test_gui.py（3个用例，含FaceRecognizer集成验证）、tests/test_performance.py（4个用例）。"
            )
            changed = True
            break

    # 9. 更新结论
    for p in doc.paragraphs:
        if p.text.startswith("人员检测：功能可用"):
            p.text = (
                "陌生人识别：人员检测+FaceRecognizer人脸比对，家庭成员不报警，陌生人触发报警，功能可用。"
            )
            changed = True
            break

    for p in doc.paragraphs:
        if p.text.startswith("火焰/烟雾检测：功能可用"):
            p.text = (
                "火焰/烟雾检测：自训练模型（mAP50=0.765），功能可用，置信度0.8下误报率低，仅检测fire和smoke类别（classes: 0=fire, 1=smoke）。"
            )
            changed = True
            break

    # 10. 更新已知限制
    for p in doc.paragraphs:
        if p.text.startswith("1. 火焰检测模型fire_model.pt为第三方"):
            p.text = (
                "1. 火焰检测模型fire_model.pt为自训练模型（基于DFire数据集迁移学习），对极端场景（强反光、远距离小火焰）检测能力有限，mAP50=0.765。"
            )
            changed = True
            break

    for p in doc.paragraphs:
        if p.text.startswith("2. 人员检测仅限person类别"):
            p.text = (
                "2. 陌生人识别依赖OpenCV LBPH算法，对光照变化、大角度侧脸的识别准确率有限，需正面光照良好的条件。"
            )
            changed = True
            break

    # 11. 更新异常测试
    for p in doc.paragraphs:
        if p.text.startswith("EX-08 模型文件缺失：删除fire_model.pt"):
            p.text = (
                "EX-08 模型文件缺失：删除fire_model.pt后启动，预期YoloDetector加载失败并提示错误，不崩溃，PASS。"
            )
            changed = True
            break

    # 12. 更新回归测试文件列表
    for p in doc.paragraphs:
        if p.text.startswith("测试文件：test_db.py、test_alarm.py"):
            p.text = (
                "测试文件：test_db.py、test_alarm.py、test_gui.py（含FaceRecognizer验证）、test_performance.py。"
            )
            changed = True
            break

    if changed:
        doc.save(path)
        print(f"[OK] 测试文档.docx updated")
    else:
        print(f"[SKIP] 测试文档.docx no changes needed")


def update_report_doc():
    """更新课程设计报告书.docx"""
    path = os.path.join(DOCS_DIR, "课程设计报告书.docx")
    doc = Document(path)
    changed = False

    # 1. 更新项目特色 - 双模型协同
    for p in doc.paragraphs:
        if p.text.startswith("2. 双模型协同：人员检测（YOLOv8n）与火焰/烟雾检测（专用fire模型）"):
            p.text = (
                "2. 双模型协同+自训练：人员检测（YOLOv8n COCO预训练）与火焰/烟雾检测（自训练模型，基于YOLOv8n迁移学习，DFire数据集，mAP50=0.765）并行运行，覆盖家庭最常见的两类安全隐患。"
            )
            changed = True
            break

    # 2. 添加陌生人识别特色
    dual_model_idx = find_paragraph_index(doc, "2. 双模型协同+自训练")
    if dual_model_idx is not None:
        has_stranger_feature = any(
            "陌生人智能识别" in p.text for p in doc.paragraphs
        )
        if not has_stranger_feature:
            stranger_text = (
                "3. 陌生人智能识别：集成FaceRecognizer人脸识别模块（OpenCV LBPH算法），"
                "布防时段检测到人员后自动比对家庭成员人脸库，仅陌生人才触发报警，家庭成员免打扰。"
            )
            insert_paragraph_after(doc, dual_model_idx, stranger_text)
            changed = True

    # 3. 更新产品范围
    for p in doc.paragraphs:
        if p.text.startswith("包含：实时视频流获取与显示"):
            p.text = (
                "包含：实时视频流获取与显示；全天候火焰/烟雾AI检测与报警（自训练模型）；特定时段陌生人闯入AI检测与报警（FaceRecognizer人脸识别）；报警防抖去重机制；报警截图自动保存；报警历史记录存储、查询、删除；GUI图形界面+CLI命令行；配置文件管理；模型训练脚本。"
            )
            changed = True
            break

    for p in doc.paragraphs:
        if p.text.startswith("不包含：云存储与远程推送"):
            p.text = (
                "不包含：云存储与远程推送（后续扩展）；多摄像头同时接入；移动端APP。"
            )
            changed = True
            break

    # 4. 更新功能点3
    for p in doc.paragraphs:
        if p.text.startswith("功能点3：特定时段入侵检测"):
            p.text = (
                "功能点3：特定时段陌生人入侵检测。系统仅在预设时段（如23:00至06:00）开启人员检测，若发现人员闯入，通过FaceRecognizer与家庭成员人脸库比对，仅陌生人才触发入侵告警。"
            )
            changed = True
            break

    # 5. 更新模型精度约束
    for p in doc.paragraphs:
        if p.text.startswith("4. 模型精度约束：火焰检测模型为第三方"):
            p.text = (
                "4. 模型精度约束：火焰检测模型为自训练模型（mAP50=0.765），对极端场景（强反光、远距离小火焰）的检测能力有限；陌生人识别依赖LBPH算法，对光照变化和大角度侧脸的识别准确率有限。"
            )
            changed = True
            break

    # 6. 更新风险2
    for p in doc.paragraphs:
        if p.text.startswith("风险2：火焰检测模型误报率偏高"):
            p.text = (
                "风险2：火焰检测模型误报。缓解措施：自训练模型已通过DFire数据集迁移学习优化（mAP50=0.765），置信度阈值设为0.8，仅检测fire和smoke类别。"
            )
            changed = True
            break

    # 7. 添加风险5
    risk4_idx = find_paragraph_index(doc, "风险4：用户修改配置文件")
    if risk4_idx is not None:
        has_risk5 = any("风险5" in p.text for p in doc.paragraphs)
        if not has_risk5:
            risk5_text = (
                "风险5：陌生人识别误判（家庭成员被误认为陌生人或反之）。缓解措施：调整LBPH容差阈值（recognition.tolerance）；确保家庭成员注册照片正面光照良好；后续可升级为深度学习人脸嵌入模型。"
            )
            insert_paragraph_after(doc, risk4_idx, risk5_text)
            changed = True

    # 8. 更新可维护性需求
    for p in doc.paragraphs:
        if p.text.startswith("1. 代码遵循模块化设计，每个.py文件职责单一"):
            p.text = (
                "1. 代码遵循模块化设计，每个.py文件职责单一（如alarm_manager.py负责防抖，db_manager.py负责数据库，yolo_detector.py负责AI推理，face_recognizer.py负责陌生人识别）。"
            )
            changed = True
            break

    # 9. 添加模型训练进度
    week4_idx = find_paragraph_index(doc, "第4周：系统测试")
    if week4_idx is not None:
        has_training_chapter = any(
            "模型训练" in p.text and p.text.startswith("第")
            for p in doc.paragraphs
        )
        if not has_training_chapter:
            training_line = (
                "第2.5周（模型训练）：收集DFire数据集（21,000+张火焰/烟雾图像），基于YOLOv8n进行迁移学习训练（50 epochs），达到mAP50=0.765，部署为fire_model.pt。同时开发FaceRecognizer陌生人识别模块。"
            )
            insert_paragraph_after(doc, week4_idx, training_line)
            changed = True

    # 10. 更新项目背景
    for p in doc.paragraphs:
        if "旨在打造一套低成本、高效率" in p.text:
            p.text = (
                "\t\t随着现代家庭安全意识的提升，家庭火灾隐患及非法入侵等安全事故频发。传统安防设备往往只能事后查看录像，缺乏主动预警能力。本项目结合深度学习（YOLO算法）与计算机视觉技术，通过自训练火焰检测模型和陌生人识别算法，旨在打造一套低成本、高效率的家庭安防监控系统，实现7×24小时主动预警与智能识别。"
            )
            changed = True
            break

    if changed:
        doc.save(path)
        print(f"[OK] 课程设计报告书.docx updated")
    else:
        print(f"[SKIP] 课程设计报告书.docx no changes needed")


if __name__ == "__main__":
    update_design_doc()
    update_test_doc()
    update_report_doc()
    print("\nAll docs updated.")
