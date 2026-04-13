import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random
import re
import io

# 1. Pagina configuratie
icon_url = "https://githubusercontent.com"

st.set_page_config(page_title="EHBO Expert", page_icon="🚑", layout="centered")

# 2. Woordenboek voor afkortingen
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

# 3. Styling
st.markdown(f"""
    <style>
        .stApp {{ background-color: white; color: #1f1f1f; }}
        h1, h2, h3, h4, p, span, .stMarkdown {{ color: #1f1f1f !important; }}
        div[role='radiogroup'] {{ gap: 0.5rem !important; padding: 10px !important; background-color: #f8f9fa; border-radius: 10px; }}
        .stButton button {{ width: 100%; border-radius: 12px; height: 3em; font-weight: bold; border: 2px solid #ff4b4b; }}
        .stExpander {{ border: 2px solid #ff4b4b; border-radius: 12px; background-color: #fffafa; }}
    </style>
""", unsafe_allow_html=True)

# 4. Hulpfuncties
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

def genereer_syllabus_html(data):
    """Genereert een HTML-syllabus die e-readers kunnen inladen."""
    html = "<html><head><meta charset='utf-8'><title>EHBO Syllabus</title></head><body>"
    html += "<h1>EHBO Expert Syllabus</h1><p>Alle stappenplannen en medische achtergronden.</p><hr>"
    for v in data:
        html += f"<h2>{v['v']}</h2>"
        html += f"<p><b>Juiste handeling:</b> {v['a']}</p>"
        html += f"<p><b>Uitleg:</b> {v['u'].replace('1.', '<br>1.')}</p>"
        if v.get('medisch'):
            html += f"<p><i>Medische achtergrond: {v['medisch']}</i></p>"
        html += "<hr>"
    html += "</body></html>"
    return html

# 5. Verbinding & Data
conn = st.connection("gsheets", type=GSheetsConnection)

def laad_data():
    try:
        df = conn.read(ttl="1m")
        if 'medisch' not in df.columns: df['medisch'] = None
        return df.dropna(subset=['type', 'v']).to_dict('records')
    except Exception as e:
        st.error(f"Fout bij laden data: {e}"); return []

data_voor_syllabus = laad_data()

# 6. Navigatie & Sidebar
st.sidebar.title("🚑 EHBO Expert")
menu = st.sidebar.radio("Navigatie:", ["📝 Doe de Quiz", "➕ Voeg Vraag Toe"])

# Syllabus Sectie
st.sidebar.markdown("---")
st.sidebar.subheader("📖 Studiemateriaal")
if data_voor_syllabus:
    syllabus_content = genereer_syllabus_html(data_voor_syllabus)
    st.sidebar.download_button(
        label="📥 Download Syllabus (ePub/HTML)",
        data=syllabus_content,
        file_name="EHBO_Expert_Syllabus.html",
        mime="text/html",
        help="Download alle EHBO kennis voor offline gebruik op je e-reader of telefoon."
    )

with st.sidebar.expander("📚 Woordenboek"):
    for afk, betekenis in AFKORTINGEN.items():
        st.markdown(f"**{afk}**: {betekenis}")

# 7. Quiz Logica
if menu == "📝 Doe de Quiz":
    st.title("EHBO Kennis Toets")
    
    if 'vragen_hussel' not in st.session_state:
        if data_voor_syllabus:
            shuffled = data_voor_syllabus.copy()
            random.shuffle(shuffled)
            st.session_state.vragen_hussel = shuffled
            st.session_state.index, st.session_state.fouten = 0, []
            st.session_state.beantwoord = False
        else: st.session_state.vragen_hussel = []

    vragen = st.session_state.vragen_hussel

    if st.session_state.index >= len(vragen) and vragen:
        if st.session_state.fouten:
            st.warning(f"Ronde klaar. {len(st.session_state.fouten)} fouten. Herhalen?")
            if st.button("🔄 Start Herhaling"):
                st.session_state.vragen_hussel = st.session_state.fouten.copy()
                st.session_state.fouten, st.session_state.index = [], 0
                st.session_state.beantwoord = False
                st.rerun()
        else:
            st.balloons()
            st.success("Gefeliciteerd! Alles correct.")
            if st.button("🏁 Opnieuw"):
                for k in ['vragen_hussel','index','fouten','beantwoord']: del st.session_state[k]
                st.rerun()
    elif vragen:
        st.progress(st.session_state.index / len(vragen))
        v = vragen[st.session_state.index]
        st.caption(f"Vraag {st.session_state.index + 1} van {len(vragen)}")
        st.markdown(f"#### {v['v']}")

        opties = [o.strip() for o in str(v["o"]).split(",")]
        if v["type"] == "mc":
            keuze = st.radio("Antwoord:", opties, key=f"mc_{st.session_state.index}", disabled=st.session_state.beantwoord, label_visibility="collapsed")
        else:
            gekozen = [o for o in opties if st.checkbox(o, key=f"ch_{o}_{st.session_state.index}", disabled=st.session_state.beantwoord)]

        if not st.session_state.beantwoord:
            if st.button("Bevestigen"):
                st.session_state.beantwoord = True
                st.rerun()
        else:
            is_correct = (keuze == v["a"]) if v["type"] == "mc" else (sorted(gekozen) == sorted([a.strip() for a in str(v["a"]).split(",")]))
            if is_correct: st.success("✅ Correct!")
            else:
                st.error(f"❌ Onjuist. Het juiste antwoord is: **{v['a']}**")
                if v not in st.session_state.fouten: st.session_state.fouten.append(v)
            
            with st.expander("📖 Bekijk uitleg", expanded=True):
                st.markdown(formatteer_uitleg(v["u"]))
                if v.get('medisch'):
                    st.markdown("---")
                    with st.popover("🔬 Medisch"): st.info(schrijf_afkortingen_voluit(str(v['medisch'])))

            if st.button("Volgende ➡️"):
                st.session_state.index += 1; st.session_state.beantwoord = False; st.rerun()

elif menu == "➕ Voeg Vraag Toe":
    st.title("Admin")
    with st.form("add_form", clear_on_submit=True):
        t = st.selectbox("Type", ["mc", "check"])
        v_t, o_t, a_t = st.text_input("Vraag"), st.text_input("Opties"), st.text_input("Antwoord")
        u_t, m_t = st.text_area("Uitleg"), st.text_area("Medisch")
        if st.form_submit_button("Opslaan"):
            conn.update(data=pd.concat([conn.read(), pd.DataFrame([{"type":t,"v":v_t,"o":o_t,"a":a_t,"u":u_t,"medisch":m_t}])], ignore_index=True))
            st.success("Opgeslagen!")
