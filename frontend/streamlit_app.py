import streamlit as st
import requests
import json

API_URL = "http://127.0.0.1:8000"  # Backend URL

st.set_page_config(page_title="Architect AI - DXF Generator", layout="wide")
st.title("Architect AI - DXF Generator")

# --- Session állapot a tervrajzhoz ---
if 'current_structure' not in st.session_state:
    st.session_state['current_structure'] = None

# --- Szöveges prompt ---
st.subheader("Ház leírása vagy módosítás")
prompt = st.text_area(
    "Írd le a ház alaprajzát, vagy adj módosítást a meglévő tervrajzra",
    height=120
)

# --- Képfeltöltés ---
st.subheader("Vázlat feltöltése (opcionális)")
uploaded_file = st.file_uploader("Tölts fel egy PNG képet", type=["png"])

# --- DXF generálása / módosítás ---
if st.button("DXF generálása / módosítás"):
    if not prompt and not uploaded_file:
        st.error("Adj meg promptot vagy tölts fel képet!")
    else:
        payload = {"prompt": prompt}

        if st.session_state['current_structure']:
            payload["current_structure"] = st.session_state['current_structure']

        try:
            # Ha van feltöltött kép, először OCR + AI pipeline
            if uploaded_file:
                files = {"file": (uploaded_file.name, uploaded_file, "image/png")}
                r = requests.post(f"{API_URL}/image-to-dxf", files=files)
                r.raise_for_status()
                image_result = r.json()
                # A képről OCR-rel generált struktúrát felhasználjuk a prompt mellé
                payload["current_structure"] = image_result.get("structure")

            # AI feldolgozás (szöveges prompt + meglévő struktúra)
            r2 = requests.post(f"{API_URL}/generate-or-modify-dxf", json=payload)
            r2.raise_for_status()
            result = r2.json()

            # Mentés session-be
            st.session_state['current_structure'] = result.get("structure")

            # --- Megjelenítés ---
            st.subheader("JSON tervrajz")
            st.json(st.session_state['current_structure'])

            st.subheader("DXF fájl elérhetősége")
            dxf_file = result.get("file")
            st.write(dxf_file)

            # Letöltés link
            with open(dxf_file, "rb") as f:
                st.download_button(
                    label="DXF letöltése",
                    data=f,
                    file_name="output.dxf",
                    mime="application/dxf"
                )

        except requests.exceptions.RequestException as e:
            st.error(f"Hálózati hiba: {e}")
        except Exception as e:
            st.error(f"Hiba történt a DXF generálás során: {e}")

# --- Új terv létrehozása ---
if st.button("Új terv"):
    st.session_state['current_structure'] = None
    st.success("Kezdeti terv törölve. Adj új promptot vagy tölts fel képet!")
