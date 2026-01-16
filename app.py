import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from streamlit_cookies_controller import CookieController

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(
    page_title="SQM CONTROL TOWER", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- 2. AUTORYZACJA ---
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
    # --- 3. STYLE CSS ---
    st.markdown("""
        <style>
        div[data-testid="stMetric"] { background-color: #f8f9fb; border: 1px solid #e0e0e0; padding: 15px; border-radius: 10px; }
        .stRadio [data-testid="stWidgetLabel"] { display: none; }
        </style>
        """, unsafe_allow_html=True)

    # --- 4. POŁĄCZENIE I DANE ---
    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    try:
        raw_df = conn.read(spreadsheet=URL, ttl="1m")
        df = raw_df.dropna(how="all").reset_index(drop=True)
        
        all_cols = [
            'Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 
            'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 
            'zrzut z currenta', 'SLOT', 'dodatkowe zdjęcie', 'NOTATKA', 'Opłata'
        ]
        
        for col in all_cols:
            if col not in df.columns: df[col] = ""
            df[col] = df[col].astype(str).replace(['nan', 'None', 'NAT', '<NA>'], '')

        # Słownik dla Autofill (ostatnie znane dane dla przewoźnika)
        carriers_db = df[df['Przewoźnik'] != ""].groupby('Przewoźnik').agg({'Auto': 'last', 'Kierowca': 'last'}).to_dict('index')
        lista_przewoznikow = sorted(list(carriers_db.keys()))

        # --- 5. SIDEBAR ---
        with st.sidebar:
            st.header("⚙️ SQM Logistics")
            if st.button("🔄 Odśwież dane"):
                st.cache_data.clear()
                st.rerun()
            st.divider()
            if st.button("🚪 Wyloguj"):
                controller.remove("sqm_login_key")
                st.rerun()

        # Konfiguracja kolumn
        column_cfg = {
            "STATUS": st.column_config.SelectboxColumn("STATUS", options=[
                "🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", 
                "🚚 ZAŁADOWANY", "⚪ PUSTY", "ODBIERA EMPTIES", "ZAVOZI EMPTIES", 
                "ODBIERA PEŁNE", "POWRÓT DO KOMORNIK", "DO ZAPLANOWANIA", 
                "PUSTE DOSTARCZONE", "PEŁNE ODEBRANE"
            ]),
            "Przewoźnik": st.column_config.SelectboxColumn("Przewoźnik", options=lista_przewoznikow),
            "SLOT": st.column_config.LinkColumn("⏰ SLOT", display_text="Otwórz"),
            "spis casów": st.column_config.LinkColumn("📋 Spis", display_text="Otwórz")
        }

        # --- 6. NAWIGACJA ---
        menu_options = ["📅 MONTAŻE", "🟢 ROZŁADOWANE", "📦 SLOTY NA EMPTIES", "🛠️ DEMONTAŻE", "📚 BAZA"]
        choice = st.radio("Widok:", menu_options, horizontal=True, key="main_nav")
        st.divider()

        edit_trackers = {}

        # --- SEKTYCJA: DEMONTAŻE (Z PRZYWRÓCONĄ EDYCJĄ) ---
        if choice == "🛠️ DEMONTAŻE":
            st.subheader("🚛 Harmonogram Demontaży")
            search_query = st.text_input("🔍 Szukaj projektu (Nr lub Nazwa):", "").lower()

            # Pobieramy projekty, które mają statusy demontażowe LUB są po prostu w bazie
            df_demo = df[(df['Nr Proj.'] != "") & (df['Nr Proj.'] != "EMPTIES")].copy()
            
            if search_query:
                df_demo = df_demo[
                    df_demo['Nr Proj.'].str.lower().str.contains(search_query) | 
                    df_demo['Nazwa Projektu'].str.lower().str.contains(search_query)
                ]

            cols_demo = ['Nr Proj.', 'Nazwa Projektu', 'Hala', 'Nr Slotu', 'Data', 'Godzina', 'STATUS', 'Przewoźnik', 'Auto', 'Kierowca', 'Opłata', 'SLOT', 'NOTATKA']
            
            ed_demo = st.data_editor(df_demo[cols_demo], use_container_width=True, key="ed_demo", column_config=column_cfg, hide_index=True)
            edit_trackers["ed_demo"] = (df_demo, ed_demo)

        # --- SEKTYCJA: MONTAŻE ---
        elif choice == "📅 MONTAŻE":
            df_in = df[(df['Nr Proj.'] != "") & (df['Nr Proj.'] != "EMPTIES") & (~df['STATUS'].str.contains("ROZŁADOWANY|ZAŁADOWANY|ODEBRANE", na=False))].copy()
            ed_in = st.data_editor(df_in, use_container_width=True, key="ed_in", column_config=column_cfg, hide_index=True)
            edit_trackers["ed_in"] = (df_in, ed_in)

        # --- SEKTYCJA: BAZA ---
        elif choice == "📚 BAZA":
            ed_full = st.data_editor(df, use_container_width=True, key="ed_full", column_config=column_cfg, hide_index=True)
            edit_trackers["ed_full"] = (df, ed_full)

        # --- SEKTYCJE DODATKOWE ---
        elif choice == "🟢 ROZŁADOWANE":
            df_out = df[df['STATUS'].str.contains("ROZŁADOWANY|ZAŁADOWANY", na=False)].copy()
            ed_out = st.data_editor(df_out, use_container_width=True, key="ed_out", column_config=column_cfg, hide_index=True)
            edit_trackers["ed_out"] = (df_out, ed_out)

        elif choice == "📦 SLOTY NA EMPTIES":
            df_sl = df[df['Nr Proj.'] == "EMPTIES"].copy()
            ed_sl = st.data_editor(df_sl, use_container_width=True, key="ed_sl", column_config=column_cfg, hide_index=True)
            edit_trackers["ed_sl"] = (df_sl, ed_sl)

        # --- 8. ZAPIS ---
        if edit_trackers:
            st.divider()
            if st.button("💾 ZAPISZ WSZYSTKIE ZMIANY", type="primary", use_container_width=True):
                final_df = df.copy()
                for k, (orig_df, ed_component) in edit_trackers.items():
                    changes = st.session_state[k].get("edited_rows", {})
                    for r_idx, c_vals in changes.items():
                        actual_idx = orig_df.index[int(r_idx)]
                        
                        # Logika Autofill przy zapisie
                        if 'Przewoźnik' in c_vals:
                            p_name = c_vals['Przewoźnik']
                            if p_name in carriers_db:
                                # Jeśli użytkownik nie wpisał auta/kierowcy ręcznie, uzupełnij z bazy
                                if 'Auto' not in c_vals or c_vals['Auto'] == "":
                                    final_df.at[actual_idx, 'Auto'] = carriers_db[p_name]['Auto']
                                if 'Kierowca' not in c_vals or c_vals['Kierowca'] == "":
                                    final_df.at[actual_idx, 'Kierowca'] = carriers_db[p_name]['Kierowca']
                        
                        for col, val in c_vals.items():
                            final_df.at[actual_idx, col] = val

                conn.update(spreadsheet=URL, data=final_df[all_cols])
                st.cache_data.clear()
                st.success("Zapisano!")
                st.rerun()

    except Exception as e:
        st.error(f"Błąd: {e}")
