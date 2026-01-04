import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="SQM Logistics", layout="wide")

URL = "https://docs.google.com/spreadsheets/d/1_h9YkM5f8Wm-Y0HWKN-_dZ1qjvTmdwMB_2TZTirlC9k/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    return conn.read(spreadsheet=URL, ttl=0).dropna(how="all")

try:
    df = get_data()
    
    st.title("🚛 System Logistyczny SQM: POZ ↔ BCN")
    
    # Podział na dwa panele (Poznań i Barcelona) dla przejrzystości
    tab1, tab2 = st.tabs(["🇵🇱 PANEL POZNAŃ (Załadunek)", "🇪🇸 PANEL BARCELONA (Rozładunek/Powroty)"])

    with tab1:
        st.header("Planowanie i Wysyłka")
        # Wybór zamówienia do edycji
        order_id = st.selectbox("Wybierz nr zamówienia/auta do opisania:", df.iloc[:, 0].tolist())
        
        col_a, col_b = st.columns(2)
        with col_a:
            eta = st.text_input("Planowany przyjazd (ETA):", placeholder="np. Poniedziałek 14:00")
            desc = st.text_area("Co jest na aucie? (Uwagi dla Barcelony):")
        with col_b:
            img_url = st.text_input("Link do zdjęcia paki (np. z Google Drive/Dropbox):")
            if st.button("Wyślij dane do Barcelony"):
                df.loc[df.iloc[:, 0] == order_id, 'ETA'] = eta
                df.loc[df.iloc[:, 0] == order_id, 'Uwagi'] = desc
                df.loc[df.iloc[:, 0] == order_id, 'Foto_Link'] = img_url
                conn.update(spreadsheet=URL, data=df)
                st.success("Logistyk w Barcelonie otrzymał powiadomienie!")

    with tab2:
        st.header("Statusy w Barcelonie")
        # Grupowanie po Auto/Kierowca, żeby nie było chaosu przy wielu zamówieniach
        # Zakładam, że kolumna 0 to Numer Auta
        unique_trucks = df.iloc[:, 0].unique()
        
        for truck in unique_trucks:
            truck_orders = df[df.iloc[:, 0] == truck]
            with st.expander(f"🚚 AUTO: {truck} (Zamówień: {len(truck_orders)})"):
                c1, c2 = st.columns(2)
                with c1:
                    st.write("**Szczegóły ładunku:**")
                    st.table(truck_orders[['Kierowca', 'Slot', 'Status']])
                    st.warning(f"📌 Uwagi z Poznania: {truck_orders['Uwagi'].iloc[0]}")
                
                with c2:
                    if truck_orders['Foto_Link'].iloc[0]:
                        st.image(truck_orders['Foto_Link'].iloc[0], caption="Zdjęcie załadunku z Poznania", width=250)
                    
                    new_stat = st.selectbox("Zmień status auta:", 
                                         ["Załadowane w POZ", "Czeka na rozładunek", "ROZŁADOWANE", "ZAŁADOWANE - POWRÓT"],
                                         key=f"status_{truck}")
                    
                    if st.button(f"Aktualizuj status {truck}", key=f"btn_{truck}"):
                        df.loc[df.iloc[:, 0] == truck, 'Status'] = new_stat
                        conn.update(spreadsheet=URL, data=df)
                        st.rerun()

except Exception as e:
    st.error(f"Skonfiguruj nagłówki w Arkuszu: {e}")
