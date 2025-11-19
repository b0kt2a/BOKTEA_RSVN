import sqlite3

conn = sqlite3.connect('database.db')  # 파일 이름 확인
cursor = conn.cursor()

# 테이블 생성
cursor.execute('''
CREATE TABLE IF NOT EXISTS stores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_name TEXT NOT NULL,
    theme_name TEXT NOT NULL,
    deadline_days INTEGER NOT NULL,
    deadline_time TEXT NOT NULL
)
''')

conn.commit()
conn.close()
