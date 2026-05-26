import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import re

# 1. CONFIGURACIÓN DE LA PÁGINA EN MODO ANCHO
st.set_page_config(page_title="Dashboard Generación Complejo Técnico Mejillones", layout="wide")

# FORZAR TEMA CLARO ABSOLUTO CON PALETA AES (Ajuste de fuentes adaptativas y diseño responsive)
st.markdown("""
    <style>
        .stApp {
            background-color: #FFFFFF !important;
            color: #1F2937 !important;
        }
        .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
        h1, h2, h3, h4, p, span, label { color: #111827 !important; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }
        .stButton>button { background-color: #3B66FF !important; color: white !important; border-radius: 4px; border: none; }
        .stButton>button:hover { background-color: #2651E6 !important; color: white !important; }
        .stDataFrame, div[data-testid="stTable"] { background-color: #F9FAFB !important; border: 1px solid #E5E7EB; }
        
        /* Contenedores personalizados para indicadores estables sin cortes de texto */
        .metric-card {
            background-color: #F9FAFB;
            border: 1px solid #E5E7EB;
            padding: 1rem;
            border-radius: 6px;
            text-align: left;
            box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
        }
        .metric-label {
            font-size: 0.85rem !important;
            color: #4B5563 !important;
            font-weight: 600;
            text-transform: uppercase;
            margin-bottom: 0.25rem;
        }
        .metric-value {
            font-size: 1.8rem !important;
            color: #111827 !important;
            font-weight: 700;
            line-height: 1.2;
        }
        .metric-subtext {
            font-size: 0.85rem !important;
            color: #2563EB !important;
            font-weight: 600;
            margin-top: 0.25rem;
        }
        .metric-subtext-red {
            font-size: 0.85rem !important;
            color: #DC2626 !important;
            font-weight: 600;
            margin-top: 0.25rem;
        }
    </style>
""", unsafe_allow_html=True)

st.title("Dashboard generación complejo térmico mejillones")
st.markdown("Visualización e ingeniería de datos para el control de despacho y desviaciones de potencia.")

# REEMPLAZA AQUÍ: Coloca la URL de exportación CSV de tu Google Sheets
URL_GOOGLE_SHEETS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTLvFug7yx0-2rF1nwhWt8q4l8mpGtO7Xpi3BK6lEvLw-L19bDQZIFXc4Fu63WHvip6PqarXxC1VJR3/pub?output=csv"

def limpiar_formato_latam(val):
    if pd.isna(val):
        return None
    s = str(val).strip().replace(' ', '').replace('\n', '').replace('\r', '').replace('\t', '')
    if s in ['', 'nan', 'None', 'NaN', 'null']:
        return None
    try:
        if ',' in s:
            partes = s.split(',')
            parte_entera = partes[0].replace('.', '')
            parte_decimal = partes[1]
            s_convertir = parte_entera + '.' + parte_decimal
        else:
            if s.count('.') == 1:
                s_convertir = s
            else:
                s_convertir = s.replace('.', '')
                
        valor = float(s_convertir)
        
        if valor > 5000.0:
            s_digitos = re.sub(r'[^\d]', '', s_convertir)
            if len(s_digitos) >= 3:
                valor = float(s_digitos[:3] + '.' + s_digitos[3:5])
        return valor
    except:
        return None

@st.cache_data(ttl=10)
def cargar_datos_produccion():
    try:
        df = pd.read_csv(URL_GOOGLE_SHEETS, on_bad_lines="skip", engine="python", dtype=str)
        st.sidebar.success("Conexión activa: Datos desde Google Sheets")
    except Exception as e:
        df = pd.read_csv("Planilla_Consolidada_GoogleSheets.csv", on_bad_lines="skip", engine="python", dtype=str)
        st.sidebar.warning("Modo offline: Cargando copia local de contingencia")
        
    df.columns = df.columns.str.strip()
    columnas_fecha = [col for col in df.columns if 'fech' in col.lower()]
    if columnas_fecha:
        df = df.rename(columns={columnas_fecha[0]: 'Fecha'})
    
    df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
    df = df.dropna(subset=['Fecha'])
    
    for col in df.columns:
        if col != 'Fecha':
            df[col] = df[col].apply(limpiar_formato_latam)
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    mapeo_pares = {
        'ANG01-R': 'ANG01-P', 'ANG02-R': 'ANG02-P',
        'CCH01-R': 'CCH01-P', 'CCH02-R': 'CCH02-P'
    }
    for col_real, col_prog in mapeo_pares.items():
        if col_real in df.columns and col_prog in df.columns:
            df.loc[df[col_real] > 300.0, col_real] = df[col_prog]
            
    return df

