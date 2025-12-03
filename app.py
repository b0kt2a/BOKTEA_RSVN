import sqlite3
import re
from flask import Flask, render_template, request, g, abort
from datetime import datetime, timedelta

app = Flask(__name__)
DATABASE = "database.db"


# --------------------------
# DB 연결
# --------------------------
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db:
        db.close()




# --------------------------
# 시간 계산
# --------------------------
def fix_time_format(t):
    t = t.strip()
    if len(t) == 4 and t.isdigit():
        return t[:2] + ':' + t[2:]
    return t

def calculate_end_time(start_time, play_time):
    try:
        start = fix_time_format(start_time)
        start_dt = datetime.strptime(start, "%H:%M")
        end_dt = start_dt + timedelta(minutes=int(play_time))
        return end_dt.strftime("%H:%M")
    except:
        return ""

def format_schedule(raw, play_time):
    if not raw:
        return "-"
    schedule = raw.split(",")
    lines = []
    for time in schedule:
        start = fix_time_format(time.strip())
        end = calculate_end_time(start, play_time)
        lines.append(f"{start} ~ {end}")
    return "\n".join(lines)


# --------------------------
# 메인 페이지
# --------------------------
@app.route('/', methods=['GET', 'POST'])
def index():
    db = get_db()
    reservation_results = []
    theme_results = []
    selected_date = ""
    selected_store = ""

    if request.method == 'POST':
        selected_date = request.form['date']
        selected_store = request.form['store'].strip()

        # ✔ 매장 검색은 keywords ONLY
        stores = db.execute('''
            SELECT *
            FROM stores
            WHERE keywords LIKE ?
        ''', (f"%{selected_store}%",)).fetchall()

        # -----------------------------------------------------------------
        # 🔥 매장 자체가 한 개도 없으면 → 바로 에러 반환
        # -----------------------------------------------------------------
        if not stores:
            return render_template(
                "index.html",
                selected_date=selected_date,
                selected_store=selected_store,
                results=[],
                error="해당 매장/테마를 찾을 수 없어요ㅠ<br>복티에게 요청주시면 빠른시일내에 업뎃할게요🤗"
            )

        # -----------------------------------------------------------------
        # 🔥 매장 있을 때 → 예약일 계산
        # -----------------------------------------------------------------
        for store in stores:

            # --- 마감일 계산 ---
            if store['always_open'] and int(store['always_open']) == 1:
                deadline = store['fixed_note'] or "상시 예약 가능"

            elif store['deadline_days'] is not None and store['deadline_time']:
                d = datetime.strptime(selected_date, '%Y-%m-%d')
                deadline_date = d - timedelta(days=int(store['deadline_days']))
                deadline = deadline_date.strftime('%Y년 %m월 %d일 ') + store['deadline_time']

            else:
                deadline = store['fixed_note'] or "정보 없음"

           

            # ✔ store_name 부분 일치로 테마 찾기
            theme_match = db.execute('''
                SELECT id, theme_name
                FROM themes
                WHERE store_name LIKE ?
                  AND (keywords LIKE ? OR theme_name LIKE ?)
                ORDER BY id LIMIT 1
            ''', (f"%{store['name']}%", f"%{selected_store}%", f"%{selected_store}%")).fetchone()

            theme_id = theme_match['id'] if theme_match else None
            theme_name = theme_match['theme_name'] if theme_match else None

            reservation_results.append({
                'name': store['name'],
                'deadline': deadline,
                
                'theme_id': theme_id,
                'theme_name': theme_name,
                'memo': store['memo']
            })

        # -----------------------------------------------------------------
        # 🔽 하단 테마 검색 (선택사항)
        # -----------------------------------------------------------------
        theme_results = db.execute('''
            SELECT *
            FROM themes
            WHERE keywords LIKE ? OR theme_name LIKE ?
        ''', (f"%{selected_store}%", f"%{selected_store}%")).fetchall()

    return render_template(
        "index.html",
        results=reservation_results,
        theme_results=theme_results,
        selected_store=selected_store,
        selected_date=selected_date
    )


# --------------------------
# 테마 상세 시간표
# --------------------------
@app.route("/theme/<int:theme_id>")
def theme_detail(theme_id):
    db = get_db()

    theme = db.execute("SELECT * FROM themes WHERE id = ?", (theme_id,)).fetchone()
    if not theme:
        abort(404)

    schedule_weekday = format_schedule(theme['time_table_weekday'], theme['play_time'])
    schedule_weekend = format_schedule(theme['time_table_weekend'], theme['play_time'])

    return render_template("theme_detail.html",
                           theme=theme,
                           schedule_weekday=schedule_weekday,
                           schedule_weekend=schedule_weekend)


# --------------------------
# 실행
# --------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
