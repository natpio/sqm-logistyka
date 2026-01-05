import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(page_title="SQM LOGISTICS PRO", layout="wide", initial_sidebar_state="collapsed")

# Dane Twojego arkusza
URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"

# Inicjalizacja połączenia tylko z arkuszem (usuwamy Google Drive API)
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. LOGIKA APLIKACJI ---
try:
    # Pobranie danych (cache 15s zapobiega blokadom API 429)
    df = conn.read(spreadsheet=URL, ttl=15).dropna(how="all")

    # NAPRAWA TYPÓW DANYCH (Wymuszamy tekst, by edytor nie wywalał błędu FLOAT)
    for col in ['NOTATKA', 'Foto1']:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].astype(str).replace('nan', '')

    st.title("🚀 SQM Logistics Operations")
    st.info("💡 INSTRUKCJA: Wklej link do zdjęcia/CMR bezpośrednio w kolumnę 'Dokumentacja', a następnie kliknij ZAPISZ.")
    
    # Przyciski kontrolne
    col_ref, col_space = st.columns([1, 4])
    with col_ref:
        if st.button("🔄 ODSWIEŻ TABELĘ"):
            st.cache_data.clear()
            st.rerun()

    # Wyszukiwarka
    search = st.text_input("🔍 Wyszukaj (Auto, Projekt, Kierowca...):")
    
    display_df = df.copy()
    if search:
        display_df = display_df[display_df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]

    # --- 3. EDYTOR DANYCH (Główny i jedyny panel) ---
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
            "Foto1": st.column_config.LinkColumn(
                "🔗 Dokumentacja (Wklej link)", 
                display_text="Otwórz plik",
                help="Wklej tu link do pliku z Dysku Google (pamiętaj o uprawnieniach 'Dla każdego z linkiem')"
            ),
            "NOTATKA": st.column_config.TextColumn(
                "📝 notatka dodatkowa", 
                width="large"
            ),
            "Hala": st.column_config.TextColumn("Hala", width="small")
        }
    )

    # Przycisk zapisu
    if st.button("💾 ZAPISZ WSZYSTKIE ZMIANY", type="primary", use_container_width=True):
        with st.spinner("Zapisywanie w Arkuszu Google..."):
            try:
                if search:
                    df.update(updated_df)
                    conn.update(spreadsheet=URL, data=df)
                else:
                    conn.update(spreadsheet=URL, data=updated_df)
                
                st.cache_data.clear()
                st.success("Zapisano pomyślnie!")
                st.rerun()
            except Exception as e:
                st.error(f"Błąd zapisu: {e}")

except Exception as e:
    if "429" in str(e):
        st.error("Przekroczono limit zapytań Google. Odczekaj 60 sekund.")
    else:
        st.error(f"Wystąpił błąd: {e}")
