import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random

# 1. Pagina configuratie
# Let op: De icoon URL moet de RAW versie zijn van GitHub voor weergave
icon_url = "https://githubusercontent.com"

st.set_page_config(
    page_title="EHBO Expert",
    page_icon="🚑",
    layout="centered"
)

# Injectie voor Android App-instellingen & Styling
st.markdown(f"""
    <div style="display:none">
        <head>
            <meta name="apple-mobile-web-app-title" content="EHBO Expert">
            <meta name="application-name" content="EHBO Expert">
            <link rel="apple-touch-icon" href="{icon_url}">
            <link rel="icon" sizes="192x192" href="{icon_url}">
            <meta name="mobile-web-app-capable" content="yes">
        </head>
    </div>
    <style>
        .stButton button {{ width: 100%; border-radius: 10px; height: 3em; background-color: #f0f2f6; }}
        .stRadio div[role='radiogroup'] {{ background-color: #f9f9f9; padding: 15px; border-radius: 10px; }}
        .stExpander {{ border: 1px solid #ff4b4b; border-radius: 10px; }}
    </style>
""", unsafe_allow_html=True)

# 2. Verbinding met Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. Hulpfuncties
def laad_data():
    try:
        df = conn.read(ttl="1m")
        return df.dropna(subset=['type', 'v']).to_dict('records')
    except Exception as e:
        st.error(f"Fout bij laden data: {e}")
        return []

def voeg_vraag_toe(nieuwe_vraag):
    bestaande_data = conn.read()
    nieuwe_rij = pd.DataFrame([nieuwe_vraag])
    geupdate_data = pd.concat([bestaande_data, nieuwe_rij], ignore_index=True)
    conn.update(data=geupdate_data)
    st.cache_data.clear()

# 4. Navigatie menu
st.sidebar.title("Navigatie")
menu = st.sidebar.radio("Ga naar:", ["📝 Doe de Quiz", "➕ Voeg Vraag Toe"])

# 5. Quiz Logica
if menu == "📝 Doe de Quiz":
    st.title("🚑 EHBO Expert Toets")
    
    if 'vragen_hussel' not in st.session_state:
        data = laad_data()
        if data:
            random.shuffle(data)
            st.session_state.vragen_hussel = data
            st.session_state.index = 0
            st.session_state.fouten = []
            st.session_state.fase = "normaal"
            st.session_state.beantwoord = False
        else:
            st.session_state.vragen_hussel = []

    vragen = st.session_state.vragen_hussel

    if not vragen and not st.session_state.get('fouten'):
        st.info("De database is leeg.")
    elif st.session_state.index >= len(vragen):
        if st.session_state.fouten:
            st.warning(f"Ronde klaar! Je hebt {len(st.session_state.fouten)} vragen gemist. We herhalen deze nu.")
            if st.button("Start Herhaling"):
                st.session_state.vragen_hussel = st.session_state.fouten.copy()
                st.session_state.fouten = []
                st.session_state.index = 0
                st.session_state.fase = "herhalen"
                st.session_state.beantwoord = False
                st.rerun()
        else:
            st.balloons()
            st.header("🏆 Toets Voltooid!")
            if st.button("Helemaal Opnieuw Starten"):
                for key in ['vragen_hussel', 'index', 'fouten', 'fase', 'beantwoord']:
                    if key in st.session_state: del st.session_state[key]
                st.rerun()
    else:
        v = vragen[st.session_state.index]
        status = "🔄 Herhaling" if st.session_state.fase == "herhalen" else "📖 Toets"
        st.caption(f"{status} | Vraag {st.session_state.index + 1} van {len(vragen)}")
        
        with st.container(border=True):
            st.markdown(f"**{v['v']}**")

        opties = [o.strip() for o in str(v["o"]).split(",")]
        
        # Logica voor MC vragen
        if v["type"] == "mc":
            keuze = st.radio("Maak een keuze:", opties, key=f"mc_{st.session_state.index}", disabled=st.session_state.beantwoord)
            
            if not st.session_state.beantwoord:
                if st.button("Antwoord Bevestigen"):
                    st.session_state.beantwoord = True
                    st.rerun()
            else:
                if keuze == v["a"]:
                    st.success("✅ Correct!")
                else:
                    st.error(f"❌ Onjuist. Het juiste antwoord was: **{v['a']}**")
                    if v not in st.session_state.fouten:
                        st.session_state.fouten.append(v)
                
                with st.expander("📖 Bekijk uitleg en stappenplan", expanded=True):
                    st.write(v["u"])
                
                if st.button("Volgende Vraag ➡️"):
                    st.session_state.index += 1
                    st.session_state.beantwoord = False
                    st.rerun()

        # Logica voor Checkbox vragen
        elif v["type"] == "check":
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
                juiste_antwoorden = sorted([a.strip() for a in str(v["a"]).split(",")])
                if sorted(gekozen) == juiste_antwoorden:
                    st.success("✅ Correct!")
                else:
                    st.error(f"❌ Onjuist. Juiste opties: **{v['a']}**")
                    if v not in st.session_state.fouten:
                        st.session_state.fouten.append(v)
                
                with st.expander("📖 Bekijk uitleg en stappenplan", expanded=True):
                    st.write(v["u"])
                
                if st.button("Volgende Vraag ➡️"):
                    st.session_state.index += 1
                    st.session_state.beantwoord = False
                    st.rerun()

# 6. Admin Logica
elif menu == "➕ Voeg Vraag Toe":
    st.title("Database Uitbreiden")
    with st.form("add_form", clear_on_submit=True):
        t = st.selectbox("Type Vraag", ["mc", "check"])
        vraag_tekst = st.text_input("Vraagstelling")
        opties_tekst = st.text_input("Opties (komma-gescheiden)")
        antwoord_tekst = st.text_input("Juiste antwoord(en)")
        uitleg_tekst = st.text_area("Uitleg + Stappenplan")
        
        if st.form_submit_button("Opslaan in Google Sheets"):
            if vraag_tekst and opties_tekst and antwoord_tekst:
                nieuwe_v = {"type": t, "v": vraag_tekst, "o": opties_tekst, "a": antwoord_tekst, "u": uitleg_tekst}
                voeg_vraag_toe(nieuwe_v)
                st.success("Vraag succesvol toegevoegd!")
