import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
import io

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="SQM LOGISTICS PRO", layout="wide", initial_sidebar_state="collapsed")

# Dane stałe - upewnij się, że FOLDER_ID jest poprawny dla Twojego dysku
URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
FOLDER_ID = "1HSyhgaJMcpPtFfcHRqdznDfJKT0tBqno"

# Połączenie z Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNKCJE GOOGLE DRIVE ---
def get_drive_service():
    # Pobiera poświadczenia z Twoich Secrets (plik JSON, który wkleiłeś)
    info = st.secrets["connections"]["gsheets"]
    creds = service_account.Credentials.from_service_account_info(info)
    return build('drive', 'v3', credentials=creds)

def upload_to_drive(file, folder_id):
    service = get_drive_service()
    file_metadata = {'name': file.name, 'parents': [folder_id]}
    
    # Ustawienie resumable=False pomaga omijać błędy limitu miejsca (Quota) na dyskach prywatnych
    media = MediaIoBaseUpload(io.BytesIO(file.read()), mimetype=file.type, resumable=False)
    
    uploaded_file = service.files().create(
        body=file_metadata, 
        media_body=media, 
        fields='id, webViewLink',
        supportsAllDrives=True 
    ).execute()
    
    # Nadanie uprawnień do wyświetlania pliku każdemu, kto ma link
    service.permissions().create(
        fileId=uploaded_file.get('id'), 
        body={'type': 'anyone', 'role': 'viewer'},
        supportsAllDrives=True
    ).execute()
    
    return uploaded_file.get('webViewLink')

# --- GŁÓWNA LOGIKA APLIKACJI ---
try:
    # Pobranie danych z arkusza (ttl=0 wymusza brak pamięci podręcznej)
    df = conn.read(spreadsheet=URL, ttl=0).dropna(how="all")

    st.title("🚀 SQM Logistics Operations")
    st.info("💡 Kliknij dwukrotnie w komórkę, aby edytować. Użyj '+' na dole tabeli, aby dodać nowy wiersz.")

    # --- WYSZUKIWARKA I FILTRY ---
    search = st.text_input("🔍 Wyszukaj transport (Auto, Projekt, Hala...):", placeholder="Wpisz frazę...")
    
    display_df = df.copy()
    if search:
        # Filtrowanie po wszystkich kolumnach
        display_df = display_df[display_df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]

    # --- EDYTOR DANYCH ---
    # Tutaj definiujemy, jak zachowują się poszczególne kolumny
    updated_df = st.data_editor(
        display_df,
        use_container_width=True,
        num_rows="dynamic",  # Pozwala na dodawanie/usuwanie wierszy bezpośrednio w aplikacji
        hide_index=False,
        column_config={
            "STATUS": st.column_config.SelectboxColumn(
                "STATUS",
                options=["status-planned", "w trasie", "pod rampą", "ROZŁADOWANY", "ZAŁADOWANY-POWRÓT"],
                help="Wybierz aktualny stan transportu"
            ),
            "Foto1": st.column_config.LinkColumn("🔗 Dokumentacja", disabled=True),
            
            # NAPRAWA: Wymuszenie typu tekstowego dla kolumny NOTATKA, aby przyjmowała litery
            "NOTATKA": st.column_config.TextColumn(
                "📝 Uwagi logistyczne", 
                placeholder="Wpisz uwagi...",
                width="large"
            ),
            
            "Hala": st.column_config.TextColumn("Hala", width="small")
        }
    )

    # --- PRZYCISK ZAPISU ---
    if st.button("💾 ZAPISZ WSZYSTKIE ZMIANY", type="primary", use_container_width=True):
        with st.spinner("Zapisywanie danych w Google Sheets..."):
            try:
                if search:
                    # Jeśli dane były filtrowane, aktualizujemy tylko zmienione wiersze w oryginalnym zbiorze
                    df.update(updated_df)
                    conn.update(spreadsheet=URL, data=df)
                else:
                    # Jeśli nie było filtrów, nadpisujemy cały arkusz (ważne przy dodawaniu nowych wierszy)
                    conn.update(spreadsheet=URL, data=updated_df)
                
                st.success("Wszystkie dane zostały pomyślnie zapisane!")
                st.rerun()
            except Exception as e:
                st.error(f"Błąd podczas zapisu: {e}")

    # --- SEKCJA PRZESYŁANIA PLIKÓW ---
    st.divider()
    st.subheader("📁 Dodaj załącznik (CMR / Foto / PDF)")
    
    if not display_df.empty:
        # Wybór transportu ograniczone do tego, co aktualnie widzimy w tabeli
        selected_index = st.selectbox(
            "Wybierz transport do przypisania pliku:",
            options=display_df.index.tolist(),
            format_func=lambda x: f"Wiersz {x} | {df.loc[x, 'Auto'] if x in df.index else 'NOWY'} | {df.loc[x, 'Nazwa Projektu'] if x in df.index else ''}"
        )
        
        up_col, btn_col = st.columns([3, 1])
        with up_col:
            uploaded_file = st.file_uploader("Wgraj dokumentację", type=['pdf', 'jpg', 'png', 'jpeg'])
        
        with btn_col:
            st.write("##") # Odstęp dla wyrównania przycisku
            if st.button("📤 WYŚLIJ NA DRIVE", use_container_width=True):
                if uploaded_file:
                    with st.spinner("Przesyłanie pliku..."):
                        try:
                            # Przesyłanie na Google Drive
                            file_url = upload_to_drive(uploaded_file, FOLDER_ID)
                            
                            # Aktualizacja linku w DataFrame i zapis w Google Sheets
                            df.at[selected_index, 'Foto1'] = file_url
                            conn.update(spreadsheet=URL, data=df)
                            
                            st.success("Plik przesłany i przypisany!")
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Błąd przesyłania: {ex}")
                else:
                    st.warning("Najpierw wybierz plik z dysku.")
    else:
        st.info("Brak danych do wyświetlenia (zmień filtry, aby dodać załącznik).")

except Exception as e:
    st.error(f"Wystąpił błąd krytyczny aplikacji: {e}")
