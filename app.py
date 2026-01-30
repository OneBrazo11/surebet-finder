import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --- CONFIGURACION ---
st.set_page_config(layout="wide")
st.title("Sniper V8.6 - Modo Seguro")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("1. Credenciales")
    raw = st.text_input("API Key", type="password")
    
    # Limpieza segura
    if raw:
        API_KEY = raw.strip()
    else:
        API_KEY = ""
    
    # --- CALCULADORA ---
    with st.expander("Calculadora", expanded=True):
        m1 = "2 Opciones (Tenis)"
        m2 = "3 Opciones (Futbol)"
        modo = st.radio("Modo:", [m1, m2])
        
        bank = st.number_input("Bank ($)", value=100.0)
        
        if modo == m1:
            # MODO 2 VIAS
            cA = st.number_input("Cuota A", value=2.0)
            cB = st.number_input("Cuota B", value=2.0)
            
            if cA > 0 and cB > 0:
                inv = (1/cA + 1/cB)
                gana = (bank / inv) - bank
                
                st.write(f"Ganancia: ${gana:.2f}")
                
                sA = (bank * (1/cA)) / inv
                sB = (bank * (1/cB)) / inv
                
                c1, c2 = st.columns(2)
                c1.metric("Apostar A", f"${sA:.0f}")
                c2.metric("Apostar B", f"${sB:.0f}")

        else:
            # MODO 3 VIAS
            cL = st.number_input("Local", value=2.5)
            cE = st.number_input("Empate", value=3.2)
            cV = st.number_input("Visita", value=3.0)
            
            if cL > 0 and cE > 0 and cV > 0:
                inv = (1/cL + 1/cE + 1/cV)
                gana = (bank / inv) - bank
                
                st.write(f"Ganancia: ${gana:.2f}")
                
                sL = (bank * (1/cL)) / inv
                sE = (bank * (1/cE)) / inv
                sV = (bank * (1/cV)) / inv
                
                k1, k2, k3 = st.columns(3)
                k1.metric("L", f"${sL:.0f}")
                k2.metric("E", f"${sE:.0f}")
                k3.metric("V", f"${sV:.0f}")

    # --- CARGA LIGAS ---
    st.header("2. Escaner")
    
    # Inicializar memoria
    if 'sports' not in st.session_state:
        st.session_state['sports'] = {}

    if API_KEY:
        if st.button("Cargar Ligas"):
            try:
                # URL partida para seguridad
                host = "https://api.the-odds-api.com"
                ruta = "/v4/sports/"
                url = f"{host}{ruta}"
                
                # Parametros
                p = {}
                p['apiKey'] = API_KEY
                
                r = requests.get(url, params=p)
                data = r.json()
                
                if isinstance(data, list):
                    temp = {}
                    for x in data:
                        if x['active']:
                            k = x['key']
                            t = x['title']
                            g = x['group']
                            nom = f"{g} - {t}"
                            temp[nom] = k
                            
                    st.session_state['sports'] = temp
                    st.success("Exito")
                else:
                    st.error(f"Error: {data}")
            except Exception as e:
                st.error(f"Fallo: {e}")

    # --- FILTROS ---
    sport_key = None
    if st.session_state['sports']:
        lista = sorted(st.session_state['sports'].keys())
        sel = st.selectbox("Liga:", lista)
        sport_key = st.session_state['sports'][sel]

    # Regiones
    regs = ["Global (Todas)", "Europa (EU)", "USA (US)", "Latam (AU)"]
    r_sel = st.selectbox("Region", regs)
    
    mapa = {}
    mapa["Global (Todas)"] = "us,uk,eu,au"
    mapa["Europa (EU)"] = "eu"
    mapa["USA (US)"] = "us"
    mapa["Latam (AU)"] = "au"
    
    # Mercados
    mercs = ["h2h", "spreads", "totals", "draw_no_bet", "double_chance"]
    m_tipo = st.selectbox("Mercado", mercs)
    
    min_p = st.slider("Min %", 0.0, 10.0, 0.0) 
    
    btn = st.button("Buscar")

