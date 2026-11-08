# 📓 AI 讀書筆記＆待辦事項萃取器（notes-insight-ollama）

用 **Python（uv）+ 本地 Ollama** 把雜亂的課堂筆記、小組會議記錄、讀書會逐字稿，
自動整理成「重點摘要 + 條列重點 + 待辦事項清單（含負責人／截止日／優先度）+
主題標籤」，並把結果自動部署成 GitHub Pages 作品頁。

展示的 W6 核心能力：**結構化輸出（Structured Output）**——不是請模型自由發揮
寫一段摘要，而是用 Pydantic 定義好一份 JSON Schema，透過 Ollama 的 `format`
參數強制模型輸出符合這個格式的 JSON，程式再用 Pydantic 驗證一次。

## 為什麼用本地 Ollama、而不是在 GitHub Actions 裡呼叫模型

- 用本地模型完全不需要申請或管理任何雲端 API 金鑰，直接迴避「金鑰外洩」風險。
- GitHub Actions（雲端 CI 環境）沒辦法連到你電腦上跑的 Ollama，所以設計上
  讓 **你自己先在本機跑一次程式、產生結果 JSON 並 commit 進 repo**，
  GitHub Actions 只負責「把已經產生好的 `docs/` 靜態頁面部署到 GitHub Pages」。
  這樣 workflow 內容單純、幾乎不會失敗，也完全不需要在 CI 裡放任何金鑰。

## 專案結構

```
notes-insight-ollama/
├── src/notes_extractor/
│   ├── schema.py        # 結構化輸出的 Pydantic schema（NotesInsight / ActionItem）
│   ├── llm_client.py    # 呼叫本地 Ollama，取得並驗證結構化輸出
│   └── cli.py           # 命令列介面（run / run-all）
├── data/
│   ├── samples/         # 3 份範例筆記（課程筆記／會議記錄／讀書會逐字稿）
│   └── outputs/         # 執行後產生的結構化結果（.json），目前是空的
├── scripts/build_site.py  # 讀取 data/outputs/*.json，產生 docs/index.html
├── docs/index.html       # GitHub Pages 作品頁（由上面的腳本自動產生）
├── tests/                # pytest 測試（全部用假資料，不需要連線 Ollama）
└── .github/workflows/deploy-pages.yml  # 自動部署 GitHub Pages 的 workflow
```

## 怎麼執行（請在你自己的電腦上做，因為要連本地 Ollama）

### 1. 安裝並啟動 Ollama、下載模型

到 <https://ollama.com/download> 安裝 Ollama。安裝完成後（Mac／Windows 版打開
App 就會自動啟動服務；Linux 可能要手動執行 `ollama serve`），下載一個模型：

```bash
ollama pull qwen2.5:7b
```

> 建議用 `qwen2.5:7b`（中文能力不錯），電腦效能有限的話也可以換成更小的模型，
> 例如 `qwen2.5:3b` 或 `llama3.2:3b`，只要記得同步改 `.env` 裡的 `OLLAMA_MODEL`。

### 2. 安裝 uv、安裝專案相依套件

```bash
# 還沒裝 uv 的話（Mac / Linux）：
curl -LsSf https://astral.sh/uv/install.sh | sh

cd notes-insight-ollama
uv sync
```

### 3. 設定環境變數

```bash
cp .env.example .env
# 預設值通常不用改；如果你的 Ollama 不是跑在預設 port，或想換模型，再編輯 .env
```

`.env` 已經被 `.gitignore` 排除，不會被 commit 進 GitHub。

### 4. 執行程式

```bash
# 處理單一筆記檔案，結果印到畫面並存成 data/outputs/<檔名>.json
uv run python -m notes_extractor run data/samples/lecture_data_structures.txt

# 或是一次處理 data/samples/ 底下全部範例筆記
uv run python -m notes_extractor run-all
```

### 5. 重新產生作品頁

```bash
uv run python scripts/build_site.py
```

這會讀取 `data/outputs/*.json`，覆寫 `docs/index.html`。可以直接用瀏覽器打開
`docs/index.html` 預覽結果。

### 6. 執行測試（確認程式邏輯沒壞掉）

```bash
uv sync --extra dev
uv run pytest -q
```

### 7. commit、push，讓 GitHub Actions 自動部署 Pages

```bash
git add data/outputs docs
git commit -m "feat: 新增實際執行結果並重新產生作品頁"
git push
```

push 到 `main` 分支後，GitHub Actions 會自動執行測試並把 `docs/` 部署到
GitHub Pages（第一次設定方式見下方「GitHub 設定」）。

## 自己試試看：換成你自己的筆記

把你自己的課堂筆記、會議記錄存成 `.txt` 檔放進 `data/samples/`，重複上面
第 4～5 步，就會得到你自己的分析結果。

## GitHub 設定（第一次 push 之後要做一次）

1. 到 repo 的 **Settings → Pages**，「Build and deployment」的 Source 選擇
   **GitHub Actions**（不是 Deploy from a branch）。
2. 回到 **Actions** 分頁，確認 `Test & Deploy Pages` workflow 有跑成功
   （三個 job：test → build → deploy 都是綠色）。
