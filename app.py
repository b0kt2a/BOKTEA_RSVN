import sqlite3
import re
import os
from flask import Flask, render_template, request, g, abort
from datetime import datetime, timedelta

app = Flask(__name__)
DATABASE = "database.db"

POSTER_DIR = os.path.join(app.root_path, "static", "posters")

def normalize_query(s: str) -> str:
    if not s:
        return ""
    s = s.strip()
    # 공백 제거
    s = re.sub(r"\s+", "", s)
    # 특수문자 제거(원하면 빼도 됨)
    s = re.sub(r"[^0-9a-zA-Z가-힣]", "", s)
    return s


def get_poster_filename(theme_id):
    """
    static/posters 폴더에서 theme_id.xxx 파일 자동 탐색
    jpg / png / gif / jpeg / webp 지원
    """
    extensions = ["jpg", "png", "gif", "jpeg", "webp"]

    for ext in extensions:
        filename = f"{theme_id}.{ext}"
        full_path = os.path.join(POSTER_DIR, filename)
        if os.path.exists(full_path):
            return filename

    return None

def parse_closed_days(raw):
    if not raw:
        return []
    s = str(raw).strip()
    if not s:
        return []
    parts = [p.strip() for p in s.split(",") if p.strip()]

    order = {"월":0, "화":1, "수":2, "목":3, "금":4, "토":5, "일":6}
    parts = sorted(set(parts), key=lambda x: order.get(x, 99))
    return parts

def get_week_labels(weekend_start):
    try:
        ws = int(weekend_start)
    except (TypeError, ValueError):
        ws = 6  # 기본값: 토~일 주말

    if ws == 5:
        return "월~목", "금~일"
    elif ws == 6:
        return "월~금", "토~일"
    else:
        return "월~금", "토~일"

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
# 요일 라벨 계산
# --------------------------
def get_week_labels(weekend_start):
    try:
        weekend_start = int(weekend_start)
    except:
        weekend_start = 6  # 기본: 토~일

    if weekend_start == 5:
        return "월~목", "금~일"
    return "월~금", "토~일"

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
        raw_query = selected_store
        q = normalize_query(raw_query)


        # ✔ 매장 검색은 keywords ONLY
        stores = db.execute(
            '''
            SELECT *
            FROM stores
            WHERE REPLACE(keywords, ' ', '') LIKE ?
            ''',
            (f"%{q}%",)
        ).fetchall()


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
                  deadline = store['fixed_note'] or "상시 예약 가능"
                  deadline_sub = "예약가능일 30일초과 매장은 상시예약가능으로 분류됩니다."

           

            # ✔ store_name 부분 일치로 테마 찾기
            theme_matches = db.execute('''
                SELECT id, theme_name
                FROM themes
                WHERE store_name LIKE ?
                AND (
                    REPLACE(keywords, ' ', '') LIKE ?
                    OR REPLACE(theme_name, ' ', '') LIKE ?
                )
                ORDER BY id
            ''', (f"%{store['name']}%", f"%{q}%", f"%{q}%")).fetchall()

            first = theme_matches[0] if theme_matches else None

            reservation_results.append({
                'name': store['name'],
                'deadline': deadline,
                'theme_id': first['id'] if first else None,
                'theme_name': first['theme_name'] if first else None,
                'themes': theme_matches,  # ✅ 추가 (여러개)
                'memo': store['memo']
            })
        # -----------------------------------------------------------------
        # 🔽 하단 테마 검색 (선택사항)
        # -----------------------------------------------------------------
        theme_results = db.execute('''
            SELECT *
            FROM themes
            WHERE REPLACE(keywords, ' ', '') LIKE ?
            OR REPLACE(theme_name, ' ', '') LIKE ?
        ''', (f"%{q}%", f"%{q}%")).fetchall()

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

    # Row → dict
    theme = dict(theme)

    price_raw = (theme.get("price") or "").strip()

    price_display = price_raw

    if " (" in price_raw:
        price_display = price_raw.replace(
            " (",
            '<br><span class="price-sub">('
        ) + '</span>'

    theme["price_display"] = price_display

    # 기본 라벨 (weekend_start 기준)
    weekday_label, weekend_label = get_week_labels(theme.get("weekend_start"))

    closed_days = parse_closed_days(theme.get("closed_days"))

    # 🔥 금요일 시간표가 따로 있으면 라벨 자동 조정
    if theme.get("time_table_friday") and str(theme.get("time_table_friday")).strip():
        weekday_label = "월~목"
    
    
    # ✅ 포스터 파일에 쓸 key 결정
    #   themes 테이블에 theme_id 컬럼이 있으면 그걸 우선 사용,
    #   없으면 id 컬럼 사용
    poster_key = theme.get("theme_id", theme_id)

    # ✅ 포스터 파일 자동 탐색
    theme["poster_file"] = get_poster_filename(poster_key)

    schedule_weekday = format_schedule(theme.get('time_table_weekday'), theme['play_time'])
    schedule_friday  = format_schedule(theme.get('time_table_friday'), theme['play_time'])
    schedule_weekend = format_schedule(theme.get('time_table_weekend'), theme['play_time'])

    return render_template(
        "theme_detail.html",
        theme=theme,
        schedule_weekday=schedule_weekday,
        schedule_friday=schedule_friday,
        schedule_weekend=schedule_weekend,
        weekday_label=weekday_label,
        weekend_label=weekend_label,
        closed_days=closed_days
    )


# --------------------------
# 실행
# --------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
