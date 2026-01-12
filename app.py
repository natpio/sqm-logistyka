import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time
from streamlit_cookies_controller import CookieController

# --- 1. KONFIGURACJA ---
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
            background-color: #2c3e50; color: white; padding: 10px 20px;
            border-radius: 8px; margin: 30px 0 10px 0; display: flex;
            justify-content: space-between; align-items: center; font-weight: bold;
        }
        .transport-card {
            background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 10px;
            padding: 15px; margin-bottom: 10px; border-left: 8px solid #ccc;
        }
        .status-trasie { border-left-color: #ffeb3b; }
        .status-rampa { border-left-color: #f44336; }
        .status-rozladowany { border-left-color: #4caf50; }
        .status-empties { border-left-color: #9e9e9e; }
        .status-zaladowany { border-left-color: #2196f3; }
        </style>
        """, unsafe_allow_html=True)

    # --- 4. DANE ---
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

        # --- 5. SIDEBAR ---
        with st.sidebar:
            st.header("⚙️ Ustawienia")
            view_mode = st.radio("Zmień widok:", ["Tradycyjny", "Kafelkowy"])
            f_hala, f_status = [], []
            if view_mode == "Kafelkowy":
                st.divider()
                st.subheader("🔍 Filtry Widoku")
                f_hala = st.multiselect("Hala:", options=sorted(df['Hala'].unique()))
                f_status = st.multiselect("Status:", options=sorted(df['STATUS'].unique()))
            st.divider()
            if st.button("Wyloguj"):
                controller.remove("sqm_login_key")
                st.rerun()

        # --- 6. METRYKI ---
        st.title("🏗️ SQM Control Tower")
        p_df = df[df['STATUS'].str.contains("PUSTY|EMPTIES", na=False, case=False)]
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("W TRASIE 🟡", len(df[df['STATUS'].str.contains("TRASIE", na=False)]))
        m2.metric("POD RAMPĄ 🔴", len(df[df['STATUS'].str.contains("RAMP", na=False)]))
        m3.metric("ZAKOŃCZONE 🟢", len(df[df['STATUS'].str.contains("ROZŁADOWANY", na=False)]))
        m4.metric("PUSTE TRUCKI ⚪", p_df['Auto'].nunique())

        # CIĄG DALSZY W CZĘŚCI 2...
        # --- 7. ZAKŁADKI ---
        tabs = st.tabs(["📅 MONTAŻE", "🟢 ROZŁADOWANE", "⚪ PUSTE TRUCKI", "📚 BAZA"])
        edit_trackers = {}

        for i, (tab, key) in enumerate(zip(tabs, ["in", "out", "empty", "full"])):
            with tab:
                # Maski
                if key == "in": mask = (~df['STATUS'].str.contains("ROZŁADOWANY|ZAŁADOWANY|PUSTY|EMPTIES", na=False, case=False))
                elif key == "out": mask = df['STATUS'].str.contains("ROZŁADOWANY|ZAŁADOWANY", na=False, case=False)
                elif key == "empty": mask = df['STATUS'].str.contains("PUSTY|EMPTIES", na=False, case=False)
                else: mask = None

                df_view = df[mask].copy() if mask is not None else df.copy()

                # Zakładka PUSTE TRUCKI - UNIKALNE
                if key == "empty":
                    if not df_view.empty:
                        df_view = df_view.groupby('Auto').agg({'Przewoźnik':'first','Kierowca':'first','STATUS':'first'}).reset_index()
                        df_view = df_view[['Przewoźnik', 'Auto', 'Kierowca', 'STATUS']]
                else:
                    # Filtry daty i szukania
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        all_d = st.checkbox("Wszystkie dni", value=True, key=f"all_{key}")
                        if not all_d:
                            # KALENDARZ WYBORU DNIA
                            d_input = st.date_input("Dzień z kalendarza:", value=datetime.now(), key=f"date_{key}")
                            df_view = df_view[df_view['Data'].astype(str).str.contains(str(d_input))]
                    with c2:
                        src = st.text_input("🔍 Szukaj:", key=f"src_{key}")
                        if src:
                            df_view = df_view[df_view.apply(lambda r: r.astype(str).str.contains(src, case=False).any(), axis=1)]

                # LP I USUWANIE
                df_view.insert(0, "LP", range(1, len(df_view) + 1))
                if key != "empty": df_view.insert(1, "USUŃ", False)

                if view_mode == "Tradycyjny":
                    cfg = {
                        "LP": st.column_config.NumberColumn("LP", width="small", disabled=True),
                        "USUŃ": st.column_config.CheckboxColumn("🗑️", width="small"),
                        "PODGLĄD": st.column_config.CheckboxColumn("👁️", width="small"),
                        "STATUS": st.column_config.SelectboxColumn("STATUS", options=["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ PUSTE"]),
                        "spis casów": st.column_config.LinkColumn("📋 Spis", display_text="Otwórz"),
                        "zdjęcie po załadunku": st.column_config.LinkColumn("📸 Foto", display_text="Otwórz"),
                        "zrzut z currenta": st.column_config.LinkColumn("🖼️ Current", display_text="Otwórz"),
                        "SLOT": st.column_config.LinkColumn("⏰ SLOT", display_text="Otwórz")
                    }
                    ed = st.data_editor(df_view, use_container_width=True, hide_index=True, key=f"ed_{key}", column_config=cfg)
                    edit_trackers[f"ed_{key}"] = (df_view, ed)
                    
                    if not ed[ed["PODGLĄD"] == True].empty:
                        row = ed[ed["PODGLĄD"] == True].iloc[-1]
                        st.info(f"**Notatka dla {row['Auto']}:** {row['NOTATKA']}")
                else:
                    # WIDOK KAFELKOWY
                    df_tile = df_view.copy()
                    if f_hala: df_tile = df_tile[df_tile['Hala'].isin(f_hala)]
                    if f_status: df_tile = df_tile[df_tile['STATUS'].isin(f_status)]
                    for truck in df_tile['Auto'].unique():
                        t_data = df_tile[df_tile['Auto'] == truck]
                        st.markdown(f'<div class="truck-separator">🚛 AUTO: {truck} | {t_data.iloc[0]["Przewoźnik"]}</div>', unsafe_allow_html=True)
                        cols = st.columns(3)
                        for idx, (_, r) in enumerate(t_data.iterrows()):
                            with cols[idx % 3]:
                                s_c = "status-trasie" if "TRASIE" in r['STATUS'] else "status-rampa" if "RAMP" in r['STATUS'] else "status-rozladowany" if "ROZŁADOWANY" in r['STATUS'] else ""
                                st.markdown(f'<div class="transport-card {s_c}"><b>{r["Nazwa Projektu"]}</b><br>Hala: {r["Hala"]} | {r["Godzina"]}<br><small>{r["STATUS"]}</small></div>', unsafe_allow_html=True)

        # --- 8. ZAPIS ZMIAN ---
        st.divider()
        if st.button("💾 ZAPISZ ZMIANY / USUŃ ZAZNACZONE", type="primary", use_container_width=True):
            final_df = df.copy()
            rows_to_delete = []
            for k, (orig_p, ed_p) in edit_trackers.items():
                ch = st.session_state[k].get("edited_rows", {})
                for r_idx, cols in ch.items():
                    ri = int(r_idx)
                    if k == "ed_empty":
                        final_df.loc[final_df['Auto'] == orig_p.iloc[ri]['Auto'], 'STATUS'] = cols.get("STATUS")
                    else:
                        real_idx = orig_p.index[ri]
                        if cols.get("USUŃ"): rows_to_delete.append(real_idx)
                        else:
                            for c, v in cols.items():
                                if c not in ["LP", "USUŃ", "PODGLĄD"]: final_df.at[real_idx, c] = v
            if rows_to_delete: final_df = final_df.drop(rows_to_delete)
            conn.update(spreadsheet=URL, data=final_df.drop(columns=["LP","USUŃ","PODGLĄD"], errors='ignore'))
            st.cache_data.clear()
            st.success("Baza zaktualizowana!"); time.sleep(1); st.rerun()

    except Exception as e:
        st.error(f"Wystąpił błąd: {e}")
