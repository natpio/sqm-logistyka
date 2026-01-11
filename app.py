import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from streamlit_cookies_controller import CookieController

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(page_title="SQM CONTROL TOWER", layout="wide", initial_sidebar_state="expanded")

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
        else: st.session_state["password_correct"] = False
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
        .truck-separator {
            background-color: #2c3e50;
            color: white;
            padding: 10px 20px;
            border-radius: 8px;
            margin: 30px 0 15px 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .transport-card {
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 10px;
            border-left: 8px solid #ccc;
        }
        .status-trasie { border-left-color: #ffeb3b; }
        .status-rampa { border-left-color: #f44336; }
        .status-rozladowany { border-left-color: #4caf50; }
        .status-empties { border-left-color: #9e9e9e; }
        .status-zaladowany { border-left-color: #2196f3; }
        .status-pusty { border-left-color: #ffffff; border-left-style: dashed; }
        hr.truck-line {
            border: 0;
            height: 2px;
            background-image: linear-gradient(to right, rgba(0, 0, 0, 0), rgba(0, 0, 0, 0.75), rgba(0, 0, 0, 0));
            margin-top: 40px;
        }
        </style>
        """, unsafe_allow_html=True)

    # --- 4. POŁĄCZENIE I DANE ---
    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    try:
        raw_df = conn.read(spreadsheet=URL, ttl="1m").dropna(how="all")
        df = raw_df.reset_index(drop=True)
        
        all_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'zrzut z currenta', 'SLOT', 'dodatkowe zdjęcie', 'NOTATKA']
        for col in all_cols:
            if col not in df.columns: df[col] = ""
            df[col] = df[col].astype(str).replace('nan', '')

        if "PODGLĄD" not in df.columns:
            df.insert(df.columns.get_loc("NOTATKA"), "PODGLĄD", False)

        # --- 5. SIDEBAR ---
        with st.sidebar:
            st.header("⚙️ Ustawienia")
            view_mode = st.radio("Zmień widok:", ["Tradycyjny", "Kafelkowy"])
            
            if view_mode == "Kafelkowy":
                st.divider()
                st.subheader("🔍 Filtry Widoku")
                f_hala = st.multiselect("Filtruj wg Hali:", options=sorted(df['Hala'].unique()))
                f_status = st.multiselect("Filtruj wg Statusu:", options=sorted(df['STATUS'].unique()))
                f_carrier = st.multiselect("Filtruj wg Przewoźnika:", options=sorted(df['Przewoźnik'].unique()))
            
            st.divider()
            if st.button("Wyloguj"):
                controller.remove("sqm_login_key")
                st.rerun()

        # Konfiguracje dla edytora
        column_cfg_main = {
            "STATUS": st.column_config.SelectboxColumn("STATUS", options=["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ PUSTY", "⚪ status-planned", "ODBIERA EMPTIES", "ZAWOZI EMPTIES", "ODBIERA PEŁNE", "POWRÓT DO KOMORNIK"], width="medium"),
            "Hala": st.column_config.SelectboxColumn("Hala", options=["HALA 1", "HALA 2", "HALA 3", "HALA 4", "HALA 5"]),
            "spis casów": st.column_config.LinkColumn("📋 Spis", display_text="Otwórz"),
            "zdjęcie po załadunku": st.column_config.LinkColumn("📸 Foto", display_text="Otwórz"),
            "zrzut z currenta": st.column_config.LinkColumn("🖼️ Current", display_text="Otwórz"),
            "SLOT": st.column_config.LinkColumn("⏰ SLOT", display_text="Otwórz"),
            "dodatkowe zdjęcie": st.column_config.LinkColumn("➕ Foto", display_text="Otwórz"),
            "PODGLĄD": st.column_config.CheckboxColumn("👁️", width="small"),
            "NOTATKA": st.column_config.TextColumn("📝 NOTATKA")
        }

        # --- 6. NAGŁÓWEK I METRYKI ---
        st.title("🏗️ SQM Control Tower")
        m1, m2, m3 = st.columns(3)
        m1.metric("W TRASIE 🟡", len(df[df['STATUS'].str.contains("TRASIE", na=False)]))
        m2.metric("POD RAMPĄ 🔴", len(df[df['STATUS'].str.contains("RAMP", na=False)]))
        m3.metric("ZAKOŃCZONE 🟢", len(df[df['STATUS'].str.contains("ROZŁADOWANY", na=False)]))

        # DEFINICJA ZAKŁADEK
        tabs = st.tabs(["📅 MONTAŻE", "🟢 ROZŁADOWANE", "⚪ PUSTE TRUCKI", "📦 SLOTY NA EMPTIES", "📚 BAZA"])
        
        statusy_rozladowane = "ROZŁADOWANY|ZAŁADOWANY"
        statusy_puste = "PUSTY|EMPTIES"
        statusy_empties_slots = "ODBIERA EMPTIES|ZAWOZI EMPTIES|ODBIERA PEŁNE|POWRÓT DO KOMORNIK"

        edit_trackers = {}

        for i, tab in enumerate(tabs):
            key = ["in", "out", "empty", "empties_slots", "full"][i]
            with tab:
                # 1. Filtrowanie bazowe dla zakładek
                if key == "in":
                    mask = (~df['STATUS'].str.contains(statusy_rozladowane, na=False, case=False)) & (~df['STATUS'].str.contains(statusy_puste, na=False, case=False)) & (~df['STATUS'].str.contains(statusy_empties_slots, na=False, case=False))
                elif key == "out":
                    mask = df['STATUS'].str.contains(statusy_rozladowane, na=False, case=False)
                elif key == "empty":
                    mask = df['STATUS'].str.contains(statusy_puste, na=False, case=False)
                elif key == "empties_slots":
                    mask = df['STATUS'].str.contains(statusy_empties_slots, na=False, case=False)
                else: mask = None

                df_view = df[mask].copy() if mask is not None else df.copy()

                # --- SPECYFIKA: SLOTY NA EMPTIES ---
                if key == "empties_slots":
                    st.subheader("Zarządzanie Slotami na Empties")
                    
                    # Edytor istniejących slotów
                    ed_es = st.data_editor(
                        df_view[['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'STATUS', 'NOTATKA']], 
                        use_container_width=True,
                        column_config=column_cfg_main,
                        key="ed_empties_slots",
                        hide_index=True
                    )
                    edit_trackers["ed_empties_slots"] = (df_view, ed_es)

                    st.divider()
                    st.subheader("➕ Dodaj nowy slot")
                    
                    # Pobieranie dostępnych aut z zakładki EMPTIES
                    df_empties_source = df[df['STATUS'].str.contains(statusy_puste, na=False, case=False)]
                    available_carriers = df_empties_source['Przewoźnik'].unique().tolist()

                    with st.form("new_empty_slot"):
                        c1, c2, c3, c4 = st.columns(4)
                        f_date = c1.date_input("Data", value=datetime.now())
                        f_slot = c2.text_input("Numer Slotu")
                        f_time = c3.text_input("Godzina")
                        f_hala = c4.selectbox("Hala", ["HALA 1", "HALA 2", "HALA 3", "HALA 4", "HALA 5"])
                        
                        c5, c6 = st.columns(2)
                        f_carrier = c5.selectbox("Przewoźnik (z zakładki EMPTIES)", options=available_carriers)
                        f_status = c6.selectbox("Status", ["ODBIERA EMPTIES", "ZAWOZI EMPTIES", "ODBIERA PEŁNE", "POWRÓT DO KOMORNIK"])
                        
                        if st.form_submit_button("DODAJ SLOT"):
                            # Pobierz dane auta i kierowcy dla wybranego przewoźnika
                            carrier_info = df_empties_source[df_empties_source['Przewoźnik'] == f_carrier].iloc[0]
                            new_row = {col: "" for col in df.columns}
                            new_row.update({
                                "Data": f_date.strftime("%Y-%m-%d"),
                                "Nr Slotu": f_slot,
                                "Godzina": f_time,
                                "Hala": f_hala,
                                "Przewoźnik": f_carrier,
                                "Auto": carrier_info['Auto'],
                                "Kierowca": carrier_info['Kierowca'],
                                "STATUS": f_status
                            })
                            
                            updated_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                            if "PODGLĄD" in updated_df.columns: updated_df = updated_df.drop(columns=["PODGLĄD"])
                            conn.update(spreadsheet=URL, data=updated_df)
                            st.cache_data.clear()
                            st.success("Slot dodany!")
                            st.rerun()

                # --- SPECYFIKA: PUSTE TRUCKI ---
                elif key == "empty":
                    if not df_view.empty:
                        df_empty_grouped = df_view.groupby('Auto').agg({
                            'Przewoźnik': 'first',
                            'Kierowca': 'first',
                            'STATUS': 'first'
                        }).reset_index()
                        
                        st.info("Poniżej lista unikalnych pojazdów o statusie PUSTY lub EMPTIES.")
                        ed_p = st.data_editor(
                            df_empty_grouped[['Przewoźnik', 'Auto', 'Kierowca', 'STATUS']], 
                            use_container_width=True, 
                            key="ed_empty",
                            column_config={"STATUS": st.column_config.SelectboxColumn("STATUS", options=["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ PUSTY"])},
                            hide_index=True
                        )
                        edit_trackers["ed_empty"] = (df_empty_grouped, ed_p)
                    else:
                        st.info("Obecnie brak pojazdów w statusie Pusty/Empties.")

                # --- STANDARDOWY WIDOK DLA RESZTY ---
                else:
                    c1, c2, c3 = st.columns([1.5, 2, 1])
                    with c1:
                        if key == "in":
                            d_val = st.date_input("Dzień:", value=datetime.now(), key=f"d_{key}")
                            all_d = st.checkbox("Wszystkie dni", value=True, key=f"a_{key}")
                    with c2: search = st.text_input("🔍 Szukaj:", key=f"s_{key}")
                    with c3:
                        st.write("###")
                        if st.button("🔄 Odśwież", key=f"r_{key}"):
                            st.cache_data.clear()
                            st.rerun()

                    if key == "in" and not all_d:
                        df_view['Data_dt'] = pd.to_datetime(df_view['Data'], errors='coerce')
                        df_view = df_view[df_view['Data_dt'].dt.date == d_val].drop(columns=['Data_dt'])
                    
                    if search:
                        df_view = df_view[df_view.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]

                    if view_mode == "Tradycyjny":
                        ed = st.data_editor(df_view, use_container_width=True, key=f"ed_{key}", column_config=column_cfg_main)
                        edit_trackers[f"ed_{key}"] = (df_view, ed)
                    else:
                        # (Tutaj Twoja funkcja render_grouped_tiles z oryginalnego kodu)
                        pass

        # --- 7. GLOBALNY ZAPIS ZMIAN ---
        if st.button("💾 ZAPISZ WSZYSTKIE ZMIANY TABELI", type="primary", use_container_width=True):
            final_df = df.copy()
            for k, (orig_df_part, ed_df) in edit_trackers.items():
                changes = st.session_state[k].get("edited_rows", {})
                
                if k == "ed_empty": 
                    for r_idx_str, col_ch in changes.items():
                        if "STATUS" in col_ch:
                            truck_id = orig_df_part.iloc[int(r_idx_str)]['Auto']
                            final_df.loc[final_df['Auto'] == truck_id, 'STATUS'] = col_ch["STATUS"]
                else: 
                    for r_idx_str, col_ch in changes.items():
                        real_idx = orig_df_part.index[int(r_idx_str)]
                        for col, val in col_ch.items():
                            final_df.at[real_idx, col] = val
            
            if "PODGLĄD" in final_df.columns: final_df = final_df.drop(columns=["PODGLĄD"])
            conn.update(spreadsheet=URL, data=final_df)
            st.cache_data.clear()
            st.success("Zapisano pomyślnie!")
            st.rerun()

    except Exception as e:
        st.error(f"Błąd: {e}")
