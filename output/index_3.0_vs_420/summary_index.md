# Index Layer: 3.0 vs 420_static

## 字段说明

| 字段 | 含义 |
|------|------|
| `period` | 回看期限（1y/3y/5y/10y/20y） |
| `n_clients` | 客户画像数量（35 = C1–C5 × S1–S7） |
| `mean_return_3.0` | 3.0 策略平均年化收益率（35 个画像的均值） |
| `mean_return_420_static` | 420_static 策略平均年化收益率 |
| `mean_vol_3.0` | 3.0 策略平均年化波动率 |
| `mean_vol_420_static` | 420_static 策略平均年化波动率 |
| `mean_sharpe_3.0` | 3.0 策略平均夏普比率（rf=2%） |
| `mean_sharpe_420_static` | 420_static 策略平均夏普比率 |
| `mean_abs_delta_sigma` | 两策略波动率之差绝对值的均值，\|vol_3.0 − vol_420\| |
| `win_rate_return` | 3.0 收益高于 420_static 的画像占比 |
| `win_rate_sharpe` | 3.0 夏普高于 420_static 的画像占比 |
| `win_rate_abs_delta_sigma` | 3.0 风险匹配优于 420_static 的画像占比（基于风险锚：\|vol − σ_mid\| 更小者胜） |
| `mean_abs_delta_sigma_3.0` | 3.0 策略的平均风险偏差，mean(\|vol_3.0 − σ_mid\|) |
| `mean_abs_delta_sigma_420_static` | 420_static 策略的平均风险偏差，mean(\|vol_420 − σ_mid\|) |

> σ_mid 来自风险锚体系（docs/风险锚体系.md），为每个客户画像的风险中枢目标波动率。\|Δσ\| 越小说明策略越匹配客户风险画像。

## 汇总表

| period | n_clients | mean_return_3.0 | mean_return_420_static | mean_vol_3.0 | mean_vol_420_static | mean_sharpe_3.0 | mean_sharpe_420_static | mean_abs_delta_sigma | win_rate_return | win_rate_sharpe | win_rate_abs_delta_sigma | mean_abs_delta_sigma_3.0 | mean_abs_delta_sigma_420_static |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 10y | 35 | 0.0712 | 0.0574 | 0.0578 | 0.0506 | 1.0505 | 1.0052 | 0.0120 | 0.8571 | 0.6000 | 0.5714 | 0.0241 | 0.0290 |
| 1y | 35 | 0.1650 | 0.1178 | 0.0534 | 0.0390 | 2.1533 | 1.8159 | 0.0156 | 0.8571 | 0.8857 | 0.7143 | 0.0284 | 0.0393 |
| 20y | 35 | 0.0713 | 0.0648 | 0.0874 | 0.0789 | 0.7790 | 0.8647 | 0.0175 | 0.7714 | 0.4571 | 0.6571 | 0.0330 | 0.0342 |
| 3y | 35 | 0.1025 | 0.0746 | 0.0599 | 0.0515 | 1.4738 | 1.2981 | 0.0130 | 0.8571 | 0.7429 | 0.5714 | 0.0233 | 0.0286 |
| 5y | 35 | 0.0717 | 0.0507 | 0.0588 | 0.0513 | 1.1212 | 1.0121 | 0.0127 | 0.8857 | 0.6000 | 0.5714 | 0.0239 | 0.0288 |