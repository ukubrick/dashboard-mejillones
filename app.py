import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests

# 1. CONFIGURACIÓN DE LA PÁGINA EN MODO ANCHO
st.set_page_config(page_title="Dashboard Generación Complejo Técnico Mejillones", layout="wide")

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
            header, footer, nav, .stSidebar, [data-testid="stSidebar"],
            [data-testid="stToolbar"], [data-testid="stDecoration"],
            [data-testid="stStatusWidget"], .stDeployButton,
            iframe, .stCheckbox, .stForm, .stButton,
            .stTextInput, .stTextArea, .stDateInput, .stSelectbox {
                display: none !important;
            }
            [data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stForm"]) {
                display: none !important;
            }
            .print-hide {
                display: none !important;
            }
            .stApp { background-color: white !important; }
            .block-container { padding: 0.5rem !important; margin: 0 !important; max-width: 100% !important; }
            .js-plotly-plot { break-inside: avoid; }
        }
    </style>
""", unsafe_allow_html=True)

st.title("Dashboard generación complejo térmico mejillones")

# --- ENLACES DE GOOGLE SHEETS ---
URL_GOOGLE_SHEETS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTLvFug7yx0-2rF1nwhWt8q4l8mpGtO7Xpi3BK6lEvLw-L19bDQZIFXc4Fu63WHvip6PqarXxC1VJR3/pub?output=csv"
URL_API_BITACORA = "https://script.google.com/macros/s/AKfycbxOKB-DXUGJBipCgyoRCQT5Iv6Q6qd2x82Vf9RY18m4uABB1uILNOcGqYR_r-f7Y67B/exec"

MAX_MW = 400.0


def limpiar_valor_mw(val_str):
    s = str(val_str).strip()
    if s in ('', 'nan', 'None', 'NaN', 'null'):
        return float('nan')
    if ',' in s:
        s = s.replace('.', '').replace(',', '.')
    try:
        num = float(s)
        return num if num <= MAX_MW else float('nan')
    except ValueError:
        return float('nan')


@st.cache_data(ttl=10)
def cargar_datos_produccion():
    try:
        df = pd.read_csv(URL_GOOGLE_SHEETS, on_bad_lines="skip", engine="python")
        st.sidebar.success("Conexión activa: Datos desde Google Sheets")
    except Exception:
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
            converted = pd.to_numeric(df[col], errors='coerce')
            if converted.isna().sum() > df[col].isna().sum() + 10:
                df[col] = df[col].apply(limpiar_valor_mw)
            else:
                df[col] = converted
    return df


def normalizar_fecha_api(fecha_raw):
    if not fecha_raw:
        return ""
    str_f = str(fecha_raw).strip()
    if "T" in str_f and "-" in str_f[:10]:
        try:
            dt = datetime.strptime(str_f[:10], "%Y-%m-%d")
            return dt.strftime("%d/%m/%Y")
        except Exception:
            pass
    try:
        dt = datetime.strptime(str_f, "%d/%m/%Y")
        return dt.strftime("%d/%m/%Y")
    except Exception:
        pass
    try:
        dt = datetime.strptime(str_f[:10], "%Y-%m-%d")
        return dt.strftime("%d/%m/%Y")
    except Exception:
        pass
    return str_f


def normalizar_hora_api(hora_raw):
    if not hora_raw:
        return "00:00"
    str_h = str(hora_raw).strip()
    if "T" in str_h:
        try:
            componente_hora = str_h.split("T")[1].replace("Z", "")
            return componente_hora[:5]
        except Exception:
            pass
    if ":" in str_h:
        partes = str_h.split(":")
        try:
            h = int(partes[0])
            m = int(partes[1][:2])
            return f"{h:02d}:{m:02d}"
        except Exception:
            pass
    return str_h[:5]


def obtener_bitacora_global():
    try:
        respuesta = requests.get(URL_API_BITACORA, timeout=15, headers={"Accept": "application/json"})
        if respuesta.status_code != 200:
            st.sidebar.warning(f"Bitácora: HTTP {respuesta.status_code}")
            return pd.DataFrame(columns=["id", "fecha", "hora", "unidad", "autor", "comentario"])
        texto = respuesta.text.strip()
        if not texto.startswith("[") and not texto.startswith("{"):
            st.sidebar.warning("Bitácora: la API no devuelve JSON. Verifica el deploy del Apps Script.")
            return pd.DataFrame(columns=["id", "fecha", "hora", "unidad", "autor", "comentario"])
        raw_data = respuesta.json()
        if raw_data and len(raw_data) > 0:
            df = pd.DataFrame(raw_data)
            for col_esperada in ["id", "fecha", "hora", "unidad", "autor", "comentario"]:
                if col_esperada not in df.columns:
                    df[col_esperada] = ""
            df['id'] = df['id'].astype(str)
            df['fecha'] = df['fecha'].apply(normalizar_fecha_api)
            df['hora'] = df['hora'].apply(normalizar_hora_api)
            df['unidad'] = df['unidad'].astype(str).str.strip()
            df['autor'] = df['autor'].astype(str).str.strip()
            df['comentario'] = df['comentario'].astype(str).str.strip()
            return df
    except requests.exceptions.Timeout:
        st.sidebar.warning("Bitácora: timeout de conexión (>15s)")
    except requests.exceptions.ConnectionError:
        st.sidebar.warning("Bitácora: sin conexión a la API")
    except Exception as e:
        st.sidebar.warning(f"Bitácora: error ({type(e).__name__}: {e})")
    return pd.DataFrame(columns=["id", "fecha", "hora", "unidad", "autor", "comentario"])


# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════
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

    rango_fechas = st.sidebar.date_input(
        "Rango de Análisis:",
        value=(fecha_inicio_defecto, fecha_max_datos),
        min_value=fecha_min_datos,
        max_value=fecha_max_datos,
        format="DD/MM/YYYY"
    )

    if isinstance(rango_fechas, tuple) and len(rango_fechas) == 2:
        inicio, fin = rango_fechas
        df_filtrado = df_metrics[
            (df_metrics['Fecha'].dt.date >= inicio) &
            (df_metrics['Fecha'].dt.date <= fin)
        ].copy()
    else:
        inicio, fin = fecha_inicio_defecto, fecha_max_datos
        df_filtrado = df_metrics.copy()

    serie_real = df_filtrado[col_real].fillna(0.0)
    serie_prog = df_filtrado[col_prog].fillna(0.0)
    df_filtrado['Desviacion_MW'] = serie_real - serie_prog
    df_filtrado['Desviacion_Abs_MW'] = df_filtrado['Desviacion_MW'].abs()

    # --- BOTÓN PDF EN SIDEBAR ---
    st.sidebar.markdown("---")
    st.sidebar.header("Reportabilidad")
    with st.sidebar:
        components.html(
            """
            <style>
                body { margin: 0; padding: 0; background: transparent; }
                .print-btn {
                    background-color: #3B66FF; color: white; border: none; border-radius: 4px;
                    padding: 0.6rem 1rem; font-size: 0.9rem; font-weight: 600; cursor: pointer;
                    width: 100%; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                }
                .print-btn:hover { background-color: #2651E6; }
            </style>
            <button class="print-btn" onclick="window.top.print();">
                🖨️ Generar Reporte / Imprimir PDF
            </button>
            """,
            height=45
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # GRÁFICO SERIE TEMPORAL (VISIBLE EN PDF)
    # ═══════════════════════════════════════════════════════════════════════════
    st.subheader(f"Monitoreo de Potencia y Despacho - {seleccion_unidad}")
    mostrar_achurado = st.checkbox("Mostrar área de desviación (Bruta vs Programada)", value=False)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_filtrado['Fecha'], y=serie_prog,
        name='Potencia Programada',
        line=dict(color='#3CD6F1', width=2.5)
    ))
    if mostrar_achurado:
        fig.add_trace(go.Scatter(
            x=df_filtrado['Fecha'], y=serie_real,
            name='Potencia Real',
            line=dict(color='#3B66FF', width=2.5),
            fill='tonexty', fillcolor='rgba(161, 134, 250, 0.25)'
        ))
    else:
        fig.add_trace(go.Scatter(
            x=df_filtrado['Fecha'], y=serie_real,
            name='Potencia Real',
            line=dict(color='#3B66FF', width=2.5)
        ))
    fig.update_layout(
        title="Curva de Desempeño Temporal (Ventana de Control Activa)",
        xaxis_title="Tiempo / Horas", yaxis_title="Potencia (MW)",
        template="plotly_white", hovermode="x unified", margin=dict(t=40, b=40)
    )
    st.plotly_chart(fig, use_container_width=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # SECCIONES OCULTAS EN PDF (dentro de un container con key para CSS)
    # ═══════════════════════════════════════════════════════════════════════════
    seccion_oculta = st.container(key="print_hide_section")
    with seccion_oculta:
        st.markdown("### Análisis Discriminado de Desviación ($P_{Real} - P_{Prog}$)")
        fig_bar = go.Figure()
        colores_barras = ['#10B981' if val >= 0 else '#EF4444' for val in df_filtrado['Desviacion_MW']]
        fig_bar.add_trace(go.Bar(
            x=df_filtrado['Fecha'], y=df_filtrado['Desviacion_MW'],
            marker_color=colores_barras, name='Delta de Potencia (MW)'
        ))
        fig_bar.update_layout(
            title="Magnitud Horaria del Desvío (Verde: Sobre-Generación | Rojo: Sub-Generación)",
            xaxis_title="Tiempo / Horas", yaxis_title="Desviación (MW)",
            template="plotly_white", hovermode="x unified", margin=dict(t=40, b=40)
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown("### Indicadores Estadísticos de Desviación")
        desvio_medio = df_filtrado['Desviacion_Abs_MW'].mean() if not df_filtrado.empty else 0.0
        energia_desviada_total = df_filtrado['Desviacion_Abs_MW'].sum() if not df_filtrado.empty else 0.0

        if not df_filtrado.empty and not df_filtrado['Desviacion_MW'].isna().all():
            idx_max_abs = df_filtrado['Desviacion_Abs_MW'].idxmax()
            valor_desvio_real = df_filtrado.loc[idx_max_abs, 'Desviacion_MW']
            desvio_max_valor = abs(valor_desvio_real)
            html_subtext = (
                "<div class='metric-subtext'>▲ POR SOBRE-GENERACIÓN</div>"
                if valor_desvio_real >= 0
                else "<div class='metric-subtext-red'>▼ POR SUB-GENERACIÓN</div>"
            )
        else:
            desvio_max_valor = 0.00
            html_subtext = "<div class='metric-subtext'>SIN REGISTROS</div>"

        m1, m2, m3 = st.columns(3)
        with m1:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">Desviación Media Global</div>'
                f'<div class="metric-value">{desvio_medio:.2f} MW</div>'
                f'<div class="metric-subtext" style="color: #6B7280 !important;">Promedio absoluto lineal</div></div>',
                unsafe_allow_html=True
            )
        with m2:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">Desviación Máxima Registrada</div>'
                f'<div class="metric-value">{desvio_max_valor:.2f} MW</div>{html_subtext}</div>',
                unsafe_allow_html=True
            )
        with m3:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">Energía Total Desviada</div>'
                f'<div class="metric-value">{energia_desviada_total:.1f} MWh</div>'
                f'<div class="metric-subtext" style="color: #6B7280 !important;">Suma acumulada del periodo</div></div>',
                unsafe_allow_html=True
            )

    # ═══════════════════════════════════════════════════════════════════════════
    # BITÁCORA — Título y tabla visible en PDF, formulario/admin oculto
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("### Bitácora de Novedades Operacionales (Historial Unificado)")

    df_comentarios = obtener_bitacora_global()

    if not df_comentarios.empty:
        df_comentarios['fecha_parsed'] = pd.to_datetime(
            df_comentarios['fecha'], format='%d/%m/%Y', errors='coerce'
        )
        mask_unidad = df_comentarios['unidad'].str.strip() == seleccion_unidad
        mask_fecha_inicio = df_comentarios['fecha_parsed'].dt.date >= inicio
        mask_fecha_fin = df_comentarios['fecha_parsed'].dt.date <= fin
        df_comentarios_filtrados = df_comentarios[
            mask_unidad & mask_fecha_inicio & mask_fecha_fin
        ].copy()
    else:
        df_comentarios_filtrados = pd.DataFrame()

    # ── TABLA DE EVENTOS (visible en PDF, ancho completo) ──
    st.subheader(f"Historial de Eventos - {seleccion_unidad}")
    if not df_comentarios_filtrados.empty:
        df_mostrar = df_comentarios_filtrados.copy()
        df_mostrar = df_mostrar.sort_values(by=["fecha_parsed", "hora"], ascending=[False, False])
        st.dataframe(
            df_mostrar[['fecha', 'hora', 'autor', 'comentario']],
            column_config={
                "fecha": "Fecha", "hora": "Hora Exacta",
                "autor": "Jefe de Turno", "comentario": "Novedad / Comentario"
            },
            use_container_width=True, hide_index=True
        )
    else:
        st.info("No hay eventos compartidos para esta unidad dentro del rango de fechas seleccionado.")

    # ── FORMULARIO Y ADMINISTRACIÓN (oculto en PDF, dentro de container con key) ──
    seccion_admin = st.container(key="print_hide_admin")
    with seccion_admin:
        col_form, col_admin = st.columns([1, 1.8])

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
                            "fecha": fecha_evento.strftime("%d/%m/%Y"),
                            "hora": hora_evento_str,
                            "unidad": seleccion_unidad,
                            "autor": operador, "comentario": texto_limpio
                        }
                        try:
                            res = requests.post(URL_API_BITACORA, json=payload, timeout=15)
                            if res.status_code == 200:
                                st.success("Registro sincronizado en Google Sheets.")
                                st.cache_data.clear()
                                st.rerun()
                        except Exception:
                            st.error("Error de conexión al guardar.")
                    else:
                        st.warning("Escribe una descripción antes de enviar.")

        with col_admin:
            if not df_comentarios_filtrados.empty:
                st.subheader("Administración de Registros")
                opciones_admin = {
                    row["id"]: f"[{row['fecha']} {row['hora']}] - {str(row['comentario'])[:30]}..."
                    for _, row in df_comentarios_filtrados.iterrows()
                }
                id_seleccionado = st.selectbox(
                    "Selecciona un evento para Gestionar o Modificar:",
                    options=list(opciones_admin.keys()),
                    format_func=lambda x: opciones_admin[x]
                )
                registro_actual = df_comentarios_filtrados[
                    df_comentarios_filtrados['id'] == id_seleccionado
                ].iloc[0]

                mod_autor = st.text_input("Modificar Autor:", value=registro_actual['autor'])
                mod_comentario = st.text_area("Modificar Descripción:", value=registro_actual['comentario'])

                c_btn1, c_btn2 = st.columns(2)
                with c_btn1:
                    if st.button("💾 Actualizar Cambios"):
                        payload_upd = {
                            "action": "update", "id": id_seleccionado,
                            "autor": mod_autor, "comentario": mod_comentario
                        }
                        try:
                            res = requests.post(URL_API_BITACORA, json=payload_upd, timeout=15)
                            if res.status_code == 200:
                                st.success("Registro actualizado con éxito.")
                                st.cache_data.clear()
                                st.rerun()
                        except Exception:
                            st.error("Error de conexión al actualizar.")
                with c_btn2:
                    if st.button("❌ Eliminar Evento Seleccionado"):
                        payload_del = {"action": "delete", "id": id_seleccionado}
                        try:
                            res = requests.post(URL_API_BITACORA, json=payload_del, timeout=15)
                            if res.status_code == 200:
                                st.success("Registro eliminado.")
                                st.cache_data.clear()
                                st.rerun()
                        except Exception:
                            st.error("Error de conexión al eliminar.")

    # ═══════════════════════════════════════════════════════════════════════════
    # CSS FINAL: ocultar containers con key específica al imprimir
    # Streamlit genera atributos data-testid basados en el key del container
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("""
        <style>
            @media print {
                /* Ocultar el container del gráfico de barras + métricas */
                [data-testid="stVerticalBlockBorderWrapper"]:has([key="print_hide_section"]),
                div[data-testid="element-container"]:has(.print_hide_section) {
                    display: none !important;
                }
                /* Ocultar el container del formulario + administración */
                [data-testid="stVerticalBlockBorderWrapper"]:has([key="print_hide_admin"]),
                div[data-testid="element-container"]:has(.print_hide_admin) {
                    display: none !important;
                }
                /* Fallback: ocultar por key en cualquier wrapper */
                [key="print_hide_section"], [key="print_hide_admin"] {
                    display: none !important;
                }
                /* Ocultar todo container que tenga forms, botones, inputs */
                .stForm, [data-testid="stForm"] {
                    display: none !important;
                }
            }
        </style>
    """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"Error en el procesamiento del sistema: {e}")