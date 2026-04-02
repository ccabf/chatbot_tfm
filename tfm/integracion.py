import streamlit as st
from fase_3 import iniciar_chatbot_con_memoria # Importas la función que ya escribiste

# 1. Configuración de la interfaz
st.set_page_config(page_title="Camarero IA - Señorito Picofino", page_icon="👨‍🍳")

st.title("👨‍🍳 Asistente Inteligente")
st.markdown("### Bienvenido al Restaurante Señorito Picofino")
st.caption("Interfaz Web oficial del TFM - Desarrollada con RAG y Gemini 3.0 Flash")
st.markdown("---")

# 2. Inicialización robusta de la cadena (Solo una vez)
if "rag_chain" not in st.session_state:
    with st.spinner("Conectando con la base de datos vectorial..."):
        # Llamamos a iniciar_chatbot que devuelve la cadena LCEL
        st.session_state.rag_chain = iniciar_chatbot_con_memoria()

# 3. Inicializar historial de chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# 4. Renderizar historial de mensajes
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 5. Lógica del Chat (Entrada del usuario)
if prompt := st.chat_input("¿En qué puedo ayudarle hoy?"):
    # 1. Guardar mensaje del usuario
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Generar respuesta de la IA
    with st.chat_message("assistant"):
        with st.spinner("Consultando la carta y alérgenos..."):
            try:
                
                input_data = {"question": prompt} 
                configuracion = {"configurable": {"session_id": "sesion_tfm"}}
                
                respuesta = st.session_state.rag_chain.invoke(
                    input_data,     # Argumento 1: Diccionario con la pregunta
                    config=configuracion  # Argumento 2: Configuración de sesión
                )
                
                # Mostrar respuesta
                st.markdown(respuesta)
                st.session_state.messages.append({"role": "assistant", "content": respuesta})
                
            except Exception as e:
                st.error(f"Error técnico: {e}")
                st.info("Nota: Si el error persiste, verifica si tu cadena espera 'question' o 'input'.")