"""命令列介面：

    uv run python -m notes_extractor run data/samples/lecture_data_structures.txt
    uv run python -m notes_extractor run-all

`run`     ：處理單一筆記檔案，結果印到畫面上，並存成 data/outputs/<檔名>.json
`run-all` ：處理 data/samples/ 底下所有 .txt 檔案
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from .llm_client import NotesExtractor, OllamaUnavailableError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SAMPLES_DIR = PROJECT_ROOT / "data" / "samples"
DEFAULT_OUTPUTS_DIR = PROJECT_ROOT / "data" / "outputs"


def _process_one(input_path: Path, output_dir: Path, extractor: NotesExtractor) -> Path:
    raw_text = input_path.read_text(encoding="utf-8")
    print(f"[處理中] {input_path.name} ...")
    insight = extractor.extract(raw_text)

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{input_path.stem}.json"

    record = {
        "source_file": input_path.name,
        "raw_text": raw_text,
        "insight": insight.model_dump(),
    }
    output_path.write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[完成] 已寫入 {output_path.relative_to(PROJECT_ROOT)}")
    print(json.dumps(insight.model_dump(), ensure_ascii=False, indent=2))
    return output_path


def cmd_run(args: argparse.Namespace) -> int:
    extractor = NotesExtractor()
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"找不到檔案：{input_path}", file=sys.stderr)
        return 1
    try:
        _process_one(input_path, Path(args.output_dir), extractor)
    except OllamaUnavailableError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


def cmd_run_all(args: argparse.Namespace) -> int:
    extractor = NotesExtractor()
    samples_dir = Path(args.samples_dir)
    txt_files = sorted(samples_dir.glob("*.txt"))
    if not txt_files:
        print(f"在 {samples_dir} 底下找不到任何 .txt 檔案", file=sys.stderr)
        return 1

    failures = 0
    for input_path in txt_files:
        try:
            _process_one(input_path, Path(args.output_dir), extractor)
        except OllamaUnavailableError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        except Exception as exc:  # noqa: BLE001 - CLI 層級想攔住所有例外繼續跑下一份
            print(f"[失敗] {input_path.name}: {exc}", file=sys.stderr)
            failures += 1
    return 1 if failures else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="notes_extractor",
        description="用本地 Ollama 模型，把筆記/會議記錄整理成結構化摘要與待辦事項",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="處理單一筆記檔案")
    p_run.add_argument("input_file", help="筆記的 .txt 檔案路徑")
    p_run.add_argument(
        "--output-dir", default=str(DEFAULT_OUTPUTS_DIR), help="結果輸出資料夾"
    )
    p_run.set_defaults(func=cmd_run)

    p_all = sub.add_parser("run-all", help="處理 data/samples 底下所有筆記")
    p_all.add_argument(
        "--samples-dir", default=str(DEFAULT_SAMPLES_DIR), help="範例筆記資料夾"
    )
    p_all.add_argument(
        "--output-dir", default=str(DEFAULT_OUTPUTS_DIR), help="結果輸出資料夾"
    )
    p_all.set_defaults(func=cmd_run_all)

    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv()  # 讀取 .env（若存在）
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
