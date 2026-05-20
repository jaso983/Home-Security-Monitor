# Home Security Monitor

基于 YOLO 深度学习与计算机视觉的 AI 家庭安防监控系统。支持 24 小时火焰/烟雾检测与夜间人员闯入检测，自动截图存证，配备简洁 GUI 图形界面。

## 功能

- **火情检测** — 全天候实时识别火焰与烟雾，发现即报警
- **入侵检测** — 预设时段（默认 23:00-06:00）检测人员闯入
- **智能防抖** — 同类事件 10 秒内合并去重，避免重复骚扰
- **自动存证** — 报警瞬间截图保存，记录写入本地数据库
- **历史管理** — 浏览、查看、删除历史报警记录
- **双模式** — GUI 图形界面（家庭用户）/ CLI 命令行（开发者调试）

## 快速开始

### 环境要求

- Windows 10/11，Python 3.9+
- 摄像头（USB 或笔记本内置）
- 4 核 CPU，8 GB 内存

### 安装

```bash
git clone https://github.com/jaso983/Home-Security-Monitor.git
cd Home-Security-Monitor
pip install ultralytics torch opencv-python Pillow
```

首次运行时会自动下载 YOLOv8n 模型（约 6 MB）。火焰检测模型需手动放入 `src/models/fire_model.pt`。

### 启动

```bash
# GUI 模式（推荐）
python main_gui.py

# 或双击
run.bat

# CLI 模式（调试用）
python src/main.py
```

按 `Esc` 或点击 Exit 退出。

## 项目结构

```
.
├── main_gui.py              # GUI 入口
├── run.bat                  # Windows 一键启动
├── src/
│   ├── main.py              # CLI 入口
│   ├── gui/                 # GUI 模块
│   │   ├── app.py           #   主控制器 + 检测循环
│   │   ├── video_panel.py   #   实时视频面板
│   │   ├── status_panel.py  #   状态指示栏
│   │   ├── history_panel.py #   报警历史列表
│   │   └── utils.py         #   帧转换工具
│   ├── core/                # 核心业务
│   │   ├── alarm_manager.py #   报警防抖去重
│   │   └── db_manager.py    #   SQLite 管理
│   └── models/              # AI 模型
│       └── yolo_detector.py #   YOLO 检测器封装
├── tests/
│   └── test_db.py           # 数据库单元测试
└── docs/
    ├── 报告文档.md           # 课程设计报告
    ├── 设计文档.md           # 架构设计（含类图、流程图）
    └── 测试文档.md           # 测试用例与结果
```

## 技术栈

| 层 | 技术 |
|----|------|
| AI 推理 | YOLOv8n + 火焰检测模型 |
| GUI | tkinter (ttk + clam 主题) |
| 数据库 | SQLite3 |
| 图像处理 | OpenCV + Pillow |
| 语言 | Python 3.11 |

## 架构概览

```
摄像头 ──► YoloDetector ──► AlarmManager ──► DatabaseManager ──► alarms.db
                │                  │                 │
                ▼                  ▼                 ▼
           VideoPanel        StatusPanel       HistoryPanel
                │                  │                 │
                └──────────────────┴─────────────────┘
                                   │
                              GUI (tkinter)
```

## 文档

- [课程设计报告](docs/报告文档.md)
- [架构设计文档](docs/设计文档.md)
- [测试文档](docs/测试文档.md)

## 许可证

本项目为软件工程课程设计项目。
