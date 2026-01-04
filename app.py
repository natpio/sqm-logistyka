import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# Ustawienia strony - szeroki układ, żeby tabela była czytelna
st.set_page_config(page_title="SQM Logistics: POZ-BCN", layout="wide")

# Link do Twojego arkusza
URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"

# Połączenie z Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Funkcja pobierająca dane
def load_data():
    # Pobieramy dane (ttl=0 sprawia, że dane nie są cache'owane i odświeżają się od razu)
    return conn.read(spreadsheet=URL, ttl=0)

try:
    df = load_data()

    st.title("🚚 Panel Logistyki: Poznań ↔ Barcelona")
    st.info("Logistyk w Barcelonie: Zmień status auta po rozładunku. Dane zostaną zapisane w arkuszu głównym.")

    # --- SEKCJA PODGLĄDU TABELI ---
    st.subheader("Aktualna lista transportów")
    st.dataframe(df, use_container_width=True)

    st.divider()

    # --- SEKCJA AKTUALIZACJI DLA LOGISTYKA ---
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🔄 Zmień status")
        # Wybór auta na podstawie pierwszej kolumny (zakładam, że to ID auta lub Kierowca)
        truck_to_update = st.selectbox("Wybierz auto z listy:", df.iloc[:, 0].tolist())
        
        # Wybór nowego statusu
        new_status = st.radio(
            "Nowy status:",
            ["W trasie", "Pod rampą", "ROZŁADOWANY", "ZAŁADOWANY - POWRÓT"],
            index=0
        )

        if st.button("Zapisz zmiany w arkuszu"):
            # Znajdujemy wiersz i kolumnę "Status" (zakładam, że kolumna nazywa się Status)
            # Jeśli kolumna nazywa się inaczej, aplikacja podpowie błąd
            if "Status" in df.columns:
                df.loc[df.iloc[:, 0] == truck_to_update, "Status"] = new_status
                conn.update(spreadsheet=URL, data=df)
                st.success(f"Zaktualizowano status dla {truck_to_update}!")
                st.rerun()
            else:
                st.error("W Twoim arkuszu nie widzę kolumny o nazwie 'Status'. Zmień nagłówek w Excelu na 'Status'.")

    with col2:
        st.subheader("📸 Dokumentacja")
        # Funkcja aparatu dla logistyka w Barcelonie
        img_file = st.camera_input("Zrób zdjęcie po załadunku")
        if img_file:
            st.warning("Zdjęcie zostało zarejestrowane. Funkcja bezpośredniego zapisu zdjęcia do komórki Excela wymaga dodatkowej konfiguracji Google Drive. Na ten moment zachowaj zdjęcie w telefonie.")

except Exception as e:
    st.error("Błąd połączenia lub struktury arkusza.")
    st.write("Upewnij się, że Twój arkusz ma nagłówki w pierwszym wierszu (np. ID, Kierowca, Status).")
    st.write("Szczegóły błędu:", e)

# Stopka dla łatwiejszej nawigacji
st.divider()
st.caption("Aplikacja logistyczna dla SQM Multimedia Solutions. Kontakt z administratorem w Poznaniu.")
