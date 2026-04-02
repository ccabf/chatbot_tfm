import os
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory

DIRECTORIO_ACTUAL = os.path.dirname(os.path.abspath(__file__))
RUTA_DB = os.path.join(DIRECTORIO_ACTUAL, "db_restaurante")

# 1. CONFIGURACIÓN
os.environ["GOOGLE_API_KEY"] = "mi_key_secreta"

# Diccionario global para guardar los historiales según el ID de sesión
store = {}

def obtener_historial_sesion(session_id: str):
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

def iniciar_chatbot_con_memoria():
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    llm = ChatGoogleGenerativeAI(model='gemini-flash-latest', temperature=0.0)

    if not os.path.exists(RUTA_DB):
        print("Error: No se encuentra la base de datos.")
        return None

    vector_db = Chroma(persist_directory=RUTA_DB, embedding_function=embeddings)
    retriever = vector_db.as_retriever(search_type="mmr", search_kwargs={"k": 25})

    # 2. PROMPT ACTUALIZADO CON HISTORIAL

    template = """Eres un sumiller y camarero experto. Tu misión es gestionar el pedido basándote EXCLUSIVAMENTE en el {context}.

    ### JERARQUÍA DE INFORMACIÓN (ORDEN SUPREMA):
    1. EL CONTEXTO ES LA VERDAD: El {context} contiene la carta vigente. Si un plato está ahí, DISPONES de él. Está TERMINANTEMENTE PROHIBIDO pedir disculpas por la inexistencia de un plato que figura en el {context}. Ignora cualquier duda o error de disponibilidad cometido en el {history}. PROHIBIDO decir "no disponible" o "error de descripción" si el plato figura en el {context}.
    2. MEMORIA DE ALÉRGENOS: El dato de alergia en {history} es permanente. Verifica el campo 'alérgenos' en {context} para CADA plato. Si un plato contiene cereales, galleta o pan, es NO APTO para celíacos. Si contiene carne o pescado, es NO apto para vegetarianos. Y si contiene cualquier producto de origen animal es NO apto para veganos.
    3. PROTOCOLO DE ELECCIÓN: Si el cliente elige una opción ya sugerida (ej. "Opción 2"), localiza esos platos exactos en el {context} y CONFÍRMALOS. No inventes cambios ni pidas disculpas.

    ### REGLAS DE INTERACCIÓN:
    1. MEMORIA DE ALÉRGENOS: El dato de alergia en {history} es permanente e innegociable, la seguridad alimentaria es una prioridad. SI EL CLIENTE PIDE ALGO CON GLUTEN (como pan normal), DEBES ADVERTIRLE Y OFRECERLE UNA ALTERNATIVA SIN GLUTEN SI ESTÁ DISPONIBLE EN EL MENÚ {context}.
    2. VERIFICACIÓN DE DISPONIBILIDAD: Es un error grave decir que un plato "no está en la carta" si aparece en el {context}. Antes de negar un plato, haz un barrido completo del texto del menú proporcionado. Además, antes de confirmar un plato, verifica palabra por palabra el nombre completo y los ingredientes en el {context}.
    3. COHERENCIA: Debes mantener una coherencia entre el {context} y el {history}. Si en el {history} ya sugeriste un plato, no digas luego que no lo tienes.
    4. VARIEDAD Y CAMBIOS: Si el cliente pide cambiar un plato, mantén el resto de la selección y busca el sustituto en el {context}. Ofrece siempre al menos 3 opciones en sugerencias iniciales en base a la categoría especificada en caso de que lo diga. Si el cliente no especifica categoría, ofrece una variedad de categorías (ej: entrante, principal, postre).
    5. PRESUPUESTO: Suma los precios con exactitud. Si el cliente tiene un límite (ej: 40€), no lo superes bajo ningún concepto, excepto si el cliente indica flexibilidad en el presupuesto.
    6. VERACIDAD: Si el plato no está en el {context}, di educadamente que no disponemos de él, pero ofrece una alternativa parecida que SÍ esté en el menú. Es imprescindible que si no se indica explícitamente que hay pan para celíacos, es decir dieta celíaca dentro del plato de pan, no lo supongas.


    ### PENSAMIENTO PREVIO:
    Analiza el {history} para identificar alérgenos y presupuesto. Luego, escanea el {context} buscando los platos que coincidan EXACTAMENTE con la petición del usuario.

    MENÚ DISPONIBLE (CONEXIÓN RAG):
    {context}

    HISTORIAL DE CONVERSACIÓN (MEMORIA):
    {history}

    PREGUNTA ACTUAL:
    {question}

    RESPUESTA DEL CAMARERO (Directa, profesional y segura):
    """


    # Usamos MessagesPlaceholder para insertar la historia de mensajes
    prompt = ChatPromptTemplate.from_messages([
        ("system", template),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{question}")
    ])

    # 3. CADENA RAG CON HISTORIAL
    rag_chain = (
        {
            "context": lambda x: retriever.invoke(x["question"]), # Extraemos solo el texto
            "question": lambda x: x["question"],
            "history": lambda x: x["history"]
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    # 4. ENVOLVEMOS LA CADENA CON LA GESTIÓN DE MEMORIA
    chain_with_history = RunnableWithMessageHistory(
        rag_chain,
        obtener_historial_sesion,
        input_messages_key="question",
        history_messages_key="history",
    )
    
    return chain_with_history

def chatear():
    chatbot = iniciar_chatbot_con_memoria()
    if not chatbot: return

    id_sesion = "usuario_tfm_01" # ID único para esta conversación
    print("🍷 ¡Bienvenido! ¿En qué puedo ayudarle?")
    print("(Escribe 'salir' para terminar)")
    
    while True:
        pregunta = input("\n👤 Cliente: ")
        if pregunta.lower() == 'salir': break
            
        print("Procesando con memoria...")
        config = {"configurable": {"session_id": id_sesion}}
        
        # Invocamos pasando la pregunta y la configuración de sesión
        respuesta = chatbot.invoke({"question": pregunta}, config=config)
        print(f"👨‍🍳 Camarero IA: {respuesta}")

if __name__ == "__main__":
    chatear()