import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random

# 1. Pagina configuratie
# Let op: Gebruik de RAW URL van GitHub voor het icoon
icon_url = "https://githubusercontent.com"

st.set_page_config(
    page_title="EHBO Expert",
    page_icon="🚑",
    layout="centered"
)

# 2. Injectie voor Android App-instellingen & Styling
st.markdown(f"""
    <div style="display:none">
        <head>
            <meta name="apple-mobile-web-app-title" content="EHBO Expert">
            <meta name="application-name" content="EHBO Expert">
            <link rel="apple-touch-icon" href="{icon_url}">
            <link rel="icon" sizes="192x192" href="{icon_url}">
            <meta name="mobile-web-app-capable" content="yes">
            <meta name="mobile-web-app-status-bar-style" content="black">
        </head>
    </div>
    <style>
        /* Mobielvriendelijke knoppen */
        .stButton button {{
            width: 100%;
            border-radius: 12px;
            height: 3.5em;
            font-weight: bold;
            text-transform: uppercase;
            border: 2px solid #ff4b4b;
            transition: 0.3s;
        }}
        /* Styling voor radio buttons en checkboxes */
        .stRadio div[role='radiogroup'], .stCheckbox {{
            background-color: #f1f3f6;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 10px;
        }}
        /* Feedback expander styling */
        .stExpander {{
            border: 2px solid #ff4b4b;
            border-radius: 12px;
            background-color: #fff5f5;
        }}
    </style>
""", unsafe_allow_html=True)

# 3. Verbinding met Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# 4. Hulpfuncties
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

def formatteer_stappenplan(tekst):
    """Vormt platte tekst om naar een genummerde Markdown lijst."""
    tekst = str(tekst)
    if "1." in tekst:
        tekst = tekst.replace("Stappen:", "### 📋 Stappenplan:\n")
        for i in range(1, 10):
            old = f"{i}."
            new = f"\n{i}."
            tekst = tekst.replace(old, new)
    return tekst

# 5. Navigatie menu
st.sidebar.title("🚑 EHBO Expert")
menu = st.sidebar.radio("Menu:", ["📝 Doe de Quiz", "➕ Voeg Vraag Toe"])

# 6. Quiz Logica
if menu == "📝 Doe de Quiz":
    st.title("Toets je EHBO Kennis")
    
    # Initialisatie
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
        st.info("De database is leeg. Voeg eerst vragen toe.")
    
    # Einde van de ronde
    elif st.session_state.index >= len(vragen):
        if st.session_state.fouten:
            st.warning(f"Ronde voltooid. Je hebt {len(st.session_state.fouten)} vragen onjuist beantwoord. Laten we deze herhalen.")
            if st.button("🔄 Start Herhaling"):
                st.session_state.vragen_hussel = st.session_state.fouten.copy()
                st.session_state.fouten = []
                st.session_state.index = 0
                st.session_state.fase = "herhalen"
                st.session_state.beantwoord = False
                st.rerun()
        else:
            st.balloons()
            st.success("🎉 Gefeliciteerd! Je hebt alle EHBO-vragen correct beantwoord.")
            if st.button("🏁 Helemaal Opnieuw Beginnen"):
                for key in ['vragen_hussel', 'index', 'fouten', 'fase', 'beantwoord']:
                    if key in st.session_state: del st.session_state[key]
                st.rerun()
    
    # De Vraag-interface
    else:
        v = vragen[st.session_state.index]
        titel_fase = "🔄 Herhaling" if st.session_state.fase == "herhalen" else "📖 Toets"
        st.caption(f"{titel_fase} | Vraag {st.session_state.index + 1} van {len(vragen)}")
        
        with st.container(border=True):
            st.markdown(f"### {v['v']}")

        opties = [o.strip() for o in str(v["o"]).split(",")]
        
        # MC Vraag
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
                    st.error(f"❌ Onjuist. Het juiste antwoord is: **{v['a']}**")
                    if v not in st.session_state.fouten:
                        st.session_state.fouten.append(v)
                
                with st.expander("📖 Bekijk Uitleg & Stappenplan", expanded=True):
                    st.markdown(formatteer_stappenplan(v["u"]))
                
                if st.button("Volgende Vraag ➡️"):
                    st.session_state.index += 1
                    st.session_state.beantwoord = False
                    st.rerun()

        # Checkbox Vraag
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
                    st.error(f"❌ Onjuist. De juiste opties waren: **{v['a']}**")
                    if v not in st.session_state.fouten:
                        st.session_state.fouten.append(v)
                
                with st.expander("📖 Bekijk Uitleg & Stappenplan", expanded=True):
                    st.markdown(formatteer_stappenplan(v["u"]))
                
                if st.button("Volgende Vraag ➡️"):
                    st.session_state.index += 1
                    st.session_state.beantwoord = False
                    st.rerun()

# 7. Admin Sectie
elif menu == "➕ Voeg Vraag Toe":
    st.title("Database Uitbreiden")
    st.info("Nieuwe vragen worden direct opgeslagen in de gekoppelde Google Sheet.")
    
    with st.form("add_form", clear_on_submit=True):
        t = st.selectbox("Type Vraag", ["mc", "check"], help="MC: Eén antwoord mogelijk. Check: Meerdere antwoorden mogelijk.")
        vraag_tekst = st.text_input("Vraagstelling of Casus")
        opties_tekst = st.text_input("Alle opties (scheiden met een komma)")
        antwoord_tekst = st.text_input("Het juiste antwoord (bij Check: alle juiste opties met komma)")
        uitleg_tekst = st.text_area("Uitleg en Stappenplan (gebruik 1. 2. 3. voor de lijst)")
        
        if st.form_submit_button("Opslaan"):
            if vraag_tekst and opties_tekst and antwoord_tekst:
                nieuwe_v = {"type": t, "v": vraag_tekst, "o": opties_tekst, "a": antwoord_tekst, "u": uitleg_tekst}
                voeg_vraag_toe(nieuwe_v)
                st.success("Vraag toegevoegd aan Google Sheets!")
            else:
                st.warning("Vul a.u.b. alle velden in.")
