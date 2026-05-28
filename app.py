import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, KeepTogether
)
import io
import tempfile
import os

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════════════════
st.set_page_config(page_title="Dashboard CTM — Complejo Térmico Mejillones", layout="wide")

st.markdown("""
    <style>
        /* ── Base ── */
        .stApp { background-color: #F8F9FB !important; }
        .block-container { padding-top: 1rem; padding-bottom: 2rem; max-width: 1200px; }

        /* ── Tipografía ── */
        h1 { color: #0F172A !important; font-size: 1.6rem !important; font-weight: 700 !important;
             font-family: 'Inter', 'Segoe UI', sans-serif !important; letter-spacing: -0.02em; }
        h2, h3 { color: #1E293B !important; font-family: 'Inter', 'Segoe UI', sans-serif !important; }
        p, span, label, div { font-family: 'Inter', 'Segoe UI', Roboto, sans-serif !important; }

        /* ── Sidebar ── */
        [data-testid="stSidebar"] { background-color: #0F172A !important; }
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3, [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] p, [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] div { color: #CBD5E1 !important; }
        [data-testid="stSidebar"] .stSuccess { background-color: #1E3A5F !important; border: none !important; }
        [data-testid="stSidebar"] .stSuccess p { color: #67E8F9 !important; }
        [data-testid="collapsedControl"] { display: none !important; }
        [data-testid="stSidebarCollapseButton"] { display: none !important; }
        button[kind="headerNoPadding"] { display: none !important; }
        .st-emotion-cache-1rtdyuf { display: none !important; }
        [data-testid="stSidebar"] > div:first-child > button { display: none !important; }

        /* ── Botones ── */
        .stButton>button { background-color: #2563EB !important; color: white !important;
            border-radius: 6px; border: none; font-weight: 600; font-size: 0.85rem; padding: 0.5rem 1.2rem; }
        .stButton>button:hover { background-color: #1D4ED8 !important; }

        /* ── Cards métricas ── */
        .metric-card { background: white; border: 1px solid #E2E8F0; padding: 1.2rem; border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
        .metric-label { font-size: 0.75rem !important; color: #64748B !important; font-weight: 600;
            text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.3rem; }
        .metric-value { font-size: 1.7rem !important; color: #0F172A !important; font-weight: 700; line-height: 1.2; }
        .metric-subtext { font-size: 0.8rem !important; color: #2563EB !important; font-weight: 600; margin-top: 0.3rem; }
        .metric-subtext-red { font-size: 0.8rem !important; color: #DC2626 !important; font-weight: 600; margin-top: 0.3rem; }

        /* ── DataFrames ── */
        .stDataFrame { border-radius: 8px; overflow: hidden; border: 1px solid #E2E8F0; }

        /* ── Separadores ── */
        hr { border-color: #E2E8F0 !important; }

        /* ── Sección header del dashboard ── */
        .dashboard-header { background: linear-gradient(135deg, #0F172A 0%, #1E3A5F 100%);
            padding: 1.5rem 2rem; border-radius: 10px; margin-bottom: 1.5rem; }
        .dashboard-header h1 { color: white !important; font-size: 1.4rem !important; margin: 0 !important; }
        .dashboard-header p { color: #94A3B8 !important; font-size: 0.85rem !important; margin: 0.3rem 0 0 0 !important; }
    </style>
""", unsafe_allow_html=True)

# ── Header profesional ──
st.markdown("""
    <div class="dashboard-header">
        <h1>Dashboard Generación — Complejo Térmico Mejillones</h1>
        <p>Control de despacho y desviaciones de potencia • Thermal Operations</p>
    </div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# CONEXIONES
# ═══════════════════════════════════════════════════════════════════════════════
URL_GOOGLE_SHEETS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTLvFug7yx0-2rF1nwhWt8q4l8mpGtO7Xpi3BK6lEvLw-L19bDQZIFXc4Fu63WHvip6PqarXxC1VJR3/pub?output=csv"
URL_API_BITACORA = "https://script.google.com/macros/s/AKfycbwY1XJ4t16zsLPDQfMFMY66IoZrbawJECpdJIfCTtDXvBKA23QS-w-ihp9a83hwBbWe/exec"

MAX_MW = 400.0
MAPEO_UNIDADES = {
    "Angamos Unidad 1": ("ANG01-R", "ANG01-P"),
    "Angamos Unidad 2": ("ANG02-R", "ANG02-P"),
    "Cochrane Unidad 1": ("CCH01-R", "CCH01-P"),
    "Cochrane Unidad 2": ("CCH02-R", "CCH02-P"),
}
NOMBRE_CORTO = {
    "Angamos Unidad 1": "Angamos 1", "Angamos Unidad 2": "Angamos 2",
    "Cochrane Unidad 1": "Cochrane 1", "Cochrane Unidad 2": "Cochrane 2",
}


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES DE DATOS
# ═══════════════════════════════════════════════════════════════════════════════
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
        st.sidebar.success("Datos en línea desde Google Sheets")
    except Exception:
        df = pd.read_csv("Planilla_Consolidada_GoogleSheets.csv", on_bad_lines="skip", engine="python")
        st.sidebar.warning("Modo offline: copia local")
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
    for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"]:
        try:
            return datetime.strptime(str_f[:len("2026-01-01T00:00:00")], fmt).strftime("%d/%m/%Y")
        except Exception:
            continue
    return str_f


def normalizar_hora_api(hora_raw):
    """
    Normaliza la hora a HH:MM. Maneja:
    - "17:01" → "17:01"
    - "'17:01" → "17:01" (prefijo de texto forzado)
    - "5:58" → "05:58"
    - "1899-12-30T17:01:00.000Z" → "17:01" (Date serializado por Sheets)
    - 0.709... → "17:01" (fracción de día de Sheets)
    """
    if not hora_raw:
        return "00:00"
    
    # Si es número (fracción de día de Google Sheets)
    try:
        num = float(hora_raw)
        if 0 <= num < 1:
            total_min = round(num * 24 * 60)
            h = total_min // 60
            m = total_min % 60
            return f"{h:02d}:{m:02d}"
    except (ValueError, TypeError):
        pass
    
    str_h = str(hora_raw).strip().lstrip("'")  # Quitar prefijo de texto forzado
    
    # Caso ISO con T
    if "T" in str_h:
        try:
            componente = str_h.split("T")[1].replace("Z", "")
            # Puede tener offset como +00:00, tomar solo HH:MM
            return componente[:5]
        except Exception:
            pass
    
    # Caso directo "17:01" o "5:58"
    if ":" in str_h:
        partes = str_h.split(":")
        try:
            return f"{int(partes[0]):02d}:{int(partes[1][:2]):02d}"
        except Exception:
            pass
    
    return str_h[:5]


def obtener_bitacora_global():
    try:
        resp = requests.get(URL_API_BITACORA, timeout=15, headers={"Accept": "application/json"})
        if resp.status_code != 200:
            return pd.DataFrame(columns=["id", "fecha", "hora", "unidad", "autor", "comentario"])
        texto = resp.text.strip()
        if not texto.startswith("[") and not texto.startswith("{"):
            st.sidebar.warning("Bitácora: API sin JSON válido")
            return pd.DataFrame(columns=["id", "fecha", "hora", "unidad", "autor", "comentario"])
        raw = resp.json()
        if raw and len(raw) > 0:
            df = pd.DataFrame(raw)
            for c in ["id", "fecha", "hora", "unidad", "autor", "comentario"]:
                if c not in df.columns:
                    df[c] = ""
            df['id'] = df['id'].astype(str)
            df['fecha'] = df['fecha'].apply(normalizar_fecha_api)
            df['hora'] = df['hora'].apply(normalizar_hora_api)
            df['unidad'] = df['unidad'].astype(str).str.strip()
            df['autor'] = df['autor'].astype(str).str.strip()
            df['comentario'] = df['comentario'].astype(str).str.strip()
            return df
    except Exception as e:
        st.sidebar.warning(f"Bitácora: {e}")
    return pd.DataFrame(columns=["id", "fecha", "hora", "unidad", "autor", "comentario"])


# ═══════════════════════════════════════════════════════════════════════════════
# GENERADOR DE REPORTE PDF
# ═══════════════════════════════════════════════════════════════════════════════
def generar_reporte_pdf(df_data, df_bitacora, fecha_ini, fecha_fin):
    """Genera PDF landscape estilo presentación: portada + 1 página por unidad."""
    tmpdir = tempfile.mkdtemp()
    pdf_path = os.path.join(tmpdir, "Reporte_CTM.pdf")

    df_rango = df_data[(df_data['Fecha'].dt.date >= fecha_ini) & (df_data['Fecha'].dt.date <= fecha_fin)].copy()
    semana_num = pd.Timestamp(fecha_fin).isocalendar()[1]
    rango_str = f"{fecha_ini.strftime('%d/%m/%Y')} — {fecha_fin.strftime('%d/%m/%Y')}"
    ahora = datetime.now().strftime("%d/%m/%Y %H:%M")

    # ── Gráficos matplotlib ──
    imgs = {}
    for nombre, (col_r, col_p) in MAPEO_UNIDADES.items():
        if col_r not in df_rango.columns or col_p not in df_rango.columns:
            continue
        fig, ax = plt.subplots(figsize=(9.5, 2.8), dpi=150)
        real = df_rango[col_r].fillna(0)
        prog = df_rango[col_p].fillna(0)
        ax.plot(df_rango['Fecha'], prog, color='#3CD6F1', linewidth=1.8, label='Potencia Programada MW')
        ax.plot(df_rango['Fecha'], real, color='#3B66FF', linewidth=1.8, label='Potencia Real MW')
        ax.fill_between(df_rango['Fecha'], 0, real, alpha=0.06, color='#3B66FF')
        ax.set_ylabel('MW', fontsize=9, color='#374151')
        ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.22), ncol=2,
            fontsize=7.5, framealpha=0.9, edgecolor='#E2E8F0')
        ax.grid(True, alpha=0.2, linewidth=0.5)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%a %d/%m'))
        ax.xaxis.set_major_locator(mdates.DayLocator())
        ax.tick_params(axis='both', labelsize=7.5, colors='#64748B')
        ax.set_ylim(bottom=0)
        ax.set_xlim(df_rango['Fecha'].min(), df_rango['Fecha'].max())
        for spine in ax.spines.values():
            spine.set_edgecolor('#E2E8F0')
            spine.set_linewidth(0.5)
        plt.tight_layout()
        p = os.path.join(tmpdir, f"chart_{col_r}.png")
        fig.savefig(p, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        imgs[nombre] = p

    # ── PDF con ReportLab ──
    doc = SimpleDocTemplate(pdf_path, pagesize=landscape(letter),
        topMargin=0.4*inch, bottomMargin=0.4*inch, leftMargin=0.5*inch, rightMargin=0.5*inch)

    s_title = ParagraphStyle('T', fontSize=28, leading=34, fontName='Helvetica-Bold',
        textColor=HexColor('#0F172A'), alignment=TA_CENTER, spaceAfter=6)
    s_sub = ParagraphStyle('ST', fontSize=14, leading=18, fontName='Helvetica',
        textColor=HexColor('#64748B'), alignment=TA_CENTER)
    s_slide = ParagraphStyle('SL', fontSize=16, leading=20, fontName='Helvetica-Bold',
        textColor=HexColor('#0F172A'), spaceAfter=4)
    s_ev_fecha = ParagraphStyle('EF', fontSize=9, leading=13, fontName='Helvetica-Bold',
        textColor=HexColor('#2563EB'), spaceBefore=4)
    s_ev_desc = ParagraphStyle('ED', fontSize=9, leading=13, fontName='Helvetica',
        textColor=HexColor('#374151'))
    s_sin = ParagraphStyle('SN', fontSize=10, leading=14, fontName='Helvetica-Oblique',
        textColor=HexColor('#94A3B8'), spaceBefore=6)
    s_foot = ParagraphStyle('F', fontSize=7, textColor=HexColor('#94A3B8'), alignment=TA_CENTER)

    story = []

    # ── PORTADA ──
    story.append(Spacer(1, 1.8*inch))
    story.append(Paragraph("Complejo T\u00e9rmico Mejillones", s_title))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Thermal Operations", s_sub))
    story.append(Spacer(1, 30))
    line = Table([['']], colWidths=[3*inch], rowHeights=[3])
    line.setStyle(TableStyle([('BACKGROUND', (0,0), (0,0), HexColor('#2563EB'))]))
    wrap = Table([[line]], colWidths=[9*inch])
    wrap.setStyle(TableStyle([('ALIGN', (0,0), (0,0), 'CENTER')]))
    story.append(wrap)
    story.append(Spacer(1, 20))
    story.append(Paragraph(f"Highlight Semana {semana_num}", ParagraphStyle('HW', fontSize=16,
        leading=20, fontName='Helvetica-Bold', textColor=HexColor('#0F172A'), alignment=TA_CENTER)))
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"Periodo: {rango_str}", ParagraphStyle('PR', fontSize=11,
        leading=14, fontName='Helvetica', textColor=HexColor('#94A3B8'), alignment=TA_CENTER)))
    story.append(PageBreak())

    # ── PÁGINAS POR UNIDAD ──
    for nombre_completo, img_path in imgs.items():
        nombre_corto = NOMBRE_CORTO.get(nombre_completo, nombre_completo)
        story.append(Paragraph(nombre_corto, s_slide))
        story.append(Spacer(1, 4))
        story.append(Image(img_path, width=9.5*inch, height=2.8*inch))
        story.append(Spacer(1, 10))

        # Novedades de bitácora
        if not df_bitacora.empty:
            df_bit_parsed = df_bitacora.copy()
            df_bit_parsed['fecha_parsed'] = pd.to_datetime(df_bit_parsed['fecha'], format='%d/%m/%Y', errors='coerce')
            eventos = df_bit_parsed[
                (df_bit_parsed['unidad'] == nombre_completo) &
                (df_bit_parsed['fecha_parsed'].dt.date >= fecha_ini) &
                (df_bit_parsed['fecha_parsed'].dt.date <= fecha_fin)
            ].sort_values('fecha_parsed')
        else:
            eventos = pd.DataFrame()

        if not eventos.empty:
            for _, ev in eventos.iterrows():
                story.append(Paragraph(f"{ev['fecha']} — {ev['hora']} hrs", s_ev_fecha))
                story.append(Paragraph(str(ev['comentario']), s_ev_desc))
        else:
            story.append(Paragraph("Sin novedades", s_sin))

        story.append(Spacer(1, 14))
        story.append(Paragraph(f"Reporte generado: {ahora}", s_foot))
        story.append(PageBreak())

    story.pop()  # Quitar último PageBreak
    doc.build(story)
    return pdf_path


# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
try:
    df_metrics = cargar_datos_produccion()
    columnas = list(df_metrics.columns)
    unidades_detectadas = {}
    for nombre, (r_tag, p_tag) in MAPEO_UNIDADES.items():
        col_r = [c for c in columnas if c.upper() == r_tag.upper()]
        col_p = [c for c in columnas if c.upper() == p_tag.upper()]
        if col_r and col_p:
            unidades_detectadas[nombre] = (col_r[0], col_p[0])

    # ── Sidebar ──
    st.sidebar.markdown("### Filtros de Operación")
    seleccion_unidad = st.sidebar.selectbox("Unidad:", list(unidades_detectadas.keys()))
    col_real, col_prog = unidades_detectadas[seleccion_unidad]

    fecha_min_datos = df_metrics['Fecha'].min().date()
    fecha_max_datos = df_metrics['Fecha'].max().date()
    fecha_inicio_defecto = max(fecha_min_datos, fecha_max_datos - timedelta(days=7))

    rango_fechas = st.sidebar.date_input("Rango de Análisis:",
        value=(fecha_inicio_defecto, fecha_max_datos),
        min_value=fecha_min_datos, max_value=fecha_max_datos, format="DD/MM/YYYY")

    if isinstance(rango_fechas, tuple) and len(rango_fechas) == 2:
        inicio, fin = rango_fechas
        df_filtrado = df_metrics[
            (df_metrics['Fecha'].dt.date >= inicio) & (df_metrics['Fecha'].dt.date <= fin)
        ].copy()
    else:
        inicio, fin = fecha_inicio_defecto, fecha_max_datos
        df_filtrado = df_metrics.copy()

    serie_real = df_filtrado[col_real].fillna(0.0)
    serie_prog = df_filtrado[col_prog].fillna(0.0)
    df_filtrado['Desviacion_MW'] = serie_real - serie_prog
    df_filtrado['Desviacion_Abs_MW'] = df_filtrado['Desviacion_MW'].abs()

    # ── Bitácora (cargar una vez) ──
    df_comentarios = obtener_bitacora_global()

    # ── Sidebar: Reportabilidad ──
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Reportabilidad")

    if st.sidebar.button("📄 Descargar Reporte PDF"):
        with st.spinner("Generando reporte..."):
            pdf_path = generar_reporte_pdf(df_metrics, df_comentarios, inicio, fin)
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
            semana = pd.Timestamp(fin).isocalendar()[1]
            st.sidebar.download_button(
                label="⬇️ Descargar PDF",
                data=pdf_bytes,
                file_name=f"Reporte_CTM_Semana_{semana}.pdf",
                mime="application/pdf"
            )

    # ═══════════════════════════════════════════════════════════════════════════
    # GRÁFICO PRINCIPAL
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown(f"#### Monitoreo de Potencia — {seleccion_unidad}")
    mostrar_achurado = st.checkbox("Mostrar área de desviación", value=False)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_filtrado['Fecha'], y=serie_prog,
        name='Programada', line=dict(color='#3CD6F1', width=2.5)))
    if mostrar_achurado:
        fig.add_trace(go.Scatter(x=df_filtrado['Fecha'], y=serie_real,
            name='Real', line=dict(color='#2563EB', width=2.5),
            fill='tonexty', fillcolor='rgba(37, 99, 235, 0.1)'))
    else:
        fig.add_trace(go.Scatter(x=df_filtrado['Fecha'], y=serie_real,
            name='Real', line=dict(color='#2563EB', width=2.5)))
    fig.update_layout(
        title="", xaxis_title="", yaxis_title="Potencia (MW)",
        template="plotly_white", hovermode="x unified",
        margin=dict(t=10, b=40, l=50, r=20), height=380,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        font=dict(family="Inter, Segoe UI, sans-serif", color="#374151")
    )
    st.plotly_chart(fig, use_container_width=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # ANÁLISIS DE DESVIACIÓN
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("#### Análisis de Desviación")
    fig_bar = go.Figure()
    colores = ['#10B981' if v >= 0 else '#EF4444' for v in df_filtrado['Desviacion_MW']]
    fig_bar.add_trace(go.Bar(x=df_filtrado['Fecha'], y=df_filtrado['Desviacion_MW'],
        marker_color=colores, name='Delta MW'))
    fig_bar.update_layout(
        title="", xaxis_title="", yaxis_title="Desviación (MW)",
        template="plotly_white", hovermode="x unified",
        margin=dict(t=10, b=40, l=50, r=20), height=280,
        font=dict(family="Inter, Segoe UI, sans-serif", color="#374151")
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # INDICADORES
    # ═══════════════════════════════════════════════════════════════════════════
    desvio_medio = df_filtrado['Desviacion_Abs_MW'].mean() if not df_filtrado.empty else 0.0
    energia_total = df_filtrado['Desviacion_Abs_MW'].sum() if not df_filtrado.empty else 0.0
    if not df_filtrado.empty and not df_filtrado['Desviacion_MW'].isna().all():
        idx_max = df_filtrado['Desviacion_Abs_MW'].idxmax()
        val_max = df_filtrado.loc[idx_max, 'Desviacion_MW']
        desvio_max = abs(val_max)
        sub_html = ("<div class='metric-subtext'>▲ Sobre-generación</div>" if val_max >= 0
                     else "<div class='metric-subtext-red'>▼ Sub-generación</div>")
    else:
        desvio_max, sub_html = 0.0, ""

    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Desviación Media</div>'
            f'<div class="metric-value">{desvio_medio:.2f} MW</div></div>', unsafe_allow_html=True)
    with m2:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Desviación Máxima</div>'
            f'<div class="metric-value">{desvio_max:.2f} MW</div>{sub_html}</div>', unsafe_allow_html=True)
    with m3:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Energía Desviada</div>'
            f'<div class="metric-value">{energia_total:.1f} MWh</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # BITÁCORA
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("#### Bitácora de Novedades Operacionales")

    if not df_comentarios.empty:
        df_comentarios['fecha_parsed'] = pd.to_datetime(df_comentarios['fecha'], format='%d/%m/%Y', errors='coerce')
        df_comentarios_filtrados = df_comentarios[
            (df_comentarios['unidad'].str.strip() == seleccion_unidad) &
            (df_comentarios['fecha_parsed'].dt.date >= inicio) &
            (df_comentarios['fecha_parsed'].dt.date <= fin)
        ].copy()
    else:
        df_comentarios_filtrados = pd.DataFrame()

    # Tabla de eventos
    st.markdown(f"**Historial — {seleccion_unidad}**")
    if not df_comentarios_filtrados.empty:
        df_mostrar = df_comentarios_filtrados.sort_values(by=["fecha_parsed", "hora"], ascending=[True, True])
        st.dataframe(df_mostrar[['fecha', 'hora', 'autor', 'comentario']],
            column_config={"fecha": "Fecha", "hora": "Hora", "autor": "Jefe de Turno", "comentario": "Novedad"},
            use_container_width=True, hide_index=True)
    else:
        st.info("Sin novedades para esta unidad en el rango seleccionado.")

    # Formulario y administración
    col_form, col_admin = st.columns([1, 1.8])

    with col_form:
        st.markdown("**Registrar Novedad**")
        with st.form("form_global", clear_on_submit=True):
            fecha_evento = st.date_input("Fecha:", value=fecha_max_datos, format="DD/MM/YYYY")
            hora_evento = st.text_input("Hora (HH:MM):", value="", max_chars=5, placeholder="Ej: 17:01")
            operador = st.text_input("Jefe de Turno:", value="")
            novedad = st.text_area("Descripción:")
            if st.form_submit_button("Guardar"):
                # Validar y normalizar hora
                hora_limpia = hora_evento.strip()
                hora_valida = False
                if ":" in hora_limpia:
                    try:
                        partes = hora_limpia.split(":")
                        h, m = int(partes[0]), int(partes[1])
                        if 0 <= h <= 23 and 0 <= m <= 59:
                            hora_limpia = f"{h:02d}:{m:02d}"
                            hora_valida = True
                    except (ValueError, IndexError):
                        pass
                
                if not hora_valida:
                    st.warning("Formato de hora inválido. Usa HH:MM (ej: 17:01)")
                elif not novedad.strip():
                    st.warning("Escribe una descripción.")
                else:
                    payload = {"action": "add", "id": str(int(datetime.now().timestamp() * 1000)),
                        "fecha": fecha_evento.strftime("%d/%m/%Y"), "hora": hora_limpia,
                        "unidad": seleccion_unidad, "autor": operador, "comentario": novedad.strip()}
                    try:
                        res = requests.post(URL_API_BITACORA, json=payload, timeout=15)
                        if res.status_code == 200:
                            st.success("Guardado."); st.cache_data.clear(); st.rerun()
                    except Exception:
                        st.error("Error de conexión.")

    with col_admin:
        if not df_comentarios_filtrados.empty:
            st.markdown("**Administración**")
            opciones = {row["id"]: f"[{row['fecha']} {row['hora']}] {str(row['comentario'])[:35]}..."
                for _, row in df_comentarios_filtrados.iterrows()}
            sel = st.selectbox("Evento:", options=list(opciones.keys()), format_func=lambda x: opciones[x])
            reg = df_comentarios_filtrados[df_comentarios_filtrados['id'] == sel].iloc[0]
            m_autor = st.text_input("Autor:", value=reg['autor'])
            m_com = st.text_area("Descripción:", value=reg['comentario'])
            c1, c2 = st.columns(2)
            with c1:
                if st.button("💾 Actualizar"):
                    try:
                        res = requests.post(URL_API_BITACORA, json={"action": "update", "id": sel,
                            "autor": m_autor, "comentario": m_com}, timeout=15)
                        if res.status_code == 200:
                            st.success("Actualizado."); st.cache_data.clear(); st.rerun()
                    except Exception:
                        st.error("Error.")
            with c2:
                if st.button("❌ Eliminar"):
                    try:
                        res = requests.post(URL_API_BITACORA, json={"action": "delete", "id": sel}, timeout=15)
                        if res.status_code == 200:
                            st.success("Eliminado."); st.cache_data.clear(); st.rerun()
                    except Exception:
                        st.error("Error.")

except Exception as e:
    st.error(f"Error del sistema: {e}")