import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# Configuración de página
st.set_page_config(page_title="Surebet Sniper Global 🌍", layout="wide")

st.title("🌍 Surebet Sniper - Escaneo Global")
st.markdown("Analiza **todas las casas de apuestas del mundo** simultáneamente (USA, Europa, UK, Latam) y muestra la fecha del evento.")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("1. Credenciales")
    API_KEY = st.text_input("Ingresa tu API Key", type="password")
    
    # Variables de estado
    if 'sports_list' not in st.session_state:
        st.session_state['sports_list'] = {}

    # Botón Cargar Deportes
    if API_KEY:
        if st.button("🔄 Cargar/Actualizar Lista de Deportes"):
            try:
                with st.spinner("Consultando deportes activos..."):
                    url_sports = f"https://api.the-odds-api.com/v4/sports/?api_key={API_KEY}"
                    r = requests.get(url_sports)
                    r.raise_for_status()
                    sports_data = r.json()
                    
                    mis_deportes = {}
                    for item in sports_data:
                        if item['active']:
                            label = f"{item['group']} - {item['title']}"
                            mis_deportes[label] = item['key']
                    
                    st.session_state['sports_list'] = mis_deportes
                    st.success(f"¡{len(mis_deportes)} ligas activas cargadas!")
            except Exception as e:
                st.error(f"Error cargando deportes: {e}")

    st.header("2. Configuración")
    
    if st.session_state['sports_list']:
        sorted_labels = sorted(st.session_state['sports_list'].keys())
        selected_label = st.selectbox("Selecciona la Liga/Torneo:", sorted_labels)
        sport_key = st.session_state['sports_list'][selected_label]
        st.caption(f"ID: {sport_key}")
    else:
        st.warning("👆 Carga la lista primero.")
        sport_key = None

    # NOTA: Eliminamos el selector de región. Ahora usamos 'us,uk,eu,au' fijo internamente.
    st.info("ℹ️ Analizando casas de: USA, UK, Europa y Australia juntas.")
    
    market_type = st.selectbox("Mercado", ["h2h", "spreads", "totals"], index=0)
    min_profit = st.slider("Beneficio Mínimo (%)", 0.0, 10.0, 1.0)
    
    if st.button("🔎 Buscar Surebets Globales"):
        run_analysis = True
    else:
        run_analysis = False

# --- FUNCIÓN DE ARBITRAJE ---
def get_arbitrage(outcomes, market_name):
    grouped_outcomes = {}
    for bookmaker in outcomes:
        title = bookmaker['title']
        for market in bookmaker['markets']:
            if market['key'] == market_name:
                for outcome in market['outcomes']:
                    name = outcome['name']
                    price = outcome['price']
                    point = outcome.get('point', 'Moneyline')
                    
                    if point not in grouped_outcomes:
                        grouped_outcomes[point] = []
                    grouped_outcomes[point].append({'bookie': title, 'name': name, 'price': price, 'point': point})

    opps = []
    if market_name == 'h2h' or market_name == 'totals':
        for point, options in grouped_outcomes.items():
            best_odds = {}
            for opt in options:
                outcome_name = opt['name']
                if outcome_name not in best_odds or opt['price'] > best_odds[outcome_name]['price']:
                    best_odds[outcome_name] = opt
            
            if len(best_odds) == 2:
                sides = list(best_odds.values())
                arb_sum = (1/sides[0]['price']) + (1/sides[1]['price'])
                
                if arb_sum < 1.0:
                    profit = (1 - arb_sum) / arb_sum * 100
                    if profit >= min_profit:
                        opps.append({
                            "Mercado": market_name,
                            "Item": point,
                            "Beneficio %": round(profit, 2),
                            f"Apuesta A ({sides[0]['name']})": f"{sides[0]['bookie']} @ {sides[0]['price']}",
                            f"Apuesta B ({sides[1]['name']})": f"{sides[1]['bookie']} @ {sides[1]['price']}"
                        })
    return opps

# --- EJECUCIÓN ---
if run_analysis and API_KEY and sport_key:
    with st.spinner(f'Analizando {sport_key} en todo el mundo...'):
        url = f'https://api.the-odds-api.com/v4/sports/{sport_key}/odds'
        
        # AQUÍ ESTÁ EL CAMBIO CLAVE: regions='us,uk,eu,au'
        params = {
            'api_key': API_KEY,
            'regions': 'us,uk,eu,au', 
            'markets': market_type,
            'oddsFormat': 'decimal'
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            all_opps = []
            
            for event in data:
                event_name = f"{event['home_team']} vs {event['away_team']}"
                
                # Convertir fecha fea (ISO) a bonita
                raw_date = event['commence_time'] # ej: 2026-02-01T14:00:00Z
                dt_object = datetime.strptime(raw_date, "%Y-%m-%dT%H:%M:%SZ")
                formatted_date = dt_object.strftime("%Y-%m-%d %H:%M") # ej: 2026-02-01 14:00
                
                opps = get_arbitrage(event['bookmakers'], market_type)
                
                for op in opps:
                    op['Evento'] = event_name
                    op['Fecha (UTC)'] = formatted_date # Nueva columna
                    all_opps.append(op)
            
            if all_opps:
                st.success(f"¡Éxito! {len(all_opps)} Oportunidades Globales detectadas.")
                df = pd.DataFrame(all_opps)
                
                # Reordenamos para poner la Fecha primero
                cols = ['Fecha (UTC)', 'Evento', 'Beneficio %', list(df.columns)[4], list(df.columns)[5]]
                st.dataframe(df[cols], use_container_width=True)
            else:
                st.info(f"No hay surebets matemáticas en {sport_key} cruzando todas las regiones.")
                
        except Exception as e:
            st.error(f"Error conectando a la API: {e}")

elif run_analysis and not sport_key:
    st.error("⚠️ Carga y selecciona una liga primero.")
