import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- SALASANASUOJAUS ---
def tarkista_salasana():
    if "kirjautunut" not in st.session_state:
        st.session_state["kirjautunut"] = False
    if st.session_state["kirjautunut"]:
        return True
    st.title("🔒 Painotalon suojattu järjestelmä")
    salasana_syote = st.text_input("Syötä järjestelmän salasana:", type="password")
    if st.button("Kirjaudu sisään"):
        if salasana_syote == "paino2026": 
            st.session_state["kirjautunut"] = True
            st.rerun()
        else:
            st.error("❌ Väärä salasana.")
    return False

if not tarkista_salasana():
    st.stop()

# --- TIETOKANNAN ALUSTUS (Versio 2) ---
def alusta_tietokanta():
    conn = sqlite3.connect("tuotanto_v2.db") # Vaihdettu uusi tiedostonimi vanhan errorin ohittamiseksi
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS kirjukset (
            id INTEGER PRIMARY KEY AUTOINCREMENT, pvm TEXT, kone TEXT, 
            tilaus_id TEXT, erajako TEXT, paperi TEXT, muste TEXT, priima INTEGER, 
            makkeli INTEGER, makkeli_prosentti REAL, hukka_euroina REAL
        )
    """)
    c.execute("CREATE TABLE IF NOT EXISTS paperit (nimi TEXT PRIMARY KEY, hinta REAL)")
    c.execute("CREATE TABLE IF NOT EXISTS musteet (nimi TEXT PRIMARY KEY, hinta REAL)")
    
    # Oletushinnat
    c.execute("SELECT COUNT(*) FROM paperit")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO paperit VALUES (?, ?)", [
            ("G-Print 100g", 0.05), ("LumiSilk 150g", 0.08), ("Kartonki 300g", 0.15)
        ])
    c.execute("SELECT COUNT(*) FROM musteet")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO musteet VALUES (?, ?)", [
            ("Vakiomuste (CMYK)", 10.0), ("Erikoisväri (Spotti)", 25.0)
        ])
    conn.commit()
    conn.close()

alusta_tietokanta()

def hae_hinnasto(taulu):
    conn = sqlite3.connect("tuotanto_v2.db")
    df_hinnat = pd.read_sql_query(f"SELECT * FROM {taulu}", conn)
    conn.close()
    return dict(zip(df_hinnat['nimi'], df_hinnat['hinta']))

# --- SIVUPALKKI ---
st.sidebar.title("Navigointi")
rooli = st.sidebar.radio("Valitse roolisi:", ["Työntekijä", "Johto"])

PAPERI_HINNAT = hae_hinnasto("paperit")
MUSTE_HINNAT = hae_hinnasto("musteet")

if st.sidebar.button("🔒 Kirjaudu ulos"):
    st.session_state["kirjautunut"] = False
    st.rerun()

st.title("🏭 Painotalon Tuotantojärjestelmä")
st.write("---")

# --- JOHDON HINNASTOHALLINTA ---
if rooli == "Johto":
    with st.expander("⚙️ MATERIAALIEN JA HINTOJEN HALLINTA (Vain Johto)"):
        kol1, kol2 = st.columns(2)
        with kol1:
            st.write("### 📄 Paperit")
            uusi_paperi = st.text_input("Uuden paperin nimi:")
            uusi_paperi_hinta = st.number_input("Hinta per arkki (€):", min_value=0.0, step=0.01, format="%.2f")
            if st.button("Lisää/Päivitä paperi"):
                if uusi_paperi:
                    conn = sqlite3.connect("tuotanto_v2.db")
                    conn.execute("INSERT OR REPLACE INTO paperit VALUES (?, ?)", (uusi_paperi, uusi_paperi_hinta))
                    conn.commit()
                    conn.close()
                    st.success(f"Tallennettu: {uusi_paperi}")
                    st.rerun()
        with kol2:
            st.write("### 🎨 Musteet")
            uusi_muste = st.text_input("Uuden musteen/värin nimi:")
            uusi_muste_hinta = st.number_input("Hinta per ajo (€):", min_value=0.0, step=1.0, format="%.2f")
            if st.button("Lisää/Päivitä muste"):
                if uusi_muste:
                    conn = sqlite3.connect("tuotanto_v2.db")
                    conn.execute("INSERT OR REPLACE INTO musteet VALUES (?, ?)", (uusi_muste, uusi_muste_hinta))
                    conn.commit()
                    conn.close()
                    st.success(f"Tallennettu: {uusi_muste}")
                    st.rerun()
    st.write("---")

# --- TYÖNTEKIJÄN LOMAKE ---
st.header("📝 Arkkikohtainen eräkirjaus tilaukselle")
sarake1, sarake2 = st.columns(2)

with sarake1:
    kone = st.selectbox("Valitse kone:", ["Kone 1", "Kone 2", "Kone 3"])
    tilaus_id = st.text_input("Tilauksen numero (ID):", placeholder="esim. 10234")
    erajako = st.selectbox("Ajon osa / Erä:", ["Aloitussäätö", "Painosajo 1", "Painosajo 2", "Kääntöpuoli", "Viimeistelyhukka"])
    paperi = st.selectbox("Käytetty paperi/materiaali:", list(PAPERI_HINNAT.keys()))
    muste = st.selectbox("Värivalinta:", list(MUSTE_HINNAT.keys()))

with sarake2:
    priima = st.number_input("Erän valmiit arkit (Priima):", min_value=0, step=100, value=0)
    makkeli = st.number_input("Erän makkelit (Hukka):", min_value=0, step=10, value=0)

tallenna_nappi = st.button("💾 Tallenna eräkirjaus", type="primary")

kokonaisajo = priima + makkeli

if tallenna_nappi:
    if tilaus_id == "" or kokonaisajo == 0:
        st.error("❌ Täytä tiedot oikein!")
    else:
        makkeli_prosentti = (makkeli / kokonaisajo) * 100
        paperin_hinta_per_arkki = PAPERI_HINNAT[paperi]
        hukka_euroina = (makkeli * paperin_hinta_per_arkki) + MUSTE_HINNAT[muste]
        nykyinen_pvm = datetime.now().strftime("%Y-%m-%d %H:%M")

        conn = sqlite3.connect("tuotanto_v2.db")
        c = conn.cursor()
        c.execute("""
            INSERT INTO kirjukset (pvm, kone, tilaus_id, erajako, paperi, muste, priima, makkeli, makkeli_prosentti, hukka_euroina)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (nykyinen_pvm, kone, tilaus_id, erajako, paperi, muste, priima, makkeli, makkeli_prosentti, hukka_euroina))
        conn.commit()
        conn.close()
        st.success(f"✅ Erä '{erajako}' tallennettu tilaukselle {tilaus_id}!")

