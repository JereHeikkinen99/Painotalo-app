import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- TÄRKEÄÄ: SALASANASUOJAUS NETTIÄ VARTEN ---
def tarkista_salasana():
    """Palauttaa True, jos käyttäjä syöttää oikean salasanan."""
    if "kirjautunut" not in st.session_state:
        st.session_state["kirjautunut"] = False

    if st.session_state["kirjautunut"]:
        return True

    st.title("🔒 Painotalon suojattu järjestelmä")
    st.write("Tämä sovellus on tarkoitettu vain valtuutetulle henkilökunnalle.")
    
    salasana_syote = st.text_input("Syötä järjestelmän salasana:", type="password")
    
    if st.button("Kirjaudu sisään"):
        # Voit muuttaa nämä salasanat miksi haluat!
        if salasana_syote == "paino2026": 
            st.session_state["kirjautunut"] = True
            st.rerun()
        else:
            st.error("❌ Väärä salasana. Yritä uudelleen.")
    return False

# Jos salasana ei ole oikein, pysäytetään koodin suoritus tähän
if not tarkista_salasana():
    st.stop()

# --- 1. TIETOKANNAN ALUSTUS ---
def alusta_tietokanta():
    conn = sqlite3.connect("tuotanto.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS kirjukset (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pvm TEXT,
            kone TEXT,
            tilaus_id TEXT,
            paperi TEXT,
            muste TEXT,
            priima INTEGER,
            makkeli INTEGER,
            makkeli_prosentti REAL,
            hukka_euroina REAL
        )
    """)
    conn.commit()
    conn.close()

alusta_tietokanta()

# --- 2. HINNASTOT TAUSTALLA ---
PAPERI_HINNAT = {
    "G-Print 100g": 0.05,
    "LumiSilk 150g": 0.08,
    "Kartonki 300g": 0.15
}

MUSTE_HINNAT = {
    "Vakiomuste (CMYK)": 10.0,
    "Erikoisväri (Spotti)": 25.0
}

# --- 3. SIVUPALKKI: ROOLIT & KIRJAUDU ULOS ---
st.sidebar.title("Käyttäjäasetukset")
rooli = st.sidebar.radio("Valitse roolisi:", ["Työntekijä", "Johto"])

st.sidebar.write("---")
if st.sidebar.button("🔒 Kirjaudu ulos"):
    st.session_state["kirjautunut"] = False
    st.rerun()

st.title("🏭 Painotalon Tuotantojärjestelmä")
st.write("---")

# --- 4. TYÖNTEKIJÄN LOMAKE ---
st.header("📝 Uusi työkirjaus")

sarake1, sarake2 = st.columns(2)

with sarake1:
    kone = st.selectbox("Valitse kone:", ["Kone 1", "Kone 2", "Kone 3"])
    tilaus_id = st.text_input("Tilauksen numero (ID):", placeholder="esim. 10234")
    paperi = st.selectbox("Käytetty paperi/materiaali:", list(PAPERI_HINNAT.keys()))
    muste = st.selectbox("Värivalinta:", list(MUSTE_HINNAT.keys()))

with sarake2:
    priima = st.number_input("Valmiit arkit (Priima):", min_value=0, step=100, value=0)
    makkeli = st.number_input("Makkelit (Hukka):", min_value=0, step=10, value=0)

tallenna_nappi = st.button("💾 Tallenna työkirjaus", type="primary")

# --- 5. TALLENNUSLOGIIKKA & LASKENTA ---
kokonaisajo = priima + makkeli

if tallenna_nappi:
    if tilaus_id == "" or kokonaisajo == 0:
        st.error("❌ Täytä tilauksen numero ja varmista, että arkkimäärät eivät ole nollia!")
    else:
        makkeli_prosentti = (makkeli / kokonaisajo) * 100
        paperin_hinta_per_arkki = PAPERI_HINNAT[paperi]
        hukka_euroina = (makkeli * paperin_hinta_per_arkki) + MUSTE_HINNAT[muste]
        nykyinen_pvm = datetime.now().strftime("%Y-%m-%d %H:%M")

        conn = sqlite3.connect("tuotanto.db")
        c = conn.cursor()
        c.execute("""
            INSERT INTO kirjukset (pvm, kone, tilaus_id, paperi, muste, priima, makkeli, makkeli_prosentti, hukka_euroina)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (nykyinen_pvm, kone, tilaus_id, paperi, muste, priima, makkeli, makkeli_prosentti, hukka_euroina))
        conn.commit()
        conn.close()
        
        st.success(f"✅ Tilaus {tilaus_id} tallennettu onnistuneesti tietokantaan!")

st.write("---")

# --- 6. DATAN LUKEMINEN JA NÄYTTÖ ---
try:
    conn = sqlite3.connect("tuotanto.db")
    df = pd.read_sql_query("SELECT * FROM kirjukset ORDER BY id DESC", conn)
    conn.close()
except:
    df = pd.DataFrame()

if not df.empty:
    if rooli == "Työntekijä":
        st.subheader("📊 Viimeisimmät ajot (Tehtaan näkymä)")
        naytettava_df = df[['pvm', 'kone', 'tilaus_id', 'priima', 'makkeli', 'makkeli_prosentti']]
        st.dataframe(naytettava_df, use_container_width=True)
        
    elif rooli == "Johto":
        st.subheader("📈 Johdon talousnäkymä & Raportit")
        kaikki_hukka_euroina = df['hukka_euroina'].sum()
        keski_makkeli_prosentti = df['makkeli_prosentti'].mean()
        
        kol1, kol2 = st.columns(2)
        kol1.metric(label="KAIKKI HUKAT YHTEENSÄ", value=f"{kaikki_hukka_euroina:.2f} €", delta="Kustannus", delta_color="inverse")
        kol2.metric(label="KESKIMÄÄRÄINEN MAKKELI-%", value=f"{keski_makkeli_prosentti:.1f} %")
        
        st.write("#### Kaikki tietokannan tuotantorivat:")
        st.dataframe(df, use_container_width=True)
else:
    st.info("Tietokannassa ei ole vielä yhtään kirjausta.")