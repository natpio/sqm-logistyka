import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
import io

# --- KONFIGURACJA ---
st.set_page_config(page_title="SQM LOGISTICS PRO", layout="wide")

URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
FOLDER_ID = "1HSyhgaJMcpPtFfcHRqdznDfJKT0tBqno"

conn = st.connection("gsheets", type=GSheetsConnection)

def get_drive_service():
    info = st.secrets["connections"]["gsheets"]
    creds = service_account.Credentials.from_service_account_info(info)
    return build('drive', 'v3', credentials=creds)

def upload_to_drive(file, folder_id):
    service = get_drive_service()
    file_metadata = {'name': file.name, 'parents': [folder_id]}
    media = MediaIoBaseUpload(io.BytesIO(file.read()), mimetype=file.type, resumable=False)
    
    uploaded_file = service.files().create(
        body=file_metadata, 
        media_body=media, 
        fields='id, webViewLink',
        supportsAllDrives=True 
    ).execute()
    
    service.permissions().create(
        fileId=uploaded_file.get('id'), 
        body={'type': 'anyone', 'role': 'viewer'},
        supportsAllDrives=True
    ).execute()
    
    return uploaded_file.get('webViewLink')

# --- GŁÓWNA LOGIKA ---
try:
    # Pobieranie danych (wymuszone odświeżenie)
    df = conn.read(spreadsheet=URL, ttl=0).dropna(how="all")

    st.title("🚀 SQM Logistics Operations")
    st.subheader("Edytuj dane, dodawaj transporty i notatki")

    # Wyszukiwarka, żeby łatwiej znaleźć konkretny transport do dopisania notatki
    search = st.text_input("🔍 Szukaj transportu do edycji:", placeholder="Auto, Projekt, Hala...")
    
    display_df = df.copy()
    if search:
        display_df = display_df[display_df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]

    # --- EDYTOR DANYCH ---
    # Tutaj dzieje się magia edycji bezpośredniej
    updated_df = st.data_editor(
        display_df,
        use_container_width=True,
        num_rows="dynamic", # Pozwala dodawać nowe wiersze przyciskiem "+"
        hide_index=False,
        column_config={
            "STATUS": st.column_config.SelectboxColumn(
                "STATUS",
                options=["status-planned", "w trasie", "pod rampą", "ROZŁADOWANY", "ZAŁADOWANY-POWRÓT"],
            ),
            "Foto1": st.column_config.LinkColumn("🔗 Dokumentacja", disabled=True),
            # Jeśli dodasz kolumnę NOTATKA w Excelu, możesz ją tu skonfigurować:
            "NOTATKA": st.column_config.TextColumn("📝 Uwagi logistyczne", width="large", help="Wpisz ważne informacje o rozładunku"),
            "Hala": st.column_config.TextColumn("Hala", width="small")
        }
    )

    # ZAPIS ZMIAN
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("💾 ZAPISZ ZMIANY", type="primary", use_container_width=True):
            try:
                if search:
                    # Jeśli filtrowaliśmy, aktualizujemy tylko zmienione wiersze w oryginale
                    df.update(updated_df)
                    conn.update(spreadsheet=URL, data=df)
                else:
                    # Jeśli nie było filtrów, nadpisujemy całość (włącznie z nowymi wierszami)
                    conn.update(spreadsheet=URL, data=updated_df)
                st.success("Dane zapisane w Google Sheets!")
                st.rerun()
            except Exception as e:
                st.error(f"Błąd zapisu: {e}")

    # --- SEKCJA PLIKÓW ---
    st.divider()
    st.subheader("📁 Dodaj załącznik")
    if not display_df.empty:
        selected_index = st.selectbox(
            "Wybierz wiersz do przypisania dokumentu:",
            options=display_df.index.tolist(),
            format_func=lambda x: f"Wiersz {x} | {df.loc[x, 'Auto'] if x in df.index else 'NOWY'}"
        )
        
        uploaded_file = st.file_uploader("Wgraj plik", type=['pdf', 'jpg', 'png', 'jpeg'])
        
        if st.button("📤 WYŚLIJ I LINKUJ"):
            if uploaded_file:
                with st.spinner("Przesyłanie..."):
                    file_url = upload_to_drive(uploaded_file, FOLDER_ID)
                    df.at[selected_index, 'Foto1'] = file_url
                    conn.update(spreadsheet=URL, data=df)
                    st.success("Dokument dodany!")
                    st.rerun()

except Exception as e:
    st.error(f"Wystąpił błąd: {e}")
