import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from streamlit_cookies_controller import CookieController

# 1. AUTORYZACJA I ZABEZPIECZENIA
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
        st.text_input("Hasło dostępowe:", type="password", on_change=password_entered, key="password")
        return False
    return True

if check_password():
    st.set_page_config(page_title="SQM CONTROL TOWER", layout="wide", initial_sidebar_state="collapsed")

    # 2. CSS - STYLIZACJA OPERACYJNA (UI/UX)
    st.markdown("""
        <style>
        .stButton button { height: 60px !important; border-radius: 10px !important; font-size: 15px !important; font-weight: bold !important; }
        .filter-box { background-color: #f8f9fa; padding: 20px; border-radius: 15px; border: 1px solid #dee2e6; margin-bottom: 25px; }
        .date-header { background-color: #1a1a1a; color: #ffffff; padding: 15px; border-radius: 10px; font-size: 24px; font-weight: bold; margin: 30px 0 15px 0; text-align: center; border-left: 10px solid #1f77b4; }
        .truck-card { background-color: #ffffff; border: 2px solid #1f77b4; border-radius: 15px; padding: 20px; margin-bottom: 25px; box-shadow: 5px 5px 15px rgba(0,0,0,0.1); }
        .project-row { background-color: #fdfdfd; border: 1px solid #eee; padding: 12px; border-radius: 8px; margin-bottom: 10px; }
        .slot-pill { background-color: #f1f3f5; padding: 4px 12px; border-radius: 15px; font-weight: bold; font-size: 14px; }
        .status-tag { padding: 6px 12px; border-radius: 8px; font-weight: bold; color: white; text-align: center; font-size: 13px; }
        </style>
        """, unsafe_allow_html=True)

    # 3. POŁĄCZENIE Z DANYMI
    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    try:
        with st.spinner('Aktualizacja danych z bazy...'):
            df = conn.read(spreadsheet=URL, ttl="1m").dropna(how="all")
            df = df.reset_index(drop=True)

        # Standaryzacja
        all_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'zrzut z currenta', 'SLOT', 'NOTATKA']
        for col in all_cols:
            if col not in df.columns: df[col] = ""
            df[col] = df[col].astype(str).replace(['nan', 'None'], '').str.strip()

        st.title("🏗️ SQM Logistics Control Tower")
        
        # 4. NAWIGACJA
        mode = st.radio("TRYB PRACY:", ["🛰️ RADAR OPERACYJNY", "🏗️ KREATOR WIDOKU", "📊 EDYCJA BAZY"], horizontal=True)
        
        # --- LOGIKA FILTROWANIA (Wspólna dla widoków i edycji) ---
        st.markdown('<div class="filter-box">', unsafe_allow_html=True)
        if mode != "📊 EDYCJA BAZY":
            f1, f2, f3 = st.columns([2, 1, 1])
            search = f1.text_input("🔍 Szukaj ładunku:", placeholder="Projekt, Auto, Kierowca...")
            unique_hale = sorted(list(set([h for h in df['Hala'].unique() if h])))
            hala_filter = f2.multiselect("📍 Hale:", options=unique_hale, default=unique_hale)
            unique_stats = sorted(df['STATUS'].unique())
            status_filter = f3.multiselect("🚦 Statusy:", options=unique_stats, default=unique_stats)
        else:
            # Wyszukiwarka dedykowana dla trybu EDYCJI
            search = st.text_input("🔍 Szybkie wyszukiwanie w bazie do edycji:", placeholder="Wpisz np. numer rejestracyjny lub numer projektu...")
        st.markdown('</div>', unsafe_allow_html=True)

        # Aplikowanie filtrów
        display_df = df.copy()
        if search:
            display_df = display_df[display_df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]
        
        if mode != "📊 EDYCJA BAZY":
            if status_filter:
                display_df = display_df[display_df['STATUS'].isin(status_filter)]
            if hala_filter:
                display_df = display_df[display_df['Hala'].isin(hala_filter)]
            display_df = display_df.sort_values(by=['Data', 'Godzina', 'Auto'])

        # --- WIDOK 1: RADAR OPERACYJNY ---
        if mode == "🛰️ RADAR OPERACYJNY":
            dates = display_df['Data'].unique()
            for d in dates:
                st.markdown(f'<div class="date-header">📅 DZIEŃ: {d}</div>', unsafe_allow_html=True)
                day_df = display_df[display_df['Data'] == d]
                auta_w_dniu = day_df['Auto'].unique()
                
                active_trucks = [a for a in auta_w_dniu if any("ROZŁADOWANY" not in s.upper() for s in day_df[day_df['Auto'] == a]['STATUS'])]
                done_trucks = [a for a in auta_w_dniu if a not in active_trucks]

                if active_trucks:
                    for a_nr in active_trucks:
                        t_data = day_df[day_df['Auto'] == a_nr]
                        with st.container(border=True):
                            h1, h2, h3 = st.columns([2, 2, 1])
                            h1.markdown(f"### 🚚 {a_nr}")
                            h1.caption(f"FIRMA: {t_data.iloc[0]['Przewoźnik']}")
                            h2.markdown(f"👤 **{t_data.iloc[0]['Kierowca']}**")
                            st.write("📦 **Ładunki:**")
                            for idx, row in t_data.iterrows():
                                st.markdown(f'<div class="project-row"><span class="slot-pill">Slot {row["Nr Slotu"]}</span> <b>{row["Nr Proj."]}</b> | {row["Nazwa Projektu"]}</div>', unsafe_allow_html=True)
                                c_btns = st.columns(5)
                                if "http" in row['zdjęcie po załadunku']: c_btns[0].link_button("📸 FOTO", row['zdjęcie po załadunku'], use_container_width=True)
                                if "http" in row['spis casów']: c_btns[1].link_button("📋 SPIS", row['spis casów'], use_container_width=True)
                                if "http" in row['zrzut z currenta']: c_btns[2].link_button("🖼️ CURR", row['zrzut z currenta'], use_container_width=True)
                                if row['NOTATKA']: 
                                    with c_btns[3].expander("📝 NOTKA"): st.info(row['NOTATKA'])
                                st_val = row['STATUS'].upper()
                                st_col = "#d73a49" if "RAMP" in st_val else "#f9c000" if "TRASIE" in st_val else "#28a745" if "ROZŁADOWANY" in st_val else "#6c757d"
                                c_btns[4].markdown(f'<div class="status-tag" style="background:{st_col};">{row["STATUS"]}</div>', unsafe_allow_html=True)
                
                if done_trucks:
                    with st.expander(f"✅ ZAKOŃCZONE ({d})"):
                        for a_nr in done_trucks: st.markdown(f"🚚 **{a_nr}** - Gotowe")

        # --- WIDOK 2: KREATOR ---
        elif mode == "🏗️ KREATOR WIDOKU":
            cols = st.columns(2)
            for i, (_, row) in enumerate(display_df.iterrows()):
                with cols[i % 2]:
                    with st.container(border=True):
                        st.write(f"**{row['Data']} | Slot {row['Nr Slotu']}**")
                        st.markdown(f"### {row['Nr Proj.']} | {row['Nazwa Projektu']}")
                        st.write(f"🚚 {row['Auto']} | 👤 {row['Kierowca']}")

        # --- WIDOK 3: EDYCJA BAZY (Z WYSZUKIWARKĄ) ---
        else:
            st.warning("Tryb edycji: Zmiany zostaną zapisane w Google Sheets. Użyj wyszukiwarki powyżej, aby odfiltrować wiersze.")
            # Wyświetlamy przefiltrowany dataframe do edycji
            edited_df = st.data_editor(display_df, use_container_width=True, num_rows="dynamic")
            
            if st.button("💾 ZAPISZ ZMIANY W ARKUSZU", type="primary", use_container_width=True):
                # Scalanie zmian z oryginalnym df (na wypadek gdyby edytowano tylko fragment)
                df.update(edited_df)
                conn.update(spreadsheet=URL, data=df)
                st.cache_data.clear()
                st.success("Dane zostały pomyślnie zapisane!")
                st.rerun()

    except Exception as e:
        st.error(f"Błąd: {e}")

    if st.sidebar.button("Wyloguj"):
        controller.remove("sqm_login_key")
        st.rerun()
