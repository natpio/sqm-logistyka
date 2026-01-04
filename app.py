import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="SQM LOGISTICS", layout="wide")

# Link do arkusza
URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"

conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    return conn.read(spreadsheet=URL, ttl=0).dropna(how="all")

try:
    # Pobieranie danych
    df = load_data()
    
    st.title("🚚 Zarządzanie Transportem SQM")

    # --- PANEL BOCZNY (FILTROWANIE) ---
    st.sidebar.header("🔍 Filtry")
    
    # 1. Wyszukiwarka ogólna (po dowolnym tekście)
    search_query = st.sidebar.text_input("Szukaj (np. nr projektu, auto, hala):")

    # 2. Filtry dynamiczne (wyciągają unikalne wartości z kolumn)
    # Zakładam nazwy kolumn na podstawie Twojego pliku: 'Data', 'Hala', 'STATUS'
    all_dates = ["Wszystkie"] + sorted(df['Data'].astype(str).unique().tolist())
    selected_date = st.sidebar.selectbox("Filtruj po dacie:", all_dates)

    all_hallas = ["Wszystkie"] + sorted(df['Hala'].astype(str).unique().tolist())
    selected_hala = st.sidebar.selectbox("Filtruj po hali:", all_hallas)

    all_statuses = ["Wszystkie"] + sorted(df['STATUS'].astype(str).unique().tolist())
    selected_status = st.sidebar.selectbox("Filtruj po statusie:", all_statuses)

    # --- LOGIKA FILTROWANIA ---
    filtered_df = df.copy()

    if search_query:
        # Przeszukuje cały arkusz pod kątem wpisanej frazy
        filtered_df = filtered_df[filtered_df.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)]

    if selected_date != "Wszystkie":
        filtered_df = filtered_df[filtered_df['Data'].astype(str) == selected_date]

    if selected_hala != "Wszystkie":
        filtered_df = filtered_df[filtered_df['Hala'].astype(str) == selected_hala]

    if selected_status != "Wszystkie":
        filtered_df = filtered_df[filtered_df['STATUS'].astype(str) == selected_status]

    # --- WIDOK GŁÓWNY ---
    st.subheader(f"Znaleziono pozycji: {len(filtered_df)}")
    
    # Wyświetlenie tabeli (z możliwością sortowania przez kliknięcie w nagłówek)
    st.dataframe(filtered_df, use_container_width=True)

    st.divider()

    # --- EDYCJA STATUSU DLA PRZELTROWANYCH DANYCH ---
    if len(filtered_df) > 0:
        st.subheader("📝 Szybka zmiana statusu")
        # Wybieramy ID z przefiltrowanej listy
        selected_id = st.selectbox("Wybierz ID wiersza do aktualizacji:", filtered_df['ID'].tolist())
        
        new_status = st.selectbox("Ustaw nowy status:", ["status-planned", "w trasie", "pod rampą", "ROZŁADOWANY", "ZAŁADOWANY-POWRÓT"])
        
        if st.button("Zapisz zmianę"):
            # Aktualizacja w pełnym DataFrame
            df.loc[df['ID'] == selected_id, 'STATUS'] = new_status
            conn.update(spreadsheet=URL, data=df)
            st.success(f"Zaktualizowano wiersz {selected_id}")
            st.rerun()
    else:
        st.warning("Brak danych spełniających kryteria filtrów.")

except Exception as e:
    st.error(f"Problem z danymi: {e}")
    st.info("Upewnij się, że nagłówki w Google Sheets to: ID, Data, Hala, STATUS itd.")
