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
        .note-box {
            background-color: #1e1e1e; color: #ffffff; padding: 15px; border-radius: 10px; border-left: 5px solid #00ff00; margin-bottom: 20px;
        }
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
            if col != "PODGLĄD":
                df[col] = df[col].astype(str).replace(['nan', 'None', 'NAT', 'nan nan', '<NA>', 'None None'], '')

        if "PODGLĄD" not in df.columns:
            df.insert(df.columns.get_loc("NOTATKA"), "PODGLĄD", False)
        else:
            df["PODGLĄD"] = pd.to_numeric(df["PODGLĄD"], errors='coerce').fillna(0).map(lambda x: True if x == 1 or x is True else False)

        # Pobieranie bazy przewoźników dla autofill
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

        column_cfg = {
            "STATUS": st.column_config.SelectboxColumn("STATUS", options=[
                "🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", 
                "🚚 ZAŁADOWANY", "⚪ PUSTY", "ODBIERA EMPTIES", "ZAVOZI EMPTIES", 
                "ODBIERA PEŁNE", "POWRÓT DO KOMORNIK", "DO ZAPLANOWANIA", 
                "PUSTE DOSTARCZONE", "PEŁNE ODEBRANE"
            ], width="medium"),
            "Przewoźnik": st.column_config.SelectboxColumn("Przewoźnik", options=lista_przewoznikow),
            "SLOT": st.column_config.LinkColumn("⏰ SLOT", display_text="Otwórz"),
            "PODGLĄD": st.column_config.CheckboxColumn("👁️", width="small")
        }

        # --- 6. NAWIGACJA ---
        menu_options = ["📅 MONTAŻE", "🟢 ROZŁADOWANE", "⚪ PUSTE TRUCKI", "📦 SLOTY NA EMPTIES", "🛠️ DEMONTAŻE", "📚 BAZA"]
        choice = st.radio("Widok:", menu_options, horizontal=True, key="main_nav")
        st.divider()

        edit_trackers = {}

        # --- SEKTYCJA: DEMONTAŻE ---
        if choice == "🛠️ DEMONTAŻE":
            st.subheader("🚛 Planowanie Demontaży")
            
            # WYSZUKIWARKA
            search_query = st.text_input("🔍 Szukaj projektu (Nr lub Nazwa):", "").lower()

            # Przygotowanie listy unikalnych projektów
            df_base_projs = df[(df['Nr Proj.'] != "") & (df['Nr Proj.'] != "EMPTIES")].drop_duplicates(subset=['Nr Proj.']).copy()
            
            # Filtrowanie wyszukiwarką
            if search_query:
                df_base_projs = df_base_projs[
                    df_base_projs['Nr Proj.'].str.lower().contains(search_query) | 
                    df_base_projs['Nazwa Projektu'].str.lower().contains(search_query)
                ]

            df_demo = pd.DataFrame(columns=all_cols)
            df_demo['Nr Proj.'] = df_base_projs['Nr Proj.']
            df_demo['Nazwa Projektu'] = df_base_projs['Nazwa Projektu']
            df_demo['Hala'] = df_base_projs['Hala']
            df_demo = df_demo.fillna("")
            
            cols_to_show = ['Nr Proj.', 'Nazwa Projektu', 'Hala', 'Nr Slotu', 'Data', 'Godzina', 'STATUS', 'Przewoźnik', 'Auto', 'Kierowca', 'Opłata', 'SLOT', 'NOTATKA']
            
            demo_cfg = column_cfg.copy()
            demo_cfg["STATUS"] = st.column_config.SelectboxColumn("STATUS", options=["DO ZAPLANOWANIA", "PUSTE DOSTARCZONE", "PEŁNE ODEBRANE"])

            ed_demo = st.data_editor(df_demo[cols_to_show], use_container_width=True, key="ed_demo", column_config=demo_cfg, hide_index=True)
            edit_trackers["ed_demo"] = (df_demo, ed_demo)

        # --- POZOSTAŁE SEKTYCJE (Skrócone dla czytelności kodu, ale w pełni funkcjonalne) ---
        elif choice == "📅 MONTAŻE":
            df_in = df[(df['Nr Proj.'] != "") & (df['Nr Proj.'] != "EMPTIES") & (~df['STATUS'].isin(["ROZŁADOWANY", "ZAŁADOWANY", "DO ZAPLANOWANIA", "PUSTE DOSTARCZONE", "PEŁNE ODEBRANE"]))].copy()
            ed_in = st.data_editor(df_in, use_container_width=True, key="ed_in", column_config=column_cfg, hide_index=True)
            edit_trackers["ed_in"] = (df_in, ed_in)
        elif choice == "🟢 ROZŁADOWANE":
            df_out = df[df['STATUS'].isin(["ROZŁADOWANY", "ZAŁADOWANY"])].copy()
            ed_out = st.data_editor(df_out, use_container_width=True, key="ed_out", column_config=column_cfg, hide_index=True)
            edit_trackers["ed_out"] = (df_out, ed_out)
        elif choice == "⚪ PUSTE TRUCKI":
            df_empty = df[df['STATUS'].isin(["PUSTY", "📦 EMPTIES"])].copy()
            ed_empty = st.data_editor(df_empty, use_container_width=True, key="ed_empty", hide_index=True)
            edit_trackers["ed_empty"] = (df_empty, ed_empty)
        elif choice == "📦 SLOTY NA EMPTIES":
            df_sl = df[df['Nr Proj.'] == "EMPTIES"].copy()
            ed_sl = st.data_editor(df_sl, use_container_width=True, key="ed_sl", column_config=column_cfg, hide_index=True)
            edit_trackers["ed_sl"] = (df_sl, ed_sl)
        elif choice == "📚 BAZA":
            ed_full = st.data_editor(df, use_container_width=True, key="ed_full", column_config=column_cfg, hide_index=True)
            edit_trackers["ed_full"] = (df, ed_full)

        # --- 8. GLOBALNY ZAPIS Z AUTO-UZUPEŁNIANIEM ---
        if edit_trackers:
            st.divider()
            if st.button("💾 ZAPISZ WSZYSTKIE ZMIANY", type="primary", use_container_width=True):
                final_df = df.copy()
                for k, (orig_df, ed_component) in edit_trackers.items():
                    changes = st.session_state[k].get("edited_rows", {})
                    if k == "ed_demo":
                        new_rows = []
                        for r_idx, c_vals in changes.items():
                            row_data = orig_df.iloc[int(r_idx)].to_dict()
                            row_data.update(c_vals)
                            
                            # LOGIKA AUTO-FILL (podczas zapisu)
                            p_name = row_data.get('Przewoźnik')
                            if p_name in carriers_db:
                                if not row_data.get('Auto'): row_data['Auto'] = carriers_db[p_name]['Auto']
                                if not row_data.get('Kierowca'): row_data['Kierowca'] = carriers_db[p_name]['Kierowca']
                            
                            new_rows.append(row_data)
                        if new_rows: final_df = pd.concat([final_df, pd.DataFrame(new_rows)], ignore_index=True)
                    else:
                        for r_idx, c_vals in changes.items():
                            actual_idx = orig_df.index[int(r_idx)]
                            for col, val in c_vals.items(): final_df.at[actual_idx, col] = val

                to_save = final_df.copy()
                if "PODGLĄD" in to_save.columns: to_save = to_save.drop(columns=["PODGLĄD"])
                conn.update(spreadsheet=URL, data=to_save[all_cols])
                st.cache_data.clear(); st.success("Zapisano i uzupełniono dane transportowe!"); st.rerun()

    except Exception as e:
        st.error(f"Błąd aplikacji: {e}")
