
import sqlite3

from utils import get_chosung  # 위 함수가 있으면 import
# 없으면 여기다 그대로 붙여도 됨

conn = sqlite3.connect("database.db")
cur = conn.cursor()

# 1) 컬럼 추가 (이미 있으면 무시)
try:
    cur.execute("ALTER TABLE themes ADD COLUMN theme_chosung TEXT")
except:
    pass

# 2) 기존 데이터 채우기
rows = cur.execute("SELECT id, theme_name FROM themes").fetchall()
for _id, name in rows:
    cur.execute(
        "UPDATE themes SET theme_chosung = ? WHERE id = ?",
        (get_chosung(name), _id)
    )

conn.commit()
conn.close()
print("초성 컬럼 생성 완료")