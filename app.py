import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests

# 1. CONFIGURACIÓN DE LA PÁGINA EN MODO ANCHO
st.set_page_config(page_title="Dashboard Generación Complejo Técnico Mejillones", layout="wide")

# FORZAR TEMA CLARO ABSOLUTO + ESTILOS DE IMPRESIÓN PROFESIONAL (PDF)
st.markdown("""
    <style>
        .stApp { background-color: #FFFFFF !important; color: #1F2937 !important; }
        .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
        h1, h2, h3, h4, p, span, label { color: #111827 !important; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }
        .stButton>button { background-color: #3B66FF !important; color: white !important; border-radius: 4px; border: none; }
        .stButton>button:hover { background-color: #2651E6 !important; color: white !important; }
        .stDataFrame, div[data-testid="stTable"] { background-color: #F9FAFB !important; border: 1px solid #E5E7EB; }
        .metric-card { background-color: #F9FAFB; border: 1px solid #E5E7EB; padding: 1rem; border-radius: 6px; text-align: left; box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05); }
        .metric-label { font-size: 0.85rem !important; color: #4B5563 !important; font-weight: 600; text-transform: uppercase; margin-bottom: 0.25rem; }
        .metric-value { font-size: 1.8rem !important; color: #111827 !important; font-weight: 700; line-height: 1.2; }
        .metric-subtext { font-size: 0.85rem !important; color: #2563EB !important; font-weight: 600; margin-top: 0.25rem; }
        .metric-subtext-red { font-size: 0.85rem !important; color: #DC2626 !important; font-weight: 600; margin-top: 0.25rem; }
        
        @media print {
            header, footer, nav, .stSidebar, [data-testid="stSidebar"], .no-print { display: none !important; }
            .stApp { background-color: white !important; }
            .block-container { padding: 0 !important; margin: 0 !important; }
        }
    </style>
""", unsafe_allow_html=True)

st.title("Dashboard generación complejo térmico mejillones")
st.markdown("Visualización e ingeniería de datos para el control de despacho y desviaciones de potencia.")

# --- ENLACES DE GOOGLE SHEETS ---
URL_GOOGLE_SHEETS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTLvFug7yx0-2rF1nwhWt8q4l8mpGtO7Xpi3BK6lEvLw-L19bDQZIFXc4Fu63WHvip6PqarXxC1VJR3/pub?output=csv"
URL_API_BITACORA = "https://script.google.com/macros/library/d/1l0zQncbODrFu_TewveQeSSte16mPdqqyiISj84wKfpbeAzICMAFF7Dvs/2"

@st.cache_data(ttl=10)
def cargar_datos_produccion():
    try:
        df = pd.read_csv(URL_GOOGLE_SHEETS, on_bad_lines="skip", engine="python")
        st.sidebar.success("Conexión activa: Datos desde Google Sheets")
    except Exception as e:
        df = pd.read_csv("Planilla_Consolidada_GoogleSheets.csv", on_bad_lines="skip", engine="python")
        st.sidebar.warning("Modo offline: Cargando copia local de contingencia")
        
    df.columns = df.columns.str.strip()
    columnas_fecha = [col for col in df.columns if 'fech' in col.lower()]
    if columnas_fecha: 
        df = df.rename(columns={columnas_fecha[0]: 'Fecha'})
    
    df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
    df = df.dropna(subset=['Fecha'])
    
    for col in df.columns:
        if col != 'Fecha':
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.replace(' ', '').str.replace(',', '.')
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    return df

def normalizar_fecha_api(fecha_raw):
    if not fecha_raw: return ""
    str_f = str(fecha_raw).strip()
    if "T" in str_f:
        try:
            dt = datetime.strptime(str_f.split("T")[0], "%Y-%m-%d")
            return dt.strftime("%d/%m/%Y")
        except: pass
    return str_f

def normalizar_hora_api(hora_raw):
    if not hora_raw: return "00:00"
    str_h = str(hora_raw).strip()
    if "T" in str_h:
        try:
            componente_hora = str_h.split("T")[1].replace("Z", "")
            return componente_hora[:5]
        except: pass
    return str_h[:5]

