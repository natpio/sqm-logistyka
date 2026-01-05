import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
import io

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="SQM LOGISTICS PRO", layout="wide", initial_sidebar_state="collapsed")

# Dane stałe pobrane z Twojej konfiguracji
URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
FOLDER_ID = "1HSyhgaJMcpPtFfcHRqdznDfJKT0tBqno"

conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNKCJE GOOGLE DRIVE (Z Twoim nowym kontem usługi) ---
def get_drive_service():
    # Wykorzystuje dane uwierzytelniające z wklejonych przez Ciebie Secrets
    info = st.secrets["connections"]["gsheets"]
    creds = service_account.Credentials.from_service_account_info(info)
    return build('drive', 'v3', credentials=creds)

def upload_to_drive(file, folder_id):
    service = get_drive_service()
    file_metadata = {'name': file.name, 'parents': [folder_id]}
    
    # resumable=False rozwiązuje problem Quota na kontach usługi
    media = MediaIoBaseUpload(io.BytesIO(file.read()), mimetype=file.type, resumable=False)
    
    uploaded_file = service.files().create(
        body=file_metadata, 
        media_body=media, 
        fields='id, webViewLink',
        supportsAllDrives=True 
    ).execute()
    
    # Publiczne uprawnienia do podglądu dokumentu
    service.permissions().create(
        fileId=uploaded_file.get('id'), 
        body={'type': 'anyone', 'role': 'viewer'},
        supportsAllDrives=True
    ).execute()
    
    return uploaded_file.get('webViewLink')

# --- FUNKCJA KOLOROWANIA WIERSZY (LOGIKA WIZUALNA) ---
def style_status(row):
    status = str(row['STATUS']).upper()
    colors = {
        "W TRASIE": "background-color: #2e7d32; color: white;",      # Zielony
        "POD RAMPĄ": "background-color: #ef6c00; color: white;",     # Pomarańczowy
        "ROZŁADOWANY": "background-color: #757575; color: white;",   # Szary
        "EMPTIES - ZAŁADUNEK": "background-color: #fdd835; color: black;", # Żółty
        "ZAŁADOWANY NA POWRÓT": "background-color: #ffffff; color: black;", # Biały
    }
    return [colors.get(status, "")] * len(row)

# --- GŁÓWNA LOGIKA APLIKACJI ---
try:
    # 1. Pobranie świeżych danych z Google Sheets
    df = conn.read(spreadsheet=URL, ttl=0).dropna(how="all")

    # 2. Naprawa typów danych dla kolumny NOTATKA (rozwiązuje błąd FLOAT/Tekst)
    if 'NOTATKA' not in df.columns:
        df['NOTATKA'] = ""
    df['NOTATKA'] = df['NOTATKA'].astype(str).replace('nan', '')

    st.title("🚀 SQM Logistics Operations")

    # --- SEKCJA 1: TABLICA MONITORINGU (PODGLĄD KOLOROWY) ---
    st.subheader("📊 Tablica Statusów (Podgląd)")
    st.dataframe(
        df.style.apply(style_status, axis=1), 
        use_container_width=True, 
        height=350,
        column_config={"Foto1": st.column_config.LinkColumn("🔗 Dokumentacja")}
    )

    st.divider()

    # --- SEKCJA 2: PANEL EDYCJI I NOWYCH TRANSPORTÓW ---
    st.subheader("📝 Edycja i Planowanie")
    search = st.text_input("🔍 Szybkie wyszukiwanie (Auto, Projekt, Kierowca...):")
    
    display_df = df.copy()
    if search:
        display_df = display_df[display_df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]

    # Edytor pozwalający na wpisywanie liter i dodawanie wierszy
    updated_df = st.data_editor(
        display_df,
        use_container_width=True,
        num_rows="dynamic",
        hide_index=False,
        column_config={
            "STATUS": st.column_config.SelectboxColumn(
                "STATUS",
                options=["W TRASIE", "POD RAMPĄ", "ROZŁADOWANY", "EMPTIES - ZAŁADUNEK", "ZAŁADOWANY NA POWRÓT", "status-planned"],
                required=True
            ),
            "Foto1": st.column_config.LinkColumn("🔗 Dokumentacja", disabled=True),
            "NOTATKA": st.column_config.TextColumn("📝 notatka dodatkowa", width="large"),
            "Hala": st.column_config.TextColumn("Hala", width="small")
        }
    )

    # Przycisk zapisu zmian do Arkusza Google
    if st.button("💾 ZAPISZ I AKTUALIZUJ STATUSY", type="primary", use_container_width=True):
        with st.spinner("Synchronizacja z Google Sheets..."):
            try:
                if search:
                    df.update(updated_df)
                    conn.update(spreadsheet=URL, data=df)
                else:
                    conn.update(spreadsheet=URL, data=updated_df)
                st.success("Dane zostały pomyślnie zapisane!")
                st.rerun()
            except Exception as e:
                st.error(f"Błąd zapisu: {e}")

    # --- SEKCJA 3: ZAŁĄCZNIKI (DODAWANIE CMR / ZDJĘĆ) ---
    st.divider()
    st.subheader("📁 Dodaj dokumentację (CMR / Foto)")
    if not display_df.empty:
        selected_index = st.selectbox(
            "Wybierz transport do aktualizacji:", 
            options=display_df.index.tolist(),
            format_func=lambda x: f"Wiersz {x} | {df.loc[x, 'Auto'] if x in df.index else 'NOWY'}"
        )
        
        up_col, btn_col = st.columns([3, 1])
        with up_col:
            uploaded_file = st.file_uploader("Wgraj plik (PDF, JPG, PNG)", type=['pdf', 'jpg', 'png', 'jpeg'])
        
        with btn_col:
            st.write("##") # Wyrównanie do przycisku
            if st.button("📤 WYŚLIJ PLIK", use_container_width=True):
                if uploaded_file:
                    with st.spinner("Wysyłanie na Google Drive..."):
                        try:
                            file_url = upload_to_drive(uploaded_file, FOLDER_ID)
                            df.at[selected_index, 'Foto1'] = file_url
                            conn.update(spreadsheet=URL, data=df)
                            st.success("Plik wgrany i podlinkowany!")
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Błąd: {ex}")
                else:
                    st.warning("Najpierw wybierz plik.")

except Exception as e:
    st.error(f"Krytyczny błąd aplikacji: {e}")
