# --- SECTION ANALYSE MULTI-COURSES ---
st.subheader("🚀 Analyse Automatique de la Journée")

# Zone de texte pour coller plusieurs URLs (une par ligne)
urls_input = st.text_area("Colle ici toutes les URLs Zeturf du jour (une par ligne) :", height=150)

if st.button("⚡ LANCER L'ANALYSE GLOBALE"):
    if not urls_input:
        st.warning("Veuillez coller au moins une URL.")
    else:
        urls = urls_input.strip().split('\n')
        st.info(f"Analyse de {len(urls)} courses en cours...")
        
        for url in urls:
            url = url.strip()
            if not url: continue
            
            df = extraire_donnees(url)
            
            if not df.empty:
                # Récupération des infos de la course
                nom_course = url.split('/')[-2].replace('-', ' ').title()
                st.write(f"--- 🏁 {nom_course} ({df['heure'].iloc[0]}) ---")
                
                for _, row in df.iterrows():
                    mise, prob = calculer_kelly(row['cote'], capital)
                    indice_value = prob * row['cote']
                    
                    # Condition d'alerte : Value > 1.10
                    if indice_value >= 1.10 and mise > 0:
                        st.success(f"💎 VALUE : {row['nom']} | Cote: {row['cote']} | Mise: {round(mise, 2)}€")
                        
                        # ENVOI ALERTE TELEGRAM
                        token = st.secrets.get("TELEGRAM_TOKEN")
                        chat_id = st.secrets.get("TELEGRAM_CHAT_ID")
                        
                        if token and chat_id:
                            message = (f"🏇 *ALERTE VALUE DETECTÉE*\n\n"
                                       f"📍 Course: {nom_course}\n"
                                       f"🕒 Départ: {row['heure']}\n"
                                       f"🐎 Cheval: *{row['nom']}*\n"
                                       f"📈 Cote: {row['cote']}\n"
                                       f"📊 Value: {round(indice_value, 2)}\n"
                                       f"💰 Mise conseillée: *{round(mise, 2)}€*")
                            
                            url_tg = f"https://api.telegram.org/bot{token}/sendMessage"
                            requests.post(url_tg, data={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"})
            else:
                st.error(f"Erreur sur l'URL : {url}")
        
        st.balloons()
        st.success("Analyse terminée et alertes envoyées !")
      
