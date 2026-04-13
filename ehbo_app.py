import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random
import re
import io
import streamlit.components.v1 as components

# 1. Pagina configuratie
icon_url = "https://githubusercontent.com"
st.set_page_config(page_title="EHBO Expert", page_icon="🚑", layout="centered")

# 2. Woordenboek & Styling
AFKORTINGEN = {
    "AED": "Automatische Externe Defibrillator",
    "FAST": "Face, Arm, Speech, Time",
    "RICE": "Rust, IJs, Compressie, Elevatie",
    "CVA": "Cerebro Vasculair Accident",
    "ABC": "Airway, Breathing, Circulation",
    "SEH": "Spoedeisende Hulp",
    "NVIC": "Nationaal Vergiftigingen Informatie Centrum",
    "RSI": "Repetitive Strain Injury",
    "KANS": "Klachten aan de Arm, Nek en/of Schouders",
    "CPR": "Cardiopulmonale Resuscitatie"
}

st.markdown(f"""
    <style>
        /* Forceer lichte weergave */
        .stApp {{ background-color: white; color: #1f1f1f; }}
        h1, h2, h3, h4, p, span, .stMarkdown {{ color: #1f1f1f !important; }}
        
        /* Maak de zijbalk menu knop (<<) duidelijker */
        [data-testid="stSidebarNav"] {{ background-color: #fffafa; border-bottom: 2px solid #ff4b4b; }}
        button[kind="header"] {{ background-color: #ff4b4b !important; color: white !important; border-radius: 50% !important; box-shadow: 0px 4px 10px rgba(0,0,0,0.2); }}

        /* Vraag & Antwoord styling */
        div[role='radiogroup'] {{ gap: 0.5rem !important; padding: 10px !important; background-color: #f8f9fa; border-radius: 10px; border: 1px solid #ddd; }}
        .stButton button {{ width: 100%; border-radius: 12px; height: 3.5em; font-weight: bold; border: 2px solid #ff4b4b; background-color: white; }}
        .stExpander {{ border: 2px solid #ff4b4b; border-radius: 12px; background-color: #fffafa; }}
        
        /* Sidebar styling */
        section[data-testid="stSidebar"] {{ border-right: 2px solid #ff4b4b; }}
    </style>
""", unsafe_allow_html=True)

# JS voor scroll naar boven
def scroll_naar_boven():
    components.html("<script>window.parent.window.scrollTo(0,0);</script>", height=0)

# 3. Hulpfuncties
def schrijf_afkortingen_voluit(tekst):
    for afk, betekenis in AFKORTINGEN.items():
        tekst = re.sub(rf"\b{afk}\b", f"{afk} ({betekenis})", tekst)
    return tekst

def formatteer_uitleg(tekst):
    if not tekst or pd.isna(tekst): return "Geen uitleg beschikbaar."
    tekst = str(tekst).strip()
    tekst = schrijf_afkortingen_voluit(tekst)
    tekst = re.sub(r"(Stappen.*?:)", r"\n\n### 📋 \1\n", tekst)
    tekst = re.sub(r"(?<!\d)([1-9])\.\s+", r"\n\1. ", tekst)
    return tekst

# 4. Data laden
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl="5m")
def laad_data():
    try:
        df = conn.read()
        if 'medisch' not in df.columns: df['medisch'] = None
        return df.dropna(subset=['type', 'v']).to_dict('records')
    except: return []

data = laad_data()

# 5. Sidebar Menu & Functies
st.sidebar.title("🚑 EHBO Expert")
st.sidebar.markdown("---")

if st.sidebar.button("🔄 Hele Toets Resetten"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.query_params.clear()
    st.rerun()

if data:
    syllabus_html = f"<html><body><h1>EHBO Syllabus</h1>" + "".join([f"<h3>{v['v']}</h3><p>{v['u']}</p>" for v in data]) + "</body></html>"
    st.sidebar.download_button("📥 Download Syllabus", syllabus_html, "EHBO_Syllabus.html", "text/html")

with st.sidebar.expander("📚 Woordenboek"):
    for afk, betekenis in AFKORTINGEN.items():
        st.markdown(f"**{afk}**: {betekenis}")

# 6. Quiz Logica
if 'index' not in st.session_state:
    st.session_state.index = int(st.query_params.get("q", 0))
    st.session_state.fase = st.query_params.get("f", "normaal")
    st.session_state.beantwoord = False
    if 'vragen_hussel' not in st.session_state:
        shuffled = data.copy()
        random.shuffle(shuffled)
        st.session_state.vragen_hussel = shuffled
        st.session_state.fouten = []

vragen = st.session_state.vragen_hussel

if st.session_state.index >= len(vragen) and vragen:
    if st.session_state.fouten:
        st.warning(f"Je hebt {len(st.session_state.fouten)} vragen onjuist. Laten we deze herhalen.")
        if st.button("🔄 Herhaal Fouten"):
            st.session_state.vragen_hussel = st.session_state.fouten.copy()
            st.session_state.fouten, st.session_state.index = [], 0
            st.session_state.fase = "herhaling"
            st.query_params.update(q=0, f="herhaling")
            scroll_naar_boven()
            st.rerun()
    else:
        st.balloons()
        st.success("🏆 Alles voltooid!")
        if st.button("Opnieuw Beginnen"):
            st.sidebar.button("🔄 Hele Toets Resetten")

elif vragen:
    st.title("EHBO Toets")
    st.progress(st.session_state.index / len(vragen))
    v = vragen[st.session_state.index]
    st.caption(f"{st.session_state.fase.upper()} | Vraag {st.session_state.index + 1} van {len(vragen)}")
    
    with st.container(border=True):
        st.markdown(f"#### {v['v']}")

    opties = [o.strip() for o in str(v["o"]).split(",")]
    if v["type"] == "mc":
        keuze = st.radio("Kies:", opties, key=f"mc_{st.session_state.index}", disabled=st.session_state.beantwoord, label_visibility="collapsed")
    else:
        gekozen = [o for o in opties if st.checkbox(o, key=f"ch_{o}_{st.session_state.index}", disabled=st.session_state.beantwoord)]

    if not st.session_state.beantwoord:
        if st.button("Bevestigen"):
            st.session_state.beantwoord = True
            st.rerun()
    else:
        # Check antwoord
        is_correct = (keuze == v["a"]) if v["type"] == "mc" else (sorted(gekozen) == sorted([a.strip() for a in str(v["a"]).split(",")]))
        if is_correct: st.success("✅ Correct!")
        else:
            st.error(f"❌ Onjuist. Correct: {v['a']}")
            if v not in st.session_state.fouten: st.session_state.fouten.append(v)
        
        with st.expander("📖 Uitleg & Stappenplan", expanded=True):
            st.markdown(formatteer_uitleg(v["u"]))
            if v.get('medisch') and not pd.isna(v['medisch']):
                st.markdown("---")
                with st.popover("🔬 Medisch"): st.info(schrijf_afkortingen_voluit(str(v['medisch'])))

        if st.button("Volgende Vraag ➡️"):
            st.session_state.index += 1
            st.session_state.beantwoord = False
            st.query_params.update(q=st.session_state.index)
            scroll_naar_boven()
            st.rerun()
