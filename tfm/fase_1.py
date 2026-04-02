import os
from pdf2image import convert_from_path
from google import genai
import PIL.Image
import json
import time
import re

# Configuración
client = genai.Client(api_key='mi_key_secreta')
ID_MODELO = 'gemini-flash-latest'

DIRECTORIO_PROYECTO = os.path.dirname(os.path.abspath(__file__))
RUTA_PDF = os.path.join(DIRECTORIO_PROYECTO, "carta-cocina-Senorito-Picofino.pdf")
CARPETA_PROCESAMIENTO = os.path.join(DIRECTORIO_PROYECTO, "debug_paginas")
CARPETA_SALIDA = os.path.join(DIRECTORIO_PROYECTO, "procesamiento_pdf")
RUTA_JSON_FINAL = os.path.join(DIRECTORIO_PROYECTO, "menu_restaurante.json")

# Crear carpeta si no existe
if not os.path.exists(CARPETA_SALIDA):
    os.makedirs(CARPETA_SALIDA)

prompt = """
        Eres un transcriptor de datos de alta precisión. 
        Tu objetivo es pasar la imagen de un menú a JSON sin añadir, quitar ni inventar nada. Es imprescindible que te ajustes a los platos de la carta sin omitir ni inventar ninguno.
        Primero tienes que detectar si el menú tiene portada o contraportada, en caso de tenerlas, es imprescindible que no inventes platos en su análsis y las omitas. 
        Por otro lado, si el menú no tiene portada y/o contraportada, debes empezar a analizar y extraer platos en la primera hoja.
        Solo debes extraer la información de los platos que aparecen en el menú.
        Actúa como un experto en análisis visual de seguridad alimentaria. 
        Analiza el menú prestando especial atención a la diferencia entre los iconos de HUEVO, GLUTEN y MOSTAZA.

        INSTRUCCIONES DE EXTRACCIÓN:
        1. RECORRIDO: Analiza la carta línea por línea, de arriba a abajo. No te saltes ningún plato.

        2.REGLAS DE DISTINCIÓN VISUAL:
        - ICONO DE HUEVO: Busca una forma ovalada blanca o amarilla, similar a un huevo cortado.
        - ICONO DE GLUTEN: Busca una forma de espiga de trigo o una silueta de pan. Es más alargada y con bordes irregulares.
        - DIETA VEGETARIANA: Busca las siglas 'V' o 'VO' o la forma de una planta. Si están presentes, el plato es Vegetariano.
        - ICONO DE LÁCTEOS: Busca una forma de Vaca/Botella
        - ICONO DE MOSTAZA: Busca una forma de semilla o un frasco pequeño, a menudo con un diseño que recuerda a la mostaza, presta espcial atención para no connfundirla conn otros alérgenos.
        - ICONO DE SÉSAMO: Busca formas de semillas pequeñas, a menudo agrupadas o con un diseño que recuerda al sésamo.
        - ICONO DE FRUCTOSA: Busca formas de frutas, como manzanas o peras, a menudo con un diseño colorido.
        - ICONO DE MOLUSCOS: Busca formas de conchas o almejas, a menudo con un diseño que recuerda a los moluscos.
        - ICONO DE PESCADO: Busca una forma de pez, a menudo con una cola distintiva.
        - ICONO DE MARISCO: Busca formas de crustáceos como cangrejos o langostas.
        - ICONO DE FRUTO SECO: Busca formas de nueces o almendras, a menudo con una textura rugosa.
        - ICONO DE SULFITOS: Busca formas de uvas o copas de vino, a menudo con un diseño elegante.
        - DIETA VEGANA: Si el plato es Vegetariano Y NO presenta iconos de Huevo o Lácteos.
        - DIETA CELÍACA: Si el plato NO presenta icono de Gluten.

        3. INSTRUCCIONES DE CATEGORIZACIÓN:
        Debes asignar a cada plato una de las siguientes categorías exactas: 
        ["Entrante", "Plato Principal", "Acompañamiento", "Postre", "Bebida"].
        - Si el plato está en una sección llamada 'Postres' o es un dulce: "Postre".
        - Si es un vino, agua, café o refresco: "Bebida".
        - Si es una guarnición o pan: "Acompañamiento".
        - Si está al principio de la carta o son raciones para compartir: "Entrante".
        - Si son platos con proteínas (carne, pescado, legumbres) o platos fuertes: "Plato Principal".

        PROCESO DE PENSAMIENTO (Paso a paso):
        - Paso 1: Identifica el nombre del plato.
        - Paso 2: Localiza todos los símbolos de ese plato.
        - Paso 3: Para cada símbolo, describe internamente su forma antes de asignarle un alérgeno.
        - Paso 4: Cruza los símbolos con la leyenda de la carta.
        - Paso 5: Extrae el precio y sepáralo en valor numérico y moneda. FORMATOS DE PRECIO: Si un plato tiene varios precios (ej: Media ración, Ración completa o Copa/Botella), desglósalos individualmente.
        - Paso 6: Determina si el plato es apto para dietas especiales (Vegetariano, Vegano (ningun ingrediente proviene de origen animal), Celíaco) basándote en los iconos y la descripción.
            Es importante que si en algún plato o pan con alérgeno de gluten aparece algo como "opción sin gluten" marques ese plato también como dieta celíaca.
            Por otro lado, si el pan no incluye alérgeno de gluten, y no especifican que es apto para celíacos, no lo marques como apto para celíacos.
        - Paso 7: Extrae la descripción o ingredientes si aparecen debajo del nombre.
        - Paso 8: Asigna la categoría del plato según las reglas de categorización.

        FORMATO DE SALIDA (JSON ESTRICTO):
        {
          "menu": [
            {
              "plato": "Nombre exacto",
              "alergenos": ["Gluten", "Huevo", "Pescado", etc],
              "dietas": ["Vegetariano", "Vegano", "Celíaco", etc],
              "precios": [
                {"formato": "Media ración", "valor": 8.50, "moneda": "€"},
                {"formato": "Ración completa", "valor": 15.00, "moneda": "€"}
                ],
              "descripcion": "Descripción o ingredientes si aparecen",
              "categoria": "Entrante / Plato Principal / Acompañamiento / Postre / Bebida"
            }
          ]
        }
        """

