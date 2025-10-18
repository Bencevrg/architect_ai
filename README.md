# Architect AI – MVP (OpenAI nélkül)


## 0) Előfeltételek
- Python 3.10+
- pip, virtualenv


## 1) Backend telepítés és futtatás
```bash
cd backend
python -m venv .venv
source .venv/bin/activate # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000