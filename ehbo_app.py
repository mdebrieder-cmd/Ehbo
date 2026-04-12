import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random
import re

# 1. Pagina configuratie
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
        .stButton button {{
            width: 100%;
            border-radius: 12px;
            height: 3.5em;
            font-weight: bold;
            text-transform: uppercase;
            border: 2px solid #ff4b4b;
            transition: 0.2s;
        }}
        .stRadio div[role='radiogroup'], .stCheckbox {{
            background-color: #f1f3f6;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 10px;
            border: 1px solid #e0e0e0;
        }}
        .stExpander {{
            border: 2px solid #ff4b4b;
            border-radius: 12px;
            background-color: #fffafa;
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

def formatteer_uitleg(tekst):
    """Vormt uitleg om en negeert getallen in '112' bij het maken van lijsten."""
    if not tekst or pd.isna(tekst):
        return "Geen uitleg beschikbaar."
    
    tekst = str(tekst).strip()
    
    # 1. Herken koppen zoals "Stappen bij Shock:" en maak ze Markdown-koppen
    tekst = re.sub(r"(Stappen.*?:)", r"\n\n### 📋 \1\n", tekst)
    
    # 2. Slimme herkenning van lijstitems:
    # Zoekt naar cijfer + punt + spatie, maar alleen als er GEEN ander cijfer direct voor staat (zoals bij 112)
    tekst = re.sub(r"(?<!\d)([1-9])\.\s+", r"\n\1. ", tekst)
    
    # 3. Opschonen en lijsten bouwen
    regels = [line.strip() for line in tekst.split('\n')]
    geformatteerd = ""
    for r in regels:
        if not r: continue
        # Als regel begint met "1. " t/m "9. "
        if re.match(r"^[1-9]\.\s", r): 
            geformatteerd += f"\n{r}"
        elif "###" in r:
            geformatteerd += f"\n{r}"
        else:
            # Voeg normale tekst toe met juiste spacing
            if geformatteerd.endswith("\n"):
                geformatteerd += r
            else:
                geformatteerd += f"\n\n{r}" if len(geformatteerd) > 0 else r
            
    return geformatteerd.strip()

# 5. Navigatie menu
st.sidebar.title("🚑 EHBO Expert")
menu = st.sidebar.radio("Navigatie:", ["📝 Doe de Quiz", "➕ Voeg Vraag Toe"])

# 6. Quiz Logica
if menu == "📝 Doe de Quiz":
    st.title("EHBO Kennis Toets")
    
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
            st.warning(f"Ronde voltooid. Je hebt {len(st.session_state.fouten)} vragen onjuist. We herhalen deze nu.")
            if st.button("🔄 Start Herhaling"):
                st.session_state.vragen_hussel = st.session_state.fouten.copy()
                st.session_state.fouten = []
                st.session_state.index = 0
                st.session_state.fase = "herhalen"
                st.session_state.beantwoord = False
                st.rerun()
        else:
            st.balloons()
            st.header("🏆 Toets Voltooid!")
            st.success("Gefeliciteerd! Je hebt alles correct beantwoord.")
            if st.button("🏁 Helemaal Opnieuw Beginnen"):
                for key in ['vragen_hussel', 'index', 'fouten', 'fase', 'beantwoord']:
                    if key in st.session_state: del st.session_state[key]
                st.rerun()
    
    else:
        v = vragen[st.session_state.index]
        titel = "🔄 Herhaling" if st.session_state.fase == "herhalen" else "📖 Toets"
        st.caption(f"{titel} | Vraag {st.session_state.index + 1} van {len(vragen)}")
        
        with st.container(border=True):
            st.markdown(f"#### {v['v']}")

        opties = [o.strip() for o in str(v["o"]).split(",")]
        
        if v["type"] == "mc":
            keuze = st.radio("Selecteer het juiste antwoord:", opties, key=f"mc_{st.session_state.index}", disabled=st.session_state.beantwoord)
            
            if not st.session_state.beantwoord:
                if st.button("Bevestigen"):
                    st.session_state.beantwoord = True
                    st.rerun()
            else:
                if keuze == v["a"]:
                    st.success("✅ Correct!")
                else:
                    st.error(f"❌ Onjuist. Het juiste antwoord is: **{v['a']}**")
                    if v not in st.session_state.fouten:
                        st.session_state.fouten.append(v)
                
                with st.expander("📖 Bekijk uitleg en stappenplan", expanded=True):
                    st.markdown(formatteer_uitleg(v["u"]))
                
                if st.button("Volgende Vraag ➡️"):
                    st.session_state.index += 1
                    st.session_state.beantwoord = False
                    st.rerun()

        elif v["type"] == "check":
            st.write("Selecteer alle opties die van toepassing zijn:")
            gekozen = []
            for i, o in enumerate(opties):
                if st.checkbox(o, key=f"ch_{i}_{st.session_state.index}", disabled=st.session_state.beantwoord):
                    gekozen.append(o)
            
            if not st.session_state.beantwoord:
                if st.button("Bevestigen"):
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
                
                with st.expander("📖 Bekijk uitleg en stappenplan", expanded=True):
                    st.markdown(formatteer_uitleg(v["u"]))
                
                if st.button("Volgende Vraag ➡️"):
                    st.session_state.index += 1
                    st.session_state.beantwoord = False
                    st.rerun()

# 7. Admin: Vragen toevoegen
elif menu == "➕ Voeg Vraag Toe":
    st.title("Database Beheer")
    with st.form("add_form", clear_on_submit=True):
        t = st.selectbox("Vraagtype", ["mc", "check"])
        vraag_tekst = st.text_input("Vraagstelling")
        opties_tekst = st.text_input("Opties (komma-gescheiden)")
        antwoord_tekst = st.text_input("Juist antwoord (komma-gescheiden bij meerdere)")
        uitleg_tekst = st.text_area("Uitleg (gebruik 'Stappen bij [Diagnose]:' voor meerdere lijsten)")
        
        if st.form_submit_button("Vraag Opslaan"):
            if vraag_tekst and opties_tekst and antwoord_tekst:
                nieuwe_v = {"type": t, "v": vraag_tekst, "o": opties_tekst, "a": antwoord_tekst, "u": uitleg_tekst}
                voeg_vraag_toe(nieuwe_v)
                st.success("Vraag succesvol toegevoegd!")
