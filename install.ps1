python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
python scripts/fetch_model.py --output models/TinyLlama-1.1B-Chat-q4_k_m.gguf