# --- LOGICA ---
def escanear(libros, tipo_mercado):
    grupo = {}
    
    for l in libros:
        # l es el bookmaker
        bookie = l['title']
        
        for m in l['markets']:
            # Verificamos mercado
            clave = m['key']
            
            # AQUI FALLABA ANTES, AHORA ESTA SEGURO:
            if clave == tipo_mercado:
                
                for out in m['outcomes']:
                    nom = out['name']
                    pr = out['price']
                    pt = out.get('point', 'ML')
                    
                    if pt not in grupo:
                        grupo[pt] = []
                    
                    item = {}
                    item['bookie'] = bookie
                    item['name'] = nom
                    item['price'] = pr
                    
                    grupo[pt].append(item)
    
    filas = []
    
    for punto, lista in grupo.items():
        # Buscar mejor cuota
        mejores = {}
        for x in lista:
            n = x['name']
            p = x['price']
            
            if n not in mejores:
                mejores[n] = x
            elif p > mejores[n]['price']:
                mejores[n] = x
        
        # Validar
        count = len(mejores)
        if count >= 2:
            objs = list(mejores.values())
            suma = 0
            for o in objs:
                suma += (1 / o['price'])
            
            if suma < 1.0:
                # Validacion estricta partida
                ok = False
                
                if tipo_mercado == 'h2h':
                    if count >= 2: ok = True
                
                if tipo_mercado == 'double_chance':
                    if count >= 3: ok = True
                    
                if tipo_mercado in ['spreads', 'totals', 'draw_no_bet']:
                    if count >= 2: ok = True
                
                if ok:
                    margen = (1 - suma) / suma
                    pct = margen * 100
                    
                    if pct >= min_p:
                        # Crear texto
                        txts = []
                        for b in objs:
                            b_n = b['bookie']
                            b_p = b['price']
                            b_s = b['name']
                            t = f"{b_s}: {b_n} @ {b_p}"
                            txts.append(t)
                        
                        fin = {}
                        fin['Mercado'] = tipo_mercado
                        fin['Sel'] = punto
                        fin['%'] = round(pct, 2)
                        fin['Apuestas'] = " | ".join(txts)
                        
                        filas.append(fin)
    return filas

# --- EJECUCION ---
if btn and API_KEY and sport_key:
    with st.spinner("Buscando..."):
        try:
            # Construir URL
            base = "https://api.the-odds-api.com"
            camino = f"/v4/sports/{sport_key}/odds"
            link = f"{base}{camino}"
            
            # Parametros
            reg_code = mapa[r_sel]
            
            par = {}
            par['apiKey'] = API_KEY
            par['regions'] = reg_code
            par['markets'] = m_tipo
            par['oddsFormat'] = 'decimal'
            
            res = requests.get(link, params=par)
            datos = res.json()
            
            if not isinstance(datos, list):
                st.error(f"Error: {datos}")
            else:
                todo = []
                for ev in datos:
                    h = ev['home_team']
                    a = ev['away_team']
                    tit = f"{h} vs {a}"
                    
                    # Fecha
                    raw = ev.get('commence_time', '')
                    try:
                        f1 = "%Y-%m-%dT%H:%M:%SZ"
                        dt = datetime.strptime(raw, f1)
                        f2 = "%Y-%m-%d %H:%M"
                        fecha = dt.strftime(f2)
                    except:
                        fecha = raw

                    # Procesar
                    books = ev['bookmakers']
                    gaps = escanear(books, m_tipo)
                    
                    for g in gaps:
                        g['Evento'] = tit
                        g['Fecha'] = fecha
                        todo.append(g)
                
                if todo:
                    st.success(f"{len(todo)} Oportunidades")
                    df = pd.DataFrame(todo)
                    
                    cols = ['Fecha','Evento','%','Apuestas']
                    st.dataframe(df[cols], use_container_width=True)
                else:
                    st.warning("Nada por ahora")
                
                with st.expander("Ver Datos"):
                    st.json(datos)

        except Exception as e:
            st.error(f"Error Critico: {e}")
