"""呼叫本地 Ollama，並用結構化輸出 (structured output) 取得固定格式的結果。

為什麼用本地 Ollama 而不是雲端 API：
- 不需要申請/管理任何 API 金鑰，完全不用擔心金鑰外洩的問題。
- 作業規定「金鑰只能放 .env、不可進 repo」，用本地模型等於直接迴避了這個風險。

結構化輸出的作法：
- 把 Pydantic model（schema.py 裡的 NotesInsight）轉成 JSON Schema，
  傳給 Ollama 的 `format` 參數。Ollama 會強制模型輸出符合這個 schema 的 JSON
  （這是 Ollama 0.5+ 內建的 structured outputs 功能，不是用 prompt「拜託」模型而已）。
- 拿到回覆後，再用 Pydantic 驗證一次，若驗證失敗會重試一次（模型偶爾還是會回傳
  不完全合法的 JSON，例如漏填必填欄位）。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

from pydantic import ValidationError

from .schema import NotesInsight

try:
    import ollama
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "找不到 ollama 套件，請先執行 `uv sync` 安裝相依套件"
    ) from exc


SYSTEM_PROMPT = """你是一位細心的筆記整理助理。
使用者會給你一段筆記、會議記錄或讀書會逐字稿（可能是中文、英文或中英混合）。
請你：
1. 幫它下一個簡短的標題。
2. 用 2 到 4 句話寫出重點摘要。
3. 條列出 3 到 6 個重點。
4. 找出筆記中提到的所有待辦事項／行動項目。**owner（負責人）欄位請特別仔細處理**：
   只要原文中「人名／代稱」跟「負責、要做、要完成、要整理、要交」等字眼出現在同一句
   或同一個待辦事項描述附近，就一定要把那個人名／代稱填進 owner，不可以留空；
   只有在整段筆記完全沒有提到任何負責人時，owner 才留 null。deadline 的判斷方式
   相同：原文有寫到日期、星期幾、「這週X前」之類的描述就要填，用筆記中原本的寫法
   即可，不用自己換算成絕對日期。如果整段筆記完全沒有提到待辦事項，action_items
   回傳空陣列即可，不要自己憑空捏造任務、負責人或日期。
5. 列出 1 到 5 個關鍵主題標籤。

範例（只是示範格式，不是真的筆記內容）：
輸入：「小明說他這週五前要把簡報做完，小華負責找資料。」
這應該產生兩個 action_items：
  - {"task": "把簡報做完", "owner": "小明", "deadline": "這週五前", "priority": "medium"}
  - {"task": "找資料", "owner": "小華", "deadline": null, "priority": "medium"}

請務必只用繁體中文回覆文字內容（title / summary / key_points / task 等欄位），
並嚴格依照要求的 JSON 格式輸出，不要加任何 JSON 以外的文字。"""


class OllamaUnavailableError(RuntimeError):
    """當本地 Ollama 服務無法連線時拋出。"""


@dataclass
class NotesExtractorConfig:
    host: str
    model: str
    timeout: float

    @classmethod
    def from_env(cls) -> "NotesExtractorConfig":
        return cls(
            host=os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
            model=os.environ.get("OLLAMA_MODEL", "qwen2.5:7b"),
            timeout=float(os.environ.get("OLLAMA_TIMEOUT", "120")),
        )


class NotesExtractor:
    """把一段原始筆記轉成結構化的 NotesInsight。"""

    def __init__(self, config: NotesExtractorConfig | None = None) -> None:
        self.config = config or NotesExtractorConfig.from_env()
        self._client = ollama.Client(host=self.config.host, timeout=self.config.timeout)

    def extract(self, raw_text: str, *, max_retries: int = 1) -> NotesInsight:
        """呼叫本地 Ollama，回傳驗證過的 NotesInsight。

        max_retries: 當模型回傳的 JSON 沒通過 Pydantic 驗證時，
        最多再重試幾次（並在第二次提示中附上錯誤訊息，請模型修正）。
        """
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": raw_text},
        ]

        last_error: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                response = self._client.chat(
                    model=self.config.model,
                    messages=messages,
                    format=NotesInsight.json_schema_for_ollama(),
                    options={"temperature": 0.2},
                )
            except Exception as exc:  # 連不到 Ollama、模型不存在等等
                raise OllamaUnavailableError(
                    f"呼叫本地 Ollama 失敗（host={self.config.host}, "
                    f"model={self.config.model}）：{exc}\n"
                    "請確認：1) 已執行 `ollama serve`（或 Ollama App 正在執行中）"
                    f" 2) 已用 `ollama pull {self.config.model}` 下載過這個模型"
                ) from exc

            content = response["message"]["content"]
            try:
                data = json.loads(content)
                return NotesInsight.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as exc:
                last_error = exc
                messages.append({"role": "assistant", "content": content})
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "你剛剛的回覆沒有通過格式驗證，錯誤訊息如下，"
                            f"請修正後重新輸出完整的 JSON：\n{exc}"
                        ),
                    }
                )

        raise ValueError(f"模型回覆經過 {max_retries + 1} 次嘗試仍無法通過格式驗證：{last_error}")
