# asset-allocation-eval

资产配置策略离线评估框架。比较智能投顾 3.0 与 420 在统一口径下的定量表现。

## 项目定位

本项目不是用于寻找某一类优化器下的“数学最优组合”，而是用于在统一口径下比较不同资产配置方案的收益、风险与客户适配性。

在智能投顾 3.0 的多引擎架构下（如 MVO / 风险平价 / 目标风险 / 规则+优化混合 / 专家覆盖），`risk_anchor.csv` 提供的不是某个单一策略的内生目标，而是一个**策略无关的统一裁判层**：

- **事前约束（ex-ante constraint）**：为不同引擎提供统一风险边界
- **事后评估（ex-post evaluation）**：对不同引擎产出的组合进行统一适配性评估
- **跨引擎可比性**：让目标函数不同的策略也能在同一把尺子下横向比较

## 两层比较逻辑

| 层级 | 策略 A | 策略 B | 收益数据来源 | 权重类型 |
|------|--------|--------|-------------|---------|
| 指数层 | 3.0 | 420_static | asset_returns.csv (四大类资产指数) | asset_class 权重 |
| 产品层 | 3.0_mapped_product | 420_online | product_returns.csv (真实产品净值) | product_code 权重 |

- **指数层**：纯资产配置能力对比，使用 CASH / BOND / EQUITY / ALT 四大类指数月收益
- **产品层**：含产品选择的端到端对比，使用实际产品月收益序列

两层均为 buy-and-hold（静态权重，不做再平衡）。

## 客户维度

5 风险等级 (C1~C5) × 7 人生阶段 (S1~S7) = 35 类客户画像。

## 关键设计原则

### 原则 1：不定义标准组合

本项目不预设标准资产配置比例，也不绑定任何单一优化范式，而是在统一输入与统一评估口径下比较不同策略表现。

### 原则 2：风险等级与生命周期解耦

- 风险等级：刻画客户可承受风险强度
- 生命周期：刻画客户长期风险承载上限

两者共同决定客户画像对应的风险锚。

### 原则 3：风险匹配优于风险最小

波动率最低不等于最优。  
对客户而言，更重要的是组合风险是否落在其应承担的风险区间内，并尽可能接近目标风险中枢。

### 原则 4：避免双重约束

- `sigma_min / sigma_mid / sigma_max`：描述常态风险预算
- `max_drawdown_tolerance`：描述极端风险红线

二者分工不同，不重复建模。

### 原则 5：risk anchor 是策略无关的裁判层

`risk_anchor.csv` 的目标不是服务某一个具体优化器，而是作为不同引擎共享的统一风险尺子，用于：

- 事前约束策略空间
- 事后评估客户适配性
- 支撑不同策略间的可比性分析

## 输入文件 Schema

所有输入文件位于 `data/` 目录：

### client_profiles.csv

| 字段 | 说明 |
|------|------|
| profile_id | 客户画像标识，格式 `{risk_level}_{life_stage}` |
| risk_level | C1~C5 |
| life_stage | S1~S7 |

### strategy_weights.csv

| 字段 | 说明 |
|------|------|
| portfolio_type | `3.0` / `420_static` / `420_online` / `3.0_mapped_product` |
| profile_id | 客户画像标识 |
| asset_class | CASH / BOND / EQUITY / ALT |
| product_code | 产品代码（指数层为空，产品层必填） |
| weight | 权重，同一 `(portfolio_type, profile_id)` 下求和为 1 |

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
| profile_id | 客户画像主键，对应 `(risk_level, life_stage)` 的组合键，不代表真实客户 ID |
| risk_level | C1~C5 |
| life_stage | S1~S7 |
| sigma_min | 风险预算闲置阈值 |
| sigma_mid | 风险预算目标中枢 |
| sigma_max | 风险上限（风险容器上边界） |
| max_drawdown_tolerance | 最大回撤容忍度 |

## 风险锚说明

`risk_anchor.csv` 描述的不是“标准组合”，而是每类客户画像的**风险容器（Risk Container）**。

