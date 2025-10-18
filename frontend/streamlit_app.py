import json
import requests
import streamlit as st

st.set_page_config(page_title="Architect AI – MVP", layout="wide")
BACKEND_URL = "http://localhost:8000"
st.title("🏗️ Architect AI – MVP (Dummy LLM)")
with st.sidebar:
    st.markdown("**Backend**: ")
    st.code(BACKEND_URL, language="text")
    if st.button("Health check"):
        try:
            r = requests.get(f"{BACKEND_URL}/health", timeout=5)
            st.success(r.json())
        except Exception as e:
            st.error(str(e))

st.subheader("1) Terv generálása promptból")
prompt = st.text_input("Szöveges prompt", "68 négyzetméteres ház, 2 hálószoba, 4 ablak, 1 ajtó")
if st.button("Generálás"):
    with st.spinner("Generálás..."):
        r = requests.post(f"{BACKEND_URL}/generate-or-modify-dxf", json={"prompt": prompt})
        if r.ok:
            st.session_state["plan"] = r.json()["plan"]
            st.session_state["dxf_path"] = r.json()["dxf_path"]
        else:
            st.error(r.text)
            
st.subheader("2) Módosítás meglévő terven")
mod = st.text_input("Módosítási utasítás (pl.: 'R2 nagyobb 1 méterrel' vagy 'ajtó jobbra 0.5 m')", "")
if st.button("Módosítás alkalmazása"):
    plan = st.session_state.get("plan")
    if not plan:
        st.warning("Előbb generálj egy tervet!")
    else:
        r = requests.post(f"{BACKEND_URL}/generate-or-modify-dxf", json={"prompt": mod, "existing_plan": plan})
        if r.ok:
            st.session_state["plan"] = r.json()["plan"]
            st.session_state["dxf_path"] = r.json()["dxf_path"]
        else:
            st.error(r.text)
            
st.divider()
col1, col2 = st.columns(2)
with col1:
    st.markdown("**Aktuális terv (JSON):**")
    st.json(st.session_state.get("plan", {}))
with col2:
    st.markdown("**DXF fájl helye a szerveren:**")
    st.code(st.session_state.get("dxf_path", "—"))
    if st.session_state.get("dxf_path"):
        st.info("A Streamlit demo lokálisan fut: töltsd le a /output mappából vagy szolgáld ki egy statikus route-tal.")