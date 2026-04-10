import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random

# 1. Pagina configuratie (MOET als eerste)
st.set_page_config(page_title="EHBO Expert Toets", page_icon="🚑", layout="centered")

# 2. Manifest link
st.markdown('<link rel="manifest" href="https://github.io">', unsafe_allow_html=True)

# 3. Verbinding met Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# 4. Hulpfuncties
def laad_data():
    try:
        df = conn.read(ttl="1m")
        # Filter lege rijen en zet om naar lijst van dicts
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

# 5. Navigatie menu (Eerst menu aanmaken, dan pas gebruiken!)
st.sidebar.title("Navigatie")
menu = st.sidebar.radio("Ga naar:", ["📝 Doe de Quiz", "➕ Voeg Vraag Toe"])

# 6. Quiz Logica
if menu == "📝 Doe de Quiz":
    st.title("🚑 EHBO Diagnose Quiz")
    
    # Initialiseer quiz data in session state
    if 'vragen_hussel' not in st.session_state:
        data = laad_data()
        if data:
            random.shuffle(data)
            st.session_state.vragen_hussel = data
            st.session_state.index = 0
            st.session_state.score = 0
            st.session_state.klaar = False
        else:
            st.session_state.vragen_hussel = []

    vragen = st.session_state.vragen_hussel

    if not vragen:
        st.info("De database is leeg of niet bereikbaar. Voeg eerst vragen toe.")
    elif st.session_state.klaar:
        st.balloons()
        st.header("Toets Voltooid!")
        st.metric("Eindscore", f"{st.session_state.score} / {len(vragen)}")
        if st.button("Opnieuw Starten"):
            del st.session_state.vragen_hussel # Forceert herladen en husselen
            st.rerun()
    else:
        # Toon huidige vraag
        v = vragen[st.session_state.index]
        st.subheader(f"Vraag {st.session_state.index + 1} van {len(vragen)}")
        st.info(v["v"])

        opties = [o.strip() for o in str(v["o"]).split(",")]
        
        if v["type"] == "mc":
            keuze = st.radio("Wat is de juiste diagnose?", opties, key=f"mc_{st.session_state.index}")
            if st.button("Antwoord Bevestigen"):
                if keuze == v["a"]:
                    st.success(f"✅ Correct! {v['u']}")
                    st.session_state.score += 1
                else:
                    st.error(f"❌ Onjuist. Het juiste antwoord: {v['a']}. \n\nUitleg: {v['u']}")
                
                # Volgende vraag logica
                if st.session_state.index + 1 < len(vragen):
                    st.session_state.index += 1
                    st.button("Volgende Vraag")
                else:
                    st.session_state.klaar = True
                    st.rerun()

        elif v["type"] == "check":
            st.write("Selecteer alle symptomen die horen bij deze diagnose:")
            gekozen = []
            for o in opties:
                if st.checkbox(o, key=f"ch_{o}_{st.session_state.index}"):
                    gekozen.append(o)
            
            if st.button("Antwoord Bevestigen"):
                juiste_antwoorden = sorted([a.strip() for a in str(v["a"]).split(",")])
                if sorted(gekozen) == juiste_antwoorden:
                    st.success(f"✅ Correct! {v['u']}")
                    st.session_state.score += 1
                else:
                    st.error(f"❌ Onjuist. De juiste symptomen waren: {v['a']}. \n\nUitleg: {v['u']}")
                
                if st.session_state.index + 1 < len(vragen):
                    st.session_state.index += 1
                    st.button("Volgende Vraag")
                else:
                    st.session_state.klaar = True
                    st.rerun()

# 7. Admin Logica
elif menu == "➕ Voeg Vraag Toe":
    st.title("Admin: Database Uitbreiden")
    with st.form("add_form", clear_on_submit=True):
        t = st.selectbox("Type Vraag", ["mc", "check"], help="mc = Meerkeuze diagnose. check = Meerdere symptomen aanvinken.")
        vraag_tekst = st.text_input("Vraag of Diagnose")
        opties_tekst = st.text_input("Alle Opties (scheiden met een komma)")
        antwoord_tekst = st.text_input("Het Juiste Antwoord (bij meerdere: komma-gescheiden)")
        uitleg_tekst = st.text_area("Uitleg")
        
        submit = st.form_submit_button("Vraag Opslaan")
        if submit:
            if vraag_tekst and opties_tekst and antwoord_tekst:
                nieuwe_v = {
                    "type": t, 
                    "v": vraag_tekst, 
                    "o": opties_tekst, 
                    "a": antwoord_tekst, 
                    "u": uitleg_tekst
                }
                voeg_vraag_toe(nieuwe_v)
                st.success("Vraag toegevoegd!")
                if 'vragen_hussel' in st.session_state:
                    del st.session_state.vragen_hussel # Zorg dat nieuwe vraag in de quiz komt
            else:
                st.warning("Vul alle verplichte velden in.")