try:
    df_metrics = cargar_datos_produccion()
    columnas = list(df_metrics.columns)

    unidades_detectadas = {}
    def buscar_par_columnas(tag_unidad):
        col_r = [c for c in columnas if tag_unidad.lower() in c.lower().replace("-", "").replace("_", "") and 'r' in c.lower()]
        col_p = [c for c in columnas if tag_unidad.lower() in c.lower().replace("-", "").replace("_", "") and 'p' in c.lower()]
        return (col_r[0], col_p[0]) if (col_r and col_p) else None

    for nombre_legible, tag in [
        ("Angamos Unidad 1", "ANG01"), ("Angamos Unidad 2", "ANG02"),
        ("Cochrane Unidad 1", "CCH01"), ("Cochrane Unidad 2", "CCH02")
    ]:
        par = buscar_par_columnas(tag)
        if par:
            unidades_detectadas[nombre_legible] = par

    # BARRA LATERAL - FILTROS
    st.sidebar.header("Filtros de Operación")
    seleccion_unidad = st.sidebar.selectbox("Selecciona Unidad:", list(unidades_detectadas.keys()))
    col_real, col_prog = unidades_detectadas[seleccion_unidad]

    fecha_min_datos = df_metrics['Fecha'].min().date()
    fecha_max_datos = df_metrics['Fecha'].max().date()
    
    # Ventana por defecto de la última semana
    fecha_inicio_defecto = max(fecha_min_datos, fecha_max_datos - timedelta(days=7))
    
    rango_fechas = st.sidebar.date_input(
        "Rango de Análisis:", 
        value=(fecha_inicio_defecto, fecha_max_datos), 
        min_value=fecha_min_datos, 
        max_value=fecha_max_datos,
        format="DD/MM/YYYY"
    )

    if isinstance(rango_fechas, tuple) and len(rango_fechas) == 2:
        inicio, fin = rango_fechas
        st.sidebar.markdown(f"**Intervalo Activo:** `{inicio.strftime('%d/%m/%Y')}` al `{fin.strftime('%d/%m/%Y')}`")
        df_filtrado = df_metrics[(df_metrics['Fecha'].dt.date >= inicio) & (df_metrics['Fecha'].dt.date <= fin)].copy()
    else:
        df_filtrado = df_metrics.copy()

    df_calc = df_filtrado.copy()
    df_calc[col_real] = df_calc[col_real].fillna(0.0)
    df_calc[col_prog] = df_calc[col_prog].fillna(0.0)
    
    # Desviación neta (Real - Programada)
    df_filtrado['Desviacion_MW'] = df_calc[col_real] - df_calc[col_prog]
    df_filtrado['Desviacion_Abs_MW'] = df_filtrado['Desviacion_MW'].abs()

    st.subheader(f"Monitoreo de Potencia y Despacho - {seleccion_unidad}")
    mostrar_achurado = st.checkbox("Mostrar área de desviación (Bruta vs Programada)", value=False)

    # 2. GRÁFICO PRINCIPAL DE LÍNEAS
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_filtrado['Fecha'], y=df_filtrado[col_prog],
        name='Potencia Programada', line=dict(color='#3CD6F1', width=2.5), connectgaps=True
    ))
    
    if mostrar_achurado:
        fig.add_trace(go.Scatter(
            x=df_filtrado['Fecha'], y=df_filtrado[col_real],
            name='Potencia Real', line=dict(color='#3B66FF', width=2.5),
            fill='tonexty', fillcolor='rgba(161, 134, 250, 0.25)', connectgaps=True
        ))
    else:
        fig.add_trace(go.Scatter(
            x=df_filtrado['Fecha'], y=df_filtrado[col_real],
            name='Potencia Real', line=dict(color='#3B66FF', width=2.5), connectgaps=True
        ))

    fig.update_layout(
        title=f"Curva de Desempeño Temporal (Ventana de Control Activa)",
        xaxis_title="Tiempo / Horas", yaxis_title="Potencia (MW)",
        template="plotly_white", hovermode="x unified",
        margin=dict(t=40, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, width="stretch")

    # 3. GRÁFICO SECUNDARIO DE BARRAS DE DESVIACIÓN DIRECTA
    st.markdown("### Análisis Discriminado de Desviación ($P_{Real} - P_{Prog}$)")
    
    fig_bar = go.Figure()
    colores_barras = ['#10B981' if val >= 0 else '#EF4444' for val in df_filtrado['Desviacion_MW']]
    
    fig_bar.add_trace(go.Bar(
        x=df_filtrado['Fecha'],
        y=df_filtrado['Desviacion_MW'],
        marker_color=colores_barras,
        name='Delta de Potencia (MW)'
    ))
    
    fig_bar.update_layout(
        title="Magnitud Horaria del Desvío (Verde: Sobre-Generación | Rojo: Sub-Generación)",
        xaxis_title="Tiempo / Horas", yaxis_title="Desviación (MW)",
        template="plotly_white", hovermode="x unified",
        margin=dict(t=40, b=40)
    )
    st.plotly_chart(fig_bar, width="stretch")

    # 4. INDICADORES ESTADÍSTICOS OPTIMIZADOS (CON DISEÑO HTML ANTI-TRUNCADO)
    st.markdown("### Indicadores Estadísticos de Desviación")
    desvio_medio = df_filtrado['Desviacion_Abs_MW'].mean()
    energia_desviada_total = df_filtrado['Desviacion_Abs_MW'].sum() 

    # Lógica de detección para la naturaleza del desvío máximo
    if not df_filtrado.empty and not df_filtrado['Desviacion_MW'].isna().all():
        idx_max_abs = df_filtrado['Desviacion_Abs_MW'].idxmax()
        valor_desvio_real = df_filtrado.loc[idx_max_abs, 'Desviacion_MW']
        desvio_max_valor = abs(valor_desvio_real)
        
        if valor_desvio_real >= 0:
            html_subtext = "<div class='metric-subtext'>▲ POR SOBRE-GENERACIÓN</div>"
        else:
            html_subtext = "<div class='metric-subtext-red'>▼ POR SUB-GENERACIÓN</div>"
    else:
        desvio_max_valor = 0.00
        html_subtext = "<div class='metric-subtext'>SIN REGISTROS</div>"

    # Despliegue de tarjetas balanceadas usando columnas e inyección HTML limpia
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Desviación Media Global</div>
                <div class="metric-value">{desvio_medio:.2f} MW</div>
                <div class="metric-subtext" style="color: #6B7280 !important;">Promedio absoluto lineal</div>
            </div>
        """, unsafe_allow_html=True)
        
    with m2:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Desviación Máxima Registrada</div>
                <div class="metric-value">{desvio_max_valor:.2f} MW</div>
                {html_subtext}
            </div>
        """, unsafe_allow_html=True)
        
    with m3:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Energía Total Desviada</div>
                <div class="metric-value">{energia_desviada_total:.1f} MWh</div>
                <div class="metric-subtext" style="color: #6B7280 !important;">Suma acumulada del periodo</div>
            </div>
        """, unsafe_allow_html=True)

    # Espaciador visual estético
    st.markdown("<br>", unsafe_allow_html=True)

    # 5. BITÁCORA DE EVENTOS OPTIMIZADA
    if "bd_comentarios_local" not in st.session_state:
        st.session_state.bd_comentarios_local = pd.DataFrame(columns=["id", "fecha", "hora", "unidad", "autor", "comentario"])

    st.markdown("---")
    st.markdown("### Bitácora de Novedades Operacionales")
    
    col_form, col_tabla = st.columns([1, 1.8])

    with col_form:
        st.subheader("Registrar Novedad")
        with st.form("form_local", clear_on_submit=True):
            fecha_evento = st.date_input("Fecha del Suceso:", value=fecha_max_datos, format="DD/MM/YYYY")
            
            hora_actual_str = datetime.now().strftime("%H:%M")
            hora_evento_str = st.text_input("Hora del Suceso (HH:MM):", value=hora_actual_str, max_chars=5)
            
            operador = st.text_input("Jefe de Turno:", value="Erick Herrera")
            novedad = st.text_area("Detalle del Evento / Restricción:")
            
            boton_guardar = st.form_submit_button("Guardar Registro")
            
            if boton_guardar:
                texto_limpio = novedad.strip()
                if texto_limpio != "":
                    nuevo_id = str(int(datetime.now().timestamp() * 1000))
                    nueva_fila = pd.DataFrame([{
                        "id": nuevo_id,
                        "fecha": fecha_evento.strftime("%d/%m/%Y"), 
                        "hora": hora_evento_str, 
                        "unidad": seleccion_unidad, 
                        "autor": operador, 
                        "comentario": texto_limpio
                    }])
                    st.session_state.bd_comentarios_local = pd.concat([st.session_state.bd_comentarios_local, nueva_fila], ignore_index=True)
                    st.success("Registro añadido con éxito.")
                    st.rerun()
                else:
                    st.warning("Escribe una descripción antes de guardar.")

    with col_tabla:
        st.subheader(f"Historial de Eventos - {seleccion_unidad}")
        df_comentarios = st.session_state.bd_comentarios_local
        df_comentarios_filtrados = df_comentarios[df_comentarios['unidad'] == seleccion_unidad]
        
        if not df_comentarios_filtrados.empty:
            df_mostrar = df_comentarios_filtrados.copy()
            df_mostrar['fecha_dt'] = pd.to_datetime(df_mostrar['fecha'], format='%d/%m/%Y', errors='coerce')
            df_mostrar = df_mostrar.sort_values(by=["fecha_dt", "hora"], ascending=[False, False])
            
            st.dataframe(
                df_mostrar[['fecha', 'hora', 'autor', 'comentario']], 
                column_config={
                    "fecha": "Fecha", "hora": "Hora Exacta",
                    "autor": "Jefe de Turno", "comentario": "Novedad / Comentario"
                },
                width="stretch", hide_index=True
            )
            
            st.markdown("#### Administración de Registros")
            
            opciones_admin = {row["id"]: f"[{row['fecha']} {row['hora']}] - {row['comentario'][:30]}..." for _, row in df_comentarios_filtrados.iterrows()}
            id_seleccionado = st.selectbox("Selecciona un evento para Gestionar:", options=list(opciones_admin.keys()), format_func=lambda x: opciones_admin[x])
            
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                if st.button("❌ Eliminar Evento Seleccionado"):
                    st.session_state.bd_comentarios_local = st.session_state.bd_comentarios_local[st.session_state.bd_comentarios_local["id"] != id_seleccionado]
                    st.success("Registro eliminado.")
                    st.rerun()
                    
            with col_btn2:
                fila_editar = df_comentarios[df_comentarios["id"] == id_seleccionado].iloc[0]
                nuevo_comentario_texto = st.text_area("Modificar descripción seleccionada:", value=fila_editar["comentario"])
                if st.button("💾 Actualizar Cambios"):
                    st.session_state.bd_comentarios_local.loc[st.session_state.bd_comentarios_local["id"] == id_seleccionado, "comentario"] = nuevo_comentario_texto
                    st.success("Registro actualizado.")
                    st.rerun()
        else:
            st.info("No hay eventos registrados para esta unidad en el turno actual.")

except Exception as e:
    st.error(f"Error en el procesamiento del sistema: {e}")