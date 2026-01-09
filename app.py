import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from streamlit_cookies_controller import CookieController

# 1. AUTORYZACJA I PAMIĘĆ LOGOWANIA (COOKIES)
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
    st.set_page_config(page_title="SQM CONTROL TOWER", layout="wide", initial_sidebar_state="expanded")

    # CSS - Stylizacja interfejsu, notatki oraz KAFELKÓW
    st.markdown("""
        <style>
        div[data-testid="stMetric"] { background-color: #f8f9fb; border: 1px solid #e0e0e0; padding: 15px; border-radius: 10px; }
        .stTabs [aria-selected="true"] { background-color: #1f77b4 !important; color: white !important; }
        
        /* Styl Kafelka */
        .transport-card {
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 15px;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
            border-left: 8px solid #ccc;
        }
        .status-trasie { border-left-color: #ffeb3b; }
        .status-rampa { border-left-color: #f44336; }
        .status-rozladowany { border-left-color: #4caf50; }
        .status-empties { border-left-color: #9e9e9e; }
        .status-zaladowany { border-left-color: #2196f3; }
        
        .notatka-display { 
            background-color: #fff3cd; 
            padding: 25px; 
            border-radius: 12px; 
            border-left: 12px solid #ffc107; 
            margin: 20px 0;
            font-size: 20px !important;
            color: #333;
            box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
        }
        </style>
        """, unsafe_allow_html=True)

    # WYBÓR WIDOKU W SIDEBARZE
    with st.sidebar:
        st.header("Ustawienia widoku")
        view_mode = st.radio("Wybierz styl wyświetlania:", ["Tradycyjny", "Kafelkowy"])
        st.divider()
        if st.sidebar.button("Wyloguj"):
            controller.remove("sqm_login_key")
            st.rerun()

    # POŁĄCZENIE Z GOOGLE SHEETS
    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    # KONFIGURACJA KOLUMN
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

    try:
        # POBIERANIE DANYCH
        with st.spinner('Synchronizacja z bazą SQM...'):
            raw_df = conn.read(spreadsheet=URL, ttl="1m").dropna(how="all")
            df = raw_df.reset_index(drop=True)
        
        all_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'zrzut z currenta', 'SLOT', 'dodatkowe zdjęcie', 'NOTATKA']
        for col in all_cols:
            if col not in df.columns: df[col] = ""
            df[col] = df[col].astype(str).replace('nan', '')

        if "PODGLĄD" not in df.columns:
            notatka_idx = df.columns.get_loc("NOTATKA")
            df.insert(notatka_idx, "PODGLĄD", False)

        statusy_wyjazdowe = "ROZŁADOWANY|ZAŁADOWANY|EMPTIES"

        st.title("🏗️ SQM Logistics Control Tower")
        
        # METRYKI
        m1, m2, m3 = st.columns(3)
        m1.metric("W TRASIE 🟡", len(df[df['STATUS'].str.contains("TRASIE", na=False)]))
        m2.metric("POD RAMPĄ 🔴", len(df[df['STATUS'].str.contains("RAMP", na=False)]))
        m3.metric("ZAKOŃCZONE 🟢", len(df[df['STATUS'].str.contains("ROZŁADOWANY", na=False)]))

        tab_in, tab_out, tab_full = st.tabs(["📅 MONTAŻE", "🔄 DEMONTAŻE", "📚 BAZA"])

        def render_note_viewer(edited_df):
            selected = edited_df[edited_df["PODGLĄD"] == True]
            if not selected.empty:
                row = selected.iloc[-1]
                st.markdown(f"""
                <div class="notatka-display">
                    <strong>📋 SZCZEGÓŁY TRANSPORTU:</strong><br>
                    <strong>Projekt:</strong> {row['Nazwa Projektu']} | <strong>Auto:</strong> {row['Auto']}<br><br>
                    <strong>PEŁNA NOTATKA:</strong><br>{row['NOTATKA']}
                </div>
                """, unsafe_allow_html=True)

        def render_tiles(dataframe):
            if dataframe.empty:
                st.info("Brak danych do wyświetlenia w tej kategorii.")
                return
            
            # Tworzymy siatkę 3 kafelki w rzędzie
            cols = st.columns(3)
            for idx, (_, row) in enumerate(dataframe.iterrows()):
                col_idx = idx % 3
                with cols[col_idx]:
                    # Dobór klasy CSS na podstawie statusu
                    status_class = ""
                    s = row['STATUS'].upper()
                    if "TRASIE" in s: status_class = "status-trasie"
                    elif "RAMP" in s: status_class = "status-rampa"
                    elif "ROZŁADOWANY" in s: status_class = "status-rozladowany"
                    elif "EMPTIES" in s: status_class = "status-empties"
                    elif "ZAŁADOWANY" in s: status_class = "status-zaladowany"

                    st.markdown(f"""
                        <div class="transport-card {status_class}">
                            <div style="font-size: 0.8em; color: gray;">{row['Data']} | Slot: {row['Nr Slotu']}</div>
                            <div style="font-weight: bold; font-size: 1.1em; margin: 5px 0;">{row['Nazwa Projektu']}</div>
                            <div style="font-size: 0.9em;">
                                🚛 <b>{row['Auto']}</b> ({row['Przewoźnik']})<br>
                                👤 {row['Kierowca']}<br>
                                📍 Hala: {row['Hala']} | Godz: {row['Godzina']}
                            </div>
                            <hr style="margin: 10px 0;">
                            <div style="font-weight: bold; color: #1f77b4;">{row['STATUS']}</div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # Przyciski akcji pod kafelkiem (opcjonalne, bo widok kafelkowy jest głównie do podglądu)
                    if row['SLOT']:
                        st.link_button(f"Link do Slotu", row['SLOT'], use_container_width=True)

        # Logika filtracji i wyświetlania dla każdego taba
        for tab, mask, key_prefix in [
            (tab_in, ~df['STATUS'].str.contains(statusy_wyjazdowe, na=False, case=False), "in"),
            (tab_out, df['STATUS'].str.contains(statusy_wyjazdowe, na=False, case=False), "out"),
            (tab_full, None, "f")
        ]:
            with tab:
                # Wspólne filtry dla tabów
                c1, c2, c3 = st.columns([1.5, 2, 1])
                with c1:
                    if key_prefix == "in":
                        selected_date = st.date_input("Dzień rozładunku:", value=datetime.now(), key=f"d_{key_prefix}")
                        all_days = st.checkbox("Pokaż wszystkie dni", value=True, key=f"a_{key_prefix}")
                with c2:
                    search_term = st.text_input("🔍 Szukaj ładunku:", key=f"s_{key_prefix}")
                with c3:
                    st.write("###")
                    if st.button("🔄 Odśwież", key=f"ref_{key_prefix}"):
                        st.cache_data.clear()
                        st.rerun()

                # Aplikacja filtrów
                df_filtered = df[mask].copy() if mask is not None else df.copy()
                
                if key_prefix == "in" and not all_days:
                    df_filtered['Data_dt'] = pd.to_datetime(df_filtered['Data'], errors='coerce')
                    df_filtered = df_filtered[df_filtered['Data_dt'].dt.date == selected_date].drop(columns=['Data_dt'])
                
                if search_term:
                    df_filtered = df_filtered[df_filtered.apply(lambda r: r.astype(str).str.contains(search_term, case=False).any(), axis=1)]

                # WYBÓR RENDEROWANIA
                if view_mode == "Tradycyjny":
                    ed = st.data_editor(df_filtered, use_container_width=True, key=f"ed_{key_prefix}", column_config=column_cfg)
                    render_note_viewer(ed)
                    # Przypisanie do zmiennych globalnych dla zapisu
                    if key_prefix == "in": df_in, ed_in = df_filtered, ed
                    elif key_prefix == "out": df_out, ed_out = df_filtered, ed
                    elif key_prefix == "f": df_f, ed_f = df_filtered, ed
                else:
                    render_tiles(df_filtered)

        # --- GLOBALNY ZAPIS ZMIAN (tylko w widoku tradycyjnym edycja jest aktywna) ---
        if view_mode == "Tradycyjny":
            st.divider()
            if st.button("💾 ZAPISZ WSZYSTKIE ZMIANY W ARKUSZU", type="primary", use_container_width=True):
                with st.spinner('Zapisywanie danych...'):
                    final_df = df.copy()
                    for key in ["ed_in", "ed_out", "ed_f"]:
                        if key in st.session_state:
                            # Wybieramy odpowiedni source_df na podstawie klucza
                            if key == "ed_in": s_df = df_in
                            elif key == "ed_out": s_df = df_out
                            else: s_df = df_f
                            
                            edytowane = st.session_state[key].get("edited_rows", {})
                            for row_idx_str, changes in edytowane.items():
                                real_idx = s_df.index[int(row_idx_str)]
                                for col, val in changes.items():
                                    final_df.at[real_idx, col] = val
                    
                    if "PODGLĄD" in final_df.columns:
                        final_df = final_df.drop(columns=["PODGLĄD"])
                    
                    conn.update(spreadsheet=URL, data=final_df)
                    st.cache_data.clear()
                    st.success("Zapisano pomyślnie!")
                    st.rerun()
        else:
            st.info("💡 Edycja danych (statusy, notatki) dostępna jest tylko w widoku 'Tradycyjnym'.")

    except Exception as e:
        st.error(f"Wystąpił błąd: {e}")