其中：

- `sigma_max`：最大可承受波动率上限
- `sigma_mid`：目标风险中枢，用于衡量风险预算占用率
- `sigma_min`：风险预算闲置阈值，长期低于该值可视为风险承担不足
- `max_drawdown_tolerance`：极端下行情形下的回撤红线

在评估中，可进一步使用：

```text
Δσ = annualized_vol - sigma_mid
```

衡量组合实际风险与目标风险中枢的偏离程度：

- `Δσ > 0`：风险高于目标中枢
- `Δσ < 0`：风险低于目标中枢
- `|Δσ| 越小`：风险匹配越好

## 输出文件

所有输出位于 `output/` 目录。

### result_detail.csv / result_detail_index.csv / result_detail_product.csv

**逐客户画像、逐周期的对比明细。** 每行 = 一个客户画像 × 一个回测周期。

- `result_detail_index.csv`：仅指数层（35 客户画像 × 5 周期 = 175 行）
- `result_detail_product.csv`：仅产品层（35 客户画像 × 1 周期 = 35 行）
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

如需做“客户适配性”评估，建议基于 `risk_anchor.csv` 衍生补充字段，例如：

| 字段 | 含义 |
|------|------|
| `delta_sigma_to_mid` | `annualized_vol - sigma_mid`，相对目标中枢的偏差 |
| `abs_delta_sigma_to_mid` | `|annualized_vol - sigma_mid|`，风险匹配偏离程度 |
| `breach_sigma_max` | 是否超过 `sigma_max` |
| `breach_sigma_min` | 是否低于 `sigma_min` |
| `breach_max_drawdown` | 是否超过最大回撤容忍度 |

### result_summary.csv

**按周期汇总的统计摘要。** 每行 = 一个回测周期 × 一个层级（指数层 5 行 + 产品层 1 行 = 6 行）。

| 字段 | 含义 | 说明 |
|------|------|------|
| `period` | 回测周期 | 1y / 3y / 5y / 10y / 20y |
| `n_clients` | 客户画像数 | 该周期下有足够数据的客户画像数（通常 35） |
| `mean_return_*` | 平均年化收益 | 35 个客户画像年化收益的均值 |
| `mean_vol_*` | 平均年化波动率 | 35 个客户画像年化波动率的均值 |
| `mean_sharpe_*` | 平均夏普比率 | 35 个客户画像夏普比率的均值 |
| `mean_abs_delta_sigma` | 平均波动率偏离 | 35 个客户画像 `abs_delta_sigma` 的均值，反映两策略风险水平的整体差异 |
| `win_rate_return` | 收益胜率 | 策略 A 年化收益 > 策略 B 的客户画像占比 |
| `win_rate_sharpe` | 夏普胜率 | 策略 A 夏普 > 策略 B 的客户画像占比 |
| `win_rate_abs_delta_sigma` | 低波动胜率 | 策略 A 波动率 < 策略 B 的客户画像占比（A 风险更低即为赢） |

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
2. 补充对应的权重行（指数层填 `asset_class`，产品层填 `product_code`）
3. 在 `main.py` 中新增 `portfolio_monthly_returns()` + `compute_all_metrics()` 调用
4. 用 `compare_pair()` 与已有策略对比
5. 如需纳入客户适配性评估，同步接入 `risk_anchor.csv` 的风险容器校验逻辑

## 体系边界与局限

- 本项目以收益率、波动率、夏普、最大回撤等指标为主，对尾部风险、流动性风险、信用风险的刻画有限
- `risk_anchor.csv` 提供的是统一风险锚，不替代收益预测、择时能力或底层研究能力
- `Δσ` 一类风险匹配指标依赖观察窗口长度，窗口过短时稳定性不足，应结合统一回测窗口与滚动评估机制使用
- 本框架适用于多资产配置策略比较，不适用于高杠杆、单一资产或衍生品主导策略的完整风险刻画

## 技术栈

- Python 3.11+
- pandas, numpy
- 函数式风格，无 class 依赖