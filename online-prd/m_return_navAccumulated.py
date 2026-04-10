import json
from pathlib import Path

import pandas as pd


INPUT_PATH = Path("online-prd/prd-data.json")
OUTPUT_PATH = Path("online-prd/alt_monthly_returns.csv")


with open(INPUT_PATH, "r", encoding="utf-8") as f:
    raw = json.load(f)

prd_name = raw["data"]["prdName"]
df = pd.DataFrame(raw["data"]["list"])

# 1) 使用累计净值，原因：累计净值包含分红再投资，能反映真实财富路径
# 2) 不使用 avgreturnDay，原因：有四舍五入误差
# 3) 月收益不是简单相加，而是由月末累计净值直接精确计算
#    r_month = NAV_month_end / NAV_prev_month_end - 1

df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
df["navAccumulated"] = pd.to_numeric(df["navAccumulated"], errors="coerce")
df = df.dropna(subset=["date", "navAccumulated"]).sort_values("date")

# 取每个月最后一个可用交易日的累计净值
month_end_nav = (
    df.assign(month=lambda x: x["date"].dt.to_period("M"))
      .groupby("month", as_index=False)
      .tail(1)
      [["date", "month", "navAccumulated"]]
      .sort_values("date")
      .reset_index(drop=True)
)

# 用相邻月末累计净值计算“精确月收益率”
month_end_nav["ALT"] = month_end_nav["navAccumulated"].pct_change()

result = month_end_nav[["date", "ALT"]].copy()
result["date"] = result["date"].dt.strftime("%Y-%m-%d")

# 先只算 ALT，其余三列留空，方便后续横向合并
result.insert(1, "CASH", pd.NA)
result.insert(2, "BOND", pd.NA)
result.insert(3, "EQUITY", pd.NA)
result = result[["date", "CASH", "BOND", "EQUITY", "ALT"]]

# 第一行没有上月月末净值，无法计算收益，删除
result = result.dropna(subset=["ALT"]).reset_index(drop=True)

result.to_csv(OUTPUT_PATH, index=False, float_format="%.8f")

print(f"product_name: {prd_name}")
print(result)
print(f"saved to: {OUTPUT_PATH}")