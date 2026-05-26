import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests

# CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Dashboard Generación Complejo Técnico Mejillones", layout="wide")

# ESTILOS DE INTERFAZ (TEMA CLARO ABSOLUTO)
st.markdown("""
    <style>
        .stApp { background-color: #FFFFFF !important; color: #1F2937 !important; }
        .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
        h1, h2, h3, h4, p, span, label { color: #111827 !important; font-family: 'Segoe UI', Roboto, sans-serif; }
        .stButton>button { background-color: #3B66FF !important; color: white !important; border-radius: 4px; }
        .stDataFrame, div[data-testid="stTable"] { background-color: #F9FAFB !important; border: 1px solid #E5E7EB; }
        .metric-card { background-color: #F9FAFB; border: 1px solid #E5E7EB; padding: 1rem; border-radius: 6px; }
        .metric-label { font-size: 0.85rem !important; color: #4B5563 !important; font-weight: 600; text-transform: uppercase; }
        .metric-value { font-size: 1.8rem !important; color: #111827 !important; font-weight: 700; }
        .metric-subtext { font-size: 0.85rem !important; color: #2563EB !important; font-weight: 600; }
        .metric-subtext-red { font-size: 0.85rem !important; color: #DC2626 !important; font-weight: 600; }
        @media print {
            header, footer, nav, .stSidebar, [data-testid="stSidebar"], .no-print { display: none !important; }
            .stApp { background-color: white !important; }
        }
    </style>
""", unsafe_allow_html=True)

st.title("Dashboard generación complejo térmico mejillones")
st.markdown("Visualización e ingeniería de datos para el control de despacho y desviaciones de potencia.")

URL_GOOGLE_SHEETS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTLvFug7yx0-2rF1nwhWt8q4l8mpGtO7Xpi3BK6lEvLw-L19bDQZIFXc4Fu63WHvip6PqarXxC1VJR3/pub?output=csv"
URL_API_BITACORA = "https://script.google.com/macros/library/d/1l0zQncbODrFu_TewveQeSSte16mPdqqyiISj84wKfpbeAzICMAFF7Dvs/2"

@st.cache_data(ttl=10)
def cargar_datos_produccion():
    try:
        df = pd.read_csv(URL_GOOGLE_SHEETS, on_bad_lines="skip", engine="python")
        st.sidebar.success("Conexión activa: Datos desde Google Sheets")
    except:
        df = pd.read_csv("Planilla_Consolidada_GoogleSheets.csv", on_bad_lines="skip", engine="python")
        st.sidebar.warning("Modo offline: Copia local")
        
    df.columns = df.columns.str.strip()
    columnas_fecha = [col for col in df.columns if 'fech' in col.lower()]
    if columnas_fecha: 
        df = df.rename(columns={columnas_fecha[0]: 'Fecha'})
    
    df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
    df = df.dropna(subset=['Fecha'])
    
    for col in df.columns:
        if col != 'Fecha':
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    return df

def obtener_bitacora_global():
    try:
        respuesta = requests.get(URL_API_BITACORA, timeout=10)
        if respuesta.status_code == 200:
            raw_data = respuesta.json()
            if raw_data:
                df = pd.DataFrame(raw_data)
                return df
    except: pass
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

    # CERO MÉTODOS OBSOLETOS: Manejo directo y seguro de nulos
    serie_real = df_filtrado[col_real].fillna(0.0)
    serie_prog = df_filtrado[col_prog].fillna(0.0)
    
    df_filtrado['Desviacion_MW'] = serie_real - serie_prog
    df_filtrado['Desviacion_Abs_MW'] = df_filtrado['Desviacion_MW'].abs()

    st.subheader(f"Monitoreo de Potencia y Despacho - {seleccion_unidad}")
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_filtrado['Fecha'], y=serie_prog, name='Potencia Programada', line=dict(color='#3CD6F1', width=2.5)))
    fig.add_trace(go.Scatter(x=df_filtrado['Fecha'], y=serie_real, name='Potencia Real', line=dict(color='#3B66FF', width=2.5)))
    fig.update_layout(title="Curva de Desempeño Temporal", xaxis_title="Tiempo", yaxis_title="Potencia (MW)", template="plotly_white", hovermode="x unified")
    st.plotly_chart(fig, width="stretch")

    st.markdown("### Indicadores Estadísticos")
    desvio_medio = df_filtrado['Desviacion_Abs_MW'].mean() if not df_filtrado.empty else 0.0
    energia_total = df_filtrado['Desviacion_Abs_MW'].sum() if not df_filtrado.empty else 0.0

    m1, m2 = st.columns(2)
    with m1: st.markdown(f'<div class="metric-card"><div class="metric-label">Desviación Media</div><div class="metric-value">{desvio_medio:.2f} MW</div></div>', unsafe_allow_html=True)
    with m2: st.markdown(f'<div class="metric-card"><div class="metric-label">Energía Total Desviada</div><div class="metric-value">{energia_total:.1f} MWh</div></div>', unsafe_allow_html=True)

except Exception as e:
    st.error(f"Error en el procesamiento del sistema: {e}")