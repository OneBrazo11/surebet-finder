import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Surebet Sniper V5 🎯", layout="wide")
st.title("🎯 Surebet Sniper - Diagnóstico")

with st.sidebar:
    st.header("1. Credenciales")
    API_KEY = st.text_input("Ingresa tu API Key", type="password")
    
    if 'sports_list' not in st.session_state:
        st.session_state['sports_list'] = {}

    if API_KEY:
        if st.button("🔄 Cargar Lista de Deportes"):
            try:
                with st.spinner("Conectando..."):
                    r = requests.get(f"https://api.the-odds-api.com/v4/sports/?api_key={API_KEY}")
                    r.raise_for_status()
                    sports_data = r.json()
                    mis_deportes = {f"{item['group']} - {item['title']}": item['key'] for item in sports_data if item['active']}
                    st.session_state['sports_list'] = mis_deportes
                    st.success(f"¡{len(mis_deportes)} ligas cargadas!")
            except Exception as e:
                st.error(f"Error: {e}")

    st.header("2. Filtros")
    if st.session_state['sports_list']:
        sorted_labels = sorted(st.session_state['sports_list'].keys())
        selected_label = st.selectbox("Liga:", sorted_labels)
        sport_key = st.session_state['sports_list'][selected_label]
    else:
        st.warning("👆 Carga la lista primero.")
        sport_key = None

    # VUELVE EL SELECTOR DE REGIONES
    region_mode = st.selectbox("Región de Casas", ["Global (Todas)", "Europa (EU)", "USA (US)", "UK", "Australia (AU)"])
    
    # Traducción del selector a código API
    region_map = {
        "Global (Todas)": "us,uk,eu,au",
        "Europa (EU)": "eu",
        "USA (US)": "us",
        "UK": "uk",
        "Australia (AU)": "au"
    }
    selected_region = region_map[region_mode]

    market_type = st.selectbox("Mercado", ["h2h", "spreads", "totals"], index=0)
    
    # BAJA ESTO A 0 PARA PROBAR
    min_profit = st.slider("Beneficio Mínimo (%)", 0.0, 10.0, 0.0) 
    
    if st.button("🔎 Buscar Ahora"):
        run_analysis = True
    else:
        run_analysis = False

def get_arbitrage(outcomes, market_name):
    grouped = {}
    for book in outcomes:
        for market in book['markets']:
            if market['key'] == market_name:
                for outcome in market['outcomes']:
                    name = outcome['name']
                    price = outcome['price']
                    point = outcome.get('point', 'Moneyline')
                    if point not in grouped: grouped[point] = []
                    grouped[point].append({'bookie': book['title'], 'name': name, 'price': price})

    opps = []
    if market_name in ['h2h', 'totals']:
        for point, options in grouped.items():
            best = {}
            for opt in options:
                if opt['name'] not in best or opt['price'] > best[opt['name']]['price']:
                    best[opt['name']] = opt
            
            if len(best) == 2:
                sides = list(best.values())
                arb_sum = sum(1/s['price'] for s in sides)
                if arb_sum < 1.0:
                    profit = (1 - arb_sum) / arb_sum * 100
                    if profit >= min_profit:
                        opps.append({
                            "Mercado": market_name,
                            "Item": point,
                            "Beneficio %": round(profit, 2),
                            "Apuesta A": f"{sides[0]['bookie']} ({sides[0]['name']}) @ {sides[0]['price']}",
                            "Apuesta B": f"{sides[1]['bookie']} ({sides[1]['name']}) @ {sides[1]['price']}"
                        })
    return opps

if run_analysis and API_KEY and sport_key:
    with st.spinner(f'Analizando {sport_key} en {region_mode}...'):
        try:
            url = f'https://api.the-odds-api.com/v4/sports/{sport_key}/odds'
            params = {'api_key': API_KEY, 'regions': selected_region, 'markets': market_type, 'oddsFormat': 'decimal'}
            
            data = requests.get(url, params=params).json()
            
            all_opps = []
            for event in data:
                opps = get_arbitrage(event['bookmakers'], market_type)
                dt = datetime.strptime(event['commence_time'], "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H:%M")
                for op in opps:
                    op['Evento'] = f"{event['home_team']} vs {event['away_team']}"
                    op['Fecha'] = dt
                    all_opps.append(op)
            
            if all_opps:
                st.success(f"¡{len(all_opps)} Oportunidades!")
                st.dataframe(pd.DataFrame(all_opps)[['Fecha', 'Evento', 'Beneficio %', 'Apuesta A', 'Apuesta B']], use_container_width=True)
            else:
                st.warning("No se encontraron surebets con estos filtros.")
                
            # ZONA DEBUG: Si esto muestra datos, la API funciona bien
            with st.expander("🕵️ Ver Datos Crudos (Debug)"):
                st.write(f"Casas encontradas: {sum(len(e['bookmakers']) for e in data)}")
                st.json(data)

        except Exception as e:
            st.error(f"Error: {e}")
