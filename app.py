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

    # CSS - Interfejs Operacyjny (duże przyciski i wyraźne karty)
    st.markdown("""
        <style>
        .stButton button { height: 65px !important; border-radius: 8px !important; font-size: 14px !important; font-weight: bold !important; }
        .hala-banner { background-color: #1f77b4; color: white; padding: 10px 20px; border-radius: 10px; font-size: 24px; font-weight: bold; margin: 20px 0; }
        .card-container { border: 1px solid #dee2e6; border-radius: 15px; padding: 15px; background-color: #ffffff; box-shadow: 2px 2px 10px rgba(0,0,0,0.05); }
        .status-dot { height: 12px; width: 12px; border-radius: 50%; display: inline-block; margin-right: 5px; }
        </style>
        """, unsafe_allow_html=True)

    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    try:
        with st.spinner('Synchronizacja danych...'):
            df = conn.read(spreadsheet=URL, ttl="1m").dropna(how="all")
            df = df.reset_index(drop=True)

        for col in ['Data', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'zrzut z currenta', 'NOTATKA']:
            if col not in df.columns: df[col] = ""
            df[col] = df[col].astype(str).replace('nan', '')

        st.title("🏗️ SQM Control Tower")
        mode = st.radio("WYBIERZ WIDOK:", ["🛰️ RADAR OPERACYJNY", "📊 EDYCJA BAZY"], horizontal=True)

        if mode == "🛰️ RADAR OPERACYJNY":
            hale = sorted([h for h in df['Hala'].unique() if h.strip() != ""])
            
            for h_name in hale:
                st.markdown(f'<div class="hala-banner">📍 HALA {h_name}</div>', unsafe_allow_html=True)
                hala_df = df[df['Hala'] == h_name].sort_values(by="Godzina")
                
                # Układ 2 kart na rząd dla iPada/Mobile
                cols = st.columns(2)
                for i, (_, row) in enumerate(hala_df.iterrows()):
                    with cols[i % 2]:
                        with st.container(border=True):
                            # Górna belka: Slot i Status
                            c1, c2 = st.columns([1, 1])
                            c1.markdown(f"### ⏰ {row['Godzina']}")
                            c2.markdown(f"**STATUS:** {row['STATUS']}")
                            
                            # Środek: Projekt
                            st.markdown(f"## {row['Nazwa Projektu']}")
                            st.markdown(f"**ID:** {row['Nr Proj.']} | **PRZEWOŹNIK:** {row['Przewoźnik']}")
                            st.markdown(f"🚚 **{row['Auto']}** | 👤 {row['Kierowca']}")
                            
                            st.write("---")
                            st.caption("🛠️ NARZĘDZIA ŁADUNKU")
                            
                            # Narzędzia - 4 duże przyciski
                            t1, t2, t3, t4 = st.columns(4)
                            
                            # Przycisk FOTO
                            if "http" in row['zdjęcie po załadunku']:
                                t1.link_button("📸 FOTO", row['zdjęcie po załadunku'], use_container_width=True)
                            else:
                                t1.button("📸 --", disabled=True, key=f"f_{i}_{h_name}", use_container_width=True)

                            # Przycisk SPIS
                            if "http" in row['spis casów']:
                                t2.link_button("📋 SPIS", row['spis casów'], use_container_width=True)
                            else:
                                t2.button("📋 --", disabled=True, key=f"s_{i}_{h_name}", use_container_width=True)

                            # Przycisk CURRENT
                            if "http" in row['zrzut z currenta']:
                                t3.link_button("🖼️ CURR", row['zrzut z currenta'], use_container_width=True)
                            else:
                                t3.button("🖼️ --", disabled=True, key=f"c_{i}_{h_name}", use_container_width=True)

                            # Przycisk NOTATKA
                            if row['NOTATKA'].strip():
                                with t4.expander("📝 NOTKA"):
                                    st.info(row['NOTATKA'])
                            else:
                                t4.button("📝 --", disabled=True, key=f"n_{i}_{h_name}", use_container_width=True)

        else:
            # TRYB EDYCJI
            column_cfg = {
                "STATUS": st.column_config.SelectboxColumn("STATUS", options=["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY"]),
                "spis casów": st.column_config.LinkColumn("📋 Spis"),
                "zdjęcie po załadunku": st.column_config.LinkColumn("📸 Foto"),
                "zrzut z currenta": st.column_config.LinkColumn("🖼️ Current"),
                "NOTATKA": st.column_config.TextColumn("📝 NOTATKA")
            }
            edited_df = st.data_editor(df, use_container_width=True, column_config=column_cfg)
            if st.button("💾 ZAPISZ ZMIANY W GOOGLE SHEETS", type="primary", use_container_width=True):
                conn.update(spreadsheet=URL, data=edited_df)
                st.cache_data.clear()
                st.success("Baza zaktualizowana!")
                st.rerun()

    except Exception as e:
        st.error(f"Błąd: {e}")

    if st.sidebar.button("Wyloguj"):
        controller.remove("sqm_login_key")
        st.rerun()