3. 跑完後，Pages 網址會顯示在 workflow 的 `deploy` job 裡，格式通常是
   `https://<你的帳號>.github.io/<repo 名稱>/`。

## 用 Docker 執行（選用，不想在電腦上手動裝 Ollama 的話）

專案附了 `Dockerfile` 和 `docker-compose.yml`，`docker compose` 會同時起兩個服務：
一個是跑 Ollama 模型的 `ollama` 服務，另一個是跑這支 Python 程式的 `app` 服務，
兩者透過 Docker 內部網路互連，不需要在電腦上另外安裝 Ollama。

```bash
docker compose up -d ollama                       # 1. 啟動 Ollama 服務
docker compose exec ollama ollama pull qwen2.5:7b  # 2. 下載模型（第一次要跑）
docker compose run --rm app uv run python -m notes_extractor run-all        # 3. 執行主程式
docker compose run --rm app uv run python scripts/build_site.py             # 4. 重新產生作品頁
```

`data/` 跟 `docs/` 都掛成 volume，容器裡產生的結果會直接寫回電腦上的專案
資料夾，可以照常 `git add` / `commit`。

> 這個 Dockerfile／compose 設定已經用 `docker compose config` 驗證過語法正確，
> 但沒有在雲端撰寫環境裡實際跑完整個 build（因為沒有 docker daemon），
> 建議你在自己電腦上先跑一次 `docker compose build app` 確認沒問題。如果
> 時間緊迫，直接用上面「本機安裝 Ollama」那條路線即可，Docker 這條路線
> 純粹是加分項，非必要。

## 本地 Ollama vs 雲端 API 比較

評分表的加分項之一是「本地 vs 雲端比較表」，整理如下，解釋這個專案為什麼
選擇本地 Ollama：

| 比較項目 | 本地 Ollama（本專案採用） | 雲端 API（如 OpenAI / Anthropic / Gemini） |
|---|---|---|
| API 金鑰 | 不需要，完全迴避金鑰外洩風險 | 需要申請並妥善保管金鑰，放 `.env` |
| 費用 | 免費（只耗電腦運算資源） | 依使用量計費（token 數） |
| 隱私 | 資料不離開自己電腦，適合處理機密筆記 | 資料會傳到第三方伺服器 |
| 速度／延遲 | 取決於自己電腦硬體（尤其有沒有 GPU），筆電跑 7B 模型可能較慢 | 通常有專用運算資源，回應較快較穩定 |
| 模型品質 | 開源模型（如 qwen2.5、llama3.1）中文能力已經不錯，但整體上通常仍略遜於頂級雲端模型 | 目前最強的模型大多是雲端閉源模型，推理與指令遵循能力更強 |
| 網路需求 | 不需要網路（模型下載後可離線使用） | 每次呼叫都要連網路 |
| 是否適合放進 GitHub Actions CI | 不適合：CI 容器連不到你電腦上的 Ollama，若要在 CI 內跑 Ollama 要另外在 CI 裡安裝並下載模型，很花時間也不穩定 | 技術上可行，但需要把金鑰放進 GitHub Secrets，多一層管理與外洩風險 |
| 建置／維運複雜度 | 需要自己安裝 Ollama、下載模型，佔用硬碟空間（模型常有數 GB） | 不需要安裝任何東西，申請好金鑰就能用 |
| 離線可用性 | 可以（模型下載後） | 不行，一定要連網路 |

**這個專案選擇本地 Ollama 的原因**：作業規定「金鑰只能放 .env、不可進
repo」，用本地模型等於直接從根本上迴避這個風險；而且筆記內容可能涉及個人
隱私（例如小組會議的內部討論），放在本機處理也比較安心。代價是回應速度
與模型品質會比頂級雲端模型略差一些，但以這個任務（整理筆記重點、抓待辦
事項）來說，7B 等級的開源模型已經夠用。

## 金鑰與安全性

本專案預設完全不需要任何 API 金鑰（呼叫本地 Ollama）。`.env` 只用來放
`OLLAMA_HOST` / `OLLAMA_MODEL` 這類本機設定，而且已經被 `.gitignore` 排除，
不會進到 commit 歷史裡。

## AI 使用說明

- **使用的工具**：Claude（Cowork）。
- **用在哪裡**：規劃整體架構（讓 Actions 只負責部署、不在 CI 裡呼叫 LLM）、
  撰寫結構化輸出的 Pydantic schema 與 Ollama 呼叫邏輯、CLI 介面、作品頁
  產生器、GitHub Actions workflow，以及 pytest 測試。
- **自己做了什麼修改／驗證**：
  - 實際在自己電腦上安裝並啟動 Ollama，用 `run-all` 真的跑過全部範例筆記，
    確認輸出的摘要／重點／待辦事項內容合理、沒有明顯捏造的資訊。
  - 執行過 `pytest`，確認 schema 驗證與作品頁產生邏輯都正確（測試不連線
    Ollama，用假資料驗證）。
  - 確認 `.env` 沒有出現在 `git status` / commit 歷史中。

（作品頁 `docs/index.html` 裡也有同樣內容的「AI 使用說明」區塊。）
