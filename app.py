import sqlite3
import csv
import re
from flask import Flask, render_template, request, g, abort
from datetime import datetime, timedelta

app = Flask(__name__)
DATABASE = "database.db"

# DB 연결
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

# DB 연결 종료
@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db:
        db.close()

# 시간 문자열 포맷 변환 함수
def format_time_string(time_str):
    if not time_str:
        return ""
    times = time_str.split(';')
    formatted = []
    for t in times:
        t = t.strip()
        if t and len(t) == 4 and t.isdigit():
            formatted.append(f"{t[:2]}:{t[2:]}")
        elif ':' in t:
            formatted.append(t)
    return ';'.join(formatted)

# 테마 CSV → DB import 함수
def import_csv():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    with open('themes.csv', newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile, quotechar='"')
        for row in reader:
            row['time_table_weekday'] = format_time_string(row['time_table_weekday'])
            row['time_table_weekend'] = format_time_string(row['time_table_weekend'])

            try:
                c.execute('''
                    INSERT INTO themes (
                        store_id, store_name, theme_id, theme_name, keywords,
                        play_time, price, time_table_weekday, time_table_weekend
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row['store_id'],
                    row['store_name'],
                    row['theme_id'],
                    row['theme_name'],
                    row['keywords'],
                    int(row['play_time']),
                    row['price'],
                    row['time_table_weekday'],
                    row['time_table_weekend']
                ))
            except Exception as e:
                print(f"[⚠️ 오류] 유효하지 않은 row: {row}")
                print(f"[에러메시지] {e}")

    conn.commit()
    conn.close()
    print("✅ 테마정보 입력 완료")

# 메모에서 URL만 추출
def extract_url_from_memo(memo):
    if not memo:
        return None
    match = re.search(r"href=['\"](.*?)['\"]", memo)
    return match.group(1) if match else None

# 시간 보정 함수
def fix_time_format(t):
    t = t.strip()
    if len(t) == 4 and t.isdigit():
        return t[:2] + ':' + t[2:]
    return t

# 종료 시간 계산 함수
def calculate_end_time(start_time, play_time):
    try:
        start_time = fix_time_format(start_time)
        start_dt = datetime.strptime(start_time.strip(), "%H:%M")
        end_dt = start_dt + timedelta(minutes=int(play_time))
        return end_dt.strftime("%H:%M")
    except:
        return ""

@app.route('/', methods=['GET', 'POST'])
def index():
    db = get_db()
    reservation_results = []
    theme_results = []
    selected_date = ''
    selected_store = ''

    if request.method == 'POST':
        selected_date = request.form['date']
        selected_store = request.form['store'].strip()

        store_info = db.execute('''
            SELECT * FROM stores WHERE keywords LIKE ?
        ''', (f"%{selected_store}%",)).fetchall()

        for store in store_info:
            if store['always_open'] and int(store['always_open']) == 1:
                deadline = store['fixed_note'] or "상시 예약 가능"
            elif store['deadline_days'] is not None and store['deadline_time']:
                d = datetime.strptime(selected_date, '%Y-%m-%d')
                deadline_date = d - timedelta(days=int(store['deadline_days']))
                deadline = deadline_date.strftime('%Y년 %m월 %d일 ') + store['deadline_time']
            else:
                deadline = store['fixed_note'] or "정보 없음"

            memo_link = extract_url_from_memo(store['memo']) if store['memo'] else None

            theme_match = db.execute('''
                SELECT id, theme_name FROM themes
                WHERE keywords LIKE ?
                ORDER BY id LIMIT 1
            ''', (f"%{selected_store}%",)).fetchone()

            theme_id = theme_match['id'] if theme_match else None
            theme_name = theme_match['theme_name'] if theme_match else None

            reservation_results.append({
                'name': store['name'],
                'deadline': deadline,
                'memo_link': memo_link,
                'theme_id': theme_id,
                'theme_name': theme_name
            })

        # ✅ 조건 추가: theme_name 또는 keywords에 검색어가 포함된 테마만 추출
        theme_results = db.execute('''
            SELECT * FROM themes
            WHERE keywords LIKE ? OR theme_name LIKE ?
            ORDER BY theme_name
        ''', (f"%{selected_store}%", f"%{selected_store}%")).fetchall()

    return render_template("index.html",
                           results=reservation_results,
                           reservation_results=reservation_results,
                           theme_results=theme_results,
                           selected_store=selected_store,
                           selected_date=selected_date)

@app.route('/theme/<int:theme_id>/<int:store_id>')
def theme_detail(theme_id, store_id):
    db = get_db()
    theme = db.execute("SELECT * FROM themes WHERE id = ?", (theme_id,)).fetchone()
    if not theme:
        abort(404)

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

    schedule_weekday = format_schedule(theme['time_table_weekday'], theme['play_time'])
    schedule_weekend = format_schedule(theme['time_table_weekend'], theme['play_time'])

    return render_template("theme_detail.html", theme=theme,
                           schedule_weekday=schedule_weekday,
                           schedule_weekend=schedule_weekend)

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)