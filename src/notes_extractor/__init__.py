"""notes_extractor

把一段原始筆記/會議記錄/讀書會逐字稿，丟給本地 Ollama 模型，
請模型用「結構化輸出」回傳固定格式的 JSON（重點摘要、條列重點、
待辦事項、主題標籤），而不是自由發揮的一大段文字。
"""

from .schema import ActionItem, NotesInsight

__all__ = ["ActionItem", "NotesInsight"]
