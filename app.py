import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. KONFIGURACJA (KRYTYCZNIE CZYSTA)
st.set_page_config(page_title="SQM RADAR", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #050505; } /* Głęboka czerń dla kontrastu */
    
    /* Nagłówek Hali - Duży i czytelny */
    .hala-header {
        background: #1f77b4;
        color: white;
        padding: 20px;
        text-align: center;
        font-size: 30px;
        font-weight: 900;
        border-radius: 10px 10px 0 0;
        margin-bottom: 2px;
    }

    /* Karta transportu - Minimalizm */
    .truck-row {
        background: #1a1a1a;
        border-bottom: 2px solid #333;
        padding: 15px;
        margin-bottom: 5px;
    }
    
    .time-large { color: #f9c000; font-size: 24px; font-weight: bold; font-family: monospace; }
    .plate-large { color: white; font-size: 26px; font-weight: 900; }
    .project-sub { color: #888; font-size: 14px; text-transform: uppercase; }
    
    /* Statusy - Wyraźne kropki */
    .dot { height: 15px; width: 15px; border-radius: 50%; display: inline-block; margin-right: 10px; }
    .dot-red { background-color: #ff4b4b; box-shadow: 0 0 10px #ff4b4b; }
    .dot-yellow { background-color: #f9c000; box-shadow: 0 0 10px #f9c000; }
    .dot-green { background-color: #00c853; box-shadow: 0 0 10px #00c853; }
    </style>
    """, unsafe_allow_html=True)

# 2. POBIERANIE DANYCH
try:
    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=URL, ttl="1m")

    # Czyszczenie danych pod kątem czytelności
    df['Hala'] = df['Hala'].astype(str).str.strip()
    df['Godzina'] = df['Godzina'].astype(str).str[:5] # Tylko HH:MM
    
    # Wybór dnia (tylko dzisiaj, żeby nie zaśmiecać)
    today = st.selectbox("📅 WYBIERZ DZIEŃ OPERACYJNY", options=df['Data'].unique())
    view_df = df[df['Data'] == today]

    # 3. UKŁAD KOLUMNOWY (KAŻDA HALA TO KOLUMNA)
    hale_names = sorted([h for h in view_df['Hala'].unique() if h and h != 'nan'])
    cols = st.columns(len(hale_names))

    for i, h_name in enumerate(hale_names):
        with cols[i]:
            st.markdown(f'<div class="hala-header">HALA {h_name}</div>', unsafe_allow_html=True)
            
            h_data = view_df[view_df['Hala'] == h_name].sort_values('Godzina')
            
            for _, row in h_data.iterrows():
                # Logika koloru statusu
                status = str(row['STATUS']).upper()
                dot_class = "dot-yellow"
                if "RAMP" in status: dot_class = "dot-red"
                elif "ROZŁADOWANY" in status: dot_class = "dot-green"
                
                # Render wiersza transportu
                st.markdown(f"""
                    <div class="truck-row">
                        <div class="time-large">{row['Godzina']}</div>
                        <div class="plate-large">{row['Auto']}</div>
                        <div style="margin: 5px 0;">
                            <span class="{dot_class}"></span>
                            <span style="color: white; font-weight: bold; font-size: 12px;">{status}</span>
                        </div>
                        <div class="project-sub">{row['Nr Proj.']} | {row['Kierowca']}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                # Tylko jeden, najważniejszy przycisk
                if "http" in str(row['spis casów']):
                    st.link_button(f"📋 SPIS: {row['Nazwa Projektu']}", row['spis casów'], use_container_width=True)

except Exception as e:
    st.error("Błąd bazy danych. Sprawdź połączenie z arkuszem.")
