import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Magazyn Supabase", layout="wide")

# --- POŁĄCZENIE Z SUPABASE ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error("Brak konfiguracji Supabase w Secrets!")
        st.stop()

supabase = init_connection()

st.title("📦 System Zarządzania Produktami")

# --- SEKCJA 1 & 2: DODAWANIE (KOLUMNY) ---
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

# --- POBIERANIE DANYCH DO ANALIZY I USUWANIA ---
try:
    # Pobieramy ID, żeby móc usuwać
    res = supabase.table("produkty").select("id, nazwa, liczba, cena, kategorie(nazwa)").execute()
    
    if res.data:
        df = pd.DataFrame(res.data)
        df['kategoria'] = df['kategorie'].apply(lambda x: x['nazwa'] if x else "Brak")
        df['wartosc_suma'] = df['cena'] * df['liczba']

        # --- SEKCJA 3: WYKRESY ---
        st.header("📊 Analiza i Stan Magazynowy")
        m1, m2, m3 = st.columns(3)
        m1.metric("Suma sztuk", int(df['liczba'].sum()))
        m2.metric("Wartość magazynu", f"{df['wartosc_suma'].sum():,.2f} zł")
        m3.metric("Liczba produktów", len(df))

        c1, c2 = st.columns(2)
        with c1:
            fig_pie = px.pie(df, values='wartosc_suma', names='kategoria', hole=0.4, title="Udział wartościowy kategorii")
            st.plotly_chart(fig_pie, use_container_width=True)
        with c2:
            fig_bar = px.bar(df, x='nazwa', y='liczba', color='kategoria', text='liczba', title="Ilość sztuk per produkt")
            st.plotly_chart(fig_bar, use_container_width=True)

        st.divider()

        # --- SEKCJA 4: USUWANIE I TABELA ---
        st.header("⚙️ Zarządzanie produktami")
        
        tab1, tab2 = st.tabs(["Lista Produktów", "Usuń Produkt"])
        
        with tab1:
            st.dataframe(df[['nazwa', 'kategoria', 'liczba', 'cena', 'wartosc_suma']], use_container_width=True)
        
        with tab2:
            st.subheader("Usuń produkt z bazy")
            # Tworzymy słownik do wyboru: "Nazwa Produktu (ID)" -> ID
            delete_options = {f"{row['nazwa']} ({row['kategoria']})": row['id'] for _, row in df.iterrows()}
            product_to_delete = st.selectbox("Wybierz produkt do usunięcia", options=list(delete_options.keys()))
            
            if st.button("❌ Usuń trwale wybrany produkt"):
                try:
                    product_id = delete_options[product_to_delete]
                    supabase.table("produkty").delete().eq("id", product_id).execute()
                    st.warning(f"Usunięto produkt!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Błąd podczas usuwania: {e}")

    else:
        st.info("Baza produktów jest pusta. Dodaj pierwszy produkt powyżej.")

except Exception as e:
    st.error(f"Problem z bazą danych: {e}")
