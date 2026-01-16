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
            background-color: #1e1e1e;
            color: #ffffff;
            padding: 15px;
            border-radius: 10px;
            border-left: 5px solid #00ff00;
            margin-bottom: 20px;
        }
        </style>
        """, unsafe_allow_html=True)

    # --- 4. POŁĄCZENIE I DANE ---
    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    try:
        raw_df = conn.read(spreadsheet=URL, ttl="1m")
        df = raw_df.dropna(how="all").reset_index(drop=True)
        
        # Definicja wszystkich kolumn w bazie (dodane 'Opłata')
        all_cols = [
            'Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 
            'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 
            'zrzut z currenta', 'SLOT', 'dodatkowe zdjęcie', 'NOTATKA', 'Opłata'
        ]
        
        for col in all_cols:
            if col not in df.columns:
                df[col] = ""
            if col != "PODGLĄD":
                df[col] = df[col].astype(str).replace(['nan', 'None', 'NAT', 'nan nan', '<NA>', 'None None'], '')

        if "PODGLĄD" not in df.columns:
            idx = df.columns.get_loc("NOTATKA")
            df.insert(idx, "PODGLĄD", False)
        else:
            df["PODGLĄD"] = pd.to_numeric(df["PODGLĄD"], errors='coerce').fillna(0).map(lambda x: True if x == 1 or x is True else False)

        # Pobieranie unikalnych przewoźników do list wyboru
        lista_przewoznikow = sorted([p for p in df['Przewoźnik'].unique() if p and p != ''])

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
            ], width="medium"),
            "Przewoźnik": st.column_config.SelectboxColumn("Przewoźnik", options=lista_przewoznikow),
            "spis casów": st.column_config.LinkColumn("📋 Spis", display_text="Otwórz"),
            "SLOT": st.column_config.LinkColumn("⏰ SLOT", display_text="Otwórz"),
            "PODGLĄD": st.column_config.CheckboxColumn("👁️", width="small")
        }

        # --- 6. METRYKI ---
        st.title("🏗️ SQM Control Tower")
        m1, m2, m3 = st.columns(3)
        m1.metric("W TRASIE 🟡", len(df[df['STATUS'].str.contains("TRASIE", na=False)]))
        m2.metric("POD RAMPĄ 🔴", len(df[df['STATUS'].str.contains("RAMP", na=False)]))
        m3.metric("ZAKOŃCZONE 🟢", len(df[df['STATUS'].str.contains("ROZŁADOWANY", na=False)]))

        # --- 7. NAWIGACJA ---
        menu_options = ["📅 MONTAŻE", "🟢 ROZŁADOWANE", "⚪ PUSTE TRUCKI", "📦 SLOTY NA EMPTIES", "🛠️ DEMONTAŻE", "📚 BAZA"]
        choice = st.radio("Widok:", menu_options, horizontal=True, key="main_nav")
        st.divider()

        edit_trackers = {}

        # --- SEKTYCJA: MONTAŻE (Domyślny widok) ---
        if choice == "📅 MONTAŻE":
            mask_in = (df['Nr Proj.'] != "") & (df['Nr Proj.'] != "EMPTIES") & (~df['STATUS'].isin(["ROZŁADOWANY", "ZAŁADOWANY", "DO ZAPLANOWANIA", "PUSTE DOSTARCZONE", "PEŁNE ODEBRANE"]))
            df_in = df[mask_in].copy()
            ed_in = st.data_editor(df_in, use_container_width=True, key="ed_in", column_config=column_cfg, hide_index=True)
            edit_trackers["ed_in"] = (df_in, ed_in)

        # --- SEKTYCJA: ROZŁADOWANE ---
        elif choice == "🟢 ROZŁADOWANE":
            df_out = df[df['STATUS'].isin(["ROZŁADOWANY", "ZAŁADOWANY"])].copy()
            ed_out = st.data_editor(df_out, use_container_width=True, key="ed_out", column_config=column_cfg, hide_index=True)
            edit_trackers["ed_out"] = (df_out, ed_out)

        # --- SEKTYCJA: PUSTE TRUCKI ---
        elif choice == "⚪ PUSTE TRUCKI":
            df_empty = df[df['STATUS'].isin(["PUSTY", "📦 EMPTIES"])].copy()
            if not df_empty.empty:
                df_empty_grouped = df_empty.groupby('Auto').agg({'Przewoźnik': 'first', 'Kierowca': 'first', 'STATUS': 'first'}).reset_index()
                ed_empty = st.data_editor(df_empty_grouped, use_container_width=True, key="ed_empty", hide_index=True)
                edit_trackers["ed_empty"] = (df_empty_grouped, ed_empty)

        # --- SEKTYCJA: SLOTY NA EMPTIES ---
        elif choice == "📦 SLOTY NA EMPTIES":
            df_sl = df[df['Nr Proj.'] == "EMPTIES"].copy()
            ed_sl = st.data_editor(df_sl, use_container_width=True, key="ed_sl", column_config=column_cfg, hide_index=True)
            edit_trackers["ed_sl"] = (df_sl, ed_sl)

        # --- SEKTYCJA: DEMONTAŻE (NOWA LOGIKA) ---
        elif choice == "🛠️ DEMONTAŻE":
            st.subheader("🚛 Planowanie Demontaży")
            
            # Pobieramy bazę projektów (bez duplikowania tych samych projektów, jeśli są wielokrotnie)
            df_base_projs = df[(df['Nr Proj.'] != "") & (df['Nr Proj.'] != "EMPTIES")].drop_duplicates(subset=['Nr Proj.']).copy()
            
            # Tworzymy "czysty" widok dla demontaży - bierzemy tylko te 3 kolumny, reszta pusta
            df_demo = pd.DataFrame(columns=all_cols)
            df_demo['Nr Proj.'] = df_base_projs['Nr Proj.']
            df_demo['Nazwa Projektu'] = df_base_projs['Nazwa Projektu']
            df_demo['Hala'] = df_base_projs['Hala']
            df_demo = df_demo.fillna("")
            
            # Kolejność wyświetlania
            cols_to_show = [
                'Nr Proj.', 'Nazwa Projektu', 'Hala', 'Nr Slotu', 'Data', 'Godzina', 
                'STATUS', 'Przewoźnik', 'Auto', 'Kierowca', 'Opłata', 'SLOT', 'NOTATKA'
            ]
            
            demo_cfg = column_cfg.copy()
            demo_cfg["STATUS"] = st.column_config.SelectboxColumn(
                "STATUS", options=["DO ZAPLANOWANIA", "PUSTE DOSTARCZONE", "PEŁNE ODEBRANE"], width="medium"
            )

            ed_demo = st.data_editor(
                df_demo[cols_to_show],
                use_container_width=True,
                key="ed_demo",
                column_config=demo_cfg,
                hide_index=True
            )
            edit_trackers["ed_demo"] = (df_demo, ed_demo)

        # --- SEKTYCJA: BAZA ---
        elif choice == "📚 BAZA":
            ed_full = st.data_editor(df, use_container_width=True, key="ed_full", column_config=column_cfg, hide_index=True)
            edit_trackers["ed_full"] = (df, ed_full)

        # --- 8. GLOBALNY ZAPIS ---
        if edit_trackers:
            st.divider()
            if st.button("💾 ZAPISZ ZMIANY / DODAJ DEMONTAŻE", type="primary", use_container_width=True):
                final_df = df.copy()
                
                for k, (orig_df, ed_component) in edit_trackers.items():
                    changes = st.session_state[k].get("edited_rows", {})
                    
                    if k == "ed_demo":
                        # Dla demontaży dodajemy NOWE wiersze do bazy zamiast nadpisywać stare
                        new_rows_list = []
                        for r_idx, c_vals in changes.items():
                            # Pobieramy dane podstawowe z czystego wiersza
                            base_row = orig_df.iloc[int(r_idx)].to_dict()
                            # Aktualizujemy o to, co wpisał użytkownik
                            base_row.update(c_vals)
                            
                            # Logika AUTO-FILL: Jeśli wybrano przewoźnika, znajdź jego dane w bazie głównej
                            if 'Przewoźnik' in c_vals and c_vals['Przewoźnik'] != "":
                                match = df[df['Przewoźnik'] == c_vals['Przewoźnik']].iloc[-1:] # bierzemy ostatnie znane dane
                                if not match.empty:
                                    if 'Auto' not in c_vals: base_row['Auto'] = match['Auto'].values[0]
                                    if 'Kierowca' not in c_vals: base_row['Kierowca'] = match['Kierowca'].values[0]
                            
                            new_rows_list.append(base_row)
                        
                        if new_rows_list:
                            new_df_rows = pd.DataFrame(new_rows_list)
                            final_df = pd.concat([final_df, new_df_rows], ignore_index=True)
                    
                    else:
                        # Standardowe nadpisywanie dla reszty zakładek
                        for r_idx, c_vals in changes.items():
                            actual_idx = orig_df.index[int(r_idx)]
                            for col, val in c_vals.items():
                                final_df.at[actual_idx, col] = val

                # Przygotowanie do wysyłki
                to_save = final_df.copy()
                if "PODGLĄD" in to_save.columns: to_save = to_save.drop(columns=["PODGLĄD"])
                
                # Zapis do Google Sheets
                conn.update(spreadsheet=URL, data=to_save[all_cols])
                st.cache_data.clear()
                st.success("Baza zaktualizowana!")
                st.rerun()

    except Exception as e:
        st.error(f"Błąd: {e}")
