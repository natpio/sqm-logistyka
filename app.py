import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from streamlit_cookies_controller import CookieController

# 1. AUTORYZACJA
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

    # CSS - Maksymalna czytelność i duże przyciski
    st.markdown("""
        <style>
        .stButton button { height: 70px !important; border-radius: 10px !important; font-size: 16px !important; font-weight: bold !important; }
        .hala-banner { background-color: #1f77b4; color: white; padding: 12px 25px; border-radius: 10px; font-size: 26px; font-weight: bold; margin: 25px 0 15px 0; }
        .slot-pill { background-color: #f0f2f6; border: 1px solid #d1d5db; padding: 4px 12px; border-radius: 20px; font-size: 18px; font-weight: bold; color: #1f2937; }
        .status-tag { padding: 6px 12px; border-radius: 8px; font-weight: bold; color: white; text-align: center; }
        </style>
        """, unsafe_allow_html=True)

    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    try:
        with st.spinner('Synchronizacja...'):
            df = conn.read(spreadsheet=URL, ttl="1m").dropna(how="all")
            df = df.reset_index(drop=True)

        # Standaryzacja kolumn
        all_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'zrzut z currenta', 'SLOT', 'NOTATKA']
        for col in all_cols:
            if col not in df.columns: df[col] = ""
            df[col] = df[col].astype(str).replace('nan', '')

        st.title("🏗️ SQM Control Tower")
        mode = st.radio("WYBIERZ WIDOK:", ["🛰️ RADAR OPERACYJNY", "📊 EDYCJA BAZY"], horizontal=True)

        if mode == "🛰️ RADAR OPERACYJNY":
            hale = sorted([h for h in df['Hala'].unique() if h.strip() != ""])
            
            for h_name in hale:
                st.markdown(f'<div class="hala-banner">📍 HALA {h_name}</div>', unsafe_allow_html=True)
                hala_df = df[df['Hala'] == h_name].sort_values(by="Godzina")
                
                # Układ 2 kart na rząd
                cols = st.columns(2)
                for i, (_, row) in enumerate(hala_df.iterrows()):
                    with cols[i % 2]:
                        with st.container(border=True):
                            # NAGŁÓWEK KARTY: Slot + Czas | Status
                            c1, c2 = st.columns([2, 1])
                            c1.markdown(f'<span class="slot-pill">SLOT {row["Nr Slotu"]} | ⏰ {row["Godzina"]}</span>', unsafe_allow_html=True)
                            
                            # Kolorowanie statusu
                            stat = row['STATUS'].upper()
                            bg_stat = "#d73a49" if "RAMP" in stat else "#f9c000" if "TRASIE" in stat else "#28a745" if "ROZŁADOWANY" in stat else "#6a737d"
                            c2.markdown(f'<div class="status-tag" style="background-color: {bg_stat};">{row["STATUS"]}</div>', unsafe_allow_html=True)
                            
                            st.write("") # Odstęp
                            
                            # PROJEKT: Numer i Nazwa tej samej wielkości
                            st.markdown(f"## {row['Nr Proj.']} | {row['Nazwa Projektu']}")
                            
                            # LOGISTYKA: Przewoźnik, Auto, Kierowca
                            st.markdown(f"**PRZEWOŹNIK:** {row['Przewoźnik']}")
                            st.markdown(f"🚚 **{row['Auto']}** | 👤 {row['Kierowca']}")
                            
                            st.write("---")
                            
                            # NARZĘDZIA ŁADUNKU - 4 duże przyciski
                            t1, t2, t3, t4 = st.columns(4)
                            
                            def render_btn(col, label, emoji, link, key_id):
                                if "http" in str(link):
                                    col.link_button(f"{emoji} {label}", link, use_container_width=True)
                                else:
                                    col.button(f"{emoji} --", disabled=True, key=key_id, use_container_width=True)

                            render_btn(t1, "FOTO", "📸", row['zdjęcie po załadunku'], f"f_{i}_{h_name}")
                            render_btn(t2, "SPIS", "📋", row['spis casów'], f"s_{i}_{h_name}")
                            render_btn(t3, "CURR", "🖼️", row['zrzut z currenta'], f"c_{i}_{h_name}")
                            
                            with t4:
                                if row['NOTATKA'].strip():
                                    with st.expander("📝 NOTATKA"):
                                        st.info(row['NOTATKA'])
                                else:
                                    st.button("📝 --", disabled=True, key=f"n_{i}_{h_name}", use_container_width=True)

        else:
            # TRYB EDYCJI (Klasyczna tabela)
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
                st.success("Zapisano!")
                st.rerun()

    except Exception as e:
        st.error(f"Błąd: {e}")

    if st.sidebar.button("Wyloguj"):
        controller.remove("sqm_login_key")
        st.rerun()
