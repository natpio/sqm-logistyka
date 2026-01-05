import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(page_title="SQM LOGISTICS PRO", layout="wide", initial_sidebar_state="collapsed")

# Link do Twojego Arkusza
URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"

# Inicjalizacja połączenia
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. LOGIKA DANYCH ---
try:
    # Pobranie danych (cache 15s)
    df = conn.read(spreadsheet=URL, ttl=15).dropna(how="all")

    # TWOJA PEŁNA LISTA KOLUMN (Stare + Nowe)
    all_cols = [
        'Data', 'Nr Slotu', 'Godzina', 'Hala', 'Przewoźnik', 
        'Auto', 'Kierowca', 'Nr Proj.', 'Nazwa Projektu', 
        'STATUS', 'spis casów', 'zdjęcie po załadunku', 
        'SLOT', 'dodatkowe zdjęcie', 'NOTATKA'
    ]
    
    # Naprawa typów danych (wymuszamy tekst dla stabilności edytora)
    for col in all_cols:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].astype(str).replace('nan', '')

    st.title("🚀 SQM Logistics Operations")
    st.info("💡 Wklej linki do odpowiednich kolumn i kliknij ZAPISZ na dole.")
    
    if st.button("🔄 ODSWIEŻ TABELĘ"):
        st.cache_data.clear()
        st.rerun()

    search = st.text_input("🔍 Wyszukaj (Auto, Projekt, Hala...):")
    
    display_df = df.copy()
    if search:
        display_df = display_df[display_df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]

    # --- 3. EDYTOR DANYCH (Pełna konfiguracja) ---
    updated_df = st.data_editor(
        display_df,
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "STATUS": st.column_config.SelectboxColumn(
                "STATUS",
                options=["W TRASIE", "POD RAMPĄ", "ROZŁADOWANY", "EMPTIES - ZAŁADUNEK", "ZAŁADOWANY NA POWRÓT", "status-planned"],
                required=True
            ),
            # Nowe kolumny jako przyciski linków
            "spis casów": st.column_config.LinkColumn("📋 Spis casów", display_text="Otwórz"),
            "zdjęcie po załadunku": st.column_config.LinkColumn("📸 Załadunek", display_text="Otwórz"),
            "SLOT": st.column_config.LinkColumn("⏰ SLOT (Link)", display_text="Otwórz"),
            "dodatkowe zdjęcie": st.column_config.LinkColumn("➕ Dodatkowe", display_text="Otwórz"),
            
            # Formaty dla pozostałych danych
            "NOTATKA": st.column_config.TextColumn("📝 NOTATKA", width="large"),
            "Data": st.column_config.TextColumn("📅 Data", width="small"),
            "Nr Slotu": st.column_config.TextColumn("Nr Slotu (Tekst)", width="small"),
            "Godzina": st.column_config.TextColumn("Godzina", width="small"),
        }
    )

    # --- 4. ZAPIS DANYCH ---
    st.markdown("---")
    if st.button("💾 ZAPISZ WSZYSTKIE ZMIANY", type="primary", use_container_width=True):
        with st.spinner("Synchronizacja z Arkuszem Google..."):
            try:
                if search:
                    df.update(updated_df)
                    conn.update(spreadsheet=URL, data=df)
                else:
                    conn.update(spreadsheet=URL, data=updated_df)
                
                st.cache_data.clear()
                st.success("Dane zapisane pomyślnie!")
                st.rerun()
            except Exception as e:
                st.error(f"Błąd zapisu: {e}")

except Exception as e:
    st.error(f"Błąd krytyczny: {e}")
