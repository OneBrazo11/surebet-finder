import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --- CONFIGURACION V12 ---
st.set_page_config(layout="wide", page_title="SCANNER V11")
st.title("🎯 SCANNER V11 - FINALE Precisión Máxima")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("1. Credenciales")
    raw_key = st.text_input("API Key", type="password")
    API_KEY = raw_key.strip() if raw_key else ""
    
    # Carga de Deportes
    if 'sports_data' not in st.session_state:
        st.session_state['sports_data'] = {}
        
    if st.button("🔄 Cargar Deportes"):
        if not API_KEY:
            st.error("Falta API Key")
        else:
            try:
                r = requests.get(f"https://api.the-odds-api.com/v4/sports/?apiKey={API_KEY}")
                data = r.json()
                if isinstance(data, list):
                    clean = {}
                    for x in data:
                        if x['active']:
                            l = f"{x['group']} - {x['title']}"
                            clean[l] = x['key']
                    st.session_state['sports_data'] = clean
                    st.success(f"¡{len(clean)} Ligas!")
                else:
                    st.error(f"Error: {data}")
            except Exception as e:
                st.error(f"Error Conexión: {e}")

    # Filtros
    sport_key = None
    if st.session_state['sports_data']:
        lista = sorted(st.session_state['sports_data'].keys())
        sel = st.selectbox("Liga:", lista)
        sport_key = st.session_state['sports_data'][sel]

    # Regiones
    reg_map = {
        "Global (Todas)": "us,uk,eu,au",
        "Europa (EU)": "eu",
        "USA (US)": "us",
        "Latam (AU)": "au"
    }
    region_label = st.selectbox("Región:", list(reg_map.keys()))
    region_code = reg_map[region_label]

    # Mercados (Todos disponibles, aunque la API bloquee algunos)
    st.write("---")
    market_map = {
        "🏆 Ganador (H2H)": "h2h",
        "🏀/🏈 Hándicaps": "spreads",
        "🔢 Totales (Alta/Baja)": "totals",
        "⚠️ Doble Oportunidad": "double_chance",
        "⚠️ Empate no Válido": "draw_no_bet"
    }
    market_label = st.selectbox("Mercado:", list(market_map.keys()))
    market_val = market_map[market_label]

    min_profit = st.slider("Min %:", 0.0, 10.0, 0.0)
    btn_buscar = st.button("🔎 BUSCAR")
    # --- MOTOR LÓGICO ---
if btn_buscar and API_KEY and sport_key:
    with st.spinner(f"Escaneando {market_label}..."):
        try:
            url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
            params = {
                'apiKey': API_KEY,
                'regions': region_code,
                'markets': market_val,
                'oddsFormat': 'decimal'
            }
            
            r = requests.get(url, params=params)
            data = r.json()
            
            # 1. Filtro de Error de API (Si el mercado está bloqueado)
            if isinstance(data, dict) and 'message' in data:
                msg = data['message']
                if 'not supported' in msg or 'INVALID_MARKET' in str(data):
                    st.error(f"🚫 BLOQUEADO: Tu plan de API no permite '{market_label}'.")
                    st.info("💡 Solución: Usa Ganador (H2H), Hándicaps o Totales.")
                    st.stop()
            
            # 2. Procesamiento de Oportunidades
            if isinstance(data, list):
                oportunidades = []
                
                for ev in data:
                    fecha = ev.get('commence_time','').replace('T',' ').replace('Z','')
                    evento = f"{ev['home_team']} vs {ev['away_team']}"
                    
                    # AGRUPAMIENTO INTELIGENTE (Crucial para Spreads/Totals)
                    # Agrupamos por 'point'. Ej: Todas las cuotas de Over 210.5 juntas.
                    # Si es H2H, el punto es 'Moneyline'.
                    grupos = {}
                    
                    for book in ev['bookmakers']:
                        for m in book['markets']:
                            if m['key'] == market_val:
                                for out in m['outcomes']:
                                    # La clave es el punto (ej: 2.5) o 'Main' si no tiene punto
                                    punto = out.get('point', 'Moneyline')
                                    
                                    if punto not in grupos: grupos[punto] = []
                                    
                                    grupos[punto].append({
                                        'bookie': book['title'],
                                        'name': out['name'],
                                        'price': out['price']
                                    })
                    
                    # ANALISIS DE ARBITRAJE POR GRUPO
                    for pt, lista_cuotas in grupos.items():
                        # Buscar la MEJOR cuota para cada opción (ej: Mejor Over y Mejor Under)
                        mejor_por_opcion = {}
                        for item in lista_cuotas:
                            nombre_opcion = item['name']
                            if nombre_opcion not in mejor_por_opcion:
                                mejor_por_opcion[nombre_opcion] = item
                            else:
                                if item['price'] > mejor_por_opcion[nombre_opcion]['price']:
                                    mejor_por_opcion[nombre_opcion] = item
                        
                        # Validar si hay suficientes lados para apostar
                        # Minimo 2 lados (A vs B)
                        if len(mejor_por_opcion) >= 2:
                            finales = list(mejor_por_opcion.values())
                            suma_arb = sum(1/x['price'] for x in finales)
                            
                            # ¿Es rentable?
                            if suma_arb < 1.0:
                                beneficio = (1 - suma_arb) / suma_arb * 100
                                
                                if beneficio >= min_profit:
                                    # Texto de apuesta
                                    txt = " | ".join([f"{x['name']} ({x['bookie']}) @ {x['price']}" for x in finales])
                                    
                                    oportunidades.append({
                                        "Fecha": fecha,
                                        "Evento": evento,
                                        "Selección": pt, # Muestra el Handicap o Total
                                        "Beneficio": f"{beneficio:.2f}%",
                                        "Apuestas": txt
                                    })
                
                if oportunidades:
                    st.success(f"¡{len(oportunidades)} Oportunidades!")
                    # --- DETECTOR DE CASAS ---
                    casas_encontradas = set()
                    for ev in data:
                        for book in ev['bookmakers']:
                            casas_encontradas.add(book['title'])
                    st.info(f"Casas escaneadas en esta búsqueda: {', '.join(casas_encontradas)}")
                    # -------------------------
                    st.dataframe(pd.DataFrame(oportunidades), use_container_width=True)
                else:
                    st.warning("No hay oportunidades ahora mismo.")
                
                with st.expander("Debug"):
                    st.json(data)

        except Exception as e:
            st.error(f"Error: {e}")
