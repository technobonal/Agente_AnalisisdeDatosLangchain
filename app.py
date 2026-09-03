import streamlit as st
import pandas as pd
import os

from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from langchain.agents import create_react_agent, AgentExecutor
from herramientas import crear_herramientas

# Inicia la aplicación
st.set_page_config(page_title="Asistente de Análisis de Datos con IA", layout="centered")
st.title("🦜 Asistente de Análisis de Datos con IA")

st.info("""
Este asistente utiliza un agente, creado con Langchain, para ayudarte a explorar, analizar y visualizar datos de forma interactiva.
Basta con subir un archivo CSV y podrás generar reportes y gráficos automáticamente.
""")

# Upload de CSV
st.markdown("### 📁 Realiza la carga de tu archivo CSV")
archivo_cargado = st.file_uploader("Selecciona un archivo CSV", type="csv", label_visibility="collapsed")

if archivo_cargado:
    df = pd.read_csv(archivo_cargado)
    st.success("Archivo cargado exitosamente!")
    st.markdown("### 🔍 Primeras filas de tu conjunto de datos")
    st.dataframe(df.head())

    # =====================================================================
    # CASCADA DE MODELOS (GROQ)
    # Nivel 1: openai/gpt-oss-120b (Principal)
    # Nivel 2: openai/gpt-oss-20b (Respaldo 1)
    # Nivel 3: qwen/qwen3.6-27b (Respaldo 2)
    # =====================================================================
    
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    
    #CASCADA DE MODELOS (GROQ OFICIAL - IDs ESTABLES)
    # =====================================================================
    
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    
   # =====================================================================
    # CASCADA DE MODELOS (USANDO TU SERVIDOR/PROXY PERSONALIZADO)
    # =====================================================================
    from langchain_openai import ChatOpenAI
    
    # La API KEY que usa tu servidor
    API_KEY = os.getenv("GROQ_API_KEY")
    
    # IMPORTANTE: Aquí debes poner la URL de tu servidor proxy o LiteLLM.
    # Si no la sabes, revisa a dónde apuntaba tu litellm en DataqualityAgent.
    # Si usas un servicio en la nube genérico, pon su URL (ej: "https://api.tu-servidor.com/v1")
    BASE_URL = os.getenv("API_BASE_URL", "https://api.groq.com/openai/v1") # <-- CAMBIA ESTO POR TU URL
    
    # 1. Principal (El que acabas de mencionar)
    modelo_principal = ChatOpenAI(
        api_key=API_KEY,
        base_url=BASE_URL,
        model="openai/gpt-oss-120b",
        temperature=0
    )
    
    # 2. Respaldo 1
    respaldo_1 = ChatOpenAI(
        api_key=API_KEY,
        base_url=BASE_URL,
        model="openai/gpt-oss-20b",
        temperature=0
    )

    # 3. Respaldo 2 (Qwen)
    respaldo_2 = ChatOpenAI(
        api_key=API_KEY,
        base_url=BASE_URL,
        model="qwen/qwen3.6-27b", # Con el prefijo qwen/
        temperature=0
    )

    # Encadenamos
    llm = modelo_principal.with_fallbacks([respaldo_1, respaldo_2])

    # Herramientas
    tools = crear_herramientas(df)

    # Prompt react
    df_head = df.head().to_markdown()

    prompt_react_es = PromptTemplate(
        input_variables=["input", "agent_scratchpad", "tools", "tool_names"],
        partial_variables={"df_head": df_head},
        template="""
            Eres un asistente que responde en castellano.

            Tienes acceso a un dataframe pandas llamado `df`.
            Aquí están las primeras filas del DataFrame, obtenidas usando `df.head().to_markdown()`:
            
            {df_head}

            Responde a las siguientes preguntas de la mejor manera posible.
            Para este fin, tienes acceso a las siguientes herramientas:

            {tools}

            Usa el siguiente formato:

            Question: La pregunta de entrada que debes responder
            Thought: Debes siempre pensar en lo que debes hacer
            Action: La acción que será ejecutada, debe ser una de las [{tool_names}]
            Action Input: La entrada para la acción
            Observation: El resultado de la acción
            ... (este Thought/Action/Action Input/Observation puede repetirse N veces)
            Thought: Ahora sé la respuesta final
            Final Answer: La respuesta final para la pregunta de entrada inicial.

            Comienza!

            Question: {input}
            Thought: {agent_scratchpad}
        """
        )

    # Agente
    agente = create_react_agent(llm=llm, tools=tools, prompt=prompt_react_es)
    orquestador = AgentExecutor(
        agent=agente,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=10,
        max_execution_time=120
    )

    # ACCIONES RÁPIDAS
    st.markdown("---")
    st.markdown("## ⚡ Acciones rápidas")

    if st.button("📄 Reporte de Informaciones Generales", key="boton_reporte_general"):
        with st.spinner("Analizando datos... 🦜"):
            respuesta = orquestador.invoke({"input": "Quiero un reporte con informaciones sobre los datos"})
            st.session_state['reporte_general'] = respuesta["output"]

    if 'reporte_general' in st.session_state:
        with st.expander("Resultado: Reporte de Informaciones Generales"):
            st.markdown(st.session_state['reporte_general'])
            st.download_button(
                label="📥 Descargar Reporte",
                data=st.session_state['reporte_general'],
                file_name="reporte_informaciones_generales.md",
                mime="text/markdown"
            )

    if st.button("📄 Reporte de estadísticas descriptivas", key="boton_reporte_estadisticas"):
        with st.spinner("Analizando datos... 🦜"):
            respuesta = orquestador.invoke({"input": "Quiero un Reporte de estadísticas descriptivas"})
            st.session_state['reporte_estadisticas'] = respuesta["output"]

    if 'reporte_estadisticas' in st.session_state:
        with st.expander("Resultado: Reporte de estadísticas descriptivas"):
            st.markdown(st.session_state['reporte_estadisticas'])
            st.download_button(
                label="📥 Descargar Reporte",
                data=st.session_state['reporte_estadisticas'],
                file_name="reporte_estadisticas_descritivas.md",
                mime="text/markdown"  
            )
   
    # PERGUNTA SOBRE LOS DATOS
    st.markdown("---")
    st.markdown("## 🔎 Preguntas sobre los datos")
    pregunta_sobre_datos = st.text_input("Realiza una pregunta sobre los datos (ej: 'Cuál es el promedio de tiempo de entrega?')")
    if st.button("Responder pregunta", key="responder_pregunta_datos"):
        with st.spinner("Analizando los datos 🦜"):
            respuesta = orquestador.invoke({"input": pregunta_sobre_datos})
            st.markdown((respuesta["output"]))

    # GENERACIÓN DE GRÁFICOS
    st.markdown("---")
    st.markdown("## 📊 Crear gráfico con base en una pregunta")
    pregunta_grafico = st.text_input("Qué deseas visualizar? (ej: 'Genera un gráfico del promedio de tiempo de entrega por clima.')")
    if st.button("Generar gráfico", key="generar_grafico"):
        with st.spinner("Generando el gráfico 🦜"):
            orquestador.invoke({"input": pregunta_grafico})