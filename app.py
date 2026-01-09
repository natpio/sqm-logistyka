import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
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

    # CSS - Stylistyka High-Visibility
    st.markdown("""
        <style>
        .stButton button {
            height: 80px !important;
            border-radius: 15px !important;
            border: 2px solid #e0e0e0 !important;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.1) !important;
        }
        .status-badge {
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: bold;
        }
        .now-marker {
            color: #d73a49;
            font-weight: bold;
            animation: blinker 2s linear infinite;
        }
        @keyframes blinker { 50% { opacity: 0.2; } }
        </style>
        """, unsafe_allow_html=True)

    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    try:
        with st.spinner('Aktualizacja danych...'):
            df = conn.read(spreadsheet=URL, ttl="1m").dropna(how="all")
            df = df.reset_index(drop=True)

        for col in ['Data', 'Godzina', 'Hala', 'Auto', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'zrzut z currenta', 'NOTATKA']:
            if col not in df.columns: df[col] = ""
            df[col] = df[col].astype(str).replace('nan', '')

        st.title("🏗️ SQM Logistics Tower")
        
        # PRZEŁĄCZNIK WIDOKU
        view = st.sidebar.radio("Nawigacja:", ["🚀 LIVE DASHBOARD", "📝 EDYCJA BAZY"])

        if view == "🚀 LIVE DASHBOARD":
            # Szybkie filtry hal
            hala_filter = st.pills("Filtruj Halę:", ["Wszystkie"] + sorted(list(df['Hala'].unique())), default="Wszystkie")
            
            display_df = df.copy()
            if hala_filter != "Wszystkie":
                display_df = display_df[display_df['Hala'] == hala_filter]
            
            # Sortowanie i podział na "Nadchodzące" i "Reszta"
            display_df = display_df.sort_values(by="Godzina")
            
            for idx, row in display_df.iterrows():
                # Logika statusu
                is_urgent = "RAMP" in row['STATUS']
                status_color = "#d73a49" if is_urgent else "#f9c000" if "TRASIE" in row['STATUS'] else "#28a745"
                
                with st.container(border=True):
                    # Główny wiersz: Czas, Projekt i Status
                    col_time, col_main, col_stat = st.columns([1, 3, 1])
                    
                    with col_time:
                        st.markdown(f"### ⏱️ {row['Godzina']}")
                        if is_urgent: st.markdown('<p class="now-marker">● POD RAMPĄ</p>', unsafe_allow_html=True)
                    
                    with col_main:
                        st.markdown(f"## {row['Nazwa Projektu']}")
                        st.markdown(f"**Auto:** {row['Auto']} | **Hala:** {row['Hala']} | **Kod:** {row['Nr Proj.']}")
                    
                    with col_stat:
                        st.write("##")
                        st.markdown(f'<div style="background:{status_color}; color:white; text-align:center; padding:10px; border-radius:10px; font-weight:bold;">{row["STATUS"]}</div>', unsafe_allow_html=True)

                    # Dolny wiersz: Interaktywne kafle linków
                    st.write("---")
                    b1, b2, b3, b4 = st.columns(4)
                    
                    # Logika przycisków - jeśli brak linku, przycisk jest nieaktywny
                    def link_btn(col, label, emoji, link, key_id):
                        if "http" in str(link):
                            col.link_button(f"{emoji} {label}", link, use_container_width=True)
                        else:
                            col.button(f"❌ {label}", disabled=True, key=key_id, use_container_width=True)

                    link_btn(b1, "FOTO", "📸", row['zdjęcie po załadunku'], f"f_{idx}")
                    link_btn(b2, "SPIS", "📋", row['spis casów'], f"s_{idx}")
                    link_btn(b3, "CURRENT", "🖼️", row['zrzut z currenta'], f"c_{idx}")
                    
                    with b4:
                        if row['NOTATKA'].strip():
                            with st.expander("📝 NOTATKA"):
                                st.info(row['NOTATKA'])
                        else:
                            st.button("🚫 BRAK NOTATKI", disabled=True, key=f"n_{idx}", use_container_width=True)

        else:
            # TRYB EDYCJI (Tabela)
            st.warning("Używaj tego widoku tylko do wprowadzania zmian w danych.")
            edited_df = st.data_editor(df, use_container_width=True, key="main_editor")
            if st.button("💾 ZAPISZ ZMIANY W GOOGLE SHEETS", type="primary", use_container_width=True):
                conn.update(spreadsheet=URL, data=edited_df)
                st.cache_data.clear()
                st.rerun()

    except Exception as e:
        st.error(f"Problem z danymi: {e}")

    if st.sidebar.button("Wyloguj"):
        controller.remove("sqm_login_key")
        st.rerun()
