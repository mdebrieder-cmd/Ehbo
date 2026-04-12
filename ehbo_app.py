import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random

st.set_page_config(page_title="EHBO Expert", page_icon="🚑")

# Injectie voor Android App-instellingen
st.markdown(f"""
    <head>
        <!-- De naam die op het startscherm komt -->
        <meta name="apple-mobile-web-app-title" content="EHBO Expert">
        <meta name="application-name" content="EHBO Expert">
        
        <!-- Het icoon voor Android/iOS -->
        <link rel="apple-touch-icon" href="http://github.com/mdebrieder-cmd/Ehbo/blob/main/ehbo_icon.jpeg">
        <link rel="icon" sizes="192x192" href="http://github.com/mdebrieder-cmd/Ehbo/blob/main/ehbo_icon.jpeg">
        
        <!-- Zorgt dat het fullscreen opent zonder browserbalk -->
        <meta name="mobile-web-app-capable" content="yes">
    </head>
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
    st.title("🚑 EHBO Diagnose Quiz")
    
    # Initialiseer session state
    if 'vragen_hussel' not in st.session_state:
        data = laad_data()
        if data:
            random.shuffle(data)
            st.session_state.vragen_hussel = data
            st.session_state.index = 0
            st.session_state.fouten = [] # Lijst voor foute vragen
            st.session_state.fase = "normaal" # 'normaal' of 'herhalen'
        else:
            st.session_state.vragen_hussel = []

    vragen = st.session_state.vragen_hussel

    if not vragen and not st.session_state.get('fouten'):
        st.info("De database is leeg of je hebt alle vragen goed!")
    elif st.session_state.index >= len(vragen):
        # Einde van een ronde bereikt
        if st.session_state.fouten:
            st.warning(f"Ronde klaar! Je hebt {len(st.session_state.fouten)} vragen fout. We gaan deze nu herhalen.")
            if st.button("Start Herhaling"):
                st.session_state.vragen_hussel = st.session_state.fouten.copy()
                st.session_state.fouten = []
                st.session_state.index = 0
                st.session_state.fase = "herhalen"
                st.rerun()
        else:
            st.balloons()
            st.header("🏆 Toets Voltooid!")
            st.success("Je hebt alle vragen correct beantwoord!")
            if st.button("Helemaal Opnieuw Starten"):
                for key in ['vragen_hussel', 'index', 'fouten', 'fase']:
                    if key in st.session_state: del st.session_state[key]
                st.rerun()
    else:
        # Toon huidige vraag
        v = vragen[st.session_state.index]
        status_tekst = "Herhaling" if st.session_state.fase == "herhalen" else "Quiz"
        st.subheader(f"{status_tekst}: Vraag {st.session_state.index + 1} van {len(vragen)}")
        
        with st.container(border=True):
            st.markdown(f"### {v['v']}")

        opties = [o.strip() for o in str(v["o"]).split(",")]
        
        if v["type"] == "mc":
            keuze = st.radio("Wat is de juiste diagnose?", opties, key=f"mc_{v['v']}_{st.session_state.index}")
            
            if st.button("Antwoord Bevestigen"):
                if keuze == v["a"]:
                    st.success(f"✅ Correct! {v['u']}")
                else:
                    st.error(f"❌ Onjuist. \n\nUitleg: {v['u']}")
                    if v not in st.session_state.fouten:
                        st.session_state.fouten.append(v)
                
                st.session_state.index += 1
                st.button("Volgende")

        elif v["type"] == "check":
            st.write("Selecteer alle symptomen:")
            gekozen = []
            for o in opties:
                if st.checkbox(o, key=f"ch_{o}_{st.session_state.index}"):
                    gekozen.append(o)
            
            if st.button("Antwoord Bevestigen"):
                juiste_antwoorden = sorted([a.strip() for a in str(v["a"]).split(",")])
                if sorted(gekozen) == juiste_antwoorden:
                    st.success(f"✅ Correct! {v['u']}")
                else:
                    st.error(f"❌ Onjuist. \n\nUitleg: {v['u']}")
                    if v not in st.session_state.fouten:
                        st.session_state.fouten.append(v)
                
                st.session_state.index += 1
                st.button("Volgende")

# 6. Admin Logica (ongewijzigd)
elif menu == "➕ Voeg Vraag Toe":
    st.title("Admin: Database Uitbreiden")
    with st.form("add_form", clear_on_submit=True):
        t = st.selectbox("Type Vraag", ["mc", "check"])
        vraag_tekst = st.text_input("Vraag of Diagnose")
        opties_tekst = st.text_input("Alle Opties (scheiden met een komma)")
        antwoord_tekst = st.text_input("Het Juiste Antwoord")
        uitleg_tekst = st.text_area("Uitleg")
        
        if st.form_submit_button("Vraag Opslaan"):
            if vraag_tekst and opties_tekst and antwoord_tekst:
                nieuwe_v = {"type": t, "v": vraag_tekst, "o": opties_tekst, "a": antwoord_tekst, "u": uitleg_tekst}
                voeg_vraag_toe(nieuwe_v)
                st.success("Vraag toegevoegd!")
