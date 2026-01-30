import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN V14.2: BET365 + DAZN ---
st.set_page_config(layout="wide", page_title="Sniper V14 - Ecuador")
st.title("SCANNER V11.29 - FINALE FINALE")

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

    # --- FILTRO DE CASAS ---
    st.header("2. Tus Casas")
    
    # Lista ampliada con DAZN Bet
    casas_posibles = [
        "Pinnacle", "1xBet", "Betsson", "Betway", "BetOnline.ag", 
        "Betfair", "Marathon Bet", "Coolbet", "William Hill", 
        "Matchbook", "888sport", "Bet365", "DAZN Bet", 
        "BetOnline.ag", "Smarkets", "Dafabet", "Nordic Bet", "LeoVegas" , 
        "BetUS" , "MyBookie.ag" , "LowVig.ag" , "Matchbook" , "Smarkets"
    ]
    
    # SELECCIÓN AUTOMÁTICA (Incluye Bet365 y DAZN Bet)
    default_ecuador = [
        "Pinnacle", "1xBet", "Bet365", "Betsson", 
        "Betway", "Unibet", "Marathon Bet", "Coolbet", "DAZN Bet"
    ]
    
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
    # --- BLOQUE 2: MOTOR LÓGICO Y MATEMÁTICO ---

if btn_buscar and API_KEY and sport_key:
    # Usamos región GLOBAL para asegurar que salgan todas (Pinnacle, Bet365, etc)
    # El filtro lo haremos nosotros manualmente abajo con tu selección.
    region_code = "us,uk,eu,au" 
    
    with st.spinner(f"Escaneando {sport_key} en busca de oportunidades..."):
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
            
            # 1. Validación de Error de API (Bloqueo de mercado)
            if isinstance(data, dict) and 'message' in data:
                if 'not supported' in data['message']:
                    st.error(f"🚫 ERROR: El mercado '{m_label}' no está disponible para este deporte o tu plan.")
                    st.info("💡 Intenta con 'Ganador (H2H)' o 'Hándicaps'.")
                    st.stop()
            
            # 2. Procesamiento Matemático
            if isinstance(data, list):
                oportunidades = []
                
                for ev in data:
                    # Limpieza de fecha
                    fecha = ev.get('commence_time','').replace('T',' ').replace('Z','')
                    evento = f"{ev['home_team']} vs {ev['away_team']}"
                    
                    # --- FASE A: AGRUPAMIENTO + FILTRADO ---
                    grupos = {}
                    
                    for book in ev['bookmakers']:
                        casa_nombre = book['title']
                        
                        # === FILTRO DE CASAS ===
                        # Solo procesamos si la casa está en tu lista 'mis_casas'
                        es_permitida = False
                        for permitido in mis_casas:
                            # Usamos coincidencia parcial (ej: "Unibet" acepta "Unibet (UK)")
                            if permitido.lower() in casa_nombre.lower():
                                es_permitida = True
                                break
                        
                        if not es_permitida:
                            continue # Si no está en tu lista, la ignoramos
                            
                        # Si pasa el filtro, extraemos sus cuotas
                        for m in book['markets']:
                            if m['key'] == m_val:
                                for out in m['outcomes']:
                                    # Agrupamos por Punto (para Totales/Handicaps) o 'Moneyline'
                                    pt = out.get('point', 'Moneyline')
                                    
                                    if pt not in grupos: grupos[pt] = []
                                    
                                    grupos[pt].append({
                                        'bookie': casa_nombre,
                                        'name': out['name'],
                                        'price': out['price']
                                    })
                    
                    # --- FASE B: CÁLCULO DE SUREBETS ---
                    for pt, cuotas in grupos.items():
                        # 1. Encontrar la MEJOR cuota para cada resultado posible
                        mejor_opcion = {}
                        for c in cuotas:
                            sel = c['name']
                            if sel not in mejor_opcion or c['price'] > mejor_opcion[sel]['price']:
                                mejor_opcion[sel] = c
                        
                        # 2. Verificar si tenemos suficientes lados (mínimo 2)
                        if len(mejor_opcion) >= 2:
                            finales = list(mejor_opcion.values())
                            suma_inversa = sum(1/x['price'] for x in finales)
                            
                            # 3. Fórmula de Arbitraje (Suma < 1.0 = Ganancia)
                            if suma_inversa < 1.0:
                                ben = (1 - suma_inversa) / suma_inversa * 100
                                
                                if ben >= min_profit:
                                    # Validación extra: Evitar "Over vs Over"
                                    nombres = [x['name'] for x in finales]
                                    es_valido = True
                                    if m_val == 'totals' and nombres[0] == nombres[1]: 
                                        es_valido = False
                                    
                                    if es_valido:
                                        # Formato visual de la apuesta
                                        detalles = " | ".join([f"{x['name']} ({x['bookie']}) @ {x['price']}" for x in finales])
                                        
                                        oportunidades.append({
                                            "Fecha": fecha,
                                            "Evento": evento,
                                            "Mercado/Sel": pt,
                                            "Beneficio": f"{ben:.2f}%",
                                            "Apuestas": detalles
                                        })
                
                # --- RESULTADOS ---
                if oportunidades:
                    st.success(f"¡{len(oportunidades)} Oportunidades Encontradas!")
                    st.dataframe(pd.DataFrame(oportunidades), use_container_width=True)
                else:
                    st.warning("No se encontraron oportunidades en las casas seleccionadas.")
                    
                with st.expander("Ver Datos Crudos (API)"):
                    st.json(data)

        except Exception as e:
            st.error(f"Error Crítico: {e}")
