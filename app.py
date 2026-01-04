import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="SQM LOGISTICS", layout="wide")

# Twój link do arkusza
URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"

conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # Odczyt danych i usunięcie całkowicie pustych wierszy
    return conn.read(spreadsheet=URL, ttl=0).dropna(how="all")

try:
    df = load_data()
    
    st.title("🚚 SQM Logistics: Zarządzanie Transportem")

    # --- BOCZNY PANEL FILTROWANIA ---
    st.sidebar.header("🔍 Szukaj i Filtruj")
    
    # Globalna wyszukiwarka (szuka w całej tabeli)
    search = st.sidebar.text_input("Wyszukaj (Projekt, Auto, Kierowca):")

    # Filtry rozwijane
    hala_list = ["Wszystkie"] + sorted(df['Hala'].unique().tolist())
    selected_hala = st.sidebar.selectbox("Hala:", hala_list)

    status_list = ["Wszystkie"] + sorted(df['STATUS'].unique().tolist())
    selected_status = st.sidebar.selectbox("Status:", status_list)

    # Logika filtrów
    filtered_df = df.copy()
    if search:
        filtered_df = filtered_df[filtered_df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]
    if selected_hala != "Wszystkie":
        filtered_df = filtered_df[filtered_df['Hala'] == selected_hala]
    if selected_status != "Wszystkie":
        filtered_df = filtered_df[filtered_df['STATUS'] == selected_status]

    # --- WIDOK GŁÓWNY ---
    st.subheader(f"Znaleziono: {len(filtered_df)} pozycji")
    st.dataframe(filtered_df, use_container_width=True, hide_index=True)

    st.divider()

    # --- AKTUALIZACJA STATUSU ---
    if not filtered_df.empty:
        st.subheader("📝 Zmiana statusu")
        
        # Wybór wiersza na podstawie kombinacji Nazwy Projektu i Auta, żeby nie było pomyłek
        options = filtered_df.apply(lambda x: f"{x['Nazwa Projektu']} | {x['Auto']} ({x['Kierowca']})", axis=1).tolist()
        selection = st.selectbox("Wybierz transport do aktualizacji:", options)
        
        # Pobieramy index wybranego wiersza
        selected_index = filtered_df.index[options.index(selection)]
        
        new_status = st.selectbox("Ustaw nowy status:", 
                                 ["status-planned", "w trasie", "pod rampą", "ROZŁADOWANY", "ZAŁADOWANY-POWRÓT"])
        
        if st.button("Zapisz zmiany w systemie"):
            # Zmiana statusu w głównym DataFrame
            df.at[selected_index, 'STATUS'] = new_status
            conn.update(spreadsheet=URL, data=df)
            st.success(f"Zaktualizowano: {selection} na status {new_status}")
            st.rerun()
    else:
        st.info("Brak transportów spełniających wybrane kryteria.")

except Exception as e:
    st.error("Nie udało się poprawnie wczytać arkusza.")
    st.write("Sprawdź, czy nazwy kolumn w Google Sheets są identyczne jak w kodzie (Data, Nr Slotu, Godzina, Hala, Przewoźnik, Auto, Kierowca, Nr Proj., Nazwa Projektu, STATUS, Foto1)")
    st.exception(e)
