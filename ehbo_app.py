import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random
import re

# 1. Pagina configuratie
icon_url = "https://githubusercontent.com"

st.set_page_config(page_title="EHBO Expert", page_icon="🚑", layout="centered")

# 2. Styling & Dark Mode Fix
st.markdown(f"""
    <style>
        /* Forceer leesbare kleuren voor Dark & Light mode */
        .stApp {{ background-color: white; color: #1f1f1f; }}
        h1, h2, h3, h4, p, span, .stMarkdown {{ color: #1f1f1f !important; }}
        
        /* MC Spacing verkleinen */
        div[role='radiogroup'] {{ 
            gap: 0.5rem !important; 
            padding: 10px !important;
            background-color: #f8f9fa;
            border-radius: 10px;
        }}
        div.stRadio > div {{ padding: 2px 0px !important; }}

        /* Button Styling */
        .stButton button {{
            width: 100%; border-radius: 12px; height: 3em;
            font-weight: bold; border: 2px solid #ff4b4b;
        }}
        
        /* Expander styling */
        .stExpander {{ border: 2px solid #ff4b4b; border-radius: 12px; background-color: #fffafa; }}
    </style>
""", unsafe_allow_html=True)

# 3. Verbinding
conn = st.connection("gsheets", type=GSheetsConnection)

def laad_data():
    try:
        df = conn.read(ttl="1m")
        # Zorg dat de kolom 'medisch' bestaat, ook als deze leeg is in de sheet
        if 'medisch' not in df.columns:
            df['medisch'] = None
        return df.dropna(subset=['type', 'v']).to_dict('records')
    except Exception as e:
        st.error(f"Fout bij laden data: {e}")
        return []

def formatteer_uitleg(tekst):
    if not tekst or pd.isna(tekst): return "Geen uitleg beschikbaar."
    tekst = str(tekst).strip()
    tekst = re.sub(r"(Stappen.*?:)", r"\n\n### 📋 \1\n", tekst)
    tekst = re.sub(r"(?<!\d)([1-9])\.\s+", r"\n\1. ", tekst)
    return tekst

# 4. Navigatie
menu = st.sidebar.radio("Navigatie:", ["📝 Doe de Quiz", "➕ Voeg Vraag Toe"])

if menu == "📝 Doe de Quiz":
    st.title("EHBO Kennis Toets")
    
    if 'vragen_hussel' not in st.session_state:
        data = laad_data()
        if data:
            random.shuffle(data)
            st.session_state.vragen_hussel = data
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
        v = vragen[st.session_state.index]
        st.caption(f"Vraag {st.session_state.index + 1} van {len(vragen)}")
        st.markdown(f"#### {v['v']}")

        opties = [o.strip() for o in str(v["o"]).split(",")]
        
        if v["type"] == "mc":
            keuze = st.radio("Kies het antwoord:", opties, key=f"mc_{st.session_state.index}", disabled=st.session_state.beantwoord, label_visibility="collapsed")
        else:
            gekozen = [o for o in opties if st.checkbox(o, key=f"ch_{o}_{st.session_state.index}", disabled=st.session_state.beantwoord)]

        if not st.session_state.beantwoord:
            if st.button("Bevestigen"):
                st.session_state.beantwoord = True
                st.rerun()
        else:
            # Check logica
            is_correct = False
            if v["type"] == "mc":
                is_correct = (keuze == v["a"])
            else:
                is_correct = (sorted(gekozen) == sorted([a.strip() for a in str(v["a"]).split(",")]))

            if is_correct: st.success("✅ Correct!")
            else:
                st.error(f"❌ Onjuist. Het juiste antwoord is: **{v['a']}**")
                if v not in st.session_state.fouten: st.session_state.fouten.append(v)
            
            with st.expander("📖 Bekijk uitleg en stappenplan", expanded=True):
                st.markdown(formatteer_uitleg(v["u"]))
                # Medische Verdieping Sectie
                med_uitleg = v.get('medisch')
                if med_uitleg and not pd.isna(med_uitleg):
                    st.markdown("---")
                    with st.popover("🔬 Waarom gebeurt dit? (Medische uitleg)"):
                        st.info(med_uitleg)

            if st.button("Volgende Vraag ➡️"):
                st.session_state.index += 1
                st.session_state.beantwoord = False
                st.rerun()

elif menu == "➕ Voeg Vraag Toe":
    st.title("Beheer")
    with st.form("add_form", clear_on_submit=True):
        t = st.selectbox("Type", ["mc", "check"])
        v_t = st.text_input("Vraag")
        o_t = st.text_input("Opties (komma-gescheiden)")
        a_t = st.text_input("Antwoord")
        u_t = st.text_area("Uitleg & Stappen")
        m_t = st.text_area("Medische verdieping (optioneel)")
        if st.form_submit_button("Opslaan"):
            conn.update(data=pd.concat([conn.read(), pd.DataFrame([{"type":t,"v":v_t,"o":o_t,"a":a_t,"u":u_t,"medisch":m_t}])], ignore_index=True))
            st.success("Opgeslagen!")
