import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# Injecteer de manifest link
st.markdown(
    f"""
    <link rel="manifest" href="https://github.io">
    """,
    unsafe_allow_html=True
)

st.set_page_config(page_title="EHBO-Expert")

# Pagina configuratie
st.set_page_config(page_title="EHBO Expert Toets", page_icon="🚑", layout="centered")

# Verbinding maken met Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def laad_data():
    # Haal de data op uit de sheet
    df = conn.read(ttl="1m")
    return df.dropna(subset=['type', 'v']) # Verwijder lege rijen

def voeg_vraag_toe(nieuwe_vraag):
    bestaande_data = conn.read()
    nieuwe_rij = pd.DataFrame([nieuwe_vraag])
    geupdate_data = pd.concat([bestaande_data, nieuwe_rij], ignore_index=True)
    conn.update(data=geupdate_data)
    st.cache_data.clear()

# Navigatie menu in de zijbalk
st.sidebar.title("Navigatie")
menu = st.sidebar.radio("Ga naar:", ["📝 Doe de Quiz", "➕ Voeg Vraag Toe"])

if menu == "📝 Doe de Quiz":
    st.title("🚑 EHBO Diagnose Quiz")
    
    vragen_df = laad_data()
    vragen = vragen_df.to_dict('records')

    if not vragen:
        st.info("De database is nog leeg. Gebruik de zijbalk om vragen toe te voegen.")
    else:
        # Session state initialiseren
        if 'index' not in st.session_state:
            st.session_state.index = 0
            st.session_state.score = 0
            st.session_state.klaar = False

        if not st.session_state.klaar:
            v = vragen[st.session_state.index]
            st.subheader(f"Vraag {st.session_state.index + 1} van {len(vragen)}")
            st.info(v["v"]) # De vraag of symptoom-omschrijving

            # Opties voorbereiden (splitsen van de komma-gescheiden tekst)
            opties = [o.strip() for o in str(v["o"]).split(",")]
            
            # Antwoord verwerking op basis van type
            if v["type"] == "mc":
                keuze = st.radio("Wat is de juiste diagnose?", opties, key=f"mc_{st.session_state.index}")
                if st.button("Antwoord Bevestigen"):
                    if keuze == v["a"]:
                        st.success(f"✅ Correct! {v['u']}")
                        st.session_state.score += 1
                    else:
                        st.error(f"❌ Onjuist. De juiste diagnose is: {v['a']}. \n\nUitleg: {v['u']}")
                    
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
                    # Vergelijk de gesorteerde lijsten van antwoorden
                    juiste_antwoorden = [a.strip() for a in str(v["a"]).split(",")]
                    if sorted(gekozen) == sorted(juiste_antwoorden):
                        st.success(f"✅ Correct! {v['u']}")
                        st.session_state.score += 1
                    else:
                        st.error(f"❌ Onjuist. De symptomen waren: {v['a']}. \n\nUitleg: {v['u']}")
                    
                    if st.session_state.index + 1 < len(vragen):
                        st.session_state.index += 1
                        st.button("Volgende Vraag")
                    else:
                        st.session_state.klaar = True
                        st.rerun()
        else:
            st.balloons()
            st.header("Toets Voltooid!")
            st.metric("Eindscore", f"{st.session_state.score} / {len(vragen)}")
            if st.button("Opnieuw Starten"):
                st.session_state.index = 0
                st.session_state.score = 0
                st.session_state.klaar = False
                st.rerun()

elif menu == "➕ Voeg Vraag Toe":
    st.title("Admin: Database Uitbreiden")
    with st.form("add_form", clear_on_submit=True):
        t = st.selectbox("Type Vraag", ["mc", "check"], help="mc = Kies de diagnose uit opties. check = Vink symptomen aan bij een diagnose.")
        v = st.text_input("De Vraag (bijv. symptomenlijst of diagnosenaam)")
        o = st.text_input("Alle Opties (scheiden met een komma)")
        a = st.text_input("Het Juiste Antwoord (bij meerdere ook scheiden met komma)")
        u = st.text_area("Uitleg (waarom is dit het juiste antwoord?)")
        
        submit = st.form_submit_button("Vraag Opslaan in Google Sheet")
        if submit:
            if v and o and a:
                nieuwe_v = {"type": t, "v": v, "o": o, "a": a, "u": u}
                voeg_vraag_toe(nieuwe_v)
                st.success("De vraag is succesvol toegevoegd aan de Google Sheet!")
            else:
                st.warning("Vul a.u.b. de velden Vraag, Opties en Antwoord in.")
            v = vragen[st.session_state.vraag_nr]
            st.subheader(f"Vraag {st.session_state.vraag_nr + 1}")
            st.write(v["v"])

            if v["type"] == "mc":
                antwoord = st.radio("Kies de juiste diagnose:", v["o"], key=f"q_{st.session_state.vraag_nr}")
                if st.button("Bevestig"):
                    if antwoord == v["a"]:
                        st.success(f"Correct! {v['u']}")
                        st.session_state.score += 1
                    else:
                        st.error(f"Onjuist. Het was: {v['a']}. {v['u']}")
                    st.session_state.vraag_nr += 1
                    st.button("Volgende vraag")
            
            else: # Checkbox type
                st.write("Selecteer alle symptomen die hierbij horen:")
                gekozen = []
                for optie in v["o"]:
                    if st.checkbox(optie, key=f"ch_{optie}_{st.session_state.vraag_nr}"):
                        gekozen.append(optie)
                
                if st.button("Bevestig"):
                    if sorted(gekozen) == sorted(v["a"]):
                        st.success(f"Correct! {v['u']}")
                        st.session_state.score += 1
                    else:
                        st.error(f"Onjuist. De juiste symptomen zijn: {', '.join(v['a'])}. {v['u']}")
                    st.session_state.vraag_nr += 1
                    st.button("Volgende vraag")
        else:
            st.balloons()
            st.success(f"Toets afgerond! Je score: {st.session_state.score}/{len(vragen)}")
            if st.button("Opnieuw starten"):
                st.session_state.vraag_nr = 0
                st.session_state.score = 0
                st.rerun()

elif keuze == "Vraag toevoegen":
    st.title("➕ Nieuwe vraag beheren")
    with st.form("vraag_form"):
        type_v = st.selectbox("Type", ["mc", "check"])
        vraag = st.text_input("Vraag of Diagnose")
        opties = st.text_input("Opties (komma-gescheiden)")
        antwoord = st.text_input("Antwoord(en) (bij meerdere: komma-gescheiden)")
        uitleg = st.text_area("Uitleg")
        
        if st.form_submit_button("Opslaan"):
            nieuwe_v = {
                "type": type_v,
                "v": vraag,
                "o": [o.strip() for o in opties.split(",")],
                "a": [a.strip() for a in antwoord.split(",")] if type_v == "check" else antwoord,
                "u": uitleg
            }
            bewaar_vraag(nieuwe_v)
            st.success("Vraag toegevoegd!")
