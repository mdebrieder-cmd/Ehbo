import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random
import re
import streamlit.components.v1 as components

# 1. Pagina configuratie
st.set_page_config(page_title="EHBO Expert", page_icon="🚑", layout="centered")

# 2. Styling voor snelheid en mobiel gebruik
st.markdown("""
    <style>
        .stApp { background-color: white; }
        .main .stButton button {
            width: 100%; border-radius: 12px; height: 3.5em; 
            font-weight: bold; border: 2px solid #ff4b4b; 
            background-color: white; color: #ff4b4b;
        }
        div[role='radiogroup'] { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border: 1px solid #eee; }
        [data-testid="stSidebar"] { background-color: #fcfcfc !important; }
    </style>
""", unsafe_allow_html=True)

def scroll_naar_boven():
    components.html("<script>window.parent.window.scrollTo({top: 0, behavior: 'smooth'});</script>", height=0)

# 3. Hulpfuncties & Woordenboek
AFKORTINGEN = {
    "AED": "Automatische Externe Defibrillator", "FAST": "Face, Arm, Speech, Time",
    "RICE": "Rust, IJs, Compressie, Elevatie", "CVA": "Cerebro Vasculair Accident",
    "ABC": "Airway, Breathing, Circulation", "SEH": "Spoedeisende Hulp",
    "NVIC": "Nationaal Vergiftigingen Informatie Centrum", "CPR": "Cardiopulmonale Resuscitatie"
}

def formatteer_uitleg(tekst):
    if not tekst or pd.isna(tekst): return "Geen informatie beschikbaar."
    tekst = str(tekst).strip()
    for afk, bet in AFKORTINGEN.items():
        tekst = re.sub(rf"\b{afk}\b", f"{afk} ({bet})", tekst)
    tekst = re.sub(r"(Stappen.*?:)", r"\n\n### 📋 \1\n", tekst)
    # Zorg dat 1. 2. 3. op nieuwe regels staan (negeert 112)
    tekst = re.sub(r"(?<!\d)([1-9])\.\s+", r"\n\1. ", tekst)
    return tekst

# 4. Data laden
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl="5m")
def laad_data():
    df = conn.read()
    if 'medisch' not in df.columns: df['medisch'] = None
    return df.dropna(subset=['type', 'v']).to_dict('records')

data = laad_data()

# 5. Session State Initialisatie (Husselen gebeurt alleen hier)
if 'vragen_hussel' not in st.session_state:
    shuffled = data.copy()
    random.shuffle(shuffled)
    st.session_state.vragen_hussel = shuffled
    st.session_state.index = 0
    st.session_state.fouten = []
    st.session_state.fase = "normaal"
    st.session_state.beantwoord = False

# 6. Sidebar
st.sidebar.title("🚑 EHBO Expert")

if st.sidebar.button("🔄 Toets resetten"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# Syllabus download
if data:
    syllabus_html = "<html><body style='font-family:sans-serif;'><h1>EHBO Syllabus</h1>"
    for v in data:
        syllabus_html += f"<h3>{v['v']}</h3><p>{v['u']}</p><hr>"
    syllabus_html += "</body></html>"
    st.sidebar.download_button("📥 Syllabus downloaden", syllabus_html, "EHBO_Syllabus.html", "text/html")

with st.sidebar.expander("📚 Woordenboek"):
    for afk, bet in AFKORTINGEN.items(): 
        st.markdown(f"**{afk}**: {bet}")

# 7. Quiz Logica
vragen = st.session_state.vragen_hussel

if st.session_state.index >= len(vragen):
    if st.session_state.fouten:
        st.warning(f"Ronde klaar! Je hebt {len(st.session_state.fouten)} fouten gemaakt.")
        if st.button("🔄 Herhaal onjuiste vragen"):
            st.session_state.vragen_hussel = st.session_state.fouten.copy()
            st.session_state.fouten = []
            st.session_state.index = 0
            st.session_state.fase = "herhaling"
            st.session_state.beantwoord = False
            st.rerun()
    else:
        st.balloons()
        st.success("🏆 Toets voltooid!")
        if st.button("Opnieuw beginnen"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
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
        keuze = st.radio("Maak een keuze:", opties, key=f"mc_{st.session_state.index}", disabled=st.session_state.beantwoord)
    else:
        st.write("Selecteer alle juiste opties:")
        gekozen = []
        for i, o in enumerate(opties):
            if st.checkbox(o, key=f"ch_{i}_{st.session_state.index}", disabled=st.session_state.beantwoord):
                gekozen.append(o)

    if not st.session_state.beantwoord:
        if st.button("Antwoord Bevestigen"):
            st.session_state.beantwoord = True
            st.rerun()
    else:
        # Check antwoord
        if v["type"] == "mc":
            is_correct = (keuze == v["a"])
        else:
            juiste_lijst = sorted([a.strip() for a in str(v["a"]).split(",")])
            is_correct = (sorted(gekozen) == juiste_lijst)
        
        if is_correct: 
            st.success("✅ Correct!")
        else:
            st.error(f"❌ Onjuist. Het juiste antwoord was: **{v['a']}**")
            if v not in st.session_state.fouten:
                st.session_state.fouten.append(v)
        
        with st.expander("📖 Uitleg & Stappenplan", expanded=True):
            st.markdown(formatteer_uitleg(v["u"]))
            if v.get('medisch') and not pd.isna(v['medisch']):
                st.markdown("---")
                with st.popover("🔬 Medische achtergrond"):
                    st.info(formatteer_uitleg(str(v['medisch'])))

        if st.button("Volgende Vraag ➡️"):
            st.session_state.index += 1
            st.session_state.beantwoord = False
            scroll_naar_boven()
            st.rerun()