def llamar_con_paciencia(prompt_texto, imagen_bloque):
    #Para gestionar los recursos de la API
    intentos = 0
    while True:
        try:
            response = client.models.generate_content(
                model=ID_MODELO,
                contents=[prompt_texto, imagen_bloque],
                config={'temperature': 0.0}
            )
            return response.text
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                intentos += 1
                # Intento extraer el tiempo de espera del mensaje de Google
                segundos_match = re.search(r'retry in (\d+\.\d+)s', err_msg)
                espera = float(segundos_match.group(1)) + 1 if segundos_match else (intentos * 10)
                
                print(f"Límite de cuota alcanzado. Esperando {espera:.1f}s antes del reintento {intentos}...")
                time.sleep(espera)
            elif "503" in err_msg:
                print("Servidor sobrecargado (503). Esperando 10s...")
                time.sleep(10)
            else:
                print(f"Error en la API: {e}")
                return None

def procesar_con_maxima_fidelidad(ruta_pdf):
    if not os.path.exists(CARPETA_PROCESAMIENTO):
        os.makedirs(CARPETA_PROCESAMIENTO)

    # Convertir con alta densidad de píxeles y forzando RGB
    print("Convirtiendo PDF a alta definición...")
    paginas = convert_from_path(ruta_pdf, dpi=350, fmt="png")
    
    resultados_totales = []

    for i, pagina in enumerate(paginas):
        # Asegurar modo RGB (evita colores extraños del PDF)
        pagina = pagina.convert("RGB")
        ancho, alto = pagina.size
        
        # DIVIDIR LA PÁGINA EN DOS (Superior e Inferior)
        # Para que los iconos de alérgenos se vean el doble de grandes y disminuir el riesgo de que el modelo no los detecte
        bloques = [
            ("sup", pagina.crop((0, 0, ancho, alto // 2))),
            ("inf", pagina.crop((0, alto // 2, ancho, alto)))
        ]

        for sufijo, bloque in bloques:
            nombre_foto = f"debug_paginas/pag_{i+1}_{sufijo}.png"
            bloque.save(nombre_foto, "PNG")
            
            print(f"Analizando bloque {sufijo} de la página {i+1}...")

            # Llamo a la nueva función resiliente
            texto_raw = llamar_con_paciencia(prompt, bloque)
            
            if texto_raw:
                try:
                    # Limpiar formato Markdown si existe
                    if "```json" in texto_raw:
                        texto_raw = texto_raw.split("```json")[1].split("```")[0]
                    elif "```" in texto_raw:
                        texto_raw = texto_raw.split("```")[1].split("```")[0]
                    
                    datos = json.loads(texto_raw.strip())
                    items = datos.get("menu", [])
                    resultados_totales.extend(items)
                    print(f"Bloque procesado. {len(items)} ítems añadidos.")
                except Exception as e_json:
                    print(f"Error al procesar JSON en bloque {sufijo}: {e_json}")
            
            time.sleep(1)


    # Guardar resultado final
    with open(RUTA_JSON_FINAL, "w", encoding="utf-8") as f:
        json.dump({"menu": resultados_totales}, f, indent=4, ensure_ascii=False)
    print("\n¡Listo! Revisa el fichero en {RUTA_JSON_FINAL}.")

if __name__ == "__main__":
    procesar_con_maxima_fidelidad(RUTA_PDF)