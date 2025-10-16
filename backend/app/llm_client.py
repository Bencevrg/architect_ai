import os
import json
from typing import Optional
from dotenv import load_dotenv
from openai import OpenAI

# --- .env betöltése ---
load_dotenv()

# --- OpenAI API kulcs ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError(
        "Az OpenAI API kulcs nincs beállítva! "
        "Helyezd el a .env fájlban: OPENAI_API_KEY=ide_illeszd_be_a_kulcsot"
    )

# --- OpenAI kliens inicializálása ---
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_or_modify_structure(prompt: str, current_structure: Optional[dict] = None) -> dict:
    """
    1️⃣ Ha nincs meglévő struktúra: teljes tervrajz generálása a promptból
    2️⃣ Ha van meglévő struktúra: frissíti azt a prompt alapján
    3️⃣ Mindig érvényes JSON-t ad vissza
    """
    system_prompt = """
    You are an AI architect.
    You are given a house description or modification instruction.
    You must return ONLY valid JSON with the following structure:
    - rooms: list of {name, x, y, w, h}  # bármilyen geometria
    - doors: list of {x, y, width, angle, swing_direction}
    - windows: list of {x, y, width}
    - metadata: {area, units}
    Rules:
    1. If current design is provided, modify it according to the instruction.
    2. If data is missing, generate plausible values logically.
    3. Do not delete existing elements unless explicitly instructed.
    4. Coordinates should be consistent and realistic.
    5. Return coordinates and dimensions in meters.
    """

    user_prompt = prompt
    if current_structure:
        user_prompt = (
            f"Modify the existing building structure according to this instruction:\n{prompt}\n\n"
            f"Existing structure:\n{json.dumps(current_structure)}"
        )

    # --- Chat completion kérés ---
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.3,
        max_tokens=2000,
    )

    content = response.choices[0].message.content.strip()

    try:
        data = json.loads(content)
        return data
    except json.JSONDecodeError:
        # Hibakezelés: ha nem valid JSON jött
        print("AI JSON parse error, content (preview):", content[:500])
        raise ValueError("Hibás JSON az AI-tól. Ellenőrizd a promptot vagy próbáld újra.")
