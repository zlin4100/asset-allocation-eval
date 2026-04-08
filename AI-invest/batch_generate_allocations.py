"""Two-stage batch asset allocation: generate proposals then extract weights."""

import csv
import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# --- Config ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(BASE_DIR, "市场分析-提示词模板.md")
CSV_PATH = os.path.join(BASE_DIR, "..", "420", "420_growth_clients_35_minimal.csv")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

STAGE1_MODEL = "qwen3-235b-a22b-instruct-2507"
STAGE2_MODEL = "qwen3.6-plus"
MAX_RETRIES = 3
RETRY_DELAY = 5
MIN_INTERVAL = 2  # seconds between API calls

# Eligibility rules
ALLOWED_ASSETS = {
    1: ["CASH", "BOND"],
    2: ["CASH", "BOND", "ALT"],
    3: ["CASH", "BOND", "EQUITY", "ALT"],
    4: ["CASH", "BOND", "EQUITY", "ALT"],
    5: ["CASH", "BOND", "EQUITY", "ALT"],
}

STAGE1_USER_PROMPT = "请结合我当前的情况和市场环境，给我一个专属的资产配置方案。"

STAGE2_SYSTEM_PROMPT = "你是一个结构化数据提取助手。只输出 JSON，不输出任何解释。"

STAGE2_USER_TEMPLATE = """请从下面这段资产配置方案中，提取"最终推荐资产配置方案"的四大类资产权重。

注意：
1. 文中可能有多个备选方案、情景方案或中间方案
2. 你只能提取最终方案
3. 优先识别带有以下字样的方案：
   - 最终推荐资产配置方案
   - 最终方案
   - 最终推荐
   - 推荐方案
   - 综合建议后的最终配置
   - 落地配置建议
4. 如果没有明确标题，请提取全文结论部分最明确的一组四大类权重
5. 不要提取中间推演方案
6. 严格遵守原文，不要脑补原文没有的信息

仅输出 JSON，不要输出任何解释：

```json
{{
  "CASH": null,
  "BOND": null,
  "EQUITY": null,
  "ALT": null
}}
```

待提取正文：
{raw_output}"""


def load_template():
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        return f.read()


def load_clients():
    rows = []
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def build_system_prompt(template: str, risk_level: int, lifecycle: str) -> str:
    """Replace the client profile JSON block in the template."""
    allowed = ALLOWED_ASSETS[risk_level]
    new_json = json.dumps(
        {
            "client_risk_tolerance": f"C{risk_level}",
            "investment_objectives": "增值",
            "life_stage": lifecycle,
            "allowed_asset_classes": allowed,
        },
        ensure_ascii=False,
        indent=2,
    )
    # Replace the JSON block between ```json and ``` under "客户投资前提"
    pattern = r'(# 客户投资前提\s*\n```json\s*\n)(\{.*?\})(\s*\n```)'
    replacement = rf'\g<1>{new_json}\g<3>'
    result = re.sub(pattern, replacement, template, flags=re.DOTALL)
    return result


class APIClient:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        if not api_key:
            raise ValueError("Set OPENAI_API_KEY or DASHSCOPE_API_KEY in .env")
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self._last_call = 0.0

    def chat(self, model: str, system_prompt: str, user_message: str,
             temperature: float = 0.1, max_tokens: int = 8192) -> dict:
        """Call API with retry. Returns dict with raw_output, finish_reason."""
        elapsed = time.time() - self._last_call
        if elapsed < MIN_INTERVAL:
            time.sleep(MIN_INTERVAL - elapsed)

        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                self._last_call = time.time()
                resp = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                text = resp.choices[0].message.content or ""
                # Strip <think>...</think> blocks (Qwen reasoning)
                text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
                finish = resp.choices[0].finish_reason or "unknown"
                return {"raw_output": text, "finish_reason": finish}
            except Exception as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    wait = RETRY_DELAY * (attempt + 1)
                    print(f"  [retry {attempt+1}/{MAX_RETRIES}] {e}, waiting {wait}s...")
                    time.sleep(wait)

        raise RuntimeError(f"API failed after {MAX_RETRIES} retries: {last_error}")


def parse_weights(stage2_output: str) -> dict:
    """Parse CASH/BOND/EQUITY/ALT from stage2 output. Returns dict with weights + parse_status."""
    result = {"CASH": None, "BOND": None, "EQUITY": None, "ALT": None,
              "weight_sum": None, "parse_status": "failed"}

    # Try direct JSON parse
    text = stage2_output.strip()
    parsed = None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        # Try extracting JSON block from markdown code fence or raw braces
        m = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if m:
            try:
                parsed = json.loads(m.group(1))
            except json.JSONDecodeError:
                pass
        if not parsed:
            m = re.search(r'\{[^{}]*"CASH"[^{}]*\}', text, re.DOTALL)
            if m:
                try:
                    parsed = json.loads(m.group(0))
                except json.JSONDecodeError:
                    pass

    if not parsed:
        return result

    for key in ["CASH", "BOND", "EQUITY", "ALT"]:
        val = parsed.get(key)
        if val is not None:
            try:
                result[key] = float(val)
            except (ValueError, TypeError):
                pass

    vals = [result[k] for k in ["CASH", "BOND", "EQUITY", "ALT"] if result[k] is not None]
    if len(vals) == 4:
        result["weight_sum"] = round(sum(vals), 4)
        if abs(result["weight_sum"] - 100) < 0.01:
            result["parse_status"] = "success"
        else:
            result["parse_status"] = "sum_not_100"
    else:
        result["parse_status"] = "failed"

    return result


