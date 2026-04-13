import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random
import re
import time
import streamlit.components.v1 as components
import extra_streamlit_components as stx
from datetime import datetime, timedelta

# 1. Pagina configuratie
st.set_page_config(page_title="EHBO Expert", page_icon="🚑", layout="centered")

# 2. Cookie Manager Initialisatie
if 'cookie_manager' not in st.session_state:
    st.session_state.cookie_manager = stx.CookieManager(key="ehbo_v5")

cookie_manager = st.session_state.cookie_manager

# 3. Styling
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

# 4. Hulpfuncties & Data
AFKORTINGEN = {
    "AED": "Automatische Externe Defibrillator", "FAST": "Face, Arm, Speech, Time",
    "RICE": "Rust, IJs, Compressie, Elevatie", "CVA": "Cerebro Vasculair Accident",
    "ABC": "Airway, Breathing, Circulation", "SEH": "Spoedeisende Hulp"
}

def formatteer_uitleg(tekst):
    if not tekst or pd.isna(tekst): return "Geen informatie beschikbaar."
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
    if 'medisch' not in df.columns: df['medisch'] = None
    return df.dropna(subset=['type', 'v']).to_dict('records')

# 5. Persistentie Logica (Cookies + Fixed Seed)
data = laad_data()
cookies = cookie_manager.get_all()

# Haal opgeslagen staat uit cookies
s_idx = cookies.get("ehbo_idx")
s_fse = cookies.get("ehbo_fse")
s_sed = cookies.get("ehbo_seed")

if 'vragen_hussel' not in st.session_state:
    # Bepaal seed: uit cookie of nieuw
    current_seed = int(s_sed) if s_sed else random.randint(1, 100000)
    
    shuffled = data.copy()
    random.seed(current_seed)
    random.shuffle(shuffled)
    
    st.session_state.vragen_hussel = shuffled
    st.session_state.index = int(s_idx) if s_idx else 0
    st.session_state.fase = s_fse if s_fse else "normaal"
    st.session_state.seed = current_seed
    st.session_state.fouten = []
    st.session_state.beantwoord = False

def save_state():
    expires = datetime.now() + timedelta(days=1)
    cookie_manager.set("ehbo_idx", str(st.session_state.index), expires_at=expires, key="c_idx")
    cookie_manager.set("ehbo_fse", st.session_state.fase, expires_at=expires, key="c_fse")
    cookie_manager.set("ehbo_seed", str(st.session_state.seed), expires_at=expires, key="c_sed")

# 6. Sidebar
st.sidebar.title("🚑 EHBO Expert")

if st.sidebar.button("🔄 Toets volledig resetten"):
    cookie_manager.delete("ehbo_idx", key="d_idx")
    cookie_manager.delete("ehbo_fse", key="d_fse")
    cookie_manager.delete("ehbo_seed", key="d_sed")
    if 'vragen_hussel' in st.session_state: del st.session_state.vragen_hussel
    st.rerun()

# Syllabus Sectie
if data:
    st.sidebar.markdown("---")
    # Printvriendelijke HTML Syllabus
    html_content = f"""
    <html><head><style>
        body {{ font-family: Arial, sans-serif; padding: 40px; line-height: 1.6; }}
        h1 {{ color: #ff4b4b; border-bottom: 2px solid #ff4b4b; }}
        .item {{ margin-bottom: 30px; page-break-inside: avoid; }}
        .medisch {{ background: #f0f2f6; padding: 10px; border-radius: 5px; font-style: italic; }}
    </style></head><body>
    <h1>EHBO Syllabus</h1>
    <p>Gegenereerd op: {datetime.now().strftime('%d-%m-%Y')}</p>
    """
    for item in data:
        html_content += f"""
        <div class="item">
            <h3>{item['v']}</h3>
            <p><b>Handeling:</b> {item['u']}</p>
        """
        if item.get('medisch') and not pd.isna(item['medisch']):
            html_content += f"<p class='medisch'><b>Medische achtergrond:</b> {item['medisch']}</p>"
        html_content += "</div><hr>"
    html_content += "</body></html>"

    st.sidebar.download_button("📥 Syllabus (HTML/PDF)", html_content, "EHBO_Syllabus.html", "text/html")

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
            save_state()
            st.rerun()
    else:
        st.balloons()
        st.success("🏆 Alles voltooid!")
        if st.button("🏁 Opnieuw beginnen"):
            cookie_manager.delete("ehbo_idx", key="r_idx")
            cookie_manager.delete("ehbo_seed", key="r_sed")
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
        st.write("Selecteer alle juiste opties:")
        gekozen = [o for o in opties if st.checkbox(o, key=f"ch_{o}_{st.session_state.index}", disabled=st.session_state.beantwoord)]

    if not st.session_state.beantwoord:
        if st.button("Antwoord Bevestigen"):
            st.session_state.beantwoord = True
            st.rerun()
    else:
        # Validatie
        if v["type"] == "mc":
            correct = (keuze == v["a"])
        else:
            correct = (sorted(gekozen) == sorted([a.strip() for a in str(v["a"]).split(",")]))
        
        if correct: 
            st.success("✅ Correct!")
        else:
            st.error(f"❌ Onjuist. Correct: **{v['a']}**")
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
            save_state()
            time.sleep(0.1)
            scroll_naar_boven()
            st.rerun()
