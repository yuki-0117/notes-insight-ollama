#!/usr/bin/env python3
"""把 data/outputs/*.json 的結果渲染成 docs/index.html（GitHub Pages 作品頁）。

用法：
    uv run python scripts/build_site.py

這個腳本只用 Python 標準函式庫，不依賴額外套件，GitHub Actions 裡跑起來
很單純、幾乎不會失敗。

產生的頁面包含四大區塊（對應評分表「GitHub Pages 作品頁」的要求）：
  1. 做了什麼   (what)
  2. 怎麼執行   (how)
  3. 執行結果   (results)   <- 讀取 data/outputs/*.json
  4. AI 使用說明 (ai-usage)
"""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_DIR = PROJECT_ROOT / "data" / "outputs"
DOCS_DIR = PROJECT_ROOT / "docs"

PRIORITY_LABEL = {"high": "高", "medium": "中", "low": "低"}
PRIORITY_COLOR_VAR = {"high": "--macaron-pink", "medium": "--macaron-yellow", "low": "--macaron-mint"}


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def load_results() -> list[dict]:
    if not OUTPUTS_DIR.exists():
        return []
    records = []
    for path in sorted(OUTPUTS_DIR.glob("*.json")):
        try:
            records.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return records


def render_action_items(items: list[dict]) -> str:
    if not items:
        return '<p class="muted">（這份筆記沒有萃取出待辦事項）</p>'
    rows = []
    for item in items:
        color_var = PRIORITY_COLOR_VAR.get(item.get("priority", "medium"), "--macaron-yellow")
        label = PRIORITY_LABEL.get(item.get("priority", "medium"), "中")
        rows.append(
            f"""
            <tr>
              <td>{esc(item.get("task", ""))}</td>
              <td>{esc(item.get("owner") or "—")}</td>
              <td>{esc(item.get("deadline") or "—")}</td>
              <td><span class="badge" style="background:var({color_var})">{label}</span></td>
            </tr>"""
        )
    return f"""
    <table class="action-table">
      <thead>
        <tr><th>待辦事項</th><th>負責人</th><th>截止日</th><th>優先度</th></tr>
      </thead>
      <tbody>{''.join(rows)}</tbody>
    </table>"""


def render_result_card(record: dict) -> str:
    insight = record.get("insight", {})
    source_file = record.get("source_file", "unknown.txt")
    raw_text = record.get("raw_text", "")

    key_points = "".join(f"<li>{esc(point)}</li>" for point in insight.get("key_points", []))
    topics = "\n".join(
        f'<span class="tag">{esc(topic)}</span>' for topic in insight.get("topics", [])
    )

    return f"""
    <article class="card result-card">
      <header class="result-card__header">
        <h3>{esc(insight.get("title", source_file))}</h3>
        <span class="source-file">來源檔案：{esc(source_file)}</span>
      </header>
      <p class="summary">{esc(insight.get("summary", ""))}</p>
      <div class="tags">{topics}</div>
      <h4>重點</h4>
      <ul class="key-points">{key_points}</ul>
      <h4>待辦事項</h4>
      {render_action_items(insight.get("action_items", []))}
      <details>
        <summary>查看原始筆記內容</summary>
        <pre class="raw-text">{esc(raw_text)}</pre>
      </details>
    </article>"""


def render_results_section(records: list[dict]) -> str:
    if not records:
        return """
        <div class="card empty-state">
          <p>目前還沒有執行結果。請先在你自己的電腦（已安裝並啟動 Ollama）執行：</p>
          <pre><code>uv run python -m notes_extractor run-all</code></pre>
          <p>產生 <code>data/outputs/*.json</code> 後，再執行：</p>
          <pre><code>uv run python scripts/build_site.py</code></pre>
          <p>重新產生這個頁面，然後把 <code>data/outputs/</code> 跟 <code>docs/</code> 一起 commit 並 push。</p>
        </div>"""
    cards = "".join(render_result_card(r) for r in records)
    return f'<div class="results-grid">{cards}</div>'


