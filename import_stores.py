import sqlite3
import csv

# DB 연결 및 커서 생성
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# 테이블 생성 (없으면 생성)
cursor.execute('''
CREATE TABLE IF NOT EXISTS stores (
    name TEXT NOT NULL,
    deadline_days INTEGER,
    deadline_time TEXT,
    keywords TEXT,
    always_open INTEGER,
    fixed_note TEXT,
    memo TEXT
)
''')

# CSV 파일 읽기 및 DB에 삽입
with open('stores.csv', newline='', encoding='utf-8-sig') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        name = row.get('name', '').strip()
        print(f"▶ name_raw: '{row.get('name')}' → name: '{name}'")  # 디버깅용 출력 추가
        keywords = row.get('keywords', '').strip()
        always_open_raw = row.get('always_open', '').strip().lower()
        fixed_note = row.get('fixed_note', '').strip()
        memo = row.get('memo', '').strip()

        if always_open_raw == 'true':
            always_open = 1
            deadline_days = None
            deadline_time = None
        else:
            always_open = 0
            deadline_days = row.get('deadline_days', '').strip()
            deadline_days = int(deadline_days) if deadline_days else None
            deadline_time = row.get('deadline_time', '').strip()

        cursor.execute('''
            INSERT INTO stores (name, deadline_days, deadline_time, keywords, always_open, fixed_note, memo)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name, deadline_days, deadline_time, keywords, always_open, fixed_note, memo))

# 저장 및 종료
conn.commit()
conn.close()

print("✅ stores.csv → 예약시간 입력 완료")
