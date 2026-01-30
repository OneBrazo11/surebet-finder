import streamlit as st
import requests
import pandas as pd

# Configuración de la página
st.set_page_config(page_title="Surebet Sniper 🎯", layout="wide")

st.title("🎯 Surebet Sniper - Arbitraje Deportivo")
st.markdown("Herramienta de análisis de arbitraje en tiempo real usando **The Odds API**.")

# Sidebar para configuración
with st.sidebar:
    st.header("Configuración")
    API_KEY = st.text_input("Ingresa tu API Key de The-Odds-API", type="password")
    region = st.selectbox("Región", ["us", "uk", "eu", "au"], index=0)
    sport = st.selectbox("Deporte", ["basketball_nba", "soccer_epl", "tennis_atp_us_open"], index=0)
    min_profit = st.slider("Beneficio Mínimo (%)", 0.0, 10.0, 1.0)
    
    if st.button("🔎 Buscar Oportunidades"):
        run_analysis = True
    else:
        run_analysis = False

# Lógica principal
if run_analysis and API_KEY:
    with st.spinner('Escaneando mercados...'):
        # 1. Obtener Odds
        url = f'https://api.the-odds-api.com/v4/sports/{sport}/odds'
        params = {
            'api_key': API_KEY,
            'regions': region,
            'markets': 'h2h',
            'oddsFormat': 'decimal'
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code != 200:
            st.error(f"Error en la API: {response.status_code}")
            st.write(response.json())
        else:
            data = response.json()
            surebets = []
            
            # 2. Analizar cada evento
            for event in data:
                home_team = event['home_team']
                away_team = event['away_team']
                
                # Encontrar la mejor cuota para HOME y AWAY entre todas las casas
                best_home_odd = 0
                best_home_bookie = ""
                best_away_odd = 0
                best_away_bookie = ""
                
                for bookmaker in event['bookmakers']:
                    for market in bookmaker['markets']:
                        if market['key'] == 'h2h':
                            for outcome in market['outcomes']:
                                if outcome['name'] == home_team:
                                    if outcome['price'] > best_home_odd:
                                        best_home_odd = outcome['price']
                                        best_home_bookie = bookmaker['title']
                                elif outcome['name'] == away_team:
                                    if outcome['price'] > best_away_odd:
                                        best_away_odd = outcome['price']
                                        best_away_bookie = bookmaker['title']
                
                # 3. Calcular Arbitraje
                if best_home_odd > 0 and best_away_odd > 0:
                    arbitrage_sum = (1/best_home_odd) + (1/best_away_odd)
                    
                    if arbitrage_sum < 1.0:
                        profit_percent = (1 - arbitrage_sum) / arbitrage_sum * 100
                        
                        if profit_percent >= min_profit:
                            surebets.append({
                                "Evento": f"{home_team} vs {away_team}",
                                "Beneficio (%)": round(profit_percent, 2),
                                "Apuesta 1 (Local)": f"{best_home_bookie} @ {best_home_odd}",
                                "Apuesta 2 (Visita)": f"{best_away_bookie} @ {best_away_odd}",
                                "Fecha": event['commence_time']
                            })
            
            # 4. Mostrar Resultados
            if surebets:
                st.success(f"¡Se encontraron {len(surebets)} oportunidades de arbitraje!")
                df = pd.DataFrame(surebets)
                st.dataframe(df, use_container_width=True)
            else:
                st.warning("No se encontraron surebets con los parámetros actuales. Intenta otro deporte o región.")

elif run_analysis and not API_KEY:
    st.warning("⚠️ Por favor ingresa tu API Key en la barra lateral.")
else:
    st.info("Ingresa tu API Key y presiona buscar para iniciar.")
