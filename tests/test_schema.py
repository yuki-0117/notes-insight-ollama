"""測試結構化輸出的 schema 本身是否正確（不需要連線 Ollama）。"""

from notes_extractor.schema import ActionItem, NotesInsight


def test_action_item_default_priority_is_medium():
    item = ActionItem(task="寫完 hw4")
    assert item.priority == "medium"
    assert item.owner is None
    assert item.deadline is None


def test_notes_insight_round_trip():
    payload = {
        "title": "資結第九週筆記",
        "summary": "複習雜湊表與紅黑樹，並公布 hw4 繳交期限。",
        "key_points": ["雜湊表平均 O(1)，最壞 O(n)", "紅黑樹靠旋轉維持平衡"],
        "action_items": [
            {
                "task": "繳交 hw4",
                "owner": None,
                "deadline": "11/14 23:59",
                "priority": "high",
            }
        ],
        "topics": ["資料結構", "雜湊表", "紅黑樹"],
    }
    insight = NotesInsight.model_validate(payload)
    assert insight.title == "資結第九週筆記"
    assert len(insight.action_items) == 1
    assert insight.action_items[0].priority == "high"
    # 確保 round-trip 回 dict 不會遺漏欄位
    dumped = insight.model_dump()
    assert dumped["topics"] == ["資料結構", "雜湊表", "紅黑樹"]


def test_json_schema_for_ollama_has_required_fields():
    schema = NotesInsight.json_schema_for_ollama()
    assert schema["type"] == "object"
    assert "title" in schema["properties"]
    assert "action_items" in schema["properties"]
