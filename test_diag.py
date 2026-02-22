import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.title("Test de Connexion Google Sheets")

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl=0)
    st.success("✅ Connexion réussie !")
    st.write("Voici les 5 dernières lignes détectées :")
    st.dataframe(df.tail(5))
except Exception as e:
    st.error("❌ La connexion a échoué.")
    st.exception(e
  )
