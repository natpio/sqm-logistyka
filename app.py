import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from streamlit_cookies_controller import CookieController

# 1. LOGOWANIE
controller = CookieController()

def check_password():
    saved_auth = controller.get("sqm_login_key")
    if saved_auth == "Czaman2026":
        st.session_state["password_correct"] = True
        return True
    def password_entered():
        if st.session_state["password"] == "Czaman2026":
            st.session_state["password_correct"] = True
            controller.set("sqm_login_key", "Czaman2026", max_age=3600*24*30)
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
    if "password_correct" not in st.session_state:
        st.title("🏗️ SQM Control Tower")
        st.text_input("Hasło:", type="password", on_change=password_entered, key="password")
        return False
    return True

if check_password():
    st.set_page_config(page_title="SQM CONTROL TOWER", layout="wide", initial_sidebar_state="collapsed")

    # CSS - Interfejs Dashboardowy
    st.markdown("""
        <style>
        .stButton button { height: 60px !important; border-radius: 10px !important; font-size: 16px !important; }
        .hala-section { background-color: #f8f9fa; padding: 20px; border-radius: 20px; border: 1px solid #dee2e6; margin-bottom: 25px; }
        .hala-title { font-size: 24px !important; font-weight: bold; color: #1f77b4; margin-bottom: 15px; border-bottom: 2px solid #1f77b4; }
        .cargo-card { background: white; border-radius: 12px; padding: 15px; border-top: 5px solid #1f77b4; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }
        .urgent-card { border-top: 5px solid #d73a49 !important; background-color: #fff9f9; }
        </style>
        """, unsafe_allow_html=True)

    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    try:
        df = conn.read(spreadsheet=URL, ttl="1m").dropna(how="all")
        df = df.reset_index(drop=True)
        all_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'zrzut z currenta', 'SLOT', 'NOTATKA']
        for col in all_cols:
            if col not in df.columns: df[col] = ""
            df[col] = df[col].astype(str).replace('nan', '')

        st.title("🏗️ SQM Logistics Radar")
        
        mode = st.radio("TRYB:", ["🛰️ RADAR HAL", "📊 EDYCJA BAZY"], horizontal=True)

        if mode == "🛰️ RADAR HAL":
            # Inteligentne grupowanie po halach
            hale = sorted([h for h in df['Hala'].unique() if h and h.strip() != ""])
            
            for h_name in hale:
                st.markdown(f'<div class="hala-title">📍 HALA {h_name}</div>', unsafe_allow_html=True)
                hala_df = df[df['Hala'] == h_name].sort_values(by="Godzina")
                
                # Wyświetlamy karty w kolumnach (max 3 w rzędzie)
                cols = st.columns(3)
                for i, (_, row) in enumerate(hala_df.iterrows()):
                    col_idx = i % 3
                    with cols[col_idx]:
                        is_ramp = "RAMP" in row['STATUS'].upper()
                        card_class = "urgent-card" if is_ramp else ""
                        
                        with st.container(border=True):
                            st.markdown(f"**{row['Godzina']}** | {row['STATUS']}")
                            st.markdown(f"### {row['Nazwa Projektu']}")
                            st.write(f"🚚 {row['Auto']} ({row['Kierowca']})")
                            
                            # Akcje (Expander zamiast miliona przycisków na raz)
                            with st.expander("🛠️ NARZĘDZIA ŁADUNKU"):
                                b1, b2 = st.columns(2)
                                if "http" in row['zdjęcie po załadunku']: b1.link_button("📸 FOTO", row['zdjęcie po załadunku'], use_container_width=True)
                                if "http" in row['spis casów']: b2.link_button("📋 SPIS", row['spis casów'], use_container_width=True)
                                
                                b3, b4 = st.columns(2)
                                if "http" in row['zrzut z currenta']: b3.link_button("🖼️ CURR", row['zrzut z currenta'], use_container_width=True)
                                if row['NOTATKA'].strip():
                                    st.info(row['NOTATKA'])
                st.divider()

        else:
            # KLASYCZNA TABELA (EDYCYJNA)
            st.write("### 📝 Edycja danych źródłowych")
            column_cfg = {
                "STATUS": st.column_config.SelectboxColumn("STATUS", options=["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY"]),
                "spis casów": st.column_config.LinkColumn("📋 Spis"),
                "zdjęcie po załadunku": st.column_config.LinkColumn("📸 Foto"),
                "zrzut z currenta": st.column_config.LinkColumn("🖼️ Current"),
                "SLOT": st.column_config.LinkColumn("⏰ SLOT")
            }
            edited_df = st.data_editor(df, use_container_width=True, column_config=column_cfg)
            if st.button("💾 ZAPISZ ZMIANY", type="primary", use_container_width=True):
                conn.update(spreadsheet=URL, data=edited_df)
                st.cache_data.clear()
                st.rerun()

    except Exception as e:
        st.error(f"Błąd: {e}")

    if st.sidebar.button("Wyloguj"):
        controller.remove("sqm_login_key")
        st.rerun()
