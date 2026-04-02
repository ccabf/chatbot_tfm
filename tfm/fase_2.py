import json
import os
import shutil
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
import google.genai as genai

os.environ["GOOGLE_API_KEY"] = "mi_key_secreta"
DIRECTORIO_ACTUAL = os.path.dirname(os.path.abspath(__file__))

ruta_json = os.path.join(DIRECTORIO_ACTUAL, "menu_restaurante.json")
# Definimos la ruta de la base de datos dentro de la carpeta de ejecución
CARPETA_DB = os.path.join(DIRECTORIO_ACTUAL, "db_restaurante")

def implantar_fase_1(archivo_json):
    print("Cargando datos del menú...")
    
    try:
        with open(ruta_json, 'r', encoding='utf-8') as f:
            datos = json.load(f)
    except FileNotFoundError:
        print(f"Error: No se encuentra el archivo {ruta_json}")
        return
    
    documentos_para_rag = []
    
    #Transformo el JSON a lenguaje natural, con metadatos para filtrados futuros (alérgenos, dietas) y precios formateados.
    for item in datos['menu']:

        lista_precios = []
        for p in item.get('precios', []):
            formato = p.get('formato', 'Ración')
            valor = p.get('valor', 'consultar')
            moneda = p.get('moneda', '€')
            lista_precios.append(f"{formato}: {valor}{moneda}")
        
        texto_precios = " / ".join(lista_precios) if lista_precios else "Precio no disponible"

        # Convierto las listas a texto porque ChromaDB no admite listas vacías y es más fácil de leer para el modelo
        alergenos_txt = ", ".join(item['alergenos']) if item.get('alergenos') else "Ninguno"
        dietas_txt = ", ".join(item['dietas']) if item.get('dietas') else "Estándar"

        # Creo una descripción narrativa del plato
        contenido_texto = (
            f"PLATO: {item['plato']}. "
            f"CATEGORÍA: {item.get('categoria', 'No especificada')}. "
            f"DESCRIPCIÓN: {item.get('descripcion', 'No especificada')}. "
            f"ALÉRGENOS: {', '.join(item['alergenos']) if item['alergenos'] else 'Ninguno'}. "
            f"DIETAS: {', '.join(item['dietas']) if item['dietas'] else 'Estándar'}."
            f"PRECIO: {texto_precios}."
        )
        
        # Guardo los metadatos para filtrados futuros (seguridad alimentaria)
        metadatos = {
            "nombre": item['plato'],
            "es_celiaco": "Celíaco" in item['dietas'],
            "es_vegetariano": "Vegetariano" in item['dietas'],
            "es_vegano": "Vegano" in item['dietas'],
            "alergenos": alergenos_txt
        }
        
        # Creo el objeto "Documento" compatible con LangChain
        doc = Document(page_content=contenido_texto, metadata=metadatos)
        documentos_para_rag.append(doc)

    print(f"{len(documentos_para_rag)} platos listos para vectorizar.")

    if os.path.exists(CARPETA_DB):
        print(f"Borrando base de datos existente ...")
        shutil.rmtree(CARPETA_DB)
    
    # Genero los embeddings con el modelo específico de Google

    print("Generando vectores (Embeddings)...")
    embeddings_model = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

    # Creeo la BBDD y la guardo en disco para la siguiente fase
    vector_db = Chroma.from_documents(
        documents=documentos_para_rag,
        embedding=embeddings_model,
        persist_directory=CARPETA_DB # Esta carpeta se creará sola
    )
    
    print("FASE 2 COMPLETADA: Base de datos vectorial guardada en {CARPETA_DB}")
    return vector_db

if __name__ == "__main__":
    implantar_fase_1("menu_restaurante.json")