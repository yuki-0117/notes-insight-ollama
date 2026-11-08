"""測試作品頁產生器（scripts/build_site.py），全程不連線 Ollama，只用假資料。"""

import json

import build_site


def write_fake_record(outputs_dir, name, *, title="假標題", task="<script>壞人</script>"):
    outputs_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "source_file": f"{name}.txt",
        "raw_text": "這是一段原始筆記內容",
        "insight": {
            "title": title,
            "summary": "這是摘要",
            "key_points": ["重點一", "重點二"],
            "action_items": [
                {"task": task, "owner": "小明", "deadline": "11/20", "priority": "high"}
            ],
            "topics": ["測試標籤"],
        },
    }
    (outputs_dir / f"{name}.json").write_text(
        json.dumps(record, ensure_ascii=False), encoding="utf-8"
    )


def test_empty_state_shown_when_no_outputs(tmp_path, monkeypatch):
    monkeypatch.setattr(build_site, "OUTPUTS_DIR", tmp_path / "outputs")
    html_out = build_site.render_page(build_site.load_results())
    assert "目前還沒有執行結果" in html_out


def test_render_page_includes_result_and_escapes_html(tmp_path, monkeypatch):
    outputs_dir = tmp_path / "outputs"
    monkeypatch.setattr(build_site, "OUTPUTS_DIR", outputs_dir)
    write_fake_record(outputs_dir, "sample1", title="假標題")

    records = build_site.load_results()
    assert len(records) == 1

    html_out = build_site.render_page(records)
    assert "假標題" in html_out
    assert "小明" in html_out
    # 確保原始文字裡的 <script> 有被跳脫，不會變成真正的 HTML 標籤
    assert "<script>壞人</script>" not in html_out
    assert "&lt;script&gt;" in html_out


def test_main_writes_index_html_and_nojekyll(tmp_path, monkeypatch):
    outputs_dir = tmp_path / "outputs"
    docs_dir = tmp_path / "docs"
    monkeypatch.setattr(build_site, "OUTPUTS_DIR", outputs_dir)
    monkeypatch.setattr(build_site, "DOCS_DIR", docs_dir)
    write_fake_record(outputs_dir, "sample1")

    build_site.main()

    assert (docs_dir / "index.html").exists()
    assert (docs_dir / ".nojekyll").exists()
