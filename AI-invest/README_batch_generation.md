# 两阶段批量资产配置生成

## 概述

对 35 个客户画像，分两阶段批量调用 Qwen 模型：

1. **Stage 1** (`qwen3-235b-a22b-instruct-2507`)：基于宏观数据 + 客户画像生成完整配置方案
2. **Stage 2** (`qwen3.6-plus`)：从方案正文中提取"最终推荐"四大类权重

## 环境准备

```bash
pip install -r requirements.txt
```

在 `.env` 中配置（已有则无需修改）：

```
OPENAI_API_KEY=your_dashscope_key
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

## 运行

```bash
cd AI-invest
python batch_generate_allocations.py
```

## 输出

`outputs/` 目录下：

| 文件 | 说明 |
|------|------|
| `stage1_raw_generations.jsonl` | 35 条完整 LLM 输出 |
| `stage2_extracted_weights.jsonl` | 35 条提取结果 |
| `extracted_weights.csv` | 汇总对比表（含原始 420 权重 + AI 提取权重） |

## 适当性规则

- C1: CASH, BOND
- C2: CASH, BOND, ALT
- C3/C4/C5: CASH, BOND, EQUITY, ALT