def obtener_bitacora_global():
    try:
        respuesta = requests.get(URL_API_BITACORA, timeout=10)
        if respuesta.status_code == 200:
            raw_data = respuesta.json()
            if raw_data:
                df = pd.DataFrame(raw_data)
                df['fecha'] = df['fecha'].apply(normalizar_fecha_api)
                df['hora'] = df['hora'].apply(normalizar_hora_api)
                return df
    except:
        pass
    return pd.DataFrame(columns=["id", "fecha", "hora", "unidad", "autor", "comentario"])

try:
    df_metrics = cargar_datos_produccion()
    columnas = list(df_metrics.columns)
    unidades_detectadas = {}
    
    mapeo_estricto = {
        "Angamos Unidad 1": ("ANG01-R", "ANG01-P"),
        "Angamos Unidad 2": ("ANG02-R", "ANG02-P"),
        "Cochrane Unidad 1": ("CCH01-R", "CCH01-P"),
        "Cochrane Unidad 2": ("CCH02-R", "CCH02-P")
    }

    for nombre_legible, (r_tag, p_tag) in mapeo_estricto.items():
        col_r = [c for c in columnas if c.upper() == r_tag.upper()]
        col_p = [c for c in columnas if c.upper() == p_tag.upper()]
        if col_r and col_p:
            unidades_detectadas[nombre_legible] = (col_r[0], col_p[0])

    st.sidebar.header("Filtros de Operación")
    seleccion_unidad = st.sidebar.selectbox("Selecciona Unidad:", list(unidades_detectadas.keys()))
    col_real, col_prog = unidades_detectadas[seleccion_unidad]

    fecha_min_datos = df_metrics['Fecha'].min().date()
    fecha_max_datos = df_metrics['Fecha'].max().date()
    fecha_inicio_defecto = max(fecha_min_datos, fecha_max_datos - timedelta(days=7))
    
    rango_fechas = st.sidebar.date_input("Rango de Análisis:", value=(fecha_inicio_defecto, fecha_max_datos), min_value=fecha_min_datos, max_value=fecha_max_datos, format="DD/MM/YYYY")

    if isinstance(rango_fechas, tuple) and len(rango_fechas) == 2:
        inicio, fin = rango_fechas
        df_filtrado = df_metrics[(df_metrics['Fecha'].dt.date >= inicio) & (df_metrics['Fecha'].dt.date <= fin)].copy()
    else:
        inicio, fin = fecha_inicio_defecto, fecha_max_datos
        df_filtrado = df_metrics.copy()

    # CORRECCIÓN AQUÍ: Usamos .ffill().fillna(0.0) para ser compatible con Pandas nuevo
    serie_real = df_filtrado[col_real].ffill().fillna(0.0)
    serie_prog = df_filtrado[col_prog].ffill().fillna(0.0)
    
    df_filtrado['Desviacion_MW'] = serie_real - serie_prog
    df_filtrado['Desviacion_Abs_MW'] = df_filtrado['Desviacion_MW'].abs()

    # --- BOTÓN EXPORTACIÓN PDF ---
    st.sidebar.markdown("---")
    st.sidebar.header("Reportabilidad")
    if st.sidebar.button("🖨️ Generar Reporte / Imprimir PDF"):
        st.markdown("<script>window.print();</script>", unsafe_allow_html=True)

    st.subheader(f"Monitoreo de Potencia y Despacho - {seleccion_unidad}")
    mostrar_achurado = st.checkbox("Mostrar área de desviación (Bruta vs Programada)", value=False)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_filtrado['Fecha'], y=serie_prog, name='Potencia Programada', line=dict(color='#3CD6F1', width=2.5), connectgaps=True))
    
    if mostrar_achurado:
        fig.add_trace(go.Scatter(x=df_filtrado['Fecha'], y=serie_real, name='Potencia Real', line=dict(color='#3B66FF', width=2.5), fill='tonexty', fillcolor='rgba(161, 134, 250, 0.25)', connectgaps=True))
    else:
        fig.add_trace(go.Scatter(x=df_filtrado['Fecha'], y=serie_real, name='Potencia Real', line=dict(color='#3B66FF', width=2.5), connectgaps=True))
        
    fig.update_layout(title="Curva de Desempeño Temporal (Ventana de Control Activa)", xaxis_title="Tiempo / Horas", yaxis_title="Potencia (MW)", template="plotly_white", hovermode="x unified", margin=dict(t=40, b=40))
    st.plotly_chart(fig, width="stretch")

    st.markdown("### Análisis Discriminado de Desviación ($P_{Real} - P_{Prog}$)")
    fig_bar = go.Figure()
    colores_barras = ['#10B981' if val >= 0 else '#EF4444' for val in df_filtrado['Desviacion_MW']]
    fig_bar.add_trace(go.Bar(x=df_filtrado['Fecha'], y=df_filtrado['Desviacion_MW'], marker_color=colores_barras, name='Delta de Potencia (MW)'))
    fig_bar.update_layout(title="Magnitud Horaria del Desvío (Verde: Sobre-Generación | Rojo: Sub-Generación)", xaxis_title="Tiempo / Horas", yaxis_title="Desviación (MW)", template="plotly_white", hovermode="x unified", margin=dict(t=40, b=40))
    st.plotly_chart(fig_bar, width="stretch")

    st.markdown("### Indicadores Estadísticos de Desviación")
    desvio_medio = df_filtrado['Desviacion_Abs_MW'].mean()
    energia_desviada_total = df_filtrado['Desviacion_Abs_MW'].sum() 

    if not df_filtrado.empty and not df_filtrado['Desviacion_MW'].isna().all():
        idx_max_abs = df_filtrado['Desviacion_Abs_MW'].idxmax()
        valor_desvio_real = df_filtrado.loc[idx_max_abs, 'Desviacion_MW']
        desvio_max_valor = abs(valor_desvio_real)
        html_subtext = "<div class='metric-subtext'>▲ POR SOBRE-GENERACIÓN</div>" if valor_desvio_real >= 0 else "<div class='metric-subtext-red'>▼ POR SUB-GENERACIÓN</div>"
    else:
        desvio_max_valor, html_subtext = 0.00, "<div class='metric-subtext'>SIN REGISTROS</div>"

    m1, m2, m3 = st.columns(3)
    with m1: st.markdown(f'<div class="metric-card"><div class="metric-label">Desviación Media Global</div><div class="metric-value">{desvio_medio:.2f} MW</div><div class="metric-subtext" style="color: #6B7280 !important;">Promedio absoluto lineal</div></div>', unsafe_allow_html=True)
    with m2: st.markdown(f'<div class="metric-card"><div class="metric-label">Desviación Máxima Registrada</div><div class="metric-value">{desvio_max_valor:.2f} MW</div>{html_subtext}</div>', unsafe_allow_html=True)
    with m3: st.markdown(f'<div class="metric-card"><div class="metric-label">Energía Total Desviada</div><div class="metric-value">{energia_desviada_total:.1f} MWh</div><div class="metric-subtext" style="color: #6B7280 !important;">Suma acumulada del periodo</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- SECCIÓN BITÁCORA ---
    st.markdown("---")
    st.markdown("### Bitácora de Novedades Operacionales (Historial Unificado)")
    
    df_comentarios = obtener_bitacora_global()
    
    if not df_comentarios.empty:
        df_comentarios['fecha_parsed'] = pd.to_datetime(df_comentarios['fecha'], format='%d/%m/%Y', errors='coerce')
        df_comentarios_filtrados = df_comentarios[
            (df_comentarios['unidad'] == seleccion_unidad) & 
            (df_comentarios['fecha_parsed'].dt.date >= inicio) & 
            (df_comentarios['fecha_parsed'].dt.date <= fin)
        ].copy()
    else:
        df_comentarios_filtrados = pd.DataFrame()

    col_form, col_tabla = st.columns([1, 1.8])

    with col_form:
        st.subheader("Registrar Novedad")
        with st.form("form_global", clear_on_submit=True):
            fecha_evento = st.date_input("Fecha del Suceso:", value=fecha_max_datos, format="DD/MM/YYYY")
            hora_actual_str = datetime.now().strftime("%H:%M")
            hora_evento_str = st.text_input("Hora del Suceso (HH:MM):", value=hora_actual_str, max_chars=5)
            operador = st.text_input("Jefe de Turno:", value="Erick Herrera")
            novedad = st.text_area("Detalle del Evento / Restricción:")
            boton_guardar = st.form_submit_button("Guardar Registro Global")
            
            if boton_guardar:
                texto_limpio = novedad.strip()
                if texto_limpio != "":
                    nuevo_id = str(int(datetime.now().timestamp() * 1000))
                    payload = {
                        "action": "add", "id": nuevo_id,
                        "fecha": fecha_evento.strftime("%d/%m/%Y"), "hora": hora_evento_str,
                        "unidad": seleccion_unidad, "autor": operador, "comentario": texto_limpio
                    }
                    try:
                        res = requests.post(URL_API_BITACORA, json=payload, timeout=10)
                        if res.status_code == 200:
                            st.success("Registro sincronizado en Google Sheets.")
                            st.rerun()
                    except: 
                        st.error("Error de conexión al guardar.")
                else: 
                    st.warning("Escribe una descripción antes de enviar.")

    with col_tabla:
        st.subheader(f"Historial en Ventana Seleccionada")
        if not df_comentarios_filtrados.empty:
            df_mostrar = df_comentarios_filtrados.copy()
            df_mostrar = df_mostrar.sort_values(by=["fecha_parsed", "hora"], ascending=[False, False])
            
            st.dataframe(df_mostrar[['fecha', 'hora', 'autor', 'comentario']], column_config={"fecha": "Fecha", "hora": "Hora Exacta", "autor": "Jefe de Turno", "comentario": "Novedad / Comentario"}, width="stretch", hide_index=True)
            
            st.markdown("#### Administración de Registros")
            opciones_admin = {row["id"]: f"[{row['fecha']} {row['hora']}] - {row['comentario'][:30]}..." for _, row in df_comentarios_filtrados.iterrows()}
            
            id_seleccionado = st.selectbox("Selecciona un evento para Gestionar o Modificar:", options=list(opciones_admin.keys()), format_func=lambda x: opciones_admin[x])
            registro_actual = df_comentarios_filtrados[df_comentarios_filtrados['id'] == id_seleccionado].iloc[0]
            
            mod_autor = st.text_input("Modificar Autor:", value=registro_actual['autor'])
            mod_comentario = st.text_area("Modificar Descripción:", value=registro_actual['comentario'])
            
            c_btn1, c_btn2 = st.columns(2)
            with c_btn1:
                if st.button("💾 Actualizar Cambios"):
                    payload_upd = {"action": "update", "id": id_seleccionado, "autor": mod_autor, "comentario": mod_comentario}
                    try:
                        res = requests.post(URL_API_BITACORA, json=payload_upd, timeout=10)
                        if res.status_code == 200:
                            st.success("Registro actualizado con éxito.")
                            st.rerun()
                    except: st.error("Error de conexión al actualizar.")
                    
            with c_btn2:
                if st.button("❌ Eliminar Evento"):
                    payload_del = {"action": "delete", "id": id_seleccionado}
                    try:
                        res = requests.post(URL_API_BITACORA, json=payload_del, timeout=10)
                        if res.status_code == 200:
                            st.success("Registro eliminado.")
                            st.rerun()
                    except: st.error("Error de conexión al eliminar.")
        else:
            st.info("No hay eventos compartidos para esta unidad dentro del rango de fechas seleccionado.")

except Exception as e:
    st.error(f"Error en el procesamiento del sistema: {e}")