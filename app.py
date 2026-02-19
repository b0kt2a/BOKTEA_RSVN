import sqlite3
import re
import os
from flask import Flask, render_template, request, g, abort
from datetime import datetime, timedelta

app = Flask(__name__)
DATABASE = "database.db"

POSTER_DIR = os.path.join(app.root_path, "static", "posters")

TIME_RE = re.compile(r'(\d{1,2}:\d{2})')

def insert_newline_after_time(text):
    if not text:
        return text

    s = str(text)

    m = TIME_RE.search(s)
    if not m:
        return s

    # 시간 뒤에 내용이 더 있으면 줄바꿈, 아니면 그대로
    after = s[m.end():]
    if after.strip() == "":
        return s  # 시간으로 끝나면 줄바꿈 X

    return s[:m.end()] + "\n" + s[m.end():]

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

    order = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5, "일": 6}
    parts = sorted(set(parts), key=lambda x: order.get(x, 99))
    return parts


# --------------------------
# 요일 라벨 계산
# --------------------------
def get_week_labels(weekend_start):
    """weekend_start: 5면 금~일, 6이면 토~일(기본)"""
    try:
        ws = int(weekend_start)
    except (TypeError, ValueError):
        ws = 6

    if ws == 5:
        return "월~목", "금~일"
    return "월~금", "토~일"


# --------------------------
# DB 연결
# --------------------------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db:
        db.close()


# --------------------------
# 시간 계산
# --------------------------
def fix_time_format(t):
    t = t.strip()
    if len(t) == 4 and t.isdigit():
        return t[:2] + ":" + t[2:]
    return t


def calculate_end_time(start_time, play_time):
    try:
        start = fix_time_format(start_time)
        start_dt = datetime.strptime(start, "%H:%M")
        end_dt = start_dt + timedelta(minutes=int(play_time))
        return end_dt.strftime("%H:%M")
    except Exception:
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
@app.route("/", methods=["GET", "POST"])
def index():
    db = get_db()
    reservation_results = []
    theme_results = []
    selected_date = ""
    selected_store = ""

    # ✅ 어떤 요청(GET/HEAD 포함)에서도 안전하게 존재하도록 기본값 지정
    raw_query = ""
    q = ""

    # ✅ GET(또는 HEAD)로 처음 들어오면: 검색/DB쿼리 없이 화면만 렌더
    if request.method != "POST":
        return render_template(
            "index.html",
            results=[],
            theme_results=[],
            selected_store="",
            selected_date=""
        )

    # --------------------------
    # POST: 검색 실행
    # --------------------------
    selected_date = request.form.get("date", "")
    selected_store = (request.form.get("store") or "").strip()
    raw_query = selected_store
    q = normalize_query(raw_query)

    # ✅ 초성만/특수문자만 입력 등으로 q가 비면 검색 막기 (LIKE '%%' 방지)
    if raw_query and not q:
        return render_template(
            "index.html",
            selected_date=selected_date,
            selected_store=selected_store,
            results=[],
            theme_results=[],
            error="초성검색은 지원하지않아요😭<br>찾는 테마가 없다면 아래 요청하기로 남겨주세요🤗",
        )

    # ✔ 매장 검색은 keywords ONLY
    stores = db.execute(
        """
        SELECT *
        FROM stores
        WHERE REPLACE(keywords, ' ', '') LIKE ?
        """,
        (f"%{q}%",),
    ).fetchall()

    # 🔥 매장 자체가 한 개도 없으면 → 바로 에러 반환
    if not stores:
        return render_template(
            "index.html",
            selected_date=selected_date,
            selected_store=selected_store,
            results=[],
            error="해당 매장/테마를 찾을 수 없어요ㅠ<br>복티에게 요청주시면 빠른시일내에 업뎃할게요🤗",
        )

  # 🔥 매장 있을 때 → 예약일 계산
    for store in stores:

        if store["always_open"] and int(store["always_open"]) == 1:
            deadline = store["fixed_note"] or "상시 예약 가능"

        elif store["deadline_days"] is not None and store["deadline_time"]:
            d = datetime.strptime(selected_date, "%Y-%m-%d")
            deadline_date = d - timedelta(days=int(store["deadline_days"]))
            deadline = deadline_date.strftime("%Y년 %m월 %d일 ") + store["deadline_time"]

        else:
            deadline = store["fixed_note"] or "상시 예약 가능"

        # ✅ 줄바꿈 적용 (if/elif/else 밖, for 안)
        deadline = insert_newline_after_time(deadline)

        # ✔ store_name 부분 일치로 테마 찾기
        theme_matches = db.execute(
            """
            SELECT id, theme_name
            FROM themes
            WHERE store_name LIKE ?
              AND (
                REPLACE(keywords, ' ', '') LIKE ?
                OR REPLACE(theme_name, ' ', '') LIKE ?
              )
            ORDER BY id
            """,
            (f"%{store['name']}%", f"%{q}%", f"%{q}%"),
        ).fetchall()

        first = theme_matches[0] if theme_matches else None

        reservation_results.append(
            {
                "name": store["name"],
                "deadline": deadline,
                "theme_id": first["id"] if first else None,
                "theme_name": first["theme_name"] if first else None,
                "themes": theme_matches,
                "memo": store["memo"],
            }
        )

    # 🔽 하단 테마 검색 (선택사항)
    theme_results = db.execute(
        """
        SELECT *
        FROM themes
        WHERE REPLACE(keywords, ' ', '') LIKE ?
           OR REPLACE(theme_name, ' ', '') LIKE ?
        """,
        (f"%{q}%", f"%{q}%"),
    ).fetchall()

    return render_template(
        "index.html",
        results=reservation_results,
        theme_results=theme_results,
        selected_store=selected_store,
        selected_date=selected_date,
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
        price_display = price_raw.replace(" (", '<br><span class="price-sub">(') + "</span>"

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

    schedule_weekday = format_schedule(theme.get("time_table_weekday"), theme["play_time"])
    schedule_friday = format_schedule(theme.get("time_table_friday"), theme["play_time"])
    schedule_weekend = format_schedule(theme.get("time_table_weekend"), theme["play_time"])

    return render_template(
        "theme_detail.html",
        theme=theme,
        schedule_weekday=schedule_weekday,
        schedule_friday=schedule_friday,
        schedule_weekend=schedule_weekend,
        weekday_label=weekday_label,
        weekend_label=weekend_label,
        closed_days=closed_days,
    )


# --------------------------
# 실행
# --------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
