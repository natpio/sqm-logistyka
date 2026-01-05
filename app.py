import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
import io

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="SQM LOGISTICS PRO", layout="wide", initial_sidebar_state="collapsed")

# Dane stałe
URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
FOLDER_ID = "1HSyhgaJMcpPtFfcHRqdznDfJKT0tBqno"

# Stylizacja wizualna
st.markdown("""
    <style>
    .stMetric { background-color: #161b22; border: 1px solid #30363d; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNKCJE GOOGLE DRIVE (Z Twoim nowym kontem usługi) ---
def get_drive_service():
    info = st.secrets["connections"]["gsheets"]
    creds = service_account.Credentials.from_service_account_info(info)
    return build('drive', 'v3', credentials=creds)

def upload_to_drive(file, folder_id):
    service = get_drive_service()
    file_metadata = {'name': file.name, 'parents': [folder_id]}
    
    # resumable=False jest kluczowe, aby ominąć błąd "storageQuotaExceeded" na Twoim dysku prywatnym
    media = MediaIoBaseUpload(io.BytesIO(file.read()), mimetype=file.type, resumable=False)
    
    uploaded_file = service.files().create(
        body=file_metadata, 
        media_body=media, 
        fields='id, webViewLink',
        supportsAllDrives=True 
    ).execute()
    
    # Uprawnienia dla każdego kto ma link (do wglądu w arkuszu)
    service.permissions().create(
        fileId=uploaded_file.get('id'), 
        body={'type': 'anyone', 'role': 'viewer'},
        supportsAllDrives=True
    ).execute()
    
    return uploaded_file.get('webViewLink')

# --- LOGIKA APLIKACJI ---
try:
    # Pobranie danych
    df = conn.read(spreadsheet=URL, ttl=0).dropna(how="all")

    # NAGŁÓWEK I KPI
    st.title("🚀 SQM Logistics Operations")
    
    total = len(df)
    in_transit = len(df[df['STATUS'] == 'w trasie'])
    unloaded = len(df[df['STATUS'] == 'ROZŁADOWANY'])
    
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Wszystkie transporty", total)
    kpi2.metric("W trasie", in_transit)
    kpi3.metric("Rozładowane", unloaded)
    kpi4.metric("Pod rampą", len(df[df['STATUS'] == 'pod rampą']))

    st.divider()

    # --- FILTRY I SORTOWANIE ---
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        search = st.text_input("🔍 Wyszukaj (Auto, Projekt, Kierowca...)", placeholder="Wpisz frazę...")
    with c2:
        # Dynamiczne pobieranie hal z arkusza
        hala_options = sorted(df['Hala'].unique().tolist()) if 'Hala' in df.columns else []
        hala_filter = st.multiselect("Filtruj wg Hali", options=hala_options)
    with c3:
        # Dynamiczne pobieranie statusów
        status_options = sorted(df['STATUS'].unique().tolist()) if 'STATUS' in df.columns else []
        status_filter = st.multiselect("Filtruj wg Statusu", options=status_options)

    # Zastosowanie filtrów do danych
    filtered_df = df.copy()
    
    if search:
        filtered_df = filtered_df[filtered_df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]
    if hala_filter:
        filtered_df = filtered_df[filtered_df['Hala'].isin(hala_filter)]
    if status_filter:
        filtered_df = filtered_df[filtered_df['STATUS'].isin(status_filter)]

    # --- REJESTR OPERACYJNY (EDYCJA) ---
    st.subheader("📋 Rejestr Operacyjny")
    updated_df = st.data_editor(
        filtered_df,
        use_container_width=True,
        hide_index=False,
        disabled=[col for col in df.columns if col != "STATUS"], # Tylko status można edytować
        column_config={
            "STATUS": st.column_config.SelectboxColumn(
                "STATUS",
                options=["status-planned", "w trasie", "pod rampą", "ROZŁADOWANY", "ZAŁADOWANY-POWRÓT"],
                required=True,
            ),
            "Foto1": st.column_config.LinkColumn("🔗 Dokumentacja")
        },
        key="main_editor"
    )

    # Przycisk zapisu zmian w tabeli
    if not updated_df.equals(filtered_df):
        if st.button("💾 ZAPISZ ZMIANY STATUSÓW", type="primary", use_container_width=True):
            # Aktualizujemy główny DataFrame zmianami z pofiltrowanego widoku
            df.update(updated_df)
            conn.update(spreadsheet=URL, data=df)
            st.success("Dane zostały zaktualizowane!")
            st.rerun()

    # --- SEKCJA PLIKÓW ---
    st.divider()
    st.subheader("📁 Dodaj załącznik (CMR / Zdjęcie / PDF)")
    
    if not filtered_df.empty:
        # Wybór transportu z listy pofiltrowanej
        transport_options = filtered_df.index.tolist()
        selected_index = st.selectbox(
            "Wybierz transport z listy do aktualizacji:",
            options=transport_options,
            format_func=lambda x: f"Wiersz {x} | {df.loc[x, 'Auto']} | {df.loc[x, 'Nazwa Projektu']} | {df.loc[x, 'STATUS']}"
        )
        
        up_col, btn_col = st.columns([3, 1])
        with up_col:
            uploaded_file = st.file_uploader("Wybierz plik dokumentacji", type=['pdf', 'jpg', 'png', 'jpeg'])
        
        with btn_col:
            st.write("##")
            if st.button("📤 WYŚLIJ DOKUMENT", use_container_width=True):
                if uploaded_file:
                    with st.spinner(f"Wysyłanie pliku dla wiersza {selected_index}..."):
                        try:
                            # Przesyłanie na Drive
                            file_url = upload_to_drive(uploaded_file, FOLDER_ID)
                            
                            # Zapis linku do arkusza w odpowiednim wierszu
                            df.at[selected_index, 'Foto1'] = file_url
                            conn.update(spreadsheet=URL, data=df)
                            
                            st.success("Plik został przypisany pomyślnie!")
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Krytyczny błąd: {ex}")
                else:
                    st.warning("Najpierw wskaż plik na dysku!")
    else:
        st.info("Brak transportów spełniających kryteria filtrów.")

except Exception as e:
    st.error(f"Błąd aplikacji: {e}")
