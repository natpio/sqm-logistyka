import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. KONFIGURACJA WIDOKU
st.set_page_config(page_title="SQM TERMINAL", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #050505; }
    /* Styl dużego numeru slotu */
    .slot-card {
        background: #111;
        border: 2px solid #333;
        border-radius: 20px;
        padding: 25px;
        text-align: center;
        margin-bottom: 20px;
    }
    .status-active { border-color: #ff4b4b; background: #220a0a; }
    .status-transit { border-color: #f9c000; background: #221d0a; }
    
    .big-plate { font-size: 42px; font-weight: 900; color: white; line-height: 1; margin: 10px 0; }
    .big-time { font-size: 24px; color: #f9c000; font-family: monospace; font-weight: bold; }
    .label { font-size: 12px; color: #666; text-transform: uppercase; letter-spacing: 2px; }
    </style>
    """, unsafe_allow_html=True)

# 2. BEZPIECZNE POBIERANIE DANYCH
URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    df = conn.read(spreadsheet=URL, ttl="1m")
    
    # NAPRAWA BŁĘDU (TypeError)
    # Zamieniamy wszystko na tekst i czyścimy puste wartości przed sortowaniem
    df['Hala'] = df['Hala'].astype(str).replace(['nan', 'None'], '').str.strip()
    
    st.title("🛰️ SQM YARD TERMINAL")
    
    # Filtry na górze - proste i czytelne
    c1, c2 = st.columns(2)
    with c1:
        day = st.selectbox("WYBIERZ DZIEŃ:", options=df['Data'].unique())
    with c2:
        # Tutaj naprawiona linia, która powodowała błąd:
        hale_options = sorted([h for h in df['Hala'].unique() if h])
        selected_hala = st.selectbox("WYBIERZ HALĘ:", options=hale_options)

    # Filtrowanie danych
    view_df = df[(df['Data'] == day) & (df['Hala'] == selected_hala)]
    
    # 3. WIDOK TERMINALA (Siatka Slotów)
    st.write("---")
    
    # Grupowanie po numerze slotu (np. 1-10)
    # Tworzymy listę slotów na podstawie tego co jest w bazie
    available_slots = sorted(view_df['Nr Slotu'].unique(), key=lambda x: str(x))
    
    if not available_slots:
        st.info("Brak zaplanowanych transportów na tę halę w wybranym dniu.")
    else:
        grid = st.columns(3) # 3 wielkie sloty w rzędzie
        for idx, s_num in enumerate(available_slots):
            trucks_in_slot = view_df[view_df['Nr Slotu'] == s_num]
            
            for _, row in trucks_in_slot.iterrows():
                status = str(row['STATUS']).upper()
                card_class = "slot-card"
                if "RAMP" in status: card_class += " status-active"
                if "TRASIE" in status: card_class += " status-transit"
                
                with grid[idx % 3]:
                    st.markdown(f"""
                        <div class="{card_class}">
                            <div class="label">SLOT {s_num}</div>
                            <div class="big-time">{str(row['Godzina'])[:5]}</div>
                            <div class="big-plate">{row['Auto']}</div>
                            <div style="color:white; font-weight:bold;">{row['Kierowca']}</div>
                            <div style="font-size:12px; color:#888; margin-top:10px;">{row['Nr Proj.']}</div>
                            <div style="color:#1f77b4; font-size:14px; font-weight:bold;">{status}</div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # Przyciski akcji - tylko jeśli są linki
                    if "http" in str(row['spis casów']):
                        st.link_button("📋 SPIS ŁADUNKU", row['spis casów'], use_container_width=True)

except Exception as e:
    st.error(f"Problem z arkuszem: {e}")
