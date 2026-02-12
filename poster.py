from pathlib import Path
import pandas as pd

THEMES_XLSX = "themes.xlsx"
THEMES_SHEET = "themes"

# 너 폴더 구조에 맞게만 여기 수정하면 됨
POSTER_DIR = Path("static/posters")

OUT_FILE = "poster_compare.xlsx"

# 1) themes 읽기
themes = pd.read_excel(THEMES_XLSX, sheet_name=THEMES_SHEET)

# 2) theme_id 정리 (문자열/공백 처리)
themes["theme_id"] = themes["theme_id"].astype("string").str.strip()
themes_ids = set(themes["theme_id"].dropna().unique())

# 3) 포스터 파일명 목록 (확장자 제거 = theme_id)
poster_files = [p for p in POSTER_DIR.glob("*.*") if p.is_file()]
poster_ids = set(p.stem.strip() for p in poster_files)

# 4) 비교
themes_missing_poster = themes_ids - poster_ids      # 테마는 있는데 포스터 없음
poster_without_theme = poster_ids - themes_ids       # 포스터는 있는데 테마 없음
both = themes_ids & poster_ids

# 5) 보기 좋은 결과표 만들기
missing_df = (
    themes[themes["theme_id"].isin(themes_missing_poster)]
    .loc[:, [c for c in ["theme_id", "theme_name", "store_name", "store_id"] if c in themes.columns]]
    .drop_duplicates("theme_id")
    .sort_values("theme_id")
    .reset_index(drop=True)
)

extra_df = (
    pd.DataFrame({"theme_id": sorted(poster_without_theme)})
    .sort_values("theme_id")
    .reset_index(drop=True)
)

summary_df = pd.DataFrame({
    "themes_count": [len(themes_ids)],
    "posters_count": [len(poster_ids)],
    "missing_poster_count": [len(themes_missing_poster)],
    "extra_poster_count": [len(poster_without_theme)],
    "both_count": [len(both)],
})

# 6) 엑셀 저장 (시트 3개)
with pd.ExcelWriter(OUT_FILE, engine="openpyxl") as writer:
    summary_df.to_excel(writer, sheet_name="summary", index=False)
    missing_df.to_excel(writer, sheet_name="themes_missing_poster", index=False)
    extra_df.to_excel(writer, sheet_name="poster_without_theme", index=False)

print(f"완료! {OUT_FILE} 생성됨")
print(f"테마는 있는데 포스터 없는 개수: {len(themes_missing_poster)}")
print(f"포스터는 있는데 테마 없는 개수: {len(poster_without_theme)}")
