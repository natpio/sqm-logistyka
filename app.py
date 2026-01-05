import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
import io

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(page_title="SQM LOGISTICS PRO", layout="wide", initial_sidebar_state="collapsed")

# Dane stałe Twojej firmy
URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
FOLDER_ID = "1HSyhgaJMcpPtFfcHRqdznDfJKT0tBqno"

# Inicjalizacja połączenia
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. FUNKCJE GOOGLE DRIVE ---
def get_drive_service():
    """Tworzy autoryzowane połączenie z Google Drive."""
    info = st.secrets["connections"]["gsheets"]
    creds = service_account.Credentials.from_service_account_info(info)
    return build('drive', 'v3', credentials=creds)

def upload_to_drive(file, folder_id):
    """Wgrywa plik na Drive i nadaje mu uprawnienia publiczne do odczytu."""
    service = get_drive_service()
    file_metadata = {'name': file.name, 'parents': [folder_id]}
    media = MediaIoBaseUpload(io.BytesIO(file.read()), mimetype=file.type, resumable=False)
    
    # Przesyłanie
    uploaded_file = service.files().create(
        body=file_metadata, 
        media_body=media, 
        fields='id, webViewLink',
        supportsAllDrives=True 
    ).execute()
    
    # Nadanie uprawnień "każdy z linkiem może zobaczyć" (dla logistyka na hali)
    service.permissions().create(
        fileId=uploaded_file.get('id'), 
        body={'type': 'anyone', 'role': 'viewer'},
        supportsAllDrives=True
    ).execute()
    
    return uploaded_file.get('webViewLink')

# --- 3. GŁÓWNA LOGIKA APLIKACJI ---
try:
    # Pobranie danych (cache 15 sekund chroni przed błędem 429 Quota Exceeded)
    df = conn.read(spreadsheet=URL, ttl=15).dropna(how="all")

    # NAPRAWA TYPU DANYCH: Wymuszamy tekst w notatkach, aby uniknąć błędów edycji
    if 'NOTATKA' not in df.columns:
        df['NOTATKA'] = ""
    df['NOTATKA'] = df['NOTATKA'].astype(str).replace('nan', '')

    st.title("🚀 SQM Logistics Operations")
    
    # Przycisk wymuszonego odświeżenia danych
    if st.button("🔄 ODSWIEŻ DANE (WYMUŚ)"):
        st.cache_data.clear()
        st.rerun()

    # Wyszukiwarka transportów
    search = st.text_input("🔍 Wyszukaj (Auto, Projekt, Hala...):", placeholder="Szukaj...")
    
    display_df = df.copy()
    if search:
        # Filtrowanie po wszystkich kolumnach
        display_df = display_df[display_df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]

    # --- 4. EDYTOR DANYCH (Główny Panel Zarządzania) ---
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
                "🔗 Dokumentacja", 
                display_text="Otwórz plik",  # Czytelny tekst zamiast długiego linku
                help="Kliknij, aby zobaczyć CMR lub zdjęcie"
            ),
            "NOTATKA": st.column_config.TextColumn(
                "📝 notatka dodatkowa", 
                width="large",  # Bardzo szeroka kolumna dla długich tekstów
                help="Kliknij dwukrotnie, aby rozwinąć i edytować"
            ),
            "Hala": st.column_config.TextColumn("Hala", width="small")
        }
    )

    # Przyciski zapisu zmian
    if st.button("💾 ZAPISZ WSZYSTKIE ZMIANY", type="primary", use_container_width=True):
        with st.spinner("Synchronizacja z Google Sheets..."):
            try:
                # Jeśli szukaliśmy czegoś, aktualizujemy tylko te wiersze, w przeciwnym razie całość
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

    # --- 5. SEKCJA ZAŁĄCZNIKÓW (Dla dokumentów wgranych z zewnątrz) ---
    st.divider()
    st.subheader("📁 Dodaj dokumentację do transportu")
    
    if not display_df.empty:
        # Wybór wiersza na podstawie danych z tabeli
        selected_index = st.selectbox(
            "Wybierz transport, do którego przypisujesz plik:",
            options=display_df.index.tolist(),
            format_func=lambda x: f"Wiersz {x} | {df.loc[x, 'Auto'] if 'Auto' in df.columns else 'NOWY'}"
        )
        
        up_col, btn_col = st.columns([3, 1])
        with up_col:
            uploaded_file = st.file_uploader("Wybierz plik (PDF, JPG, PNG)", type=['pdf', 'jpg', 'png', 'jpeg'])
        
        with btn_col:
            st.write("##") # Margines dla wyrównania przycisku
            if st.button("📤 WYŚLIJ I PODLINKUJ", use_container_width=True):
                if uploaded_file:
                    with st.spinner("Przesyłanie na Google Drive..."):
                        try:
                            # 1. Wgrywamy plik
                            file_url = upload_to_drive(uploaded_file, FOLDER_ID)
                            # 2. Wpisujemy link do kolumny Foto1 w pamięci
                            df.at[selected_index, 'Foto1'] = file_url
                            # 3. Zapisujemy zaktualizowaną tabelę do arkusza
                            conn.update(spreadsheet=URL, data=df)
                            st.cache_data.clear()
                            st.success("Plik przypisany!")
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Błąd wysyłki: {ex}")
                else:
                    st.warning("Najpierw wskaż plik na swoim komputerze.")

except Exception as e:
    # Obsługa błędu limitów Google (Quota)
    if "429" in str(e):
        st.error("Przekroczono limit zapytań Google Sheets. Poczekaj 60 sekund bez odświeżania strony.")
    else:
        st.error(f"Wystąpił nieoczekiwany błąd: {e}")
