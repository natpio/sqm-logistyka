import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from streamlit_cookies_controller import CookieController

# 1. KONFIGURACJA I AUTORYZACJA
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
        st.text_input("Hasło dostępu:", type="password", on_change=password_entered, key="password")
        return False
    return True

if check_password():
    st.set_page_config(page_title="SQM CONTROL TOWER", layout="wide", initial_sidebar_state="collapsed")

    # 2. STYLIZACJA CSS (INTERFEJS OPERACYJNY)
    st.markdown("""
        <style>
        /* Kafelki transportów */
        .truck-group-card {
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            border-left: 8px solid #1f77b4;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 25px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        }
        .project-sub-row {
            background-color: #f8f9fa;
            border-radius: 8px;
            padding: 12px;
            margin-top: 8px;
            border: 1px solid #eee;
        }
        .status-badge {
            padding: 4px 10px;
            border-radius: 6px;
            color: white;
            font-weight: bold;
            font-size: 11px;
            text-transform: uppercase;
            display: inline-block;
        }
        .notatka-display { 
            background-color: #fff3cd; 
            padding: 20px; 
            border-radius: 12px; 
            border-left: 10px solid #ffc107; 
            margin: 15px 0;
            font-size: 18px !important;
        }
        .date-tag {
            background: #333;
            color: white;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 12px;
        }
        </style>
        """, unsafe_allow_html=True)

    # 3. POŁĄCZENIE Z DANYMI
    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    # Definicje kolumn i opcji
    status_options = ["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ status-planned"]
    column_cfg = {
        "STATUS": st.column_config.SelectboxColumn("STATUS", options=status_options, width="medium"),
        "spis casów": st.column_config.LinkColumn("📋 Spis", display_text="Otwórz"),
        "zdjęcie po załadunku": st.column_config.LinkColumn("📸 Foto", display_text="Otwórz"),
        "zrzut z currenta": st.column_config.LinkColumn("🖼️ Current", display_text="Otwórz"),
        "SLOT": st.column_config.LinkColumn("⏰ SLOT", display_text="Otwórz"),
        "PODGLĄD": st.column_config.CheckboxColumn("👁️", width="small", default=False),
        "NOTATKA": st.column_config.TextColumn("📝 NOTATKA", width="medium")
    }

    # --- FUNKCJA WIDOKU KAFELKOWEGO (Grupowanie po aucie) ---
    def render_tile_view(data):
        if data.empty:
            st.info("Brak transportów spełniających kryteria.")
            return

        # Grupowanie po Dacie i Aucie (jeden zestaw = jedna karta)
        grouped = data.sort_values(['Data', 'Godzina']).groupby(['Data', 'Auto'])

        for (d_val, a_val), group in grouped:
            with st.container():
                st.markdown(f"""
                <div class="truck-group-card">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <span class="date-tag">📅 {d_val}</span>
                            <h2 style="margin: 5px 0 0 0; color: #1f77b4; font-size: 32px;">🚚 {a_val}</h2>
                            <p style="margin: 0; color: #666;">Firma: <b>{group.iloc[0]['Przewoźnik']}</b> | Kierowca: <b>{group.iloc[0]['Kierowca']}</b></p>
                        </div>
                        <div style="text-align: right;">
                            <span style="font-size: 24px; font-weight: bold; color: #333;">⏰ {group.iloc[0]['Godzina']}</span><br>
                            <span style="font-size: 14px; color: #888;">SLOT: {group.iloc[0]['Nr Slotu']}</span>
                        </div>
                    </div>
                    <div style="margin-top: 15px;">
                """, unsafe_allow_html=True)

                # Wyświetlanie projektów wewnątrz karty auta
                for _, row in group.iterrows():
                    st_val = str(row['STATUS']).upper()
                    st_bg = "#d73a49" if "RAMP" in st_val else "#f9c000" if "TRASIE" in st_val else "#28a745" if "ROZŁADOWANY" in st_val else "#6c757d"
                    
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"""
                        <div class="project-sub-row">
                            <span class="status-badge" style="background:{st_bg}">{row['STATUS']}</span>
                            <b style="font-size: 16px; margin-left: 10px;">{row['Nr Proj.']}</b> | {row['Nazwa Projektu']} | 📍 Hala: {row['Hala']}
                        </div>
                        """, unsafe_allow_html=True)
                    with c2:
                        st.write("") # wyrównanie
                        b1, b2, b3 = st.columns(3)
                        if "http" in str(row['spis casów']): b1.link_button("📋", row['spis casów'])
                        if "http" in str(row['zdjęcie po załadunku']): b2.link_button("📸", row['zdjęcie po załadunku'])
                        if row['NOTATKA']:
                            with b3.expander("📝"): st.caption(row['NOTATKA'])
                
                st.markdown("</div></div>", unsafe_allow_html=True)

    try:
        # POBIERANIE DANYCH
        raw_df = conn.read(spreadsheet=URL, ttl="1m").dropna(how="all")
        df = raw_df.reset_index(drop=True)
        
        # Standaryzacja kolumn
        all_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'zrzut z currenta', 'SLOT', 'NOTATKA']
        for col in all_cols:
            if col not in df.columns: df[col] = ""
            df[col] = df[col].astype(str).replace('nan', '')

        if "PODGLĄD" not in df.columns:
            df.insert(df.columns.get_loc("NOTATKA"), "PODGLĄD", False)

        # UI GŁÓWNE
        st.title("🏗️ SQM Logistics Control Tower")
        
        # Wybór widoku
        view_mode = st.radio("WIDOK:", ["📱 KAFELKI (OPERACYJNY)", "📊 TABELA (EDYCJA)"], horizontal=True)
        
        statusy_wyjazdowe = "ROZŁADOWANY|ZAŁADOWANY|EMPTIES"
        tab_in, tab_out, tab_full = st.tabs(["📅 MONTAŻE", "🔄 DEMONTAŻE", "📚 BAZA"])

        for tab, mode_type in [(tab_in, "IN"), (tab_out, "OUT"), (tab_full, "FULL")]:
            with tab:
                # Logika filtrów dla taba
                if mode_type == "IN":
                    work_df = df[~df['STATUS'].str.contains(statusy_wyjazdowe, na=False, case=False)].copy()
                elif mode_type == "OUT":
                    work_df = df[df['STATUS'].str.contains(statusy_wyjazdowe, na=False, case=False)].copy()
                else:
                    work_df = df.copy()

                # Wyszukiwarka na każdym tabie
                s_key = f"search_{mode_type}"
                search_query = st.text_input("🔍 Szukaj (Auto, Projekt, Kierowca...):", key=s_key)
                if search_query:
                    work_df = work_df[work_df.apply(lambda r: r.astype(str).str.contains(search_query, case=False).any(), axis=1)]

                # RENDEROWANIE
                if view_mode == "📊 TABELA (EDYCJA)":
                    ed_df = st.data_editor(work_df, use_container_width=True, key=f"ed_{mode_type}", column_config=column_cfg)
                    # Podgląd notatki pod tabelą
                    sel = ed_df[ed_df["PODGLĄD"] == True]
                    if not sel.empty:
                        r = sel.iloc[-1]
                        st.markdown(f'<div class="notatka-display"><b>{r["Auto"]}</b>: {r["NOTATKA"]}</div>', unsafe_allow_html=True)
                else:
                    render_tile_view(work_df)

        # ZAPIS ZMIAN (Pojawia się tylko w widoku tabeli)
        if view_mode == "📊 TABELA (EDYCJA)":
            st.divider()
            if st.button("💾 ZAPISZ WSZYSTKIE ZMIANY", type="primary", use_container_width=True):
                with st.spinner('Zapisywanie do Google Sheets...'):
                    final_df = df.copy()
                    # Mapowanie zmian z edytorów do głównego DF
                    for k in ["ed_IN", "ed_OUT", "ed_FULL"]:
                        if k in st.session_state:
                            edits = st.session_state[k].get("edited_rows", {})
                            source_df = (df[~df['STATUS'].str.contains(statusy_wyjazdowe, na=False, case=False)] if k == "ed_IN" 
                                         else df[df['STATUS'].str.contains(statusy_wyjazdowe, na=False, case=False)] if k == "ed_OUT" 
                                         else df)
                            for r_idx, changes in edits.items():
                                real_idx = source_df.index[int(r_idx)]
                                for c, v in changes.items():
                                    final_df.at[real_idx, c] = v
                    
                    if "PODGLĄD" in final_df.columns: final_df = final_df.drop(columns=["PODGLĄD"])
                    conn.update(spreadsheet=URL, data=final_df)
                    st.cache_data.clear()
                    st.success("Dane zapisane!")
                    st.rerun()

    except Exception as e:
        st.error(f"Błąd krytyczny: {e}")

    if st.sidebar.button("Wyloguj"):
        controller.remove("sqm_login_key")
        st.rerun()
