import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# ==========================================
# 1. KONFIGURACJA STRONY I STYLIZACJA
# ==========================================
st.set_page_config(
    page_title="SQM LOGISTICS PRO", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# Dodajemy odrobinę cienia pod metrykami dla lepszego wyglądu
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 24px; }
    div[data-testid="metric-container"] {
        background-color: rgba(28, 131, 225, 0.1);
        border: 1px solid rgba(28, 131, 225, 0.1);
        padding: 10px 15px;
        border-radius: 10px;
        color: #000000;
    }
    </style>
    """, unsafe_allow_html=True)

# Link do Twojego Arkusza
URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# ==========================================
# 2. POBIERANIE I NAPRAWA DANYCH
# ==========================================
try:
    df = conn.read(spreadsheet=URL, ttl=10).dropna(how="all")

    # TWOJA PEŁNA LISTA KOLUMN ZGODNA Z ARKUSZEM
    all_cols = [
        'Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 
        'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 
        'STATUS', 'spis casów', 'zdjęcie po załadunku', 
        'SLOT', 'dodatkowe zdjęcie', 'NOTATKA'
    ]
    
    # Naprawa typów danych (wymuszamy tekst, by edytor nie wywalał błędu)
    for col in all_cols:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].astype(str).replace('nan', '')

    # ==========================================
    # 3. DASHBOARD LOGISTYKA (PODRASOWANY WYGLĄD)
    # ==========================================
    st.title("🚀 SQM Logistics Operations")
    
    # Obliczamy statystyki do metryk
    total_trucks = len(df)
    under_ramp = len(df[df['STATUS'].str.contains("RAMP", na=False)])
    in_transit = len(df[df['STATUS'].str.contains("TRASIE", na=False)])
    completed = len(df[df['STATUS'].str.contains("ROZŁADOWANY", na=False)])

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Wszystkie transporty", total_trucks)
    m2.metric("Pod rampą 🔴", under_ramp)
    m3.metric("W trasie 🟡", in_transit)
    m4.metric("Zakończone 🟢", completed)

    st.markdown("---")

    # Sekcja wyszukiwania i odświeżania
    c1, c2 = st.columns([4, 1])
    with c1:
        search = st.text_input("🔍 Wyszukaj (Auto, Projekt, Kierowca, Hala...):", placeholder="Wpisz cokolwiek...")
    with c2:
        st.write("##") # Margines
        if st.button("🔄 Odśwież dane", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # Filtrowanie danych
    display_df = df.copy()
    if search:
        display_df = display_df[display_df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]

    # ==========================================
    # 4. EDYTOR DANYCH (GŁÓWNA TABELA)
    # ==========================================
    updated_df = st.data_editor(
        display_df,
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "STATUS": st.column_config.SelectboxColumn(
                "STATUS",
                options=[
                    "🟡 W TRASIE", 
                    "🔴 POD RAMPĄ", 
                    "🟢 ROZŁADOWANY", 
                    "📦 EMPTIES - ZAŁADUNEK", 
                    "🚚 ZAŁADOWANY NA POWRÓT", 
                    "⚪ status-planned"
                ],
                required=True
            ),
            # Załączniki jako przyciski
            "spis casów": st.column_config.LinkColumn("📋 Spis casów", display_text="Otwórz"),
            "zdjęcie po załadunku": st.column_config.LinkColumn("📸 Załadunek", display_text="Otwórz"),
            "SLOT": st.column_config.LinkColumn("⏰ SLOT", display_text="Otwórz"),
            "dodatkowe zdjęcie": st.column_config.LinkColumn("➕ Dodatkowe", display_text="Otwórz"),
            
            # Formaty kolumn tekstowych
            "NOTATKA": st.column_config.TextColumn("📝 NOTATKA", width="large"),
            "Data": st.column_config.TextColumn("📅 Data", width="small"),
            "Nr Slotu": st.column_config.TextColumn("Nr Slotu", width="small"),
            "Hala": st.column_config.TextColumn("Hala", width="small"),
        }
    )

    # ==========================================
    # 5. ZAPISYWANIE
    # ==========================================
    st.write("##")
    if st.button("💾 ZAPISZ WSZYSTKIE ZMIANY", type="primary", use_container_width=True):
        with st.spinner("Synchronizacja z bazą danych SQM..."):
            try:
                if search:
                    df.update(updated_df)
                    conn.update(spreadsheet=URL, data=df)
                else:
                    conn.update(spreadsheet=URL, data=updated_df)
                
                st.cache_data.clear()
                st.success("Dane zostały poprawnie zapisane w Arkuszu Google!")
                st.rerun()
            except Exception as e:
                st.error(f"Błąd zapisu: {e}")

except Exception as e:
    st.error(f"Wystąpił błąd: {e}")
