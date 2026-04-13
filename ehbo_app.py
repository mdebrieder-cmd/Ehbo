import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random
import re
import streamlit.components.v1 as components

# 1. Pagina configuratie
st.set_page_config(page_title="EHBO Expert", page_icon="🚑", layout="centered")

# 2. Styling (Minimaal voor maximale snelheid)
st.markdown("""
    <style>
        .stApp { background-color: white; }
        .main .stButton button {
            width: 100%; border-radius: 12px; height: 3.5em; 
            font-weight: bold; border: 2px solid #ff4b4b; 
            background-color: white; color: #ff4b4b;
        }
        div[role='radiogroup'] { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border: 1px solid #eee; }
    </style>
""", unsafe_allow_html=True)

def scroll_naar_boven():
    components.html("<script>window.parent.window.scrollTo({top: 0, behavior: 'smooth'});</script>", height=0)

# 3. Data laden & Hulpfuncties
AFKORTINGEN = {"AED": "Defibrillator", "FAST": "Beroerte-test", "RICE": "Koelen/Rust"}

def formatteer_uitleg(tekst):
    if not tekst or pd.isna(tekst): return "Geen info."
    tekst = str(tekst).strip()
    tekst = re.sub(r"(Stappen.*?:)", r"\n\n### 📋 \1\n", tekst)
    tekst = re.sub(r"(?<!\d)([1-9])\.\s+", r"\n\1. ", tekst)
    return tekst

conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl="10m")
def laad_data():
    df = conn.read()
    if 'medisch' not in df.columns: df['medisch'] = None
    return df.dropna(subset=['type', 'v']).to_dict('records')

# 4. URL-gebaseerde State Management (Vervangt Cookies)
params = st.query_params

# Haal staat uit URL of gebruik defaults
u_idx = int(params.get("idx", 0))
u_seed = int(params.get("seed", random.randint(1, 100000)))
u_fse = params.get("fse", "normaal")

data = laad_data()

# Initialiseer hussel op basis van de URL-seed
if 'vragen_hussel' not in st.session_state or st.session_state.get('current_seed') != u_seed:
    shuffled = data.copy()
    random.seed(u_seed)
    random.shuffle(shuffled)
    st.session_state.vragen_hussel = shuffled
    st.session_state.current_seed = u_seed
    st.session_state.index = u_idx
    st.session_state.fase = u_fse
    st.session_state.fouten = []
    st.session_state.beantwoord = False

# 5. Navigatie & Reset
st.sidebar.title("🚑 EHBO Expert")
if st.sidebar.button("🔄 Toets volledig resetten"):
    st.query_params.clear()
    for key in list(st.session_state.keys()): del st.session_state[key]
    st.rerun()

# Syllabus download (HTML)
if data:
    html_content = f"<html><body><h1>EHBO Syllabus</h1>" + "".join([f"<h3>{v['v']}</h3><p>{v['u']}</p>" for v in data]) + "</body></html>"
    st.sidebar.download_button("📥 Syllabus downloaden", html_content, "EHBO_Syllabus.html", "text/html")

# 6. Quiz Logica
vragen = st.session_state.vragen_hussel

if st.session_state.index >= len(vragen):
    if st.session_state.fouten:
        st.warning(f"Ronde klaar! {len(st.session_state.fouten)} fouten.")
        if st.button("🔄 Herhaal fouten"):
            st.session_state.vragen_hussel = st.session_state.fouten.copy()
            st.session_state.fouten, st.session_state.index = [], 0
            st.session_state.fase = "herhaling"
            st.session_state.beantwoord = False
            st.rerun()
    else:
        st.balloons()
        st.success("🏆 Voltooid!")
        if st.button("Opnieuw beginnen"):
            st.query_params.clear()
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
        keuze = st.radio("Antwoord:", opties, key=f"mc_{st.session_state.index}", disabled=st.session_state.beantwoord)
    else:
        gekozen = [o for o in opties if st.checkbox(o, key=f"ch_{o}_{st.session_state.index}", disabled=st.session_state.beantwoord)]

    if not st.session_state.beantwoord:
        if st.button("Antwoord Bevestigen"):
            st.session_state.beantwoord = True
            st.rerun()
    else:
        correct = (keuze == v["a"]) if v["type"] == "mc" else (sorted(gekozen) == sorted([a.strip() for a in str(v["a"]).split(",")]))
        if correct: st.success("✅ Correct!")
        else:
            st.error(f"❌ Fout. Correct: **{v['a']}**")
            if v not in st.session_state.fouten: st.session_state.fouten.append(v)
        
        with st.expander("📖 Uitleg", expanded=True):
            st.markdown(formatteer_uitleg(v["u"]))
            if v.get('medisch') and not pd.isna(v['medisch']):
                st.markdown("---")
                with st.popover("🔬 Medisch"): st.info(formatteer_uitleg(str(v['medisch'])))

        if st.button("Volgende Vraag ➡️"):
            st.session_state.index += 1
            st.session_state.beantwoord = False
            # Werk URL parameters bij voor persistentie
            st.query_params.update(idx=st.session_state.index, seed=st.session_state.current_seed, fse=st.session_state.fase)
            scroll_naar_boven()
            st.rerun()
