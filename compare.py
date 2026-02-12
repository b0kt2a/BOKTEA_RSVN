import pandas as pd

STORES_FILE = "stores.xlsx"
THEMES_FILE = "themes.xlsx"
OUT_FILE = "store_compare.xlsx"

# 1) 파일 읽기
stores = pd.read_excel(STORES_FILE, sheet_name="stores")
themes = pd.read_excel(THEMES_FILE, sheet_name="themes")

# 2) 컬럼명 통일 (stores: name -> store_name)
if "name" in stores.columns and "store_name" not in stores.columns:
    stores = stores.rename(columns={"name": "store_name"})

# 3) store_id 정리 (문자열/공백/NaN 처리)
def clean_id(s: pd.Series) -> pd.Series:
    return (
        s.astype("string")
         .str.strip()
         .replace({"<NA>": pd.NA, "nan": pd.NA, "None": pd.NA})
    )

stores["store_id"] = clean_id(stores["store_id"])
themes["store_id"] = clean_id(themes["store_id"])

stores = stores.dropna(subset=["store_id"])
themes = themes.dropna(subset=["store_id"])

# 4) 비교용 set
stores_ids = set(stores["store_id"].unique())
themes_ids = set(themes["store_id"].unique())

only_in_stores_ids = stores_ids - themes_ids
only_in_themes_ids = themes_ids - stores_ids
both_ids = stores_ids & themes_ids

# 5) 보기 좋은 표 만들기
# stores에만 있는 매장(= themes 업데이트 안된 매장 후보)
only_in_stores_df = (
    stores[stores["store_id"].isin(only_in_stores_ids)]
    .loc[:, ["store_id", "store_name"]]
    .sort_values(["store_id"])
    .reset_index(drop=True)
)

# themes에만 있는 store_id (stores에 등록 안된 id)
themes_store_name_map = (
    themes.dropna(subset=["store_name"])
          .groupby("store_id", as_index=False)["store_name"]
          .first()
)

theme_count = (
    themes.groupby("store_id", as_index=False)
          .agg(theme_count=("theme_id", "count"))
)

only_in_themes_df = (
    theme_count[theme_count["store_id"].isin(only_in_themes_ids)]
    .merge(themes_store_name_map, on="store_id", how="left")
    .loc[:, ["store_id", "store_name", "theme_count"]]
    .sort_values(["store_id"])
    .reset_index(drop=True)
)

# 둘 다 있는 매장 요약(매장별 테마 개수)
stores_basic = stores.loc[:, ["store_id", "store_name"]].drop_duplicates("store_id")
both_summary_df = (
    stores_basic[stores_basic["store_id"].isin(both_ids)]
    .merge(theme_count, on="store_id", how="left")
    .sort_values(["theme_count", "store_id"], ascending=[True, True])
    .reset_index(drop=True)
)

# 6) 엑셀로 저장 (시트 3개)
with pd.ExcelWriter(OUT_FILE, engine="openpyxl") as writer:
    only_in_stores_df.to_excel(writer, sheet_name="stores_only", index=False)
    only_in_themes_df.to_excel(writer, sheet_name="themes_only", index=False)
    both_summary_df.to_excel(writer, sheet_name="both_summary", index=False)

print(f"완료! {OUT_FILE} 생성됨")
print(f"stores_only: {len(only_in_stores_df)}개 / themes_only: {len(only_in_themes_df)}개 / both_summary: {len(both_summary_df)}개")
