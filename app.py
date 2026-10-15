import streamlit as st
import pandas as pd
import plotly.express as px
from influxdb_client import InfluxDBClient
from streamlit_autorefresh import st_autorefresh

# ==================================================
# CONFIGURACIÓN
# ==================================================
st.set_page_config(
    page_title="Mi espacio | IoT",
    page_icon="🌷",
    layout="wide",
    initial_sidebar_state="expanded"
)

URL = st.secrets["INFLUX_URL"]
TOKEN = st.secrets["INFLUX_TOKEN"]
ORG = st.secrets["INFLUX_ORG"]
BUCKET = st.secrets["INFLUX_BUCKET"]

# ==================================================
# ESTILO VISUAL
# ==================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Nunito', sans-serif;
}

.stApp {
    background: #F8F7FF;
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
    max-width: 1400px;
}

h1, h2, h3 {
    color: #302B50;
}

p, label {
    color: #65617D;
}

[data-testid="stMetric"] {
    background: white;
    padding: 22px 24px;
    border-radius: 20px;
    border: 1px solid #EAE6FA;
    box-shadow: 0 5px 18px rgba(80, 65, 130, 0.05);
}

[data-testid="stMetricLabel"] {
    color: #77718F;
    font-weight: 700;
}

[data-testid="stMetricValue"] {
    color: #39325F;
}

div[data-testid="stVerticalBlockBorderWrapper"] {
    background: white;
    border-radius: 20px;
}

.stPlotlyChart {
    border-radius: 18px;
}

div.stButton > button {
    background: #7969D8;
    color: white;
    border: none;
    border-radius: 12px;
    font-weight: 700;
}

div.stButton > button:hover {
    background: #6251BF;
    color: white;
}

section[data-testid="stSidebar"] {
    background: #F0EDFF;
}

hr {
    border-color: #E8E2F8;
}
</style>
""", unsafe_allow_html=True)

# ==================================================
# ENCABEZADO
# ==================================================
st.title("🌷 El clima de tu espacio")
st.markdown(
    "¡Hola! Aquí puedes descubrir cómo cambian "
    "la temperatura y la humedad de tu entorno."
)

st.write("")

# ==================================================
# FILTROS
# ==================================================
with st.sidebar:
    st.title("⚙️ Personaliza tu vista")
    st.caption("Elige qué datos quieres explorar.")

    opciones = {
        "Última hora": "-1h",
        "Últimas 6 horas": "-6h",
        "Últimas 12 horas": "-12h",
        "Últimas 24 horas": "-24h",
        "Últimos 7 días": "-7d"
    }

    seleccion = st.selectbox(
        "📅 ¿Qué periodo quieres ver?",
        list(opciones.keys()),
        index=3
    )

    refresco = st.select_slider(
        "🔄 Actualización automática",
        options=[0, 5, 10, 15, 30, 60],
        value=10,
        format_func=lambda x: "Desactivada" if x == 0
        else f"Cada {x} segundos"
    )

    st.divider()

    st.markdown("### 🎨 Guía de colores")
    st.markdown("🩷 Temperatura")
    st.markdown("🩵 Humedad")
    st.caption(
        "Los colores identifican cada variable. "
        "No representan por sí solos un nivel de riesgo."
    )

# Actualiza los datos sin crear un ciclo infinito de reruns.
if refresco > 0:
    st_autorefresh(
        interval=refresco * 1000,
        key="actualizacion_iot"
    )

# ==================================================
# CONSULTA A INFLUXDB
# ==================================================
@st.cache_data(ttl=5)
def cargar_datos(periodo):
    consulta = f'''
    from(bucket: "{BUCKET}")
      |> range(start: {periodo})
      |> filter(fn: (r) =>
          r["_field"] == "temperature" or
          r["_field"] == "humidity"
      )
      |> pivot(
          rowKey: ["_time"],
          columnKey: ["_field"],
          valueColumn: "_value"
      )
      |> keep(columns: ["_time", "temperature", "humidity"])
      |> sort(columns: ["_time"])
    '''

    with InfluxDBClient(
        url=URL,
        token=TOKEN,
        org=ORG,
        timeout=15000
    ) as cliente:
        resultado = cliente.query_api().query_data_frame(
            consulta,
            org=ORG
        )

    if isinstance(resultado, list):
        tablas = [t for t in resultado if not t.empty]
        if not tablas:
            return pd.DataFrame()
        datos = pd.concat(tablas, ignore_index=True)
    else:
        datos = resultado

    if datos.empty or "_time" not in datos.columns:
        return pd.DataFrame()

    datos["_time"] = pd.to_datetime(
        datos["_time"], errors="coerce", utc=True
    )

    for columna in ["temperature", "humidity"]:
        if columna not in datos.columns:
            datos[columna] = float("nan")
        datos[columna] = pd.to_numeric(
            datos[columna], errors="coerce"
        )

    datos = datos.dropna(subset=["_time"])
    datos = datos.sort_values("_time")
    datos = datos.drop_duplicates(subset=["_time"], keep="last")

    return datos.reset_index(drop=True)


# ==================================================
# CARGA Y ESTADOS
# ==================================================
try:
    df = cargar_datos(opciones[seleccion])

except Exception as error:
    st.error(
        "No pudimos conectar con los datos. "
        "Verifica la conexión, las credenciales y el bucket "
        "de InfluxDB."
    )
    with st.expander("Ver detalles técnicos"):
        st.code(str(error))
    st.stop()

if df.empty:
    st.info(
        "🌱 Todavía no hay mediciones para este periodo. "
        "Prueba con un rango de tiempo mayor o comprueba "
        "que tu sensor esté enviando información."
    )
    st.stop()

# ==================================================
# TARJETAS PRINCIPALES
# ==================================================
temperaturas = df["temperature"].dropna()
humedades = df["humidity"].dropna()

c1, c2, c3, c4 = st.columns(4)

if not temperaturas.empty:
    temp_actual = temperaturas.iloc[-1]
    c1.metric(
        "🌡️ Temperatura actual",
        f"{temp_actual:.1f} °C",
        help="Última medición de temperatura recibida."
    )
    c3.metric(
        "📈 Temperatura promedio",
        f"{temperaturas.mean():.1f} °C",
        help="Promedio de las mediciones del periodo seleccionado."
    )
else:
    temp_actual = None
    c1.metric("🌡️ Temperatura actual", "Sin datos")
    c3.metric("📈 Temperatura promedio", "Sin datos")

if not humedades.empty:
    humedad_actual = humedades.iloc[-1]
    c2.metric(
        "💧 Humedad actual",
        f"{humedad_actual:.1f} %",
        help="Última medición de humedad relativa."
    )
    c4.metric(
        "🫧 Humedad promedio",
        f"{humedades.mean():.1f} %",
        help="Promedio de las mediciones del periodo seleccionado."
    )
else:
    humedad_actual = None
    c2.metric("💧 Humedad actual", "Sin datos")
    c4.metric("🫧 Humedad promedio", "Sin datos")

st.write("")

# ==================================================
# INTERPRETACIÓN SENCILLA
# ==================================================
st.subheader("✨ ¿Qué está pasando?")

mensajes = []

for nombre, serie, unidad in [
    ("La temperatura", temperaturas, "°C"),
    ("La humedad", humedades, "%")
]:
    if len(serie) >= 2:
        diferencia = serie.iloc[-1] - serie.iloc[-2]

        if diferencia > 0:
            estado = "subió"
        elif diferencia < 0:
            estado = "bajó"
        else:
            estado = "se mantuvo estable"

        mensajes.append(
            f"**{nombre}** {estado} en la última comparación "
            f"registrada ({diferencia:+.2f} {unidad})."
        )

if mensajes:
    for mensaje in mensajes:
        st.markdown(f"🌱 {mensaje}")
else:
    st.caption(
        "Necesitamos más de una medición para describir los cambios."
    )

st.caption(
    "Estas descripciones comparan las últimas mediciones disponibles; "
    "no son diagnósticos ni alertas de seguridad."
)

st.write("")

# ==================================================
# GRÁFICA DE TEMPERATURA
# ==================================================
st.subheader("🩷 Así cambia la temperatura")
st.caption(
    "Observa cómo sube o baja la temperatura con el paso del tiempo."
)

if not temperaturas.empty:
    df_temp = df.dropna(subset=["temperature"])

    fig_temp = px.area(
        df_temp,
        x="_time",
        y="temperature",
        markers=True,
        color_discrete_sequence=["#F08CB8"],
        labels={
            "_time": "Momento",
            "temperature": "Temperatura (°C)"
        }
    )

    fig_temp.update_traces(
        fill="tozeroy",
        fillcolor="rgba(240, 140, 184, 0.13)",
        line=dict(width=3),
        marker=dict(size=6)
    )

    fig_temp.update_layout(
        template="plotly_white",
        height=350,
        margin=dict(l=15, r=15, t=20, b=15),
        hovermode="x unified",
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#57516F"),
        yaxis_title="Temperatura (°C)",
        xaxis_title="Hora y fecha"
    )

    fig_temp.update_xaxes(showgrid=False)
    fig_temp.update_yaxes(
        gridcolor="#F0ECF7",
        zeroline=False
    )

    st.plotly_chart(
        fig_temp,
        use_container_width=True
    )
else:
    st.info("Aún no hay mediciones de temperatura.")

# ==================================================
# GRÁFICA DE HUMEDAD
# ==================================================
st.subheader("🩵 Así cambia la humedad")
st.caption(
    "La humedad relativa indica cuánta humedad hay en el aire, "
    "expresada como porcentaje."
)

if not humedades.empty:
    df_hum = df.dropna(subset=["humidity"])

    fig_hum = px.line(
        df_hum,
        x="_time",
        y="humidity",
        markers=True,
        color_discrete_sequence=["#65BDEB"],
        labels={
            "_time": "Momento",
            "humidity": "Humedad relativa (%)"
        }
    )

    fig_hum.update_traces(
        line=dict(width=3),
        marker=dict(size=7)
    )

    fig_hum.update_layout(
        template="plotly_white",
        height=350,
        margin=dict(l=15, r=15, t=20, b=15),
        hovermode="x unified",
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#57516F"),
        yaxis_title="Humedad relativa (%)",
        xaxis_title="Hora y fecha"
    )

    fig_hum.update_xaxes(showgrid=False)
    fig_hum.update_yaxes(
        gridcolor="#E7F2FA",
        zeroline=False
    )

    st.plotly_chart(
        fig_hum,
        use_container_width=True
    )
else:
    st.info("Aún no hay mediciones de humedad.")

# ==================================================
# PROMEDIOS CADA 10 MINUTOS
# ==================================================
st.subheader("⏱️ Una mirada más tranquila")
st.caption(
    "Agrupamos las mediciones en intervalos de 10 minutos "
    "para facilitar la lectura de las tendencias."
)

df_promedio = (
    df.set_index("_time")[["temperature", "humidity"]]
    .resample("10min")
    .mean()
    .dropna(how="all")
    .reset_index()
)

if not df_promedio.empty:
    variable = st.radio(
        "¿Qué variable quieres explorar?",
        ["Temperatura", "Humedad"],
        horizontal=True
    )

    columna = (
        "temperature" if variable == "Temperatura"
        else "humidity"
    )
    color = (
        "#F08CB8" if variable == "Temperatura"
        else "#65BDEB"
    )
    unidad = "°C" if variable == "Temperatura" else "%"

    fig_prom = px.bar(
        df_promedio.dropna(subset=[columna]),
        x="_time",
        y=columna,
        color_discrete_sequence=[color],
        labels={
            "_time": "Intervalo",
            columna: f"Promedio ({unidad})"
        }
    )

    fig_prom.update_layout(
        template="plotly_white",
        height=300,
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#57516F"),
        xaxis_title="Hora y fecha",
        yaxis_title=f"Promedio ({unidad})"
    )

    fig_prom.update_traces(
        marker_line_width=0,
        opacity=0.85
    )

    st.plotly_chart(
        fig_prom,
        use_container_width=True
    )
else:
    st.caption("Aún no hay suficientes datos para agrupar.")

# ==================================================
# TABLA TÉCNICA OPCIONAL
# ==================================================
with st.expander("🔎 Ver datos detallados"):
    tabla = df.rename(columns={
        "_time": "Fecha y hora",
        "temperature": "Temperatura (°C)",
        "humidity": "Humedad (%)"
    })

    st.dataframe(
        tabla.sort_values("Fecha y hora", ascending=False),
        use_container_width=True,
        hide_index=True
    )

    st.download_button(
        "📥 Descargar mediciones en CSV",
        data=tabla.to_csv(index=False).encode("utf-8-sig"),
        file_name="mediciones_iot.csv",
        mime="text/csv"
    )

# ==================================================
# PIE DE PÁGINA
# ==================================================
st.divider()

st.markdown(
    "<div style='text-align:center; color:#8983A2;'>"
    "🌷 Mi espacio IoT · Datos de temperatura y humedad"
    "<br>Pequeños datos, grandes descubrimientos."
    "</div>",
    unsafe_allow_html=True
)
