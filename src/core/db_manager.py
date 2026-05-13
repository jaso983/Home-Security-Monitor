class DatabaseManager:
    def __init__(self):
        print("数据库连接初始化...")
        # 以后同学D在这里建 SQLite 表
        
    def insert_alarm(self, event_type, image_path):
        print(f"--> [数据库] 成功记录一条报警: {event_type}, 截图保存在: {image_path}")