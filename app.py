import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="SQM LOGISTICS", layout="wide")

# Twój link do arkusza
URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"

# Połączenie
conn = st.connection("gsheets", type=GSheetsConnection)

# Funkcja odczytu danych
def load_data():
    # Pobieramy dane bez zapamiętywania (cache), żeby zawsze były świeże
    return conn.read(spreadsheet=URL, ttl=0)

try:
    df = load_data()
    
    st.title("🚚 SQM Logistics: Poznań - Barcelona")

    # 1. PODGLĄD CAŁEJ TABELI (Sprawdzenie czy dane płyną)
    st.subheader("Podgląd arkusza (wszystkie dane)")
    st.dataframe(df)

    st.divider()

    # 2. PROSTA EDYCJA STATUSU
    st.subheader("Aktualizacja statusu")
    
    # Wybieramy auto z pierwszej kolumny
    lista_aut = df.iloc[:, 0].tolist()
    wybrane_auto = st.selectbox("Wybierz auto/zlecenie:", lista_aut)
    
    nowy_status = st.radio("Zmień status na:", ["W trasie", "Czeka na rozładunek", "ROZŁADOWANY", "ZAŁADOWANY - POWRÓT"])

    if st.button("Zapisz w Google Sheets"):
        # Znajdujemy wiersz dla wybranego auta i zmieniamy mu status w kolumnie 'Status'
        df.loc[df.iloc[:, 0] == wybrane_auto, 'Status'] = nowy_status
        
        # Wysyłamy całą zaktualizowaną tabelę z powrotem do Google
        conn.update(spreadsheet=URL, data=df)
        st.success(f"Zmieniono status dla {wybrane_auto} na: {nowy_status}")
        # Odświeżamy aplikację, żeby pokazała nowe dane
        st.rerun()

except Exception as e:
    st.error("Błąd zaczytywania danych.")
    st.write("Sprawdź czy:")
    st.write("1. Arkusz ma nagłówki w 1. wierszu.")
    st.write("2. Jedna z kolumn nazywa się dokładnie 'Status'.")
    st.write("3. Link do arkusza jest poprawny.")
    st.exception(e)
