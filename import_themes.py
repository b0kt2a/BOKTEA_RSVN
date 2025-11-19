import csv
import sqlite3

DB_FILE = 'database.db'
CSV_FILE = 'themes.csv'

def create_table():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # 기존 테이블 삭제하고 새로 생성 (price TEXT 설정 보장)
    c.execute('DROP TABLE IF EXISTS themes')  # ← 수정: 테이블 초기화
    c.execute('''
        CREATE TABLE IF NOT EXISTS themes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id TEXT,
            store_name TEXT,
            theme_id TEXT,
            theme_name TEXT,
            keywords TEXT,
            play_time INTEGER,
            price TEXT,
            time_table_weekday TEXT,
            time_table_weekend TEXT
        )
    ''')
    conn.commit()
    conn.close()

def import_csv():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    with open(CSV_FILE, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # 필수 필드 누락된 줄은 건너뜀
            if not row['store_id'] or not row['theme_id']:
                print(f"⚠️ [▲ 스킵] 유효하지 않은 row: {row}")
                continue

            try:
                c.execute('''
                    INSERT INTO themes (
                        store_id, store_name, theme_id, theme_name, keywords,
                        play_time, price, time_table_weekday, time_table_weekend
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row['store_id'].strip(),
                    row['store_name'].strip(),
                    row['theme_id'].strip(),
                    row['theme_name'].strip(),
                    row['keywords'].strip(),
                    int(row['play_time'].strip()) if row['play_time'].strip().isdigit() else 0,
                    row['price'].strip(),
                    row['time_table_weekday'].strip(),
                    row['time_table_weekend'].strip()
                ))
            except Exception as e:
                print(f"❌ 오류 발생한 행: {row}")
                print("에러 메시지:", e)

    conn.commit()
    conn.close()
    print("✅ themes 테이블에 데이터 입력 완료 (price=문자열모드)")

if __name__ == '__main__':
    create_table()
    import_csv()
