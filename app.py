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
        st.title("🏗️ SQM Logistics - Control Tower")
        st.text_input("Hasło:", type="password", on_change=password_entered, key="password")
        return False
    return True

if check_password():
    st.set_page_config(page_title="SQM CONTROL TOWER", layout="wide", initial_sidebar_state="collapsed")

    # CSS - Nowoczesne, duże karty operacyjne
    st.markdown("""
        <style>
        .stMetric { background-color: #ffffff; border: 1px solid #dfe3e8; padding: 15px; border-radius: 12px; }
        
        /* Styl karty głównej */
        .op-card {
            background-color: #ffffff;
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            border: 1px solid #e1e4e8;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            border-left: 12px solid #1f77b4;
        }
        
        /* Kolory statusów dla kart */
        .status-ramp { border-left-color: #d73a49 !important; background-color: #fff5f5; }
        .status-trasie { border-left-color: #f9c000 !important; background-color: #fffdf2; }
        
        /* Nagłówki w karcie */
        .proj-name { font-size: 26px !important; font-weight: 800; color: #1a1c21; line-height: 1.2; margin-bottom: 5px; }
        .proj-nr { font-size: 18px; color: #586069; font-weight: 400; }
        
        /* Slot czasowy */
        .slot-badge {
            background-color: #1a1c21;
            color: white;
            padding: 8px 15px;
            border-radius: 8px;
            font-size: 20px;
            font-weight: 700;
            float: right;
        }
        
        .info-row { margin-top: 15px; font-size: 16px; color: #24292e; }
        .label { color: #6a737d; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; }
        </style>
        """, unsafe_allow_html=True)

    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    try:
        with st.spinner('Synchronizacja...'):
            df = conn.read(spreadsheet=URL, ttl="1m").dropna(how="all")
            df = df.reset_index(drop=True)

        all_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'zrzut z currenta', 'SLOT', 'NOTATKA']
        for col in all_cols:
            if col not in df.columns: df[col] = ""
            df[col] = df[col].astype(str).replace('nan', '')

        st.title("🏗️ SQM Control Tower")
        
        view_mode = st.radio("Widok:", ["📦 OPERACYJNY (Karty)", "📊 EDYCJA (Tabela)"], horizontal=True)

        if view_mode == "📦 OPERACYJNY (Karty)":
            st.write("##")
            c_search, c_filter = st.columns([2, 1])
            search = c_search.text_input("🔍 Szybkie szukanie (Projekt, Auto, Kierowca):", placeholder="Wpisz cokolwiek...")
            
            # Filtrowanie
            display_df = df.copy()
            if search:
                display_df = display_df[display_df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]
            
            # Sortowanie po godzinie slotu
            display_df = display_df.sort_values(by="Godzina")

            for _, row in display_df.iterrows():
                # Dobór klasy koloru
                card_style = "op-card"
                if "RAMP" in row['STATUS']: card_style += " status-ramp"
                if "TRASIE" in row['STATUS']: card_style += " status-trasie"

                st.markdown(f"""
                <div class="{card_style}">
                    <div class="slot-badge">⏰ {row['Godzina']}</div>
                    <div class="proj-name">{row['Nazwa Projektu']}</div>
                    <div class="proj-nr">PROJEKT: {row['Nr Proj.']} | HALA: {row['Hala']}</div>
                    
                    <div class="info-row">
                        <span class="label">Transport:</span> <b>{row['Auto']}</b> ({row['Kierowca']}) | {row['Przewoźnik']}<br>
                        <span class="label">Status:</span> {row['STATUS']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # PRZYCISKI AKCJI - DUŻE I WYGODNE
                col1, col2, col3, col4 = st.columns(4)
                
                if row['zdjęcie po załadunku']:
                    col1.link_button("📸 FOTO ZAŁADUNEK", row['zdjęcie po załadunku'], use_container_width=True, type="secondary")
                if row['spis casów']:
                    col2.link_button("📋 SPIS TOWARU", row['spis casów'], use_container_width=True, type="secondary")
                if row['zrzut z currenta']:
                    col3.link_button("🖼️ CURRENT", row['zrzut z currenta'], use_container_width=True, type="secondary")
                if row['NOTATKA'] and row['NOTATKA'].strip() != "":
                    with col4.expander("📝 NOTATKA"):
                        st.info(row['NOTATKA'])
                
                st.markdown("<br>", unsafe_allow_html=True)

        else:
            # TRYB TABELI (Twoja sprawdzona edycja)
            st.info("Tryb edycji danych. Pamiętaj o kliknięciu ZAPISZ na dole.")
            column_cfg = {
                "STATUS": st.column_config.SelectboxColumn("STATUS", options=["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ status-planned"]),
                "spis casów": st.column_config.LinkColumn("📋 Spis"),
                "zdjęcie po załadunku": st.column_config.LinkColumn("📸 Foto"),
                "zrzut z currenta": st.column_config.LinkColumn("🖼️ Current"),
                "SLOT": st.column_config.LinkColumn("⏰ SLOT"),
                "NOTATKA": st.column_config.TextColumn("📝 NOTATKA")
            }
            edited_df = st.data_editor(df, use_container_width=True, column_config=column_cfg, key="editor")
            
            if st.button("💾 ZAPISZ ZMIANY W BAZIE", type="primary", use_container_width=True):
                conn.update(spreadsheet=URL, data=edited_df)
                st.cache_data.clear()
                st.success("Zapisano!")
                st.rerun()

    except Exception as e:
        st.error(f"Błąd: {e}")

    if st.sidebar.button("Wyloguj"):
        controller.remove("sqm_login_key")
        st.rerun()
