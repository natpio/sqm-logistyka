import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
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

    # CSS - Twój ulubiony styl z poprawkami pod daty
    st.markdown("""
        <style>
        .stButton button { height: 70px !important; border-radius: 10px !important; font-size: 16px !important; font-weight: bold !important; }
        .date-header { background-color: #2e3b4e; color: white; padding: 15px; border-radius: 10px; font-size: 28px; font-weight: bold; margin: 30px 0 10px 0; text-align: center; border-bottom: 5px solid #1f77b4; }
        .hala-banner { background-color: #1f77b4; color: white; padding: 10px 20px; border-radius: 8px; font-size: 20px; font-weight: bold; margin: 15px 0 10px 0; }
        .slot-pill { background-color: #f0f2f6; border: 1px solid #d1d5db; padding: 6px 15px; border-radius: 20px; font-size: 16px; font-weight: bold; color: #1f2937; }
        .status-tag { padding: 6px 12px; border-radius: 8px; font-weight: bold; color: white; text-align: center; }
        </style>
        """, unsafe_allow_html=True)

    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    try:
        with st.spinner('Pobieranie danych...'):
            df = conn.read(spreadsheet=URL, ttl="1m").dropna(how="all")
            df = df.reset_index(drop=True)

        # Czyszczenie danych
        all_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'zrzut z currenta', 'SLOT', 'NOTATKA']
        for col in all_cols:
            if col not in df.columns: df[col] = ""
            df[col] = df[col].astype(str).replace(['nan', 'None'], '')

        st.title("🏗️ SQM Control Tower")
        
        # 2. WYBÓR WIDOKU
        mode = st.radio("WYBIERZ WIDOK:", ["🛰️ RADAR OPERACYJNY", "🏗️ KREATOR KAFELKA", "📊 EDYCJA BAZY"], horizontal=True)
        st.divider()

        # 3. FILTROWANIE (Widoczne dla widoków kafelkowych)
        if mode != "📊 EDYCJA BAZY":
            c_search, c_hala = st.columns([2, 1])
            search = c_search.text_input("🔍 Szukaj (Projekt, Auto, Kierowca...):")
            hala_filter = c_hala.multiselect("Filtruj Hale:", options=sorted(df['Hala'].unique()))

            display_df = df.copy()
            if search:
                display_df = display_df[display_df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]
            if hala_filter:
                display_df = display_df[display_df['Hala'].isin(hala_filter)]
            
            # SORTOWANIE: Data i Godzina to podstawa
            display_df = display_df.sort_values(by=['Data', 'Godzina'])

        # --- WIDOK 1: RADAR OPERACYJNY ---
        if mode == "🛰️ RADAR OPERACYJNY":
            dates = display_df['Data'].unique()
            for d in dates:
                st.markdown(f'<div class="date-header">📅 DZIEŃ: {d}</div>', unsafe_allow_html=True)
                date_df = display_df[display_df['Data'] == d]
                
                hale = sorted(date_df['Hala'].unique())
                for h in hale:
                    st.markdown(f'<div class="hala-banner">📍 HALA {h}</div>', unsafe_allow_html=True)
                    hala_df = date_df[date_df['Hala'] == h]
                    
                    cols = st.columns(2)
                    for i, (_, row) in enumerate(hala_df.iterrows()):
                        with cols[i % 2]:
                            with st.container(border=True):
                                # Nagłówek: Data + Slot + Godzina
                                c1, c2 = st.columns([2, 1])
                                c1.markdown(f'<span class="slot-pill">SLOT {row["Nr Slotu"]} | {row["Data"]} | ⏰ {row["Godzina"]}</span>', unsafe_allow_html=True)
                                
                                stat = row['STATUS'].upper()
                                bg_stat = "#d73a49" if "RAMP" in stat else "#f9c000" if "TRASIE" in stat else "#28a745" if "ROZŁADOWANY" in stat else "#6a737d"
                                c2.markdown(f'<div class="status-tag" style="background-color: {bg_stat};">{row["STATUS"]}</div>', unsafe_allow_html=True)
                                
                                st.markdown(f"## {row['Nr Proj.']} | {row['Nazwa Projektu']}")
                                st.markdown(f"**PRZEWOŹNIK:** {row['Przewoźnik']}")
                                st.markdown(f"🚚 **{row['Auto']}** | 👤 {row['Kierowca']}")
                                st.write("---")
                                
                                # Narzędzia
                                t1, t2, t3, t4 = st.columns(4)
                                def r_btn(col, label, emoji, link, k):
                                    if "http" in str(link): col.link_button(f"{emoji} {label}", link, use_container_width=True)
                                    else: col.button(f"{emoji} --", disabled=True, key=k, use_container_width=True)
                                
                                r_btn(t1, "FOTO", "📸", row['zdjęcie po załadunku'], f"f_{i}_{h}_{d}")
                                r_btn(t2, "SPIS", "📋", row['spis casów'], f"s_{i}_{h}_{d}")
                                r_btn(t3, "CURR", "🖼️", row['zrzut z currenta'], f"c_{i}_{h}_{d}")
                                with t4:
                                    if row['NOTATKA'].strip():
                                        with st.expander("📝 NOTATKA"): st.info(row['NOTATKA'])
                                    else: st.button("📝 --", disabled=True, key=f"n_{i}_{h}_{d}", use_container_width=True)

        # --- WIDOK 2: KREATOR KAFELKA ---
        elif mode == "🏗️ KREATOR KAFELKA":
            st.info("Zaznacz elementy, które chcesz widzieć na kafelku w tym momencie.")
            c_cfg1, c_cfg2, c_cfg3 = st.columns(3)
            show_przew = c_cfg1.checkbox("Przewoźnik", value=True)
            show_auto = c_cfg1.checkbox("Auto i Kierowca", value=True)
            show_proj_nr = c_cfg2.checkbox("Nr Projektu", value=True)
            show_hala_cfg = c_cfg2.checkbox("Hala", value=True)
            show_tools = c_cfg3.checkbox("Przyciski (Foto, Spis...)", value=True)
            show_notatka_direct = c_cfg3.checkbox("Notatka zawsze widoczna", value=False)

            st.divider()

            for _, row in display_df.iterrows():
                with st.container(border=True):
                    # Zawsze widoczne: Czas i Nazwa
                    st.markdown(f"📅 **{row['Data']} | Godz: {row['Godzina']} | SLOT: {row['Nr Slotu']}**")
                    p_nr = f"{row['Nr Proj.']} | " if show_proj_nr else ""
                    st.markdown(f"### {p_nr}{row['Nazwa Projektu']}")
                    
                    details = []
                    if show_hala_cfg: details.append(f"📍 Hala: {row['Hala']}")
                    if show_przew: details.append(f"🏢 {row['Przewoźnik']}")
                    if details: st.write(" | ".join(details))
                    
                    if show_auto: st.write(f"🚚 {row['Auto']} | 👤 {row['Kierowca']}")
                    
                    if show_notatka_direct and row['NOTATKA'].strip():
                        st.warning(f"📝 {row['NOTATKA']}")
                    
                    if show_tools:
                        b1, b2, b3 = st.columns(3)
                        if "http" in row['zdjęcie po załadunku']: b1.link_button("📸 Foto", row['zdjęcie po załadunku'], use_container_width=True)
                        if "http" in row['spis casów']: b2.link_button("📋 Spis", row['spis casów'], use_container_width=True)
                        if "http" in row['zrzut z currenta']: b3.link_button("🖼️ Curr", row['zrzut z currenta'], use_container_width=True)

        # --- WIDOK 3: EDYCJA BAZY ---
        else:
            column_cfg = {
                "STATUS": st.column_config.SelectboxColumn("STATUS", options=["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY"]),
                "spis casów": st.column_config.LinkColumn("📋 Spis"),
                "zdjęcie po załadunku": st.column_config.LinkColumn("📸 Foto"),
                "zrzut z currenta": st.column_config.LinkColumn("🖼️ Current")
            }
            edited_df = st.data_editor(df, use_container_width=True, column_config=column_cfg)
            if st.button("💾 ZAPISZ ZMIANY", type="primary", use_container_width=True):
                conn.update(spreadsheet=URL, data=edited_df)
                st.cache_data.clear()
                st.success("Baza zaktualizowana!")
                st.rerun()

    except Exception as e:
        st.error(f"Błąd: {e}")

    if st.sidebar.button("Wyloguj"):
        controller.remove("sqm_login_key")
        st.rerun()
