import streamlit as st
import pandas as pd

# BD NMEX
NMEX = st.secrets["URL_NMEX"]
NTE = st.secrets["URL_NTE"]

df_base = pd.read_csv(NMEX)

# Funciones para cálculo de PVP
def calcular_pvp_func(F, R, I, M):
    return (1 + 0.85 * R) * (F * 6.96 * (1 + I)) / (0.84 - 0.84 * M)

def calcular_pvp_func_nte(F, R, I, M):
    return (1 + 0.85 * R) * (F * 6.96 * (1 + I)) / (0.84 - 0.84 * M)

def redondeo_especial(valor):
    if valor < 1:
        return 9
    else:
        return int((valor - (valor % 10)) + 9)

def limpiar_fob(valor):
    if pd.isna(valor) or valor == "No encontrado":
        return None
    try:
        return float(valor)
    except ValueError:
        return None
    
# Interfaz de Streamlit
st.title("🔎 Calculadora PVP Parts sobre FOB")

# Selección de origen de datos
origen = st.radio("Seleccionar base de datos para la búsqueda:", ["NMEX", "NTE"], index=0)

# Entrada de usuario
st.write("Ingrese los PART NUMBER separados por espacios.")
input_text = st.text_area("Ingrese aquí la lista:")

# Ingreso de parámetros adicionales
tasa_remesas = st.number_input("Tasa de remesas (%)", min_value=0.0, max_value=200.0, value=85.0) / 100
margen = st.number_input("Margen bruto post-remesas (%)", min_value=0.0, max_value=150.0, value=30.0) / 100

# Botón para ejecutar la búsqueda
ejecutar_busqueda = st.button("Buscar y Calcular PVP")

if ejecutar_busqueda:
    # Importar la base de datos según el origen seleccionado
    if origen == "NMEX":
        columna_fob = "FOB_NMEX"
    elif origen == "NTE":
        df_base = pd.read_csv(NTE)
        columna_fob = "FOB_NTE"

    # Función para buscar FOB
    def buscar_fob(np_lista, df_base, columna_fob):
        df_resultados = df_base[df_base["NP"].isin(np_lista)].copy()
        df_resultados = df_resultados[["NP", columna_fob]]
        df_resultados = df_resultados.fillna(0)
        return df_resultados

    # Función para calcular PVP
    def calcular_pvp(df_resultados, origen, tasa_remesas, margen):
        df_no_encontrados = df_resultados[df_resultados[columna_fob] == 0]

        np_no_en_base = [np for np in np_lista if np not in df_base["NP"].tolist()]
        df_no_en_base = pd.DataFrame({
            "NP": np_no_en_base,
            columna_fob: [0] * len(np_no_en_base)})

        df_no_encontrados = pd.concat([df_no_encontrados, df_no_en_base], ignore_index=True)
        df_no_encontrados = df_no_encontrados.drop_duplicates()

        df_resultados = df_resultados[df_resultados[columna_fob] > 0]
        
        if origen == "NMEX":
            df_resultados["PVP Marítimo"] = df_resultados[columna_fob].apply(
                lambda x: redondeo_especial(calcular_pvp_func(x, tasa_remesas, 0.20, margen))
            )
            df_resultados["PVP Aéreo"] = df_resultados[columna_fob].apply(
                lambda x: redondeo_especial(calcular_pvp_func(x, tasa_remesas, 0.90, margen))
            )
        elif origen == "NTE":
            df_resultados["PVP Marítimo"] = df_resultados[columna_fob].apply(
                lambda x: redondeo_especial(calcular_pvp_func_nte(x * 1.3, tasa_remesas, 0.35, margen))
            )
            df_resultados["PVP Aéreo"] = df_resultados[columna_fob].apply(
                lambda x: redondeo_especial(calcular_pvp_func_nte(x * 1.3, tasa_remesas, 0.95, margen))
            )
        
        return df_resultados, df_no_encontrados

    np_lista = [item.strip() for item in input_text.split() if item.strip()]
    if len(np_lista) == 0:
        st.error("❌ No has ingresado ningún PART NUMBER.")
    else:
        df_resultados = buscar_fob(np_lista, df_base, columna_fob)
        df_resultados, df_no_encontrados = calcular_pvp(df_resultados, origen, tasa_remesas, margen)
        
        st.dataframe(df_resultados)

        if not df_no_encontrados.empty:        
            st.warning("Los siguientes PART NUMBER no se encontraron o tienen valor cero. Consulte con el proveedor:")
            st.dataframe(df_no_encontrados)

st.title("Simulador PVP vs FOB")

# Entrada de FOBs
st.subheader("Ingresa hasta 5 FOBs")
fobs = []
for i in range(5):
    fob = st.text_input(f"FOB {i+1}", "")
    if fob:
        fobs.append([fob])

if fobs:
    df_fobs = pd.DataFrame(fobs, columns=["FOB"])
    
    # Entrada de parámetros
    st.subheader("Parámetros de cálculo")
    tasa_remesas = st.number_input("Tasa de remesas (%)", min_value=0.0, max_value=500.0, value=85.0, key="tasa_remesas_sim") / 100
    margen_bruto = st.number_input("Margen bruto post-remesas (%)", min_value=0.0, max_value=150.0, value=30.0, key="margen_bruto_sim") / 100
    incremento_maritimo = st.number_input("Índice de incremento para PVP Marítimo (%)", min_value=0.0, max_value=100.0, value=20.0, key="inc_maritimo_sim") / 100
    incremento_aereo = st.number_input("Índice de incremento para PVP Aéreo (%)", min_value=0.0, max_value=100.0, value=80.0, key="inc_aereo_sim") / 100

    # Cálculo de PVPs
    df_fobs["PVP Marítimo"] = df_fobs["FOB"].apply(
        lambda x: redondeo_especial(calcular_pvp_func(limpiar_fob(x), tasa_remesas, incremento_maritimo, margen_bruto))
        if limpiar_fob(x) is not None else "No calculado"
    )
    df_fobs["PVP Aéreo"] = df_fobs["FOB"].apply(
        lambda x: redondeo_especial(calcular_pvp_func(limpiar_fob(x), tasa_remesas, incremento_aereo, margen_bruto))
        if limpiar_fob(x) is not None else "No calculado"
    )
    
    st.subheader("Resultados")
    st.dataframe(df_fobs)
