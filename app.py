import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# ==========================================
# 1. KONFIGURACJA STRONY I POŁĄCZENIA
# ==========================================
st.set_page_config(
    page_title="SQM LOGISTICS PRO", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# Adres Twojego Arkusza Google
URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"

# Inicjalizacja połączenia ze Streamlit GSheets
conn = st.connection("gsheets", type=GSheetsConnection)

# ==========================================
# 2. POBIERANIE I NAPRAWA DANYCH
# ==========================================
try:
    # Pobranie danych z cache 15s (ochrona przed błędem 429)
    df = conn.read(spreadsheet=URL, ttl=15).dropna(how="all")

    # Lista Twoich specyficznych kolumn na załączniki
    foto_cols = ['spis casów', 'zdjęcie po załadunku', 'SLOT', 'dodatkowe zdjęcie']
    
    # Wszystkie kolumny, które muszą być tekstem, żeby edytor działał poprawnie
    all_text_cols = ['NOTATKA', 'Hala', 'STATUS', 'Auto', 'Kierowca', 'Projekt'] + foto_cols
    
    # Naprawa typów: wymuszamy tekst w każdej kolumnie (rozwiązuje błąd FLOAT/DataKind)
    for col in all_text_cols:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].astype(str).replace('nan', '')

    # ==========================================
    # 3. INTERFEJS UŻYTKOWNIKA
    # ==========================================
    st.title("🚀 SQM Logistics Operations")
    st.info("💡 INSTRUKCJA: Wklej link do pliku (Dysk Google/Inne) w odpowiednią komórkę i kliknij przycisk ZAPISZ na dole strony.")
    
    # Przycisk wymuszający odświeżenie danych z Arkusza
    if st.button("🔄 ODSWIEŻ TABELĘ"):
        st.cache_data.clear()
        st.rerun()

    # Wyszukiwarka transportów
    search = st.text_input("🔍 Wyszukaj transport (wpisz nr rejestracyjny, projekt lub halę):")
    
    display_df = df.copy()
    if search:
        # Filtrowanie wierszy zawierających wpisaną frazę
        display_df = display_df[display_df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]

    # ==========================================
    # 4. EDYTOR DANYCH (GŁÓWNA TABELA)
    # ==========================================
    updated_df = st.data_editor(
        display_df,
        use_container_width=True,
        num_rows="dynamic",
        hide_index=False,
        column_config={
            "STATUS": st.column_config.SelectboxColumn(
                "STATUS",
                options=[
                    "W TRASIE", 
                    "POD RAMPĄ", 
                    "ROZŁADOWANY", 
                    "EMPTIES - ZAŁADUNEK", 
                    "ZAŁADOWANY NA POWRÓT", 
                    "status-planned"
                ],
                required=True
            ),
            # Konfiguracja Twoich linków jako przyciski "Otwórz"
            "spis casów": st.column_config.LinkColumn("📋 Spis casów", display_text="Otwórz"),
            "zdjęcie po załadunku": st.column_config.LinkColumn("📸 Załadunek", display_text="Otwórz"),
            "SLOT": st.column_config.LinkColumn("⏰ SLOT", display_text="Otwórz"),
            "dodatkowe zdjęcie": st.column_config.LinkColumn("➕ Dodatkowe", display_text="Otwórz"),
            
            # Szeroka notatka dla lepszej czytelności
            "NOTATKA": st.column_config.TextColumn("📝 notatka dodatkowa", width="large"),
            "Hala": st.column_config.TextColumn("Hala", width="small")
        }
    )

    # ==========================================
    # 5. ZAPISYWANIE ZMIAN
    # ==========================================
    st.markdown("---")
    if st.button("💾 ZAPISZ WSZYSTKIE ZMIANY W ARKUSZU", type="primary", use_container_width=True):
        with st.spinner("Trwa synchronizacja z Google Sheets..."):
            try:
                # Jeśli użyto wyszukiwarki, aktualizujemy tylko zmienione fragmenty oryginalnego df
                if search:
                    df.update(updated_df)
                    conn.update(spreadsheet=URL, data=df)
                else:
                    conn.update(spreadsheet=URL, data=updated_df)
                
                st.cache_data.clear()
                st.success("Dane zostały pomyślnie zapisane!")
                st.rerun()
            except Exception as e:
                st.error(f"Błąd zapisu danych: {e}")

except Exception as e:
    # Obsługa błędu limitów API Google
    if "429" in str(e):
        st.error("Przekroczono limity zapytań Google (Quota). Poczekaj 60 sekund.")
    else:
        st.error(f"Błąd krytyczny aplikacji: {e}")
