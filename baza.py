import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Magazyn Supabase", layout="wide")

# --- POŁĄCZENIE Z SUPABASE ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

st.title("📦 System Zarządzania Produktami")

# --- SEKCJA 1 & 2: FORMULARZE (Dwie kolumny) ---
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
                    st.rerun() # Odświeżamy, aby kategoria pojawiła się w selectboxie
                except Exception as e:
                    st.error(f"Błąd: {e}")
            else:
                st.error("Nazwa jest wymagana!")

with col_right:
    st.header("Dodaj Produkt")
    # Pobranie kategorii do selectboxa
    try:
        categories_query = supabase.table("kategorie").select("id, nazwa").execute()
        cat_options = {c['nazwa']: c['id'] for c in categories_query.data}
    except:
        cat_options = {}

    with st.form("form_produkty", clear_on_submit=True):
        prod_nazwa = st.text_input("Nazwa produktu")
        prod_liczba = st.number_input("Liczba (szt.)", min_value=0, step=1)
        prod_cena = st.number_input("Cena (zł)", min_value=0.0, format="%.2f")
        selected_cat_name = st.selectbox("Wybierz kategorię", options=list(cat_options.keys()))
        submit_prod = st.form_submit_button("Zapisz produkt")

        if submit_prod:
            if prod_nazwa and selected_cat_name:
                product_data = {
                    "nazwa": prod_nazwa,
                    "liczba": prod_liczba,
                    "cena": prod_cena,
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

# --- SEKCJA 3: PODGLĄD DANYCH I WYKRESY ---
st.header("📊 Analiza i Stan Magazynowy")

try:
    # Pobieramy produkty wraz z nazwą kategorii (join)
    res = supabase.table("produkty").select("nazwa, liczba, cena, kategorie(nazwa)").execute()
    
    if res.data:
        # Konwersja do DataFrame
        df = pd.DataFrame(res.data)
        # Wyciąganie nazwy kategorii z relacji
        df['kategoria'] = df['kategorie'].apply(lambda x: x['nazwa'] if x else "Brak")
        df['wartosc_suma'] = df['cena'] * df['liczba']

        # Wyświetlanie metryk na górze
        m1, m2, m3 = st.columns(3)
        m1.metric("Suma sztuk", int(df['liczba'].sum()))
        m2.metric("Wartość magazynu", f"{df['wartosc_suma'].sum():,.2f} zł")
        m3.metric("Liczba produktów", len(df))

        # Wykresy
        c1, c2 = st.columns(2)
        
        with c1:
            st.subheader("Udział wartościowy kategorii")
            fig_pie = px.pie(df, values='wartosc_suma', names='kategoria', hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with c2:
            st.subheader("Ilość sztuk per produkt")
            fig_bar = px.bar(df, x='nazwa', y='liczba', color='kategoria', text='liczba')
            st.plotly_chart(fig_bar, use_container_width=True)

        # Tabela na samym dole
        with st.expander("Zobacz pełną tabelę danych"):
            st.dataframe(df[['nazwa', 'kategoria', 'liczba', 'cena', 'wartosc_suma']], use_container_width=True)
            
    else:
        st.info("Brak danych do wyświetlenia. Dodaj pierwszy produkt!")

except Exception as e:
    st.error(f"Wystąpił problem z pobieraniem danych: {e}")
