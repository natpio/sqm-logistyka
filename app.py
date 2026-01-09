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
        st.text_input("Hasło dostępu:", type="password", on_change=password_entered, key="password")
        return False
    return True

if check_password():
    st.set_page_config(page_title="SQM CONTROL TOWER", layout="wide", initial_sidebar_state="collapsed")

    # CSS - Stylizacja kafelków i notatek
    st.markdown("""
        <style>
        .truck-tile {
            background-color: #ffffff;
            border: 2px solid #1f77b4;
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 3px 3px 10px rgba(0,0,0,0.1);
        }
        .status-pill {
            padding: 5px 15px;
            border-radius: 20px;
            color: white;
            font-weight: bold;
            font-size: 14px;
            display: inline-block;
            margin-bottom: 10px;
        }
        .notatka-display { 
            background-color: #fff3cd; 
            padding: 20px; 
            border-radius: 12px; 
            border-left: 10px solid #ffc107; 
            margin: 15px 0;
            font-size: 18px !important;
        }
        </style>
        """, unsafe_allow_html=True)

    # POŁĄCZENIE Z GOOGLE SHEETS
    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    # KONFIGURACJA
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

    def render_tile_view(data):
        """Funkcja generująca widok kafelkowy"""
        if data.empty:
            st.info("Brak danych do wyświetlenia.")
            return

        cols = st.columns(3) # 3 kafelki w rzędzie
        for idx, (_, row) in enumerate(data.iterrows()):
            with cols[idx % 3]:
                # Logika koloru statusu
                st_val = str(row['STATUS']).upper()
                st_color = "#d73a49" if "RAMP" in st_val else "#f9c000" if "TRASIE" in st_val else "#28a745" if "ROZŁADOWANY" in st_val else "#6c757d"
                
                st.markdown(f"""
                <div class="truck-tile">
                    <div class="status-pill" style="background-color: {st_color};">{row['STATUS']}</div>
                    <div style="font-size: 24px; font-weight: bold; color: #1f77b4;">{row['Auto']}</div>
                    <div style="font-size: 16px; font-weight: bold;">Slot {row['Nr Slotu']} | ⏰ {row['Godzina']}</div>
                    <div style="color: #666; margin-bottom: 10px;">📍 Hala: {row['Hala']} | 👤 {row['Kierowca']}</div>
                    <hr style="margin: 10px 0;">
                    <div style="font-size: 14px;"><strong>{row['Nr Proj.']}</strong><br>{row['Nazwa Projektu']}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Przyciski akcji wewnątrz kafelka
                b1, b2, b3 = st.columns(3)
                if "http" in str(row['spis casów']): b1.link_button("📋", row['spis casów'], use_container_width=True)
                if "http" in str(row['zdjęcie po załadunku']): b2.link_button("📸", row['zdjęcie po załadunku'], use_container_width=True)
                if row['NOTATKA']:
                    with b3.expander("📝"): st.caption(row['NOTATKA'])

    try:
        raw_df = conn.read(spreadsheet=URL, ttl="1m").dropna(how="all")
        df = raw_df.reset_index(drop=True)
        
        all_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'zrzut z currenta', 'SLOT', 'NOTATKA']
        for col in all_cols:
            if col not in df.columns: df[col] = ""
            df[col] = df[col].astype(str).replace('nan', '')

        if "PODGLĄD" not in df.columns:
            df.insert(df.columns.get_loc("NOTATKA"), "PODGLĄD", False)

        st.title("🏗️ SQM Logistics Control Tower")

        # --- NOWY PRZEŁĄCZNIK WIDOKU ---
        c_top1, c_top2 = st.columns([1, 1])
        view_mode = c_top1.radio("POZIOM PREZENTACJI:", ["📊 TABELA (EDYCJA)", "📱 KAFELKI (OPERACYJNE)"], horizontal=True)
        
        statusy_wyjazdowe = "ROZŁADOWANY|ZAŁADOWANY|EMPTIES"

        tab_in, tab_out, tab_full = st.tabs(["📅 MONTAŻE", "🔄 DEMONTAŻE", "📚 BAZA"])

        # --- LOGIKA DLA TABÓW ---
        for tab, mask_type in [(tab_in, "IN"), (tab_out, "OUT"), (tab_full, "FULL")]:
            with tab:
                # Filtrowanie lokalne dla taba
                if mask_type == "IN":
                    current_df = df[~df['STATUS'].str.contains(statusy_wyjazdowe, na=False, case=False)].copy()
                elif mask_type == "OUT":
                    current_df = df[df['STATUS'].str.contains(statusy_wyjazdowe, na=False, case=False)].copy()
                else:
                    current_df = df.copy()

                # Wyszukiwarka
                search = st.text_input(f"🔍 Szukaj w {mask_type}:", key=f"search_{mask_type}")
                if search:
                    current_df = current_df[current_df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]

                if view_mode == "📊 TABELA (EDYCJA)":
                    ed_df = st.data_editor(current_df, use_container_width=True, key=f"ed_{mask_type}", column_config=column_cfg)
                    # Podgląd notatki
                    selected = ed_df[ed_df["PODGLĄD"] == True]
                    if not selected.empty:
                        row = selected.iloc[-1]
                        st.markdown(f'<div class="notatka-display"><strong>{row["Auto"]}</strong>: {row["NOTATKA"]}</div>', unsafe_allow_html=True)
                else:
                    render_tile_view(current_df)

        # ZAPIS (Tylko w trybie tabeli ma sens)
        if view_mode == "📊 TABELA (EDYCJA)":
            st.divider()
            if st.button("💾 ZAPISZ ZMIANY W ARKUSZU", type="primary", use_container_width=True):
                # Tutaj logika scalania zmian z edytorów (analogiczna do Twojej)
                final_df = df.copy()
                for key in ["ed_IN", "ed_OUT", "ed_FULL"]:
                    if key in st.session_state:
                        edits = st.session_state[key].get("edited_rows", {})
                        # ... (logika mapowania indeksów)
                # (Dla uproszczenia w tym przykładzie pomijam pełną pętlę scalania, którą już masz w kodzie)
                st.success("Wysłano dane do Google Sheets!")

    except Exception as e:
        st.error(f"Błąd: {e}")
