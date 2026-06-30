# Home Security Monitor

基于 YOLO 深度学习与计算机视觉的 AI 家庭安防监控系统。支持 24 小时火焰/烟雾检测、夜间人员闯入检测、陌生人脸识别，自动截图存证，配备简洁 GUI 图形界面。

## 功能

- **火情检测** — 全天候实时识别火焰与烟雾（自训练 YOLO 火焰模型），发现即报警
- **入侵检测** — 预设时段（默认 00:00-23:59）检测人员闯入，陌生面孔触发报警
- **人脸识别** — 基于 ArcFace 的家庭成员/陌生人识别，白天夜间自适应策略
- **智能防抖** — 同类事件合并去重，火焰冷却 + 人员间隔双机制，避免重复骚扰
- **自动存证** — 报警瞬间截图保存（原始帧 + 标注帧），记录写入 SQLite 数据库
- **历史管理** — 浏览、查看详情、删除历史报警记录，支持事件筛选
- **双模式** — GUI 图形界面（家庭用户）/ CLI 命令行（开发者调试）

## 快速开始

### 环境要求

- Windows 10/11，Python 3.9+
- 摄像头（USB 或笔记本内置）
- 4 核 CPU，8 GB 内存（推荐 GPU 加速）

### 安装

```bash
git clone https://github.com/jaso983/Home-Security-Monitor.git
cd Home-Security-Monitor
pip install ultralytics torch opencv-python Pillow numpy onnxruntime
```

模型文件已包含在仓库中（`yolov8n.pt` 约 6 MB，`fire_model.pt` 约 6 MB），无需额外下载。

### 启动

```bash
# GUI 模式（推荐）
python -m src.gui

# 或双击
run.bat

# CLI 模式（调试用）
python src/main.py
```

按 `Esc` 或点击 Exit 退出。

## 项目结构

```
.
├── main_gui.py                 # GUI 入口（兼容旧版）
├── run.bat                     # Windows 一键启动
├── config.yaml                 # 全局配置文件
├── src/
│   ├── main.py                 # CLI 入口
│   ├── gui/                    # GUI 模块
│   │   ├── __main__.py         #   GUI 启动入口
│   │   ├── app.py              #   主控制器 + 检测循环
│   │   ├── video_panel.py      #   实时视频面板
│   │   ├── status_panel.py     #   状态指示栏
│   │   ├── history_panel.py    #   报警历史列表
│   │   ├── theme.py            #   界面主题样式
│   │   └── utils.py            #   帧转换工具
│   ├── core/                   # 核心业务
│   │   ├── alarm_manager.py    #   报警防抖去重 + 数据库管理
│   │   ├── config.py           #   配置加载
│   │   └── face_recognizer.py  #   ArcFace 人脸识别
│   └── models/                 # AI 模型
│       ├── yolo_detector.py    #   YOLO 检测器封装（人物+火焰）
│       ├── yolov8n.pt          #   YOLOv8n 人物检测模型
│       ├── fire_model.pt       #   自训练火焰检测模型
│       └── family_faces/       #   家庭成员照片库
├── tests/
│   ├── test_alarm.py           # 报警管理器测试
│   └── test_gui.py             # GUI 组件测试
├── training/                   # 模型训练脚本
│   ├── train_fire.py           #   火焰检测模型训练
│   ├── export_model.py         #   模型导出
│   └── validate_model.py       #   模型验证
├── scripts/
│   ├── rebuild_docx.py         #   文档构建
│   ├── capture_screenshots.py  #   截图采集
│   └── add_comparison.py       #   对比图生成
└── docs/
    ├── 报告文档.md              # 课程设计报告
    ├── 设计文档.md              # 架构设计（含类图、流程图）
    ├── 测试文档.md              # 测试用例与结果
    └── 系统实现说明.md          # 实现细节说明
```

## 技术栈

| 层 | 技术 |
|----|------|
| AI 推理 | YOLOv8n + 自训练火焰检测模型 + ArcFace 人脸识别 |
| GUI | tkinter (ttk + 自定义主题) |
| 数据库 | SQLite3 |
| 图像处理 | OpenCV + Pillow |
| 语言 | Python 3.11 |

## 架构概览

```
                    ┌─ 家庭成员 ──┐
                    │  人脸库    │
                    └──────┬─────┘
                           │
摄像头 ──► YoloDetector ──┼──► FaceRecognizer ──► AlarmManager ──► alarms.db
             │    │       │                        │
             │    │       └── 陌生人/无脸 ──────────┘
             │    ▼
             │  FireDetection ──► AlarmManager ──► alarms.db
             ▼
          VideoPanel     StatusPanel          HistoryPanel
             │                │                    │
             └────────────────┴────────────────────┘
                              │
                         GUI (tkinter)
```

## 配置说明

通过 `config.yaml` 可灵活调整：

- **检测时段** — 人员检测开始/结束时间
- **报警冷却** — 火焰报警间隔、人员报警间隔
- **置信度阈值** — 人员、火焰检测分别设置
- **人脸识别** — 家庭成员照片目录、识别阈值
- **连续确认帧数** — 火焰、烟雾、人员分别设置防抖参数

详细配置项见 [config.yaml](config.yaml)。

## 文档

- [课程设计报告](docs/报告文档.md)
- [架构设计文档](docs/设计文档.md)
- [测试文档](docs/测试文档.md)
- [系统实现说明](docs/系统实现说明.md)

## 许可证

本项目为软件工程课程设计项目。