st.write("---")

# --- DATAN LUKEMINEN & TILAUSKOHTAISET MITTARIT ---
try:
    conn = sqlite3.connect("tuotanto_v2.db")
    df = pd.read_sql_query("SELECT * FROM kirjukset ORDER BY id DESC", conn)
    conn.close()
except:
    df = pd.DataFrame()

if not df.empty:
    st.header("🔍 Hae ja tarkastele tiettyä tilausta")
    uniikit_tilaukset = list(df['tilaus_id'].unique())
    valittu_tilaus = st.selectbox("Valitse tilauksen numero tarkasteluun:", uniikit_tilaukset)
    
    df_tilaus = df[df['tilaus_id'] == valittu_tilaus]
    
    tilaus_priima = df_tilaus['priima'].sum()
    tilaus_makkeli = df_tilaus['makkeli'].sum()
    tilaus_kokonais = tilaus_priima + tilaus_makkeli
    tilaus_makkeli_prosa = (tilaus_makkeli / tilaus_kokonais) * 100 if tilaus_kokonais > 0 else 0
    tilaus_hukka_euroina = df_tilaus['hukka_euroina'].sum()
    
    st.subheader(f"📊 Tilauksen {valittu_tilaus} yhteenveto")
    
    if rooli == "Työntekijä":
        m_kol1, m_kol2, m_kol3 = st.columns(3)
        m_kol1.metric(label="Kokonaispriima", value=f"{tilaus_priima} kpl")
        m_kol2.metric(label="Kokonaismakkeli", value=f"{tilaus_makkeli} kpl")
        m_kol3.metric(label="Tilauksen Makkeli-%", value=f"{tilaus_makkeli_prosa:.1f} %")
        
        st.dataframe(df_tilaus[['pvm', 'kone', 'erajako', 'priima', 'makkeli', 'makkeli_prosentti']], use_container_width=True)
        
    elif rooli == "Johto":
        m_kol1, m_kol2, m_kol3, m_kol4 = st.columns(4)
        m_kol1.metric(label="Kokonaispriima", value=f"{tilaus_priima} kpl")
        m_kol2.metric(label="Kokonaisajo", value=f"{tilaus_kokonais} kpl")
        m_kol3.metric(label="Makkeli-%", value=f"{tilaus_makkeli_prosa:.1f} %")
        m_kol4.metric(label="Hukan kustannus firmalle", value=f"{tilaus_hukka_euroina:.2f} €", delta=f"{tilaus_hukka_euroina:.2f} €", delta_color="inverse")
        
        st.dataframe(df_tilaus, use_container_width=True)
        
    st.write("---")
    if rooli == "Johto":
        st.header("📈 Tehtaan kokonaisnäkymä (Kaikki tilaukset yhteensä)")
        kaikki_hukka_euroina = df['hukka_euroina'].sum()
        st.metric(label="KAIKKI TEHTAAN HUKAT YHTEENSÄ", value=f"{kaikki_hukka_euroina:.2f} €")
        st.dataframe(df, use_container_width=True)
    else:
        st.header("📋 Viimeisimmät kirjaukset tehtaalta")
        st.dataframe(df[['pvm', 'kone', 'tilaus_id', 'erajako', 'priima', 'makkeli']], use_container_width=True)
else:
    st.info("Tietokannassa ei ole vielä yhtään kirjausta.")