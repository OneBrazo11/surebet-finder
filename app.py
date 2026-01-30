import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN BÁSICA ---
st.set_page_config(layout="wide", page_title="Sniper V11")
st.title("🎯 Sniper V11 - FINALE")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("Configuración")
    
    # 1. API KEY
    raw_key = st.text_input("API Key", type="password")
    API_KEY = raw_key.strip() if raw_key else ""
    
    # 2. CARGAR LIGAS
    if 'sports_data' not in st.session_state:
        st.session_state['sports_data'] = {}
    
    if st.button("🔄 Cargar Deportes"):
        if not API_KEY:
            st.error("Pon tu API Key primero.")
        else:
            try:
                # Url oficial
                url = "https://api.the-odds-api.com/v4/sports/"
                params = {'apiKey': API_KEY}
                r = requests.get(url, params=params)
                data = r.json()
                
                if isinstance(data, list):
                    clean_dict = {}
                    for x in data:
                        if x['active']:
                            label = f"{x['group']} - {x['title']}"
                            clean_dict[label] = x['key']
                    
                    st.session_state['sports_data'] = clean_dict
                    st.success(f"¡{len(clean_dict)} Ligas Activas!")
                else:
                    st.error(f"Error: {data}")
            except Exception as e:
                st.error(f"Error de conexión: {e}")

    # 3. FILTROS
    sport_key = None
    if st.session_state['sports_data']:
        sorted_list = sorted(st.session_state['sports_data'].keys())
        selection = st.selectbox("Liga / Deporte:", sorted_list)
        sport_key = st.session_state['sports_data'][selection]
    
    # Regiones
    reg_map = {
        "Global (Todas)": "us,uk,eu,au",
        "Europa (EU)": "eu",
        "USA (US)": "us",
        "Latam (AU)": "au"
    }
    region_label = st.selectbox("Región:", list(reg_map.keys()))
    region_val = reg_map[region_label]
    
    # Mercados solicitados
    markets_list = [
        "h2h",              # Ganador
        "spreads",          # Handicaps
        "totals",           # Altas/Bajas
        "draw_no_bet",      # Empate no valido
        "double_chance"     # Doble oportunidad
    ]
    market_val = st.selectbox("Mercado:", markets_list)
    
    min_profit = st.slider("Beneficio Min %:", 0.0, 10.0, 0.0)
    
    btn_run = st.button("🔎 BUSCAR AHORA")
    # --- LÓGICA PURA ---
if btn_run and API_KEY and sport_key:
    with st.spinner("Escaneando mercado..."):
        try:
            # Construcción URL
            base = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
            params = {
                'apiKey': API_KEY,
                'regions': region_val,
                'markets': market_val,
                'oddsFormat': 'decimal'
            }
            
            response = requests.get(base, params=params)
            odds_data = response.json()
            
            # Verificación básica
            if not isinstance(odds_data, list):
                st.error(f"API Error: {odds_data}")
            else:
                opportunities = []
                
                for event in odds_data:
                    # Datos del evento
                    ev_name = f"{event['home_team']} vs {event['away_team']}"
                    
                    # Fecha segura
                    raw_date = event.get('commence_time', '')
                    fecha = raw_date.replace('T', ' ').replace('Z', '')
                    
                    # Agrupar cuotas
                    grouped_odds = {}
                    
                    for book in event['bookmakers']:
                        for m in book['markets']:
                            if m['key'] == market_val:
                                for out in m['outcomes']:
                                    # La clave de agrupación: Point (handicap/total) o Moneyline
                                    key_point = out.get('point', 'Moneyline')
                                    
                                    if key_point not in grouped_odds:
                                        grouped_odds[key_point] = []
                                    
                                    info = {
                                        'bookie': book['title'],
                                        'name': out['name'],
                                        'price': out['price']
                                    }
                                    grouped_odds[key_point].append(info)
                    
                    # Analizar cada grupo
                    for g_key, options_list in grouped_odds.items():
                        
                        # Encontrar MEJOR cuota por selección
                        best_in_market = {}
                        for opt in options_list:
                            sel_name = opt['name']
                            if sel_name not in best_in_market:
                                best_in_market[sel_name] = opt
                            else:
                                if opt['price'] > best_in_market[sel_name]['price']:
                                    best_in_market[sel_name] = opt
                        
                        # Verificar arbitraje (mínimo 2 lados)
                        if len(best_in_market) >= 2:
                            final_odds = list(best_in_market.values())
                            arb_sum = sum(1 / item['price'] for item in final_odds)
                            
                            # ¿Es Surebet?
                            if arb_sum < 1.0:
                                profit = (1 - arb_sum) / arb_sum * 100
                                
                                if profit >= min_profit:
                                    bets_text = []
                                    for bo in final_odds:
                                        txt = f"{bo['name']} ({bo['bookie']}) @ {bo['price']}"
                                        bets_text.append(txt)
                                    
                                    full_bet_str = "  |  ".join(bets_text)
                                    
                                    opportunities.append({
                                        "Fecha": fecha,
                                        "Evento": ev_name,
                                        "Selección": g_key,
                                        "Beneficio": f"{profit:.2f}%",
                                        "Apuestas": full_bet_str
                                    })
                
                # Mostrar resultados
                if opportunities:
                    st.success(f"¡{len(opportunities)} Oportunidades Encontradas!")
                    df = pd.DataFrame(opportunities)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.warning("No se encontraron surebets con estos filtros.")
                    
                with st.expander("Ver respuesta de API (Debug)"):
                    st.write(f"Eventos analizados: {len(odds_data)}")
                    st.json(odds_data)

        except Exception as e:
            st.error(f"Error Crítico: {e}")
