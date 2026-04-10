import json
import pandas as pd

with open("online-prd/prd-data.json", "r", encoding="utf-8") as f:
    raw = json.load(f)

prd_name = raw["data"]["prdName"]
df = pd.DataFrame(raw["data"]["list"])

df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
df["navAccumulated"] = df["navAccumulated"].astype(float)
df = df.sort_values("date")

df["daily_return"] = df["navAccumulated"].pct_change()

monthly = (
    df.dropna(subset=["daily_return"])
      .assign(month=lambda x: x["date"].dt.to_period("M"))
      .groupby("month")["daily_return"]
      .apply(lambda x: (1 + x).prod() - 1)
      .reset_index(name="return")
)

monthly["date"] = monthly["month"].dt.to_timestamp("M")
monthly["product_name"] = prd_name
monthly = monthly[["date", "product_name", "return"]]

print(monthly)