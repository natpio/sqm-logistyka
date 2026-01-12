import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time
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
        </style>
        """, unsafe_allow_html=True)

    # --- 4. POŁĄCZENIE I DANE ---
    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    try:
        # Wczytujemy dane i resetujemy indeks, aby mieć czystą bazę do mapowania
        raw_df = conn.read(spreadsheet=URL, ttl="10s").dropna(how="all")
        df = raw_df.reset_index(drop=True)
        
        all_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'zrzut z currenta', 'SLOT', 'dodatkowe zdjęcie', 'NOTATKA']
        for col in all_cols:
            if col not in df.columns: df[col] = ""
            df[col] = df[col].astype(str).replace('nan', '')

        # FIX dla błędu "ColumnDataKind.FLOAT":
        # Tworzymy kolumnę PODGLĄD jako typ bool, co rozwiązuje błąd widoczny na screenie
        df["PODGLĄD"] = False
        # Dodajemy kolumnę USUŃ (techniczną), aby móc usuwać wiersze
        df.insert(0, "USUŃ", False)

        # --- 5. SIDEBAR ---
        with st.sidebar:
            st.header("⚙️ Ustawienia")
            view_mode = st.radio("Zmień widok:", ["Tradycyjny", "Kafelkowy"])
            if view_mode == "Kafelkowy":
                st.divider()
                f_hala = st.multiselect("Hala:", options=sorted(df['Hala'].unique()))
                f_status = st.multiselect("Status:", options=sorted(df['STATUS'].unique()))
            st.divider()
            if st.button("Wyloguj"):
                controller.remove("sqm_login_key")
                st.rerun()

        # --- 6. NAGŁÓWEK I METRYKI ---
        st.title("🏗️ SQM Control Tower")
        m1, m2, m3 = st.columns(3)
        m1.metric("W TRASIE 🟡", len(df[df['STATUS'].str.contains("TRASIE", na=False)]))
        m2.metric("POD RAMPĄ 🔴", len(df[df['STATUS'].str.contains("RAMP", na=False)]))
        m3.metric("ZAKOŃCZONE 🟢", len(df[df['STATUS'].str.contains("ROZŁADOWANY", na=False)]))

        # --- 7. ZAKŁADKI ---
        tabs = st.tabs(["📅 MONTAŻE", "🟢 ROZŁADOWANE", "⚪ PUSTE TRUCKI", "📚 BAZA"])
        edit_trackers = {}

        for i, (tab, key) in enumerate(zip(tabs, ["in", "out", "empty", "full"])):
            with tab:
                if key == "in":
                    mask = (~df['STATUS'].str.contains("ROZŁADOWANY|ZAŁADOWANY|PUSTY|EMPTIES", na=False, case=False))
                elif key == "out":
                    mask = df['STATUS'].str.contains("ROZŁADOWANY|ZAŁADOWANY", na=False, case=False)
                elif key == "empty":
                    mask = df['STATUS'].str.contains("PUSTY|EMPTIES", na=False, case=False)
                else: mask = None

                df_view = df[mask].copy() if mask is not None else df.copy()

                # Filtrowanie daty i szukanie
                if key != "empty":
                    c1, c2, c3 = st.columns([1.5, 2, 1])
                    with c1:
                        d_val = st.date_input("Dzień:", value=datetime.now(), key=f"d_{key}")
                        all_d = st.checkbox("Wszystkie dni", value=True, key=f"a_{key}")
                    with c2: search = st.text_input("🔍 Szukaj:", key=f"s_{key}")
                    with c3:
                        st.write("###")
                        if st.button("🔄 Odśwież", key=f"r_{key}"):
                            st.cache_data.clear()
                            st.rerun()

                    if not all_d:
                        df_view = df_view[df_view['Data'] == str(d_val)]
                    if search:
                        df_view = df_view[df_view.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]

                # Wyświetlanie danych
                if view_mode == "Tradycyjny":
                    column_cfg = {
                        "USUŃ": st.column_config.CheckboxColumn("🗑️", width="small"),
                        "PODGLĄD": st.column_config.CheckboxColumn("👁️", width="small"),
                        "STATUS": st.column_config.SelectboxColumn("STATUS", options=["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ PUSTE"], width="medium"),
                        "spis casów": st.column_config.LinkColumn("📋 Spis", display_text="Otwórz"),
                        "zdjęcie po załadunku": st.column_config.LinkColumn("📸 Foto", display_text="Otwórz"),
                        "zrzut z currenta": st.column_config.LinkColumn("🖼️ Current", display_text="Otwórz"),
                        "SLOT": st.column_config.LinkColumn("⏰ SLOT", display_text="Otwórz")
                    }
                    ed = st.data_editor(df_view, use_container_width=True, hide_index=True, key=f"ed_{key}", column_config=column_cfg)
                    edit_trackers[f"ed_{key}"] = (df_view, ed)
                    
                    if not ed[ed["PODGLĄD"] == True].empty:
                        row = ed[ed["PODGLĄD"] == True].iloc[-1]
                        st.info(f"**Notatka:** {row['NOTATKA']}")
                else:
                    st.warning("Widok kafelkowy nie obsługuje edycji. Przełącz na Tradycyjny, aby zapisać zmiany.")

        # --- 8. GLOBALNY ZAPIS I USUWANIE (Fix błędu out of bounds) ---
        st.divider()
        if st.button("💾 ZAPISZ ZMIANY / USUŃ ZAZNACZONE", type="primary", use_container_width=True):
            final_df = df.copy()
            rows_to_delete = []

            for k, (orig_df_part, ed_df) in edit_trackers.items():
                # Streamlit session state przechowuje tylko zmiany
                changes = st.session_state[k].get("edited_rows", {})
                
                for r_idx_str, col_ch in changes.items():
                    # Mapowanie indeksu widoku na indeks bazy głównej
                    real_idx = orig_df_part.index[int(r_idx_str)]
                    
                    if col_ch.get("USUŃ") == True:
                        rows_to_delete.append(real_idx)
                    else:
                        for col, val in col_ch.items():
                            if col not in ["USUŃ", "PODGLĄD"]:
                                final_df.at[real_idx, col] = val
            
            # Usuwamy zaznaczone wiersze
            if rows_to_delete:
                final_df = final_df.drop(rows_to_delete)
            
            # Czyścimy kolumny techniczne przed zapisem do GSheets
            cols_to_drop = [c for c in ["USUŃ", "PODGLĄD"] if c in final_df.columns]
            final_df = final_df.drop(columns=cols_to_drop)
            
            conn.update(spreadsheet=URL, data=final_df)
            st.cache_data.clear()
            st.success(f"Pomyślnie zaktualizowano bazę! (Usunięto: {len(rows_to_delete)})")
            time.sleep(1)
            st.rerun()

    except Exception as e:
        st.error(f"Wystąpił błąd: {e}")
