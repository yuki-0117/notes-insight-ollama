"""定義 LLM 必須回傳的結構化輸出格式。

這是本專案展示的 W6 核心能力：「結構化輸出 (Structured Output)」。
我們不會請模型「自由發揮寫一段摘要」，而是給它一個明確的 JSON Schema
（由這幾個 Pydantic model 自動產生），模型的回覆會被強制符合這個格式，
程式再用 Pydantic 驗證一次，確保欄位型別、必填項目都正確。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Priority = Literal["high", "medium", "low"]


class ActionItem(BaseModel):
    """一個待辦事項。"""

    task: str = Field(..., description="待辦事項的具體內容，例如「完成第三章習題」")
    owner: str | None = Field(
        default=None,
        description=(
            "負責人姓名或代稱。只要原文中有人名跟這個待辦事項寫在一起"
            "（例如「OOO 負責」「OOO 要做」），務必填入這裡，不要留空；"
            "完全沒提到負責人才填 null"
        ),
    )
    deadline: str | None = Field(
        default=None,
        description=(
            "截止日期或時間，照原文寫法填即可（例如「這週五前」「11/14」）；"
            "完全沒提到才填 null"
        ),
    )
    priority: Priority = Field(
        default="medium", description="優先度：high / medium / low"
    )


class NotesInsight(BaseModel):
    """一份筆記被 LLM 整理後的完整結構化結果。"""

    title: str = Field(..., description="這份筆記的主題標題，15 個字以內")
    summary: str = Field(..., description="2 到 4 句話的重點摘要")
    key_points: list[str] = Field(
        ..., min_length=1, description="條列式重點，3 到 6 點"
    )
    action_items: list[ActionItem] = Field(
        default_factory=list, description="從筆記中萃取出的待辦事項；若沒有則為空陣列"
    )
    topics: list[str] = Field(
        default_factory=list, description="1 到 5 個關鍵主題標籤"
    )

    @classmethod
    def json_schema_for_ollama(cls) -> dict:
        """回傳給 Ollama `format` 參數使用的 JSON Schema。"""
        return cls.model_json_schema()
