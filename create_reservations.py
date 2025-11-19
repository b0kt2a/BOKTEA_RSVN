import sqlite3

conn = sqlite3.connect('database.db')
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

# 예시 데이터 삽입
cursor.execute("INSERT INTO stores (store_name, theme_name, deadline_days, deadline_time) VALUES (?, ?, ?, ?)",
               ("키이스케이프", "메모리컴퍼니점", "에디", "필름바이에디" "eddy" 6, "오전 10:30"))
cursor.execute("INSERT INTO stores (store_name, theme_name, deadline_days, deadline_time) VALUES (?, ?, ?, ?)",
               ("방탈출 아파트", "숨은범인", 3, "오후 2:00"))

conn.commit()
conn.close()

print("✅ 매장 데이터가 추가되었습니다.")
