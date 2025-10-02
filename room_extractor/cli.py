import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

import yaml

from .llm import LocalLLM
from .pdf_processing import extract_pdf_pages
from .postprocess import build_mindmap_html, normalise_item


CATEGORY_MAP = {
    "FLOOR": "Floor",
    "WALL": "Walls",
    "WALLS": "Walls",
    "CEILING": "Ceiling",
    "FURNITURE": "Furniture",
    "CASEWORK": "Furniture",
    "EQUIPMENT": "Furniture",
}


@dataclass
class Config:
    pdf_dir: Path
    rooms: List[str]
    model_path: Path
    output_dir: Path
    max_pages: Optional[int] = None
    temperature: float = 0.1
    top_p: float = 0.15
    ctx_size: int = 2048
    n_threads: Optional[int] = None
    n_gpu_layers: int = 0

    @staticmethod
    def from_args() -> "Config":
        parser = argparse.ArgumentParser(description="Extract finishes and furniture data from architectural PDFs.")
        parser.add_argument("--config", type=Path, help="Path to YAML configuration file.")
        parser.add_argument("--rooms", nargs="*", help="Override rooms defined in the config file.")
        parser.add_argument("--pdf-dir", type=Path, help="Override PDF directory.", dest="pdf_dir")
        parser.add_argument("--model-path", type=Path, help="Override local GGUF model path.", dest="model_path")
        parser.add_argument("--output-dir", type=Path, help="Override output directory.", dest="output_dir")
        parser.add_argument("--max-pages", type=int, help="Maximum pages to read per PDF.")
        args = parser.parse_args()

        if not args.config:
            raise SystemExit("Configuration file (--config) is required.")
        with args.config.open("r", encoding="utf-8") as fh:
            payload = yaml.safe_load(fh) or {}

        def _override(key, attr=None):
            value = getattr(args, attr or key, None)
            if value is not None:
                payload[key] = value

        _override("pdf_dir")
        _override("model_path")
        _override("output_dir")
        if args.rooms:
            payload["rooms"] = args.rooms
        if args.max_pages is not None:
            payload["max_pages"] = args.max_pages

        missing = [k for k in ("pdf_dir", "rooms", "model_path", "output_dir") if k not in payload]
        if missing:
            raise SystemExit(f"Missing configuration values: {', '.join(missing)}")

        return Config(
            pdf_dir=Path(payload["pdf_dir"]).expanduser().resolve(),
            rooms=[str(r) for r in payload.get("rooms", [])],
            model_path=Path(payload["model_path"]).expanduser().resolve(),
            output_dir=Path(payload["output_dir"]).expanduser().resolve(),
            max_pages=payload.get("max_pages"),
            temperature=float(payload.get("temperature", 0.1)),
            top_p=float(payload.get("top_p", 0.15)),
            ctx_size=int(payload.get("ctx_size", 2048)),
            n_threads=payload.get("n_threads"),
            n_gpu_layers=int(payload.get("n_gpu_layers", 0)),
        )


def run(config: Config) -> None:
    config.output_dir.mkdir(parents=True, exist_ok=True)

    llm = LocalLLM(
        model_path=config.model_path,
        temperature=config.temperature,
        top_p=config.top_p,
        ctx_size=config.ctx_size,
        n_threads=config.n_threads,
        n_gpu_layers=config.n_gpu_layers,
    )

    room_data, stats = collect_room_data(
        rooms=config.rooms,
        pages=extract_pdf_pages(config.pdf_dir, config.max_pages),
        llm=llm,
    )

    if not any(room_data[room][category] for room in room_data for category in room_data[room]):
        print("No qualifying items were found for the requested rooms.")

    yaml_path = config.output_dir / "room_inventory.yaml"
    with yaml_path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(format_yaml_payload(room_data), fh, sort_keys=False, allow_unicode=True)

    html_path = config.output_dir / "room_inventory.html"
    html_content = build_mindmap_html(room_data)
    html_path.write_text(html_content, encoding="utf-8")

    print(f"Processed {stats['pages_total']} pages across {stats['pdf_count']} PDFs.")
    print(f"Pages mentioning target rooms: {stats['pages_with_hits']}.")
    print(f"YAML saved to {yaml_path}")
    print(f"Mind map saved to {html_path}")


def collect_room_data(
    *,
    rooms: Iterable[str],
    pages: Iterable[Tuple[Path, int, str]],
    llm: LocalLLM,
) -> Tuple[Dict[str, Dict[str, Dict[Tuple[str, str], Dict[str, Set[str]]]]], Dict[str, int]]:
    rooms = list(rooms)
    room_data: Dict[str, Dict[str, Dict[Tuple[str, str], Dict[str, Set[str]]]]] = {
        room: {"Floor": {}, "Walls": {}, "Ceiling": {}, "Furniture": {}} for room in rooms
    }
    stats = {"pages_total": 0, "pages_with_hits": 0, "pdf_count": 0}
    current_pdf: Optional[Path] = None

    for pdf_path, page_number, text in pages:
        if current_pdf != pdf_path:
            stats["pdf_count"] += 1
            current_pdf = pdf_path
        stats["pages_total"] += 1
        if not text:
            continue
        text_lower = text.lower()
        page_had_room = False
        for room in rooms:
            if room.lower() not in text_lower:
                continue
            page_had_room = True
            for raw in llm.extract_items(room, text):
                category_key = CATEGORY_MAP.get(raw.category.upper())
                if not category_key:
                    continue
                cleaned = normalise_item(text, raw)
                if not cleaned:
                    continue
                item_code, description = cleaned
                key = (item_code, raw.url)
                bucket = room_data[room][category_key]
                record = bucket.setdefault(key, {"description": description, "sources": set()})
                detail_suffix = f"; {raw.detail}" if raw.detail else ""
                record["sources"].add(f"{pdf_path.name} p.{page_number}{detail_suffix}")
        if page_had_room:
            stats["pages_with_hits"] += 1

    return room_data, stats


def format_yaml_payload(room_data):
    payload = {}
    for room, categories in room_data.items():
        payload[room] = {}
        for category, items in categories.items():
            entries = []
            for (item_code, url), record in sorted(items.items(), key=lambda x: x[0][0]):
                sources = sorted(record["sources"])
                source_text = ", ".join(sources)
                entries.append(f"{item_code} → {record['description']} → {source_text} → {url}")
            if entries:
                payload[room][category] = entries
    return payload


if __name__ == "__main__":
    cfg = Config.from_args()
    run(cfg)
