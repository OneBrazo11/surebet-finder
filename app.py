import streamlit as st
import requests
import pandas as pd

# Configuración de página
st.set_page_config(page_title="Surebet Sniper Auto 🎯", layout="wide")

st.title("🎯 Surebet Sniper - Listado Automático")
st.markdown("Esta versión **detecta automáticamente** todos los torneos activos (ATP, Liga Pro, NBA...) para que no tengas que configurarlos manualmente.")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("1. Credenciales")
    # Pedimos la clave primero
    API_KEY = st.text_input("Ingresa tu API Key", type="password")
    
    # Variables para guardar el estado de la lista de deportes
    if 'sports_list' not in st.session_state:
        st.session_state['sports_list'] = {}

    # Botón para cargar ligas activas (No gasta cuota)
    if API_KEY:
        if st.button("🔄 Cargar/Actualizar Lista de Deportes"):
            try:
                with st.spinner("Consultando deportes activos..."):
                    # Endpoint que NO gasta créditos
                    url_sports = f"https://api.the-odds-api.com/v4/sports/?api_key={API_KEY}"
                    r = requests.get(url_sports)
                    r.raise_for_status()
                    sports_data = r.json()
                    
                    # Creamos un diccionario: Nombre Legible -> Código API
                    # Filtramos solo los activos
                    mis_deportes = {}
                    for item in sports_data:
                        if item['active']:
                            # Creamos un nombre bonito: "Tenis - ATP Rio de Janeiro"
                            label = f"{item['group']} - {item['title']}"
                            mis_deportes[label] = item['key']
                    
                    st.session_state['sports_list'] = mis_deportes
                    st.success(f"¡Se encontraron {len(mis_deportes)} ligas activas!")
            except Exception as e:
                st.error(f"Error cargando deportes: {e}")

    st.header("2. Configuración de Búsqueda")
    
    # Si ya tenemos deportes cargados, mostramos el Selectbox
    if st.session_state['sports_list']:
        # Ordenamos la lista alfabéticamente para que sea fácil buscar "Ecuador" o "Tennis"
        sorted_labels = sorted(st.session_state['sports_list'].keys())
        
        selected_label = st.selectbox("Selecciona la Liga/Torneo:", sorted_labels)
        sport_key = st.session_state['sports_list'][selected_label]
        
        st.info(f"Código interno: {sport_key}") # Para que veas qué está seleccionando
    else:
        st.warning("👆 Ingresa tu API Key y dale al botón 'Cargar' para ver las ligas.")
        sport_key = None

    region = st.selectbox("Región de Casas", ["eu", "us", "uk", "au"], index=0)
    market_type = st.selectbox("Mercado", ["h2h", "spreads", "totals"], index=0)
    min_profit = st.slider("Beneficio Mínimo (%)", 0.0, 10.0, 1.0)
    
    if st.button("🔎 Buscar Surebets Ahora"):
        run_analysis = True
    else:
        run_analysis = False

# --- LÓGICA DE ARBITRAJE (Igual que antes) ---
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
    # Lógica simplificada Moneyline y Totales
    if market_name == 'h2h' or market_name == 'totals':
        for point, options in grouped_outcomes.items():
            best_odds = {}
            for opt in options:
                outcome_name = opt['name']
                # Nos quedamos con la mejor cuota de cada opción (ej. Mejor Over, Mejor Under)
                if outcome_name not in best_odds or opt['price'] > best_odds[outcome_name]['price']:
                    best_odds[outcome_name] = opt
            
            # Si hay 2 lados opuestos
            if len(best_odds) == 2:
                sides = list(best_odds.values())
                arb_sum = (1/sides[0]['price']) + (1/sides[1]['price'])
                
                if arb_sum < 1.0:
                    profit = (1 - arb_sum) / arb_sum * 100
                    if profit >= min_profit:
                        opps.append({
                            "Liga": selected_label if 'selected_label' in locals() else sport_key,
                            "Mercado": market_name,
                            "Item": point,
                            "Beneficio %": round(profit, 2),
                            f"Apuesta A ({sides[0]['name']})": f"{sides[0]['bookie']} @ {sides[0]['price']}",
                            f"Apuesta B ({sides[1]['name']})": f"{sides[1]['bookie']} @ {sides[1]['price']}"
                        })
    return opps

# --- EJECUCIÓN PRINCIPAL ---
if run_analysis and API_KEY and sport_key:
    with st.spinner(f'Analizando {sport_key}...'):
        url = f'https://api.the-odds-api.com/v4/sports/{sport_key}/odds'
        params = {
            'api_key': API_KEY,
            'regions': region,
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
                opps = get_arbitrage(event['bookmakers'], market_type)
                
                for op in opps:
                    op['Evento'] = event_name
                    all_opps.append(op)
            
            if all_opps:
                st.success(f"¡Éxito! {len(all_opps)} Oportunidades detectadas.")
                df = pd.DataFrame(all_opps)
                # Reordenar columnas para legibilidad
                cols = ['Evento', 'Beneficio %', list(df.columns)[4], list(df.columns)[5], 'Liga']
                st.dataframe(df[cols], use_container_width=True)
            else:
                st.info(f"No hay surebets matemáticas en {sport_key} ({market_type}) con las casas seleccionadas.")
                
        except Exception as e:
            st.error(f"Error conectando a la API: {e}")

elif run_analysis and not sport_key:
    st.error("⚠️ Primero debes cargar y seleccionar una liga del menú.")
