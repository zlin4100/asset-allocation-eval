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

所有输出位于 `output/` 目录：

| 文件 | 说明 |
|------|------|
| result_detail.csv | 每个客户 × 每个周期的指标对比明细 |
| result_summary.csv | 按周期汇总的均值、胜率等统计 |
| summary.md | Markdown 格式的对比摘要 |

### 输出指标

**Per-client**: annualized_return, annualized_vol, sharpe_ratio, max_drawdown, delta_sigma

**Summary**: mean_return, mean_vol, mean_sharpe, mean_abs_delta_sigma, win_rate_return, win_rate_sharpe, win_rate_abs_delta_sigma

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
