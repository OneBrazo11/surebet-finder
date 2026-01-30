import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN V14: FILTRO ECUADOR ---
st.set_page_config(layout="wide", page_title="Sniper V14 - Ecuador")
st.title("🇪🇨 Sniper V14 - Filtro Personalizado")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("1. Configuración")
    raw_key = st.text_input("API Key", type="password")
    API_KEY = raw_key.strip() if raw_key else ""
    
    # Carga Inicial
    if 'sports_data' not in st.session_state:
        st.session_state['sports_data'] = {}

    if st.button("🔄 Cargar Deportes"):
        if API_KEY:
            try:
                r = requests.get(f"https://api.the-odds-api.com/v4/sports/?apiKey={API_KEY}")
                data = r.json()
                if isinstance(data, list):
                    clean = {f"{x['group']} - {x['title']}": x['key'] for x in data if x['active']}
                    st.session_state['sports_data'] = clean
                    st.success("¡Deportes Actualizados!")
                else:
                    st.error(f"Error: {data}")
            except Exception as e:
                st.error(f"Error: {e}")

    # --- SELECTOR DE DEPORTE ---
    sport_key = None
    if st.session_state['sports_data']:
        lista = sorted(st.session_state['sports_data'].keys())
        sel = st.selectbox("Liga:", lista)
        sport_key = st.session_state['sports_data'][sel]

    # --- FILTRO DE CASAS (LA MAGIA) ---
    st.header("2. Tus Casas")
    
    # Lista de TODAS las casas que detectaste en el escaneo + las que te interesan
    # He pre-seleccionado las que funcionan internacionalmente o en Latam
    casas_posibles = [
        "Pinnacle", "1xBet", "Betsson", "Betway", "Unibet", 
        "Betfair", "Marathon Bet", "Coolbet", "William Hill", 
        "Matchbook", "888sport", "Bet365", "BetOnline.ag",
        "Smarkets", "Dafabet", "Nordic Bet", "LeoVegas"
    ]
    
    # Selección por defecto (Las top para Ecuador)
    default_ecuador = ["Pinnacle", "1xBet", "Betsson", "Betway", "Unibet", "Marathon Bet", "Coolbet"]
    
    # Widget Multiselect: Tú decides cuáles activar
    mis_casas = st.multiselect(
        "Casas Activas:", 
        options=casas_posibles, 
        default=default_ecuador
    )
    
    st.caption(f"Buscando en {len(mis_casas)} casas seleccionadas.")

    # --- RESTO DE FILTROS ---
    st.header("3. Mercado")
    market_map = {
        "🏆 Ganador (H2H)": "h2h",
        "🏀/🏈 Hándicaps": "spreads",
        "🔢 Totales": "totals",
        "⚠️ Doble Oportunidad": "double_chance",
        "⚠️ Empate no Válido": "draw_no_bet"
    }
    m_label = st.selectbox("Tipo:", list(market_map.keys()))
    m_val = market_map[m_label]
    
    min_profit = st.slider("Min %:", 0.0, 10.0, 0.0)
    btn_buscar = st.button("🔎 BUSCAR OPORTUNIDADES")
    # --- MOTOR PRINCIPAL ---
if btn_buscar and API_KEY and sport_key:
    # Usamos región GLOBAL para asegurar que salgan todas (Pinnacle, etc)
    # El filtro lo haremos nosotros manualmente abajo.
    region_code = "us,uk,eu,au" 
    
    with st.spinner(f"Escaneando {sport_key}..."):
        try:
            url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
            params = {
                'apiKey': API_KEY,
                'regions': region_code,
                'markets': m_val,
                'oddsFormat': 'decimal'
            }
            
            r = requests.get(url, params=params)
            data = r.json()
            
            # 1. Validación de Error de API
            if isinstance(data, dict) and 'message' in data:
                if 'not supported' in data['message']:
                    st.error(f"Este deporte no soporta '{m_label}' en tu plan.")
                    st.stop()
            
            # 2. Procesamiento
            if isinstance(data, list):
                oportunidades = []
                
                for ev in data:
                    fecha = ev.get('commence_time','').replace('T',' ').replace('Z','')
                    evento = f"{ev['home_team']} vs {ev['away_team']}"
                    
                    # --- AGRUPAMIENTO + FILTRADO ---
                    grupos = {}
                    
                    for book in ev['bookmakers']:
                        # AQUÍ ESTÁ EL FILTRO DE ECUADOR:
                        # Si la casa NO está en tu lista seleccionada, la saltamos.
                        # Usamos "in" para que coincidencia parcial funcione (ej: "Unibet (UK)" entra en "Unibet")
                        casa_nombre = book['title']
                        es_permitida = False
                        
                        for permitido in mis_casas:
                            if permitido.lower() in casa_nombre.lower():
                                es_permitida = True
                                break
                        
                        if not es_permitida:
                            continue # Saltamos esta casa
                            
                        # Si pasa el filtro, procesamos sus cuotas
                        for m in book['markets']:
                            if m['key'] == m_val:
                                for out in m['outcomes']:
                                    pt = out.get('point', 'Moneyline')
                                    if pt not in grupos: grupos[pt] = []
                                    grupos[pt].append({
                                        'bookie': casa_nombre,
                                        'name': out['name'],
                                        'price': out['price']
                                    })
                    
                    # --- CÁLCULO DE SUREBETS ---
                    for pt, cuotas in grupos.items():
                        mejor = {}
                        for c in cuotas:
                            sel = c['name']
                            if sel not in mejor or c['price'] > mejor[sel]['price']:
                                mejor[sel] = c
                        
                        if len(mejor) >= 2:
                            finales = list(mejor.values())
                            suma = sum(1/x['price'] for x in finales)
                            
                            if suma < 1.0:
                                ben = (1 - suma) / suma * 100
                                if ben >= min_profit:
                                    # Validación extra para no mezclar Over vs Over
                                    nombres = [x['name'] for x in finales]
                                    valido = True
                                    if m_val == 'totals' and nombres[0] == nombres[1]: valido = False
                                    
                                    if valido:
                                        txt = " | ".join([f"{x['name']} ({x['bookie']}) @ {x['price']}" for x in finales])
                                        oportunidades.append({
                                            "Fecha": fecha,
                                            "Evento": evento,
                                            "Sel": pt,
                                            "Beneficio": f"{ben:.2f}%",
                                            "Apuestas": txt
                                        })
                
                if oportunidades:
                    st.success(f"¡{len(oportunidades)} Oportunidades Válidas!")
                    st.dataframe(pd.DataFrame(oportunidades), use_container_width=True)
                else:
                    st.warning("No hay oportunidades en TUS casas seleccionadas.")
                    
                with st.expander("Ver Datos Crudos"):
                    st.json(data)

        except Exception as e:
            st.error(f"Error: {e}")
