import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random
import re
import streamlit.components.v1 as components
import extra_streamlit_components as stx
from datetime import datetime, timedelta

# 1. Pagina configuratie
st.set_page_config(page_title="EHBO Expert", page_icon="🚑", layout="centered")

# 2. Cookie Manager Initialisatie
@st.cache_resource
def get_cookie_manager():
    return stx.CookieManager()

cookie_manager = get_cookie_manager()

# 3. Styling
st.markdown("""
    <style>
        .stApp { background-color: white; color: #1f1f1f; }
        button[kind="header"] {
            background-color: #ff4b4b !important;
            color: white !important;
            border-radius: 8px !important;
            width: 80px !important;
        }
        .main .stButton button {
            width: 100%; border-radius: 12px; height: 3.5em; 
            font-weight: bold; border: 2px solid #ff4b4b; 
            background-color: white; color: #ff4b4b;
        }
        div[role='radiogroup'] { background-color: #f8f9fa; padding: 10px; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

def scroll_naar_boven():
    components.html("<script>window.parent.window.scrollTo({top: 0, behavior: 'smooth'});</script>", height=0)

# 4. Hulpfuncties & Data
AFKORTINGEN = {
    "AED": "Automatische Externe Defibrillator", "FAST": "Face, Arm, Speech, Time",
    "RICE": "Rust, IJs, Compressie, Elevatie", "CVA": "Cerebro Vasculair Accident",
    "ABC": "Airway, Breathing, Circulation", "SEH": "Spoedeisende Hulp",
    "CPR": "Cardiopulmonale Resuscitatie"
}

def formatteer_uitleg(tekst):
    if not tekst or pd.isna(tekst): return "Geen uitleg beschikbaar."
    tekst = str(tekst).strip()
    for afk, bet in AFKORTINGEN.items():
        tekst = re.sub(rf"\b{afk}\b", f"{afk} ({bet})", tekst)
    tekst = re.sub(r"(Stappen.*?:)", r"\n\n### 📋 \1\n", tekst)
    tekst = re.sub(r"(?<!\d)([1-9])\.\s+", r"\n\1. ", tekst)
    return tekst

conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl="5m")
def laad_data():
    df = conn.read()
    return df.dropna(subset=['type', 'v']).to_dict('records')

# 5. Cookie & State Logica
def save_state():
    # Sla index en fase op in cookies voor 1 dag
    expires = datetime.now() + timedelta(days=1)
    cookie_manager.set("ehbo_index", str(st.session_state.index), expires_at=expires)
    cookie_manager.set("ehbo_fase", st.session_state.fase, expires_at=expires)

# Initialiseer data
data = laad_data()

# Haal waarden uit cookies
saved_index = cookie_manager.get("ehbo_index")
saved_fase = cookie_manager.get("ehbo_fase")

if 'vragen_hussel' not in st.session_state:
    # Bij eerste laad of hussel-reset: hussel de data
    shuffled = data.copy()
    random.shuffle(shuffled)
    st.session_state.vragen_hussel = shuffled
    # Gebruik cookie waarde als die bestaat, anders 0
    st.session_state.index = int(saved_index) if saved_index else 0
    st.session_state.fase = saved_fase if saved_fase else "normaal"
    st.session_state.fouten = []
    st.session_state.beantwoord = False

# 6. Sidebar & Reset
st.sidebar.title("🚑 EHBO Expert")

if st.sidebar.button("🔄 Toets resetten"):
    cookie_manager.delete("ehbo_index")
    cookie_manager.delete("ehbo_fase")
    # Verwijder hussel om nieuwe random volgorde te forceren
    del st.session_state.vragen_hussel
    st.rerun()

# 7. Quiz Logica
vragen = st.session_state.vragen_hussel

if st.session_state.index >= len(vragen):
    if st.session_state.fouten:
        st.warning(f"Ronde klaar met {len(st.session_state.fouten)} fouten.")
        if st.button("🔄 Herhaal fouten"):
            st.session_state.vragen_hussel = st.session_state.fouten.copy()
            st.session_state.fouten, st.session_state.index = [], 0
            st.session_state.fase = "herhaling"
            st.session_state.beantwoord = False
            save_state()
            st.rerun()
    else:
        st.balloons()
        st.success("🏆 Alles voltooid!")
        if st.button("Helemaal opnieuw beginnen"):
            cookie_manager.delete("ehbo_index")
            del st.session_state.vragen_hussel
            st.rerun()

elif vragen:
    st.title("EHBO Toets")
    st.progress(st.session_state.index / len(vragen))
    
    v = vragen[st.session_state.index]
    st.caption(f"{st.session_state.fase.upper()} | Vraag {st.session_state.index + 1} van {len(vragen)}")
    
    with st.container(border=True):
        st.markdown(f"#### {v['v']}")

    opties = [o.strip() for o in str(v["o"]).split(",")]
    
    if v["type"] == "mc":
        keuze = st.radio("Kies:", opties, key=f"mc_{st.session_state.index}", disabled=st.session_state.beantwoord)
    else:
        gekozen = [o for o in opties if st.checkbox(o, key=f"ch_{o}_{st.session_state.index}", disabled=st.session_state.beantwoord)]

    if not st.session_state.beantwoord:
        if st.button("Antwoord Bevestigen"):
            st.session_state.beantwoord = True
            st.rerun()
    else:
        is_correct = (keuze == v["a"]) if v["type"] == "mc" else (sorted(gekozen) == sorted([a.strip() for a in str(v["a"]).split(",")]))
        
        if is_correct: 
            st.success("✅ Correct!")
        else:
            st.error(f"❌ Onjuist. Correct: {v['a']}")
            if v not in st.session_state.fouten:
                st.session_state.fouten.append(v)
        
        with st.expander("📖 Uitleg", expanded=True):
            st.markdown(formatteer_uitleg(v["u"]))

        if st.button("Volgende Vraag ➡️"):
            st.session_state.index += 1
            st.session_state.beantwoord = False
            save_state() # Update de cookie voor de volgende vraag
            scroll_naar_boven()
            st.rerun()