def run():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    template = load_template()
    clients = load_clients()
    template_hash = hashlib.md5(template.encode()).hexdigest()[:12]
    api = APIClient()

    print(f"Loaded {len(clients)} clients, template hash={template_hash}")

    # --- Stage 1 ---
    stage1_path = os.path.join(OUTPUT_DIR, "stage1_raw_generations_v2.jsonl")
    stage1_results = []

    print("\n=== Stage 1: Generating allocation proposals ===")
    for i, row in enumerate(clients):
        client_id = int(row["id"])
        lifecycle = row["lifecycle"]
        risk_level = int(row["risk_level"])
        allowed = ALLOWED_ASSETS[risk_level]

        print(f"[{i+1}/35] id={client_id} lifecycle={lifecycle} risk=C{risk_level} ...", end=" ", flush=True)

        sys_prompt = build_system_prompt(template, risk_level, lifecycle)

        try:
            resp = api.chat(STAGE1_MODEL, sys_prompt, STAGE1_USER_PROMPT, temperature=0.7, max_tokens=8192)
            status = "success"
        except Exception as e:
            resp = {"raw_output": "", "finish_reason": "error"}
            status = f"error: {e}"
            print(f"FAILED: {e}")

        record = {
            "id": client_id,
            "lifecycle": lifecycle,
            "risk_level": risk_level,
            "allowed_asset_classes": allowed,
            "stage1_model": STAGE1_MODEL,
            "system_prompt_path": TEMPLATE_PATH,
            "system_prompt_hash": template_hash,
            "user_prompt": STAGE1_USER_PROMPT,
            "raw_output": resp["raw_output"],
            "finish_reason": resp["finish_reason"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": status,
        }
        stage1_results.append(record)
        print(f"OK ({len(resp['raw_output'])} chars)")

    with open(stage1_path, "w", encoding="utf-8") as f:
        for r in stage1_results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\nStage 1 saved to {stage1_path}")

    # --- Stage 2 ---
    stage2_path = os.path.join(OUTPUT_DIR, "stage2_extracted_weights_v2.jsonl")
    stage2_results = []

    print("\n=== Stage 2: Extracting weights ===")
    for i, s1 in enumerate(stage1_results):
        client_id = s1["id"]
        print(f"[{i+1}/35] id={client_id} ...", end=" ", flush=True)

        if not s1["raw_output"]:
            print("SKIP (empty stage1)")
            stage2_results.append({
                "id": client_id, "stage2_model": STAGE2_MODEL,
                "stage1_raw_output": "", "stage2_raw_output": "",
                "CASH": None, "BOND": None, "EQUITY": None, "ALT": None,
                "weight_sum": None, "parse_status": "failed",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            continue

        user_msg = STAGE2_USER_TEMPLATE.format(raw_output=s1["raw_output"])

        try:
            resp = api.chat(STAGE2_MODEL, STAGE2_SYSTEM_PROMPT, user_msg, temperature=0.0, max_tokens=512)
            s2_output = resp["raw_output"]
        except Exception as e:
            s2_output = ""
            print(f"FAILED: {e}")

        weights = parse_weights(s2_output)
        record = {
            "id": client_id,
            "stage2_model": STAGE2_MODEL,
            "stage1_raw_output": s1["raw_output"],
            "stage2_raw_output": s2_output,
            **{k: weights[k] for k in ["CASH", "BOND", "EQUITY", "ALT", "weight_sum", "parse_status"]},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        stage2_results.append(record)
        print(f"OK  CASH={weights['CASH']} BOND={weights['BOND']} EQ={weights['EQUITY']} ALT={weights['ALT']} sum={weights['weight_sum']} [{weights['parse_status']}]")

    with open(stage2_path, "w", encoding="utf-8") as f:
        for r in stage2_results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\nStage 2 saved to {stage2_path}")

    # --- Final CSV ---
    csv_path = os.path.join(OUTPUT_DIR, "extracted_weights_v2.csv")
    fieldnames = ["id", "lifecycle", "risk_level", "cash_pct", "bond_pct",
                  "equity_pct", "commodity_pct", "CASH", "BOND", "EQUITY", "ALT",
                  "weight_sum", "parse_status"]

    # Build lookup from original CSV
    client_map = {int(r["id"]): r for r in clients}

    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for s2 in stage2_results:
            cid = s2["id"]
            orig = client_map[cid]
            writer.writerow({
                "id": cid,
                "lifecycle": orig["lifecycle"],
                "risk_level": orig["risk_level"],
                "cash_pct": orig["cash_pct"],
                "bond_pct": orig["bond_pct"],
                "equity_pct": orig["equity_pct"],
                "commodity_pct": orig["commodity_pct"],
                "CASH": s2["CASH"],
                "BOND": s2["BOND"],
                "EQUITY": s2["EQUITY"],
                "ALT": s2["ALT"],
                "weight_sum": s2["weight_sum"],
                "parse_status": s2["parse_status"],
            })
    print(f"Final CSV saved to {csv_path}")

    # Summary
    success = sum(1 for r in stage2_results if r["parse_status"] == "success")
    failed = sum(1 for r in stage2_results if r["parse_status"] == "failed")
    not100 = sum(1 for r in stage2_results if r["parse_status"] == "sum_not_100")
    print(f"\nDone. success={success} sum_not_100={not100} failed={failed}")


if __name__ == "__main__":
    run()
