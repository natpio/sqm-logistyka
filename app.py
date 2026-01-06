import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# ==========================================
# 1. KONFIGURACJA STRONY I STYLE CSS
# ==========================================
st.set_page_config(
    page_title="SQM CONTROL TOWER", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# Stylizacja: Tła metryk, zakładki i przyciski
st.markdown("""
    <style>
    /* Styl kafelków dashboardu */
    div[data-testid="stMetric"] {
        background-color: #f8f9fb;
        border: 1px solid #e0e0e0;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    /* Wyraźniejszy kolor liczb w metrykach */
    div[data-testid="stMetricValue"] > div {
        color: #1f77b4;
    }
    /* Styl zakładek */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #f0f2f6;
        border-radius: 5px 5px 0 0;
        padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1f77b4 !important;
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Połączenie
URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# ==========================================
# 2. POBIERANIE I NAPRAWA DANYCH
# ==========================================
try:
    # TTL 5s dla dynamicznej pracy na hali
    df = conn.read(spreadsheet=URL, ttl=5).dropna(how="all")

    # TWOJA KOMPLETNA LISTA KOLUMN
    all_cols = [
        'Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 
        'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 
        'STATUS', 'spis casów', 'zdjęcie po załadunku', 
        'SLOT', 'dodatkowe zdjęcie', 'NOTATKA'
    ]
    
    # Krytyczna poprawka: Wymuszamy typ tekstowy dla wszystkich kolumn
    for col in all_cols:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].astype(str).replace('nan', '')

    # ==========================================
    # 3. NAGŁÓWEK I DASHBOARD (METRYKI)
    # ==========================================
    st.title("🏗️ SQM Logistics Control Tower")
    
    # Obliczenia do metryk
    total_trucks = len(df)
    under_ramp = len(df[df['STATUS'].str.contains("RAMP", na=False)])
    in_transit = len(df[df['STATUS'].str.contains("TRASIE", na=False)])
    completed = len(df[df['STATUS'].str.contains("ROZŁADOWANY", na=False)])

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Suma transportów", total_trucks)
    m2.metric("POD RAMPĄ 🔴", under_ramp)
    m3.metric("W TRASIE 🟡", in_transit)
    m4.metric("ZAKOŃCZONE 🟢", completed)

    st.write("##")

    # ==========================================
    # 4. PODZIAŁ NA ZAKŁADKI (OPERACYJNE)
    # ==========================================
    tab_active, tab_priority, tab_full = st.tabs([
        "🚀 OPERACJE DZISIAJ", 
        "🚨 TYLKO POD RAMPĄ", 
        "📚 PEŁNA BAZA (EDYCJA)"
    ])

    # --- ZAKŁADKA 1: DZISIAJSZE OPERACJE ---
    with tab_active:
        col_search, col_ref = st.columns([4, 1])
        with col_search:
            search = st.text_input("🔍 Filtruj (Nr rej / Projekt / Kierowca):", key="search_active")
        with col_ref:
            st.write("##")
            if st.button("🔄 Odśwież", use_container_width=True):
                st.cache_data.clear()
                st.rerun()

        # Filtrujemy transporty, które NIE są jeszcze rozładowane
        active_mask = ~df['STATUS'].str.contains("ROZŁADOWANY", na=False)
        display_df = df[active_mask].copy()

        if search:
            display_df = display_df[display_df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]

        # Edytor dla aktywnych transportów
        updated_active = st.data_editor(
            display_df,
            use_container_width=True,
            num_rows="dynamic",
            key="active_editor",
            column_config={
                "STATUS": st.column_config.SelectboxColumn("STATUS", options=["🟡 W TRASIE", "🔴 POD RAMPĄ", "🟢 ROZŁADOWANY", "📦 EMPTIES", "🚚 ZAŁADOWANY", "⚪ status-planned"]),
                "spis casów": st.column_config.LinkColumn("📋 Spis", display_text="Otwórz"),
                "zdjęcie po załadunku": st.column_config.LinkColumn("📸 Foto", display_text="Otwórz"),
                "SLOT": st.column_config.LinkColumn("⏰ SLOT", display_text="Otwórz"),
                "dodatkowe zdjęcie": st.column_config.LinkColumn("➕ Dodatkowe", display_text="Otwórz"),
                "NOTATKA": st.column_config.TextColumn("📝 NOTATKA", width="large")
            }
        )

    # --- ZAKŁADKA 2: TYLKO POD RAMPĄ ---
    with tab_priority:
        st.subheader("Auta aktualnie obsługiwane")
        ramp_only = df[df['STATUS'].str.contains("RAMP", na=False)]
        if not ramp_only.empty:
            st.table(ramp_only[['Hala', 'Auto', 'Kierowca', 'Nazwa Projektu', 'Godzina']])
        else:
            st.info("Brak aut pod rampą.")

    # --- ZAKŁADKA 3: PEŁNA BAZA ---
    with tab_full:
        st.subheader("Wszystkie dane (łącznie z archiwalnymi)")
        full_editor = st.data_editor(df, use_container_width=True, key="full_editor")

    # ==========================================
    # 5. LOGIKA ZAPISU (INTEGRACJA)
    # ==========================================
    st.divider()
    if st.button("💾 ZAPISZ WSZYSTKIE ZMIANY", type="primary", use_container_width=True):
        with st.spinner("Synchronizacja z Google Sheets..."):
            try:
                # Decydujemy które dane zapisać (priorytet ma aktywny edytor)
                # Jeśli użytkownik edytował w zakładce 1, aktualizujemy główny df
                if not updated_active.equals(display_df):
                    df.update(updated_active)
                    conn.update(spreadsheet=URL, data=df)
                else:
                    conn.update(spreadsheet=URL, data=full_editor)
                
                st.cache_data.clear()
                st.success("Zapisano pomyślnie!")
                st.rerun()
            except Exception as e:
                st.error(f"Błąd zapisu: {e}")

except Exception as e:
    st.error(f"Błąd krytyczny aplikacji: {e}")
