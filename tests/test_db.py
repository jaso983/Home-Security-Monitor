import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from core.db_manager import DatabaseManager


def test_db():
    # 使用临时文件，不污染正式数据库
    tmp_db = os.path.join(tempfile.gettempdir(), "test_alarms.db")
    db = DatabaseManager(db_path=tmp_db)
    print(f"测试数据库路径: {tmp_db}")

    # 1. 验证表结构存在
    cursor = db.conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='alarms'")
    assert cursor.fetchone() is not None, "FAIL: alarms 表未创建"
    print("[PASS] 建表成功")

    # 2. 插入测试数据
    id1 = db.insert_alarm("fire", "screenshots/fire_test.jpg")
    id2 = db.insert_alarm("person", "screenshots/person_test.jpg")
    id3 = db.insert_alarm("fire", "screenshots/fire_test2.jpg")
    assert id1 == 1 and id2 == 2 and id3 == 3, "FAIL: 自增ID异常"
    print(f"[PASS] 插入3条记录 (ID: {id1}, {id2}, {id3})")

    # 3. 查询全部记录
    all_alarms = db.get_recent_alarms()
    assert len(all_alarms) == 3, f"FAIL: 期望3条，实际{len(all_alarms)}条"
    print("[PASS] 查询全部记录通过")

    # 4. 按类型筛选
    fire_alarms = db.get_alarms_by_type("fire")
    person_alarms = db.get_alarms_by_type("person")
    assert len(fire_alarms) == 2, f"FAIL: fire期望2条，实际{len(fire_alarms)}条"
    assert len(person_alarms) == 1, f"FAIL: person期望1条，实际{len(person_alarms)}条"
    print("[PASS] 按类型筛选通过")

    # 5. 验证字段内容
    for alarm in all_alarms:
        row_id, event_type, timestamp, image_path = alarm
        assert event_type in ("fire", "person"), f"FAIL: 未知类型 {event_type}"
        assert timestamp is not None
        assert image_path.startswith("screenshots/"), f"FAIL: 路径格式异常 {image_path}"
    print("[PASS] 字段内容验证通过")

    # 6. 验证 limit 参数
    limited = db.get_recent_alarms(limit=2)
    assert len(limited) == 2, f"FAIL: limit期望2条，实际{len(limited)}条"
    print("[PASS] limit参数验证通过")

    db.close()

    # 清理临时文件
    os.remove(tmp_db)
    print(f"\n全部测试通过！临时数据库已清理。")


if __name__ == "__main__":
    test_db()
