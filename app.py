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

    # CSS - Minimalistyczny styl dla maksymalnej czytelności na hali
    st.markdown("""
        <style>
        .stButton button {
            height: 70px !important;
            font-size: 20px !important;
            border-radius: 12px !important;
        }
        .main-header { font-size: 32px !important; font-weight: bold; color: #1f77b4; }
        .slot-text { font-size: 24px !important; font-weight: bold; background-color: #f0f2f6; padding: 10px; border-radius: 8px; }
        </style>
        """, unsafe_allow_html=True)

    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    try:
        with st.spinner('Pobieranie danych...'):
            df = conn.read(spreadsheet=URL, ttl="1m").dropna(how="all")
            df = df.reset_index(drop=True)

        all_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'zrzut z currenta', 'SLOT', 'NOTATKA']
        for col in all_cols:
            if col not in df.columns: df[col] = ""
            df[col] = df[col].astype(str).replace('nan', '')

        st.title("🏗️ SQM Control Tower")
        view_mode = st.radio("Widok:", ["📦 OPERACYJNY (Karty)", "📊 EDYCJA (Tabela)"], horizontal=True)

        if view_mode == "📦 OPERACYJNY (Karty)":
            search = st.text_input("🔍 Szukaj ładunku:", placeholder="Projekt, Auto, Hala...")
            
            display_df = df.copy()
            if search:
                display_df = display_df[display_df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]
            
            display_df = display_df.sort_values(by="Godzina")

            for idx, row in display_df.iterrows():
                with st.container(border=True):
                    # NAGŁÓWEK: Godzina i Nazwa Projektu
                    c_head1, c_head2 = st.columns([1, 4])
                    c_head1.markdown(f"### ⏰ {row['Godzina']}")
                    c_head2.markdown(f"### {row['Nazwa Projektu']}")
                    
                    # SZCZEGÓŁY
                    st.markdown(f"**PROJEKT:** {row['Nr Proj.']} | **HALA:** {row['Hala']} | **TRANSPORT:** {row['Auto']}")
                    st.markdown(f"**STATUS:** {row['STATUS']}")

                    # DUŻE PRZYCISKI - każdy z unikalnym kluczem idx
                    b1, b2, b3, b4 = st.columns(4)
                    
                    if "http" in row['zdjęcie po załadunku']:
                        b1.link_button("📸 FOTO", row['zdjęcie po załadunku'], use_container_width=True)
                    else:
                        b1.button("❌ BRAK FOTO", disabled=True, key=f"bf_{idx}", use_container_width=True)

                    if "http" in row['spis casów']:
                        b2.link_button("📋 SPIS", row['spis casów'], use_container_width=True)
                    else:
                        b2.button("❌ BRAK SPISU", disabled=True, key=f"bs_{idx}", use_container_width=True)

                    if "http" in row['zrzut z currenta']:
                        b3.link_button("🖼️ CURRENT", row['zrzut z currenta'], use_container_width=True)
                    else:
                        b3.button("❌ BRAK CURR", disabled=True, key=f"bc_{idx}", use_container_width=True)

                    if row['NOTATKA'].strip():
                        with b4.expander("📝 NOTATKA"):
                            st.info(row['NOTATKA'])
                st.write("") # Odstęp między kartami

        else:
            # TRYB EDYCJI
            column_cfg = {
                "STATUS": st.column_config.SelectboxColumn("STATUS", options=["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ status-planned"]),
                "spis casów": st.column_config.LinkColumn("📋 Spis"),
                "zdjęcie po załadunku": st.column_config.LinkColumn("📸 Foto"),
                "zrzut z currenta": st.column_config.LinkColumn("🖼️ Current"),
                "SLOT": st.column_config.LinkColumn("⏰ SLOT"),
                "NOTATKA": st.column_config.TextColumn("📝 NOTATKA")
            }
            edited_df = st.data_editor(df, use_container_width=True, column_config=column_cfg, key="editor_v3")
            
            if st.button("💾 ZAPISZ ZMIANY", type="primary", use_container_width=True):
                conn.update(spreadsheet=URL, data=edited_df)
                st.cache_data.clear()
                st.success("Zapisano!")
                st.rerun()

    except Exception as e:
        st.error(f"Błąd: {e}")

    if st.sidebar.button("Wyloguj"):
        controller.remove("sqm_login_key")
        st.rerun()
