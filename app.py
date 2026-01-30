import streamlit as st
import requests
import pandas as pd

st.set_page_config(layout="wide", page_title="Inspector V13")
st.title("🕵️ V13 - Inspector de Casas de Apuestas")

# --- SIDEBAR ---
with st.sidebar:
    st.header("Configuración")
    api_input = st.text_input("API Key", type="password")
    API_KEY = api_input.strip() if api_input else ""
    
    if st.button("🔄 Cargar Deportes"):
        if API_KEY:
            try:
                r = requests.get(f"https://api.the-odds-api.com/v4/sports/?apiKey={API_KEY}")
                data = r.json()
                if isinstance(data, list):
                    # Filtramos solo los activos
                    sports = {f"{x['group']} - {x['title']}": x['key'] for x in data if x['active']}
                    st.session_state['sports'] = sports
                    st.success("Deportes cargados")
                else:
                    st.error("Error cargando deportes")
            except:
                st.error("Error de conexión")

    # Selectores
    sport_key = None
    if 'sports' in st.session_state and st.session_state['sports']:
        sorted_sports = sorted(st.session_state['sports'].keys())
        sel = st.selectbox("Deporte:", sorted_sports)
        sport_key = st.session_state['sports'][sel]

    # AQUÍ ESTÁ LA CLAVE: PROBAR REGIONES
    st.info("💡 Prueba 'Europa' para ver Pinnacle/1xBet")
    reg_map = {
        "Europa (eu) - RECOMENDADO": "eu",
        "Reino Unido (uk)": "uk",
        "Global (Todas)": "us,uk,eu,au",
        "Latam/Australia (au)": "au",
        "USA (us)": "us"
    }
    region_label = st.selectbox("Región a Escanear:", list(reg_map.keys()))
    region_code = reg_map[region_label]

    btn_scan = st.button("🕵️ VER QUÉ CASAS HAY")

# --- LÓGICA DE INSPECCIÓN ---
if btn_scan and API_KEY and sport_key:
    st.subheader(f"Analizando casas en: {region_label}...")
    
    try:
        # Pedimos solo H2H para gastar poco cupo y ver las casas
        url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
        params = {
            'apiKey': API_KEY,
            'regions': region_code,
            'markets': 'h2h', 
            'oddsFormat': 'decimal'
        }
        
        r = requests.get(url, params=params)
        data = r.json()
        
        if isinstance(data, list):
            # Recolectar TODAS las casas que aparecen
            casas_encontradas = set()
            eventos_analizados = len(data)
            
            for evento in data:
                for book in evento['bookmakers']:
                    casas_encontradas.add(book['title'])
            
            # MOSTRAR RESULTADOS
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Eventos Leídos", eventos_analizados)
            with col2:
                st.metric("Casas Encontradas", len(casas_encontradas))
            
            st.divider()
            
            if casas_encontradas:
                st.success("✅ Casas detectadas en esta región:")
                
                # Convertir a lista y ordenar
                lista_casas = sorted(list(casas_encontradas))
                
                # Buscador visual de tus favoritas
                favoritas = ["Pinnacle", "1xBet", "Betano", "Bet365", "Betway", "Stake", "Betsson", "Unibet"]
                
                for casa in lista_casas:
                    # Chequeo si es una de tus favoritas
                    es_top = any(fav.lower() in casa.lower() for fav in favoritas)
                    
                    if es_top:
                        st.markdown(f"### ⭐ **{casa}**")
                    else:
                        st.write(f"- {casa}")
            else:
                st.warning("⚠️ No se encontraron casas. Intenta cambiar de Región o de Deporte.")
                
        else:
            st.json(data)

    except Exception as e:
        st.error(f"Error: {e}")
