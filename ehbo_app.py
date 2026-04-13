import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random
import re
import streamlit.components.v1 as components

# 1. Pagina configuratie
icon_url = "https://githubusercontent.com"
st.set_page_config(page_title="EHBO Expert", page_icon="🚑", layout="centered")

# 2. Styling (Menu knop met tekst 'MENU' en Zijbalk)
st.markdown(f"""
    <style>
        .stApp {{ background-color: white; color: #1f1f1f; }}
        
        /* De Menu-knop styling */
        button[kind="header"] {{
            background-color: #ff4b4b !important;
            color: white !important;
            border-radius: 8px !important;
            width: 80px !important;
            height: 40px !important;
            box-shadow: 0px 4px 10px rgba(255, 75, 75, 0.3) !important;
            border: 2px solid white !important;
        }}
        /* Tekst "MENU" toevoegen aan de knop via CSS */
        button[kind="header"]::after {{
            content: " MENU";
            font-weight: bold;
            font-size: 14px;
        }}

        /* Zijbalk & Knoppen */
        [data-testid="stSidebar"] {{ background-color: #fcfcfc !important; border-right: none; }}
        section[data-testid="stSidebar"] .stButton button {{
            width: 100% !important;
            height: 3.5em !important;
            border-radius: 10px !important;
            border: 1px solid #ff4b4b !important;
            color: #ff4b4b !important;
        }}

        /* Main Quiz UI */
        .main .stButton button {{
            width: 100%; border-radius: 12px; height: 3.5em; 
            font-weight: bold; border: 2px solid #ff4b4b; 
            background-color: white; color: #ff4b4b;
        }}
        div[role='radiogroup'] {{ background-color: #f8f9fa; padding: 10px; border-radius: 10px; border: 1px solid #eee; }}
    </style>
""", unsafe_allow_html=True)

# JS voor scroll naar boven
def scroll_naar_boven():
    components.html("<script>window.parent.window.scrollTo({top: 0, behavior: 'smooth'});</script>", height=0)

# 3. Hulpfuncties
AFKORTINGEN = {
    "AED": "Automatische Externe Defibrillator", "FAST": "Face, Arm, Speech, Time",
    "RICE": "Rust, IJs, Compressie, Elevatie", "CVA": "Cerebro Vasculair Accident",
    "ABC": "Airway, Breathing, Circulation", "SEH": "Spoedeisende Hulp",
    "NVIC": "Nationaal Vergiftigingen Informatie Centrum", "RSI": "Repetitive Strain Injury",
    "KANS": "Klachten aan de Arm, Nek en/of Schouders", "CPR": "Cardiopulmonale Resuscitatie"
}

def formatteer_uitleg(tekst):
    if not tekst or pd.isna(tekst): return "Geen uitleg beschikbaar."
    tekst = str(tekst).strip()
    for afk, bet in AFKORTINGEN.items():
        tekst = re.sub(rf"\b{afk}\b", f"{afk} ({bet})", tekst)
    tekst = re.sub(r"(Stappen.*?:)", r"\n\n### 📋 \1\n", tekst)
    tekst = re.sub(r"(?<!\d)([1-9])\.\s+", r"\n\1. ", tekst)
    return tekst

# 4. Data & State Management
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl="5m")
def laad_en_filter_data():
    df = conn.read()
    if 'medisch' not in df.columns: df['medisch'] = None
    return df.dropna(subset=['type', 'v']).to_dict('records')

data = laad_en_filter_data()

# 5. Persistentie Logica: Voorkom husselen bij refresh
if 'vragen_hussel' not in st.session_state:
    shuffled = data.copy()
    random.shuffle(shuffled)
    st.session_state.vragen_hussel = shuffled
    st.session_state.index = 0
    st.session_state.fouten = []
    st.session_state.fase = "normaal"
    st.session_state.beantwoord = False

# 6. Sidebar Layout
st.sidebar.title("🚑 EHBO Expert")
st.sidebar.markdown("---")

if st.sidebar.button("🔄 Toets resetten"):
    for key in list(st.session_state.keys()): del st.session_state[key]
    st.rerun()

if data:
    syllabus_html = f"<html><body><h1>EHBO Syllabus</h1>" + "".join([f"<h3>{v['v']}</h3><p>{v['u']}</p>" for v in data]) + "</body></html>"
    st.sidebar.download_button("📥 Syllabus downloaden", syllabus_html, "EHBO_Syllabus.html", "text/html")

with st.sidebar.expander("📚 Woordenboek"):
    for afk, bet in AFKORTINGEN.items(): st.markdown(f"**{afk}**: {bet}")

# 7. Quiz Logica
vragen = st.session_state.vragen_hussel

if st.session_state.index >= len(vragen):
    if st.session_state.fouten:
        st.warning(f"Ronde klaar! Je hebt {len(st.session_state.fouten)} fouten gemaakt.")
        if st.button("🔄 Herhaal onjuiste vragen"):
            st.session_state.vragen_hussel = st.session_state.fouten.copy()
            st.session_state.fouten, st.session_state.index = [], 0
            st.session_state.fase = "herhaling"
            st.session_state.beantwoord = False
            scroll_naar_boven()
            st.rerun()
    else:
        st.balloons()
        st.success("🏆 Alles voltooid!")
        if st.button("Opnieuw beginnen"):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()

elif vragen:
    st.title("EHBO Toets")
    st.progress(st.session_state.index / len(vragen))
    
    v = vragen[st.session_state.index]
    st.caption(f"{st.session_state.fase.upper()} | Vraag {st.session_state.index + 1} van {len(vragen)}")
    
    with st.container(border=True):
        st.markdown(f"#### {v['v']}")

    opties = [o.strip() for o in str(v["o"]).split(",")]
    v_key = f"q_{v['v']}_{st.session_state.index}" # Unieke key voor radio/checkbox
    
    if v["type"] == "mc":
        keuze = st.radio("Kies:", opties, key=f"mc_{v_key}", disabled=st.session_state.beantwoord, label_visibility="collapsed")
    else:
        gekozen = [o for o in opties if st.checkbox(o, key=f"ch_{o}_{v_key}", disabled=st.session_state.beantwoord)]

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
        
        with st.expander("📖 Uitleg & Stappenplan", expanded=True):
            st.markdown(formatteer_uitleg(v["u"]))
            if v.get('medisch') and not pd.isna(v['medisch']):
                st.markdown("---")
                with st.popover("🔬 Medisch"): st.info(formatteer_uitleg(str(v['medisch'])))

        if st.button("Volgende Vraag ➡️"):
            st.session_state.index += 1
            st.session_state.beantwoord = False
            scroll_naar_boven()
            st.rerun()
