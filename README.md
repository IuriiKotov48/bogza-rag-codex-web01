# Room Inventory Extractor

A minimal local workflow for scanning architectural drawing PDFs, extracting finish and furniture references for specific rooms, and producing both a YAML schedule and an interactive mind-map.

## Highlights

- Works entirely offline with a quantised TinyLlama local model.
- Handles batches of 10–100 PDFs with automatic text extraction and OCR fallback (Tesseract).
- Produces a clean YAML file (`room_inventory.yaml`) and an interactive HTML mind-map (`room_inventory.html`).
- Designed for Windows 10/11 or Linux with 16 GB RAM.
- One-command install, one-command run.

## Prerequisites

- Python 3.10+
- Tesseract OCR (optional but recommended for scanned drawings).
  - Windows: install from [UB Mannheim builds](https://github.com/UB-Mannheim/tesseract/wiki).
  - Linux: `sudo apt-get install tesseract-ocr`.

## Quick start

```bash
# 1. Install dependencies and download the default TinyLlama model
./install.sh

# 2. Copy and edit the configuration
cp config.example.yaml config.yaml
# Edit pdf_dir, rooms, and output_dir to match your project

# 3. Run the extractor
./run.sh
```

On Windows PowerShell use:

```powershell
# Install
./install.ps1
# Run
./run.ps1
```

Both scripts accept the same optional CLI overrides exposed by `python -m room_extractor`. Example:

```bash
./run.sh --rooms "Room 101" "Room 203" --max-pages 10
```

## Configuration (`config.yaml`)

| Key | Description |
| --- | --- |
| `pdf_dir` | Folder containing 10–100 PDF drawing files. Subdirectories are scanned automatically. |
| `rooms` | List of room names to analyse. You can re-run the pipeline with a different list at any time. |
| `model_path` | Path to a local GGUF model (default TinyLlama chat model). |
| `output_dir` | Folder where YAML/HTML artefacts are written. |
| `max_pages` | Optional limit of pages per PDF for faster debugging. |
| `ctx_size`, `temperature`, `top_p`, `n_threads`, `n_gpu_layers` | Advanced knobs for llama.cpp runtime. |

## Outputs

- `room_inventory.yaml`: Structured data ready for Excel/Notion with four categories (Floor, Walls, Ceiling, Furniture). Each line follows `item-code → description → PDF source → product URL`.
- `room_inventory.html`: Interactive mind-map. Each room renders as a central node with four radial branches (Floor, Walls, Ceiling, Furniture). Click a branch to reveal its leaves and hover over any leaf to see the description, drawing references, and product URL.
- Console output summarises how many PDFs and pages were processed plus how many pages actually referenced the requested rooms.

## How it works

1. **Text capture** – Vector text is extracted via `pdfplumber`. Low-text pages automatically fall back to OCR with `pytesseract`.
2. **LLM extraction** – A TinyLlama chat model (through `llama_cpp`) reviews every page that mentions one of the target rooms. The model outputs only verifiable items that include a product URL.
3. **Validation & aggregation** – Items are cross-checked against the original page text, grouped by room/category, and de-duplicated while retaining all referenced pages/details.
4. **Reporting** – YAML is emitted for downstream tools. The HTML mind-map renders a radial diagram per room with hoverable leaves. Both artefacts are generated locally with no external dependencies.

## Extending

- Swap the model by editing `config.yaml` with a different GGUF checkpoint.
- Adjust prompt logic in `room_extractor/llm.py` or post-processing in `room_extractor/postprocess.py` to fit project-specific coding standards.
- Add alternative OCR or vector parsing by modifying `room_extractor/pdf_processing.py`.

## Troubleshooting

- If OCR is missing, install Tesseract and ensure it is in your system PATH.
- To inspect raw model output, temporarily insert a `print()` inside `LocalLLM.extract_items`.
- For GPU acceleration set `n_gpu_layers` in `config.yaml` (requires llama-cpp built with CUDA/Metal).

## License

This project is released under the MIT license.
