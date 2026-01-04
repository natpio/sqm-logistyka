import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# Konfiguracja PRO-99
st.set_page_config(page_title="SQM LOGISTICS PRO", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS dla wyglądu "Premium"
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stDataFrame { border: 1px solid #30363d; border-radius: 10px; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; padding: 15px; border-radius: 10px; }
    div[data-testid="stExpander"] { border: none !important; box-shadow: none !important; }
    </style>
    """, unsafe_allow_html=True)

URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    return conn.read(spreadsheet=URL, ttl=0).dropna(how="all")

try:
    df = load_data()

    # NAGŁÓWEK PRO
    col_t, col_s = st.columns([3, 1])
    with col_t:
        st.title("🚀 SQM Logistics Operations")
        st.caption("Barcelona ↔ Poznań Hub | Real-time Sync")
    
    # KPI - Wskaźniki na górze (wygląd Pro)
    total = len(df)
    in_transit = len(df[df['STATUS'] == 'w trasie'])
    unloaded = len(df[df['STATUS'] == 'ROZŁADOWANY'])
    
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Wszystkie transporty", total)
    kpi2.metric("W trasie", in_transit, delta_color="normal")
    kpi3.metric("Rozładowane", unloaded, delta=f"{int(unloaded/total*100)}%")
    kpi4.metric("Pod rampą", len(df[df['STATUS'] == 'pod rampą']))

    st.divider()

    # --- FILTROWANIE (Zintegrowane w jednej linii) ---
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        search = st.text_input("🔍 Szybkie wyszukiwanie (Auto, Projekt, Kierowca...)", placeholder="Wpisz cokolwiek...")
    with c2:
        hala_filter = st.multiselect("Hala", options=df['Hala'].unique())
    with c3:
        status_filter = st.multiselect("Status", options=df['STATUS'].unique())

    # Logika filtrów
    filtered_df = df.copy()
    if search:
        filtered_df = filtered_df[filtered_df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]
    if hala_filter:
        filtered_df = filtered_df[filtered_df['Hala'].isin(hala_filter)]
    if status_filter:
        filtered_df = filtered_df[filtered_df['STATUS'].isin(status_filter)]

    # --- EDYCJA BEZPOŚREDNIO W TABELI (PRO FEATURE) ---
    st.subheader("📋 Rejestr Operacyjny")
    st.info("💡 Kliknij dwukrotnie w komórkę STATUS, aby ją zmienić. Po edycji kliknij 'Zatwierdź zmiany' pod tabelą.")

    # Konfiguracja edytora kolumn
    updated_df = st.data_editor(
        filtered_df,
        use_container_width=True,
        hide_index=True,
        disabled=["Data", "Nr Slotu", "Godzina", "Hala", "Przewoźnik", "Auto", "Kierowca", "Nr Proj.", "Nazwa Projektu", "Foto1"], # Tylko STATUS edytowalny
        column_config={
            "STATUS": st.column_config.SelectboxColumn(
                "STATUS",
                help="Zmień status operacyjny",
                options=["status-planned", "w trasie", "pod rampą", "ROZŁADOWANY", "ZAŁADOWANY-POWRÓT"],
                required=True,
            ),
            "Foto1": st.column_config.LinkColumn("Zdjęcie")
        },
        key="main_editor"
    )

    # Przycisk zapisu (widoczny tylko gdy dane się zmieniły)
    if not updated_df.equals(filtered_df):
        if st.button("💾 ZATWIERDŹ ZMIANY I SYNCHRONIZUJ", type="primary", use_container_width=True):
            # Łączymy zmienione dane z oryginalnym DF (żeby zachować wiersze, które odfiltrowaliśmy)
            df.update(updated_df)
            conn.update(spreadsheet=URL, data=df)
            st.success("Dane zsynchronizowane z Google Sheets!")
            st.rerun()

except Exception as e:
    st.error(f"Krytyczny błąd aplikacji: {e}")
