import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Magazyn Supabase PRO", layout="wide")

# --- POŁĄCZENIE Z SUPABASE ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception:
        st.error("Brak konfiguracji Supabase w Secrets!")
        st.stop()

supabase = init_connection()

st.title("📦 Zaawansowany System Magazynowy")

# --- SEKCJA 1 & 2: DODAWANIE ---
col_left, col_right = st.columns(2)

with col_left:
    st.header("Dodaj Kategorię")
    with st.form("form_kategorie", clear_on_submit=True):
        kat_nazwa = st.text_input("Nazwa kategorii")
        kat_opis = st.text_area("Opis kategorii")
        submit_kat = st.form_submit_button("Zapisz kategorię")

        if submit_kat:
            if kat_nazwa:
                try:
                    supabase.table("kategorie").insert({"nazwa": kat_nazwa, "opis": kat_opis}).execute()
                    st.success(f"Dodano kategorię: {kat_nazwa}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Błąd: {e}")
            else:
                st.error("Nazwa jest wymagana!")

with col_right:
    st.header("Dodaj Produkt")
    try:
        categories_query = supabase.table("kategorie").select("id, nazwa").execute()
        cat_options = {c['nazwa']: c['id'] for c in categories_query.data}
    except:
        cat_options = {}

    with st.form("form_produkty", clear_on_submit=True):
        prod_nazwa = st.text_input("Nazwa produktu")
        prod_liczba = st.number_input("Początkowa liczba (szt.)", min_value=0, step=1)
        prod_cena = st.number_input("Cena (zł)", min_value=0.0, format="%.2f")
        selected_cat_name = st.selectbox("Wybierz kategorię", options=list(cat_options.keys()))
        submit_prod = st.form_submit_button("Zapisz produkt")

        if submit_prod:
            if prod_nazwa and selected_cat_name:
                product_data = {
                    "nazwa": prod_nazwa, "liczba": prod_liczba, "cena": prod_cena,
                    "kategoria_id": cat_options[selected_cat_name]
                }
                try:
                    supabase.table("produkty").insert(product_data).execute()
                    st.success(f"Dodano produkt: {prod_nazwa}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Błąd: {e}")
            else:
                st.error("Wypełnij wymagane pola!")

st.divider()

# --- POBIERANIE DANYCH ---
try:
    res = supabase.table("produkty").select("id, nazwa, liczba, cena, kategorie(nazwa)").execute()
    
    if res.data:
        df = pd.DataFrame(res.data)
        df['kategoria'] = df['kategorie'].apply(lambda x: x['nazwa'] if x else "Brak")
        df['wartosc_suma'] = df['cena'] * df['liczba']

        # --- SEKCJA 3: WYKRESY ---
        st.header("📊 Analiza Magazynu")
        m1, m2, m3 = st.columns(3)
        m1.metric("Łącznie sztuk", int(df['liczba'].sum()))
        m2.metric("Wartość całkowita", f"{df['wartosc_suma'].sum():,.2f} zł")
        m3.metric("Liczba pozycji", len(df))

        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(px.pie(df, values='wartosc_suma', names='kategoria', hole=0.4, title="Wartość wg kategorii"), use_container_width=True)
        with c2:
            st.plotly_chart(px.bar(df, x='nazwa', y='liczba', color='kategoria', title="Stany ilościowe"), use_container_width=True)

        st.divider()

        # --- SEKCJA 4: ZARZĄDZANIE (NAPRAWIONE BŁĘDY ID) ---
        st.header("⚙️ Operacje na produktach")
        
        tab_list, tab_edit, tab_delete = st.tabs(["📋 Lista", "📉 Zdejmij ze stanu", "🗑️ Usuń całkowicie"])
        
        with tab_list:
            st.dataframe(df[['nazwa', 'kategoria', 'liczba', 'cena', 'wartosc_suma']], use_container_width=True)
        
        with tab_edit:
            st.subheader("Zmniejsz ilość produktu")
            # Używamy unikalnych kluczy dla selectboxa
            edit_options = {f"{row['nazwa']} (ID: {row['id']})": row for _, row in df.iterrows()}
            selected_prod_label = st.selectbox("Wybierz produkt do wydania", options=list(edit_options.keys()), key="sb_edit")
            selected_row = edit_options[selected_prod_label]
            
            remove_amount = st.number_input("Ile sztuk usunąć/wydać?", min_value=1, max_value=int(selected_row['liczba']) if selected_row['liczba'] > 0 else 1, step=1, key="ni_edit")
            
            # Dodany unikalny klucz 'key' do przycisku
            if st.button("Zaktualizuj stan", key="btn_update_stock"):
                new_qty = selected_row['liczba'] - remove_amount
                supabase.table("produkty").update({"liczba": new_qty}).eq("id", selected_row['id']).execute()
                st.success(f"Zaktualizowano stan dla {selected_row['nazwa']}!")
                st.rerun()

        with tab_delete:
            st.subheader("Usuwanie rekordu")
            del_options = {f"{row['nazwa']} (ID: {row['id']})": row['id'] for _, row in df.iterrows()}
            prod_to_del_label = st.selectbox("Wybierz produkt do usunięcia", options=list(del_options.keys()), key="sb_delete")
            
            confirm = st.checkbox("Potwierdzam chęć trwałego usunięcia", key="cb_confirm_del")
            
            # Dodany unikalny klucz 'key' do przycisku
            if st.button("❌ Usuń produkt z bazy", key="btn_delete_final"):
                if confirm:
                    supabase.table("produkty").delete().eq("id", del_options[prod_to_del_label]).execute()
                    st.warning("Produkt usunięty.")
                    st.rerun()
                else:
                    st.error("Zaznacz pole potwierdzenia!")

    else:
        st.info("Brak produktów w bazie.")

except Exception as e:
    st.error(f"Błąd krytyczny: {e}")
