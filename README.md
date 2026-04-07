# asset-allocation-eval

资产配置策略离线评估框架。比较智能投顾 3.0 与 420 在统一口径下的定量表现。

## 两层比较逻辑

| 层级 | 策略 A | 策略 B | 收益数据来源 | 权重类型 |
|------|--------|--------|-------------|---------|
| 指数层 | 3.0 | 420_static | asset_returns.csv (四大类资产指数) | asset_class 权重 |
| 产品层 | 3.0_mapped_product | 420_online | product_returns.csv (真实产品净值) | product_code 权重 |

- **指数层**：纯资产配置能力对比，使用 CASH / BOND / EQUITY / ALT 四大类指数月收益
- **产品层**：含产品选择的端到端对比，使用实际产品月收益序列

两层均为 buy-and-hold（静态权重，不做再平衡）。

## 客户维度

5 风险等级 (C1~C5) × 7 人生阶段 (S1~S7) = 35 类客户。

## 输入文件 Schema

所有输入文件位于 `data/` 目录：

### client_profiles.csv
| 字段 | 说明 |
|------|------|
| client_id | 客户标识，格式 `{risk_level}_{life_stage}` |
| risk_level | C1~C5 |
| life_stage | S1~S7 |

### strategy_weights.csv
| 字段 | 说明 |
|------|------|
| portfolio_type | `3.0` / `420_static` / `420_online` / `3.0_mapped_product` |
| client_id | 客户标识 |
| asset_class | CASH / BOND / EQUITY / ALT |
| product_code | 产品代码（指数层为空，产品层必填） |
| weight | 权重，同一 (portfolio_type, client_id) 下求和为 1 |

### asset_returns.csv
| 字段 | 说明 |
|------|------|
| date | 月末日期 YYYY-MM-DD |
| asset_class | CASH / BOND / EQUITY / ALT |
| return | 月收益率 |

### product_returns.csv
| 字段 | 说明 |
|------|------|
| date | 月末日期 YYYY-MM-DD |
| product_code | 产品代码 |
| asset_class | 所属大类 |
| return | 月收益率 |

### risk_anchor.csv
| 字段 | 说明 |
|------|------|
| client_id | 客户标识 |
| risk_level | C1~C5 |
| target_vol | 目标年化波动率 |
| max_drawdown_tolerance | 最大回撤容忍度 |

## 输出文件

所有输出位于 `output/` 目录。

### result_detail.csv / result_detail_index.csv / result_detail_product.csv

**逐客户、逐周期的对比明细。** 每行 = 一个客户 × 一个回测周期。

- `result_detail_index.csv`：仅指数层（35 客户 × 5 周期 = 175 行）
- `result_detail_product.csv`：仅产品层（35 客户 × 1 周期 = 35 行）
- `result_detail.csv`：合并以上两者，额外增加 `layer` 列标识所属层级

每个策略的指标以后缀区分（如 `_3.0` / `_420_static`），含义如下：

| 字段 | 含义 | 计算方式 |
|------|------|---------|
| `annualized_return` | 年化收益率 | `∏(1 + r_月)^(12/n) - 1`，将月度复利收益折算为年化 |
| `annualized_vol` | 年化波动率 | `std(月收益, ddof=1) × √12`，衡量收益的离散程度 |
| `sharpe_ratio` | 夏普比率 | `(年化收益 - 0.02) / 年化波动率`，无风险利率固定 2%，衡量单位风险的超额收益 |
| `max_drawdown` | 最大回撤 | 累计净值序列中，从峰值到谷值的最大跌幅（负数），衡量极端下行风险 |
| `delta_return` | 收益差 | 策略 A 年化收益 - 策略 B 年化收益，正值表示 A 更优 |
| `delta_sharpe` | 夏普差 | 策略 A 夏普 - 策略 B 夏普 |
| `delta_sigma` | 波动率差 | 策略 A 年化波动率 - 策略 B 年化波动率，正值表示 A 风险更高 |
| `abs_delta_sigma` | 波动率差绝对值 | `|delta_sigma|`，用于汇总时衡量两策略的风险偏离程度 |

### result_summary.csv

**按周期汇总的统计摘要。** 每行 = 一个回测周期 × 一个层级（指数层 5 行 + 产品层 1 行 = 6 行）。

| 字段 | 含义 | 说明 |
|------|------|------|
| `period` | 回测周期 | 1y / 3y / 5y / 10y / 20y |
| `n_clients` | 客户数 | 该周期下有足够数据的客户数（通常 35） |
| `mean_return_*` | 平均年化收益 | 35 个客户年化收益的均值 |
| `mean_vol_*` | 平均年化波动率 | 35 个客户年化波动率的均值 |
| `mean_sharpe_*` | 平均夏普比率 | 35 个客户夏普比率的均值 |
| `mean_abs_delta_sigma` | 平均波动率偏离 | 35 个客户 `abs_delta_sigma` 的均值，反映两策略风险水平的整体差异 |
| `win_rate_return` | 收益胜率 | 策略 A 年化收益 > 策略 B 的客户占比 |
| `win_rate_sharpe` | 夏普胜率 | 策略 A 夏普 > 策略 B 的客户占比 |
| `win_rate_abs_delta_sigma` | 低波动胜率 | 策略 A 波动率 < 策略 B 的客户占比（A 风险更低即为赢） |

### summary.md

与 `result_summary.csv` 内容一致的 Markdown 表格，按指数层 / 产品层分段展示，便于直接阅读或嵌入文档。

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 生成 mock 数据
python generate_mock.py

# 运行评估
python main.py
```

## 回测周期

- 指数层：1y / 3y / 5y / 10y / 20y
- 产品层：按数据可用性（mock 数据为 5y）

## 扩展新策略

1. 在 `strategy_weights.csv` 中新增 `portfolio_type`（如 `new_strategy`）
2. 补充对应的权重行（指数层填 asset_class，产品层填 product_code）
3. 在 `main.py` 中新增 `portfolio_monthly_returns()` + `compute_all_metrics()` 调用
4. 用 `compare_pair()` 与已有策略对比

## 技术栈

- Python 3.11+
- pandas, numpy
- 函数式风格，无 class 依赖
