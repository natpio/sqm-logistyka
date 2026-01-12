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
        </style>
        """, unsafe_allow_html=True)

    # --- 4. POŁĄCZENIE I DANE ---
    URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)

    try:
        raw_df = conn.read(spreadsheet=URL, ttl="10s").dropna(how="all")
        df = raw_df.reset_index(drop=True)
        
        all_cols = ['Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 'STATUS', 'spis casów', 'zdjęcie po załadunku', 'zrzut z currenta', 'SLOT', 'dodatkowe zdjęcie', 'NOTATKA']
        for col in all_cols:
            if col not in df.columns: df[col] = ""
            df[col] = df[col].astype(str).replace('nan', '')

        df["PODGLĄD"] = False
        # Zamiast kolumny USUŃ na początku, dodajemy ją później, by LP było pierwsze

        # --- 5. SIDEBAR ---
        with st.sidebar:
            st.header("⚙️ Ustawienia")
            view_mode = st.radio("Zmień widok:", ["Tradycyjny", "Kafelkowy"])
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

                # Filtrowanie i wyszukiwanie
                if key != "empty":
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        d_val = st.date_input("Dzień:", value=datetime.now(), key=f"d_{key}")
                        all_d = st.checkbox("Wszystkie dni", value=True, key=f"a_{key}")
                    with c2: search = st.text_input("🔍 Szukaj:", key=f"s_{key}")

                    if not all_d: df_view = df_view[df_view['Data'] == str(d_val)]
                    if search: df_view = df_view[df_view.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]

                # DODAWANIE NUMERACJI I KOLUMNY USUŃ
                df_view.insert(0, "LP", range(1, len(df_view) + 1)) # Numeracja od 1
                df_view.insert(1, "USUŃ", False)

                if view_mode == "Tradycyjny":
                    column_cfg = {
                        "LP": st.column_config.NumberColumn("LP", width="small", disabled=True),
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
                    
                    sel = ed[ed["PODGLĄD"] == True]
                    if not sel.empty:
                        row = sel.iloc[-1]
                        st.info(f"**Notatka:** {row['NOTATKA']}")
                else:
                    st.warning("Widok kafelkowy nie obsługuje edycji.")

        # --- 8. GLOBALNY ZAPIS I USUWANIE ---
        st.divider()
        if st.button("💾 ZAPISZ ZMIANY / USUŃ ZAZNACZONE", type="primary", use_container_width=True):
            final_df = df.copy()
            rows_to_delete = []

            for k, (orig_df_part, ed_df) in edit_trackers.items():
                changes = st.session_state[k].get("edited_rows", {})
                
                for r_idx_str, col_ch in changes.items():
                    # Mapowanie indeksu widoku na indeks bazy głównej
                    real_idx = orig_df_part.index[int(r_idx_str)]
                    
                    if col_ch.get("USUŃ") == True:
                        rows_to_delete.append(real_idx)
                    else:
                        for col, val in col_ch.items():
                            if col not in ["LP", "USUŃ", "PODGLĄD"]:
                                final_df.at[real_idx, col] = val
            
            if rows_to_delete: final_df = final_df.drop(rows_to_delete)
            
            # Usuwamy wszystkie kolumny techniczne przed zapisem do Sheets
            cols_to_drop = ["LP", "USUŃ", "PODGLĄD"]
            final_df = final_df.drop(columns=[c for c in cols_to_drop if c in final_df.columns])
            
            conn.update(spreadsheet=URL, data=final_df)
            st.cache_data.clear()
            st.success(f"Baza zaktualizowana! Usunięto: {len(rows_to_delete)}")
            time.sleep(1)
            st.rerun()

    except Exception as e:
        st.error(f"Wystąpił błąd: {e}")