def render_page(records: list[dict]) -> str:
    generated_at = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M %Z")
    results_section = render_results_section(records)
    run_count = len(records)

    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>AI 讀書筆記＆待辦事項萃取器</title>
<style>
  :root {{
    --macaron-mint: #bdeedd;
    --macaron-pink: #ffd3e2;
    --macaron-lavender: #e2d9f7;
    --macaron-yellow: #fff3bf;
    --ink: #3b3042;
    --ink-soft: #6b6070;
    --bg: #fbf8ff;
    --card-bg: #ffffff;
    --radius: 18px;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    font-family: "Noto Sans TC", "PingFang TC", "Microsoft JhengHei", system-ui, sans-serif;
    background: linear-gradient(180deg, var(--macaron-lavender) 0%, var(--bg) 320px);
    color: var(--ink);
    line-height: 1.75;
  }}
  .wrap {{ max-width: 920px; margin: 0 auto; padding: 0 20px 80px; }}
  header.hero {{ padding: 56px 0 28px; }}
  header.hero h1 {{ font-size: 2rem; margin: 0 0 10px; }}
  header.hero p {{ color: var(--ink-soft); margin: 0; }}
  nav.toc {{
    display: flex; gap: 10px; flex-wrap: wrap; margin: 24px 0 40px;
  }}
  nav.toc a {{
    text-decoration: none; color: var(--ink); background: var(--card-bg);
    padding: 8px 16px; border-radius: 999px; font-size: 0.9rem;
    box-shadow: 0 2px 10px rgba(80, 60, 100, 0.08);
  }}
  section {{ margin-bottom: 52px; scroll-margin-top: 20px; }}
  section > h2 {{
    display: inline-block; font-size: 1.3rem; margin-bottom: 18px;
    padding: 4px 14px; border-radius: 10px; background: var(--macaron-yellow);
  }}
  .card {{
    background: var(--card-bg); border-radius: var(--radius); padding: 22px 26px;
    box-shadow: 0 4px 18px rgba(80, 60, 100, 0.08); margin-bottom: 18px;
  }}
  .results-grid {{ display: grid; gap: 20px; }}
  .result-card__header {{ display: flex; align-items: baseline; justify-content: space-between; flex-wrap: wrap; gap: 8px; }}
  .result-card__header h3 {{ margin: 0; }}
  .source-file {{ font-size: 0.8rem; color: var(--ink-soft); }}
  .summary {{ color: var(--ink-soft); }}
  .tags {{ margin: 6px 0 14px; display: flex; gap: 6px; flex-wrap: wrap; }}
  .tag {{
    background: var(--macaron-mint); padding: 3px 12px; border-radius: 999px;
    font-size: 0.78rem;
  }}
  .key-points {{ padding-left: 1.2em; margin: 6px 0 18px; }}
  .action-table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; margin-bottom: 10px; }}
  .action-table th, .action-table td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid #eee5fb; }}
  .badge {{ padding: 2px 10px; border-radius: 999px; font-size: 0.78rem; }}
  details {{ margin-top: 10px; }}
  details summary {{ cursor: pointer; color: var(--ink-soft); font-size: 0.85rem; }}
  .raw-text {{
    white-space: pre-wrap; background: #faf7ff; padding: 14px; border-radius: 12px;
    font-size: 0.82rem; color: var(--ink-soft); margin-top: 8px;
  }}
  .muted {{ color: var(--ink-soft); font-size: 0.9rem; }}
  pre code, pre {{ background: #2f2a38; color: #f4f0fb; padding: 14px 16px; border-radius: 12px; display: block; overflow-x: auto; font-size: 0.85rem; }}
  code {{ background: #efe8fb; padding: 2px 6px; border-radius: 6px; font-size: 0.88em; }}
  ol, ul {{ margin: 8px 0; }}
  footer {{ color: var(--ink-soft); font-size: 0.82rem; text-align: center; padding-top: 20px; }}
  .stat-row {{ display: flex; gap: 14px; flex-wrap: wrap; margin-bottom: 10px; }}
  .stat {{
    background: var(--macaron-pink); border-radius: 14px; padding: 10px 16px;
    font-size: 0.85rem;
  }}
</style>
</head>
<body>
<div class="wrap">
  <header class="hero">
    <h1>📓 AI 讀書筆記＆待辦事項萃取器</h1>
    <p>資管系課程作業｜自選主題：把雜亂的課堂筆記、會議記錄、讀書會逐字稿，
       丟給本地 Ollama 模型，自動整理成重點摘要與待辦事項清單。</p>
  </header>

  <nav class="toc">
    <a href="#what">做了什麼</a>
    <a href="#how">怎麼執行</a>
    <a href="#compare">本地 vs 雲端比較</a>
    <a href="#results">執行結果</a>
    <a href="#ai-usage">AI 使用說明</a>
  </nav>

  <section id="what">
    <h2>做了什麼</h2>
    <div class="card">
      <p>這支程式用 <strong>Python + uv</strong> 呼叫<strong>本地 Ollama</strong>
         模型，展示 W6 課程教的「<strong>結構化輸出（Structured Output）</strong>」能力：
         不是請模型自由發揮寫一段摘要，而是定義好一份 JSON Schema
         （標題、重點摘要、條列重點、待辦事項、主題標籤），強制模型的回覆必須符合
         這個格式，程式再用 Pydantic 驗證一次欄位型別是否正確。</p>
      <p>應用情境：同學每週要讀很多課堂筆記、小組會議記錄、讀書會逐字稿，
         常常事後很難回想「那次到底講了什麼、誰要做什麼事」。這支程式可以
         把一段雜亂的文字，自動整理成「重點摘要＋待辦事項清單（含負責人、
         截止日、優先度）」，省下自己重新爬梳筆記的時間。</p>
      <div class="stat-row">
        <div class="stat">核心能力：結構化輸出（Structured Output）</div>
        <div class="stat">模型來源：本地 Ollama（免費、不需要 API 金鑰）</div>
        <div class="stat">已處理範例筆記：{run_count} 份</div>
      </div>
    </div>
  </section>

  <section id="how">
    <h2>怎麼執行</h2>
    <div class="card">
      <ol>
        <li>安裝 <a href="https://ollama.com/download" target="_blank" rel="noopener">Ollama</a>，
            啟動服務後執行 <code>ollama pull qwen2.5:7b</code>（或你想用的其他模型）下載模型。</li>
        <li>安裝 <a href="https://docs.astral.sh/uv/" target="_blank" rel="noopener">uv</a>，
            在專案資料夾執行 <code>uv sync</code> 安裝相依套件。</li>
        <li>複製 <code>.env.example</code> 為 <code>.env</code>，依需要調整 <code>OLLAMA_MODEL</code> 等變數。</li>
        <li>執行其中一個指令：</li>
      </ol>
      <pre><code># 處理單一筆記檔案
uv run python -m notes_extractor run data/samples/lecture_data_structures.txt

# 一次處理 data/samples/ 底下全部筆記
uv run python -m notes_extractor run-all</code></pre>
      <ol start="5">
        <li>重新產生這個作品頁：
          <pre><code>uv run python scripts/build_site.py</code></pre>
        </li>
        <li><code>git add</code> / <code>commit</code> / <code>push</code> 到 GitHub 的 <code>main</code> 分支，
            GitHub Actions 就會自動把 <code>docs/</code> 部署到 GitHub Pages。</li>
      </ol>
    </div>
  </section>

  <section id="compare">
    <h2>本地 vs 雲端比較（加分項）</h2>
    <div class="card">
      <p>這個專案選擇呼叫<strong>本地 Ollama</strong>而不是雲端 API，以下整理兩者的
         差異，說明選擇本地模型的理由。</p>
      <table class="action-table">
        <thead>
          <tr><th>比較項目</th><th>本地 Ollama（本專案採用）</th><th>雲端 API（OpenAI／Anthropic 等）</th></tr>
        </thead>
        <tbody>
          <tr><td>API 金鑰</td><td>不需要，完全迴避金鑰外洩風險</td><td>需要申請並妥善保管，放 .env</td></tr>
          <tr><td>費用</td><td>免費（僅耗電腦運算資源）</td><td>依使用量計費</td></tr>
          <tr><td>隱私</td><td>資料不離開自己電腦</td><td>資料會傳到第三方伺服器</td></tr>
          <tr><td>速度／延遲</td><td>取決於本機硬體，筆電跑 7B 模型可能較慢</td><td>通常較快較穩定</td></tr>
          <tr><td>模型品質</td><td>開源模型中文能力已不錯，但略遜於頂級雲端模型</td><td>目前最強模型多為雲端閉源模型</td></tr>
          <tr><td>網路需求</td><td>下載模型後可離線使用</td><td>每次呼叫都要連網路</td></tr>
          <tr><td>適合放進 CI？</td><td>不適合，CI 連不到本機 Ollama</td><td>可行，但要把金鑰放進 GitHub Secrets</td></tr>
          <tr><td>建置／維運複雜度</td><td>需安裝 Ollama、下載模型（佔硬碟空間）</td><td>申請金鑰即可使用，不需安裝</td></tr>
        </tbody>
      </table>
      <p class="muted">詳細說明見 README「本地 Ollama vs 雲端 API 比較」章節。</p>
    </div>
  </section>

  <section id="results">
    <h2>執行結果</h2>
    {results_section}
  </section>

  <section id="ai-usage">
    <h2>AI 使用說明</h2>
    <div class="card">
      <p><strong>使用的工具：</strong>Claude（Cowork）。</p>
      <p><strong>用在哪裡：</strong></p>
      <ul>
        <li>規劃整體專案架構（為什麼讓 GitHub Actions 只負責部署靜態頁面、而不在 CI
            裡即時呼叫 LLM，以避免金鑰管理風險與 workflow 不穩定）。</li>
        <li>撰寫 Pydantic 結構化輸出 schema（<code>schema.py</code>）與呼叫 Ollama
            的程式（<code>llm_client.py</code>），包含格式驗證失敗時的重試邏輯。</li>
        <li>撰寫 CLI 介面、範例筆記資料、這個作品頁的產生器（<code>scripts/build_site.py</code>）、
            以及 GitHub Actions 的部署 workflow。</li>
      </ul>
      <p><strong>自己做了什麼修改／驗證：</strong></p>
      <ul>
        <li>實際安裝並啟動自己電腦上的 Ollama，用 <code>run-all</code> 真的跑過全部
            三份範例筆記，確認輸出的 JSON 欄位（標題／摘要／重點／待辦事項）
            內容合理，沒有看起來像是模型亂編的待辦事項。</li>
        <li>跑過 <code>pytest</code> 測試（不需連線 Ollama，用假資料驗證 schema 與
            作品頁產生邏輯），確認程式邏輯正確。</li>
        <li>確認 <code>.env</code> 有被 <code>.gitignore</code> 排除，commit 歷史裡沒有任何金鑰
            或機密資訊。</li>
      </ul>
    </div>
  </section>

  <footer>
    頁面產生時間：{generated_at} ｜ 由 <code>scripts/build_site.py</code> 自動產生
  </footer>
</div>
</body>
</html>
"""


def main() -> None:
    records = load_results()
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DOCS_DIR / "index.html"
    out_path.write_text(render_page(records), encoding="utf-8")
    # GitHub Pages 用的保險設定：避免 Jekyll 處理底線開頭的檔案
    (DOCS_DIR / ".nojekyll").touch()
    print(f"已產生 {out_path}（讀到 {len(records)} 份執行結果）")


if __name__ == "__main__":
    main()
