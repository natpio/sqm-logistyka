import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from streamlit_cookies_controller import CookieController

# 1. AUTORYZACJA I KONFIGURACJA
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
        st.title("🏗️ SQM Logistics Tower")
        st.text_input("Hasło:", type="password", on_change=password_entered, key="password")
        return False
    return True

if check_password():
    st.set_page_config(page_title="SQM CONTROL TOWER", layout="wide", initial_sidebar_state="collapsed")

    # CSS - Stylizacja dla wszystkich widoków
    st.markdown("""
        <style>
        .stButton button { height: 60px !important; font-weight: bold !important; border-radius: 10px !important; }
        .slot-header { background-color: #f8f9fa; border: 2px solid #1f77b4; padding: 10px; border-radius: 12px; font-size: 20px; font-weight: bold; color: #1f77b4; display: inline-block; margin-bottom: 10px; }
        .status-badge { float: right; padding: 8px 15px; border-radius: 8px; color: white; font-weight: bold; }
        .custom-card { background: white; border: 1px solid #e1e4e8; border-radius: 15px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; }
        </style>
        """, unsafe_allow_html=True)

    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    try:
        df = conn.read(spreadsheet=URL, ttl="1m").dropna(how="all")
        df = df.reset_index(drop=True)
        
        # Standaryzacja nazw kolumn i czyszczenie danych
        all_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'zrzut z currenta', 'SLOT', 'NOTATKA']
        for col in all_cols:
            if col not in df.columns: df[col] = ""
            df[col] = df[col].astype(str).replace(['nan', 'None'], '')

        st.title("🏗️ SQM Logistics Control Tower")
        
        # 2. NAWIGACJA
        tabs = st.tabs(["🛰️ RADAR OPERACYJNY", "🎨 UŁÓŻ SWÓJ KAFELEK", "📊 EDYCJA BAZY"])

        # WSPÓLNA WYSZUKIWARKA DLA WIDOKÓW KAFELKOWYCH
        with st.sidebar:
            st.header("🔍 Filtrowanie")
            search_query = st.text_input("Szukaj (Projekt, Auto, Hala...):", key="global_search")
            selected_hala = st.multiselect("Filtruj Hale:", options=sorted(list(df['Hala'].unique())), default=[])

        # Aplikowanie filtrów
        filtered_df = df.copy()
        if search_query:
            filtered_df = filtered_df[filtered_df.apply(lambda r: r.astype(str).str.contains(search_query, case=False).any(), axis=1)]
        if selected_hala:
            filtered_df = filtered_df[filtered_df['Hala'].isin(selected_hala)]
        filtered_df = filtered_df.sort_values(by=["Data", "Godzina"])

        # --- WIDOK 1: RADAR OPERACYJNY ---
        with tabs[0]:
            if filtered_df.empty:
                st.warning("Brak danych dla wybranych filtrów.")
            else:
                for idx, row in filtered_df.iterrows():
                    stat_color = "#d73a49" if "RAMP" in row['STATUS'].upper() else "#f9c000" if "TRASIE" in row['STATUS'].upper() else "#28a745" if "ROZŁADOWANY" in row['STATUS'].upper() else "#6c757d"
                    
                    with st.container(border=True):
                        # Nagłówek danych slotu
                        c1, c2 = st.columns([3, 1])
                        c1.markdown(f'<div class="slot-header">📅 {row["Data"]} | SLOT: {row["Nr Slotu"]} | ⏰ {row["Godzina"]}</div>', unsafe_allow_html=True)
                        c2.markdown(f'<div class="status-badge" style="background:{stat_color};">{row["STATUS"]}</div>', unsafe_allow_html=True)
                        
                        # Nazwa i Nr projektu
                        st.markdown(f"## {row['Nr Proj.']} | {row['Nazwa Projektu']}")
                        st.markdown(f"**HALA:** {row['Hala']} | **PRZEWOŹNIK:** {row['Przewoźnik']}")
                        st.markdown(f"🚚 {row['Auto']} | 👤 {row['Kierowca']}")
                        
                        # Narzędzia
                        t1, t2, t3, t4 = st.columns(4)
                        def tool_btn(col, label, emoji, link, k):
                            if "http" in str(link): col.link_button(f"{emoji} {label}", link, use_container_width=True)
                            else: col.button(f"{emoji} --", disabled=True, key=f"{k}_{idx}", use_container_width=True)
                        
                        tool_btn(t1, "FOTO", "📸", row['zdjęcie po załadunku'], "f")
                        tool_btn(t2, "SPIS", "📋", row['spis casów'], "s")
                        tool_btn(t3, "CURR", "🖼️", row['zrzut z currenta'], "c")
                        if row['NOTATKA'].strip():
                            with t4.expander("📝 NOTKA"): st.info(row['NOTATKA'])
                        else: t4.button("📝 --", disabled=True, key=f"n_{idx}", use_container_width=True)

        # --- WIDOK 2: UŁÓŻ SWÓJ KAFELEK ---
        with tabs[1]:
            st.header("🎨 Konfigurator Twojego widoku")
            st.write("Wybierz elementy, które chcesz widzieć na kafelku:")
            
            col_sel1, col_sel2 = st.columns(2)
            with col_sel1:
                show_nr_proj = st.checkbox("Numer Projektu", value=True)
                show_przewoznik = st.checkbox("Przewoźnik", value=True)
                show_kierowca = st.checkbox("Kierowca i Auto", value=True)
            with col_sel2:
                show_hala = st.checkbox("Hala", value=True)
                show_notatka = st.checkbox("Notatka (jako tekst pod spodem)", value=False)
                show_tools = st.checkbox("Przyciski narzędzi (Foto, Spis...)", value=True)

            st.divider()
            
            # Renderowanie kafelków wg wyboru
            for idx, row in filtered_df.iterrows():
                with st.container(border=True):
                    # Zawsze widoczne: Slot, Data, Godzina i Nazwa
                    st.markdown(f"**SLOT {row['Nr Slotu']}** ({row['Data']} {row['Godzina']})")
                    
                    proj_line = f"## {row['Nr Proj.']} | " if show_nr_proj else "## "
                    st.markdown(f"{proj_line}{row['Nazwa Projektu']}")
                    
                    # Elementy opcjonalne
                    info_line = []
                    if show_hala: info_line.append(f"📍 Hala: {row['Hala']}")
                    if show_przewoznik: info_line.append(f"🏢 {row['Przewoźnik']}")
                    if info_line: st.write(" | ".join(info_line))
                    
                    if show_kierowca:
                        st.write(f"🚚 {row['Auto']} | 👤 {row['Kierowca']}")
                    
                    if show_notatka and row['NOTATKA'].strip():
                        st.info(f"📝 {row['NOTATKA']}")
                    
                    if show_tools:
                        b1, b2, b3 = st.columns(3)
                        if "http" in str(row['zdjęcie po załadunku']): b1.link_button("📸 Foto", row['zdjęcie po załadunku'], use_container_width=True)
                        if "http" in str(row['spis casów']): b2.link_button("📋 Spis", row['spis casów'], use_container_width=True)
                        if "http" in str(row['zrzut z currenta']): b3.link_button("🖼️ Curr", row['zrzut z currenta'], use_container_width=True)

        # --- WIDOK 3: EDYCJA BAZY ---
        with tabs[2]:
            st.header("📊 Edycja Bazy GSheet")
            column_cfg = {
                "STATUS": st.column_config.SelectboxColumn("STATUS", options=["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY"]),
                "spis casów": st.column_config.LinkColumn("📋 Spis"),
                "zdjęcie po załadunku": st.column_config.LinkColumn("📸 Foto"),
                "zrzut z currenta": st.column_config.LinkColumn("🖼️ Current")
            }
            edited_df = st.data_editor(df, use_container_width=True, column_config=column_cfg, key="global_editor")
            
            if st.button("💾 ZAPISZ ZMIANY W GOOGLE SHEETS", type="primary", use_container_width=True):
                conn.update(spreadsheet=URL, data=edited_df)
                st.cache_data.clear()
                st.success("Dane zapisane!")
                st.rerun()

    except Exception as e:
        st.error(f"Błąd krytyczny: {e}")

    if st.sidebar.button("Wyloguj"):
        controller.remove("sqm_login_key")
        st.rerun()
