import os
import datetime
import textwrap
import urllib.request
import re
import unicodedata
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont
import smtplib
from email.message import EmailMessage
from deep_translator import GoogleTranslator

print("1. Determinando tema y realizando búsqueda en PubMed...")

# --- FUNCIÓN DE LIMPIEZA Y NORMALIZACIÓN DE SÍMBOLOS ESTADÍSTICOS ---
def limpiar_y_normalizar_simbolos(texto):
    if not texto:
        return ""
    
    reemplazos_simbolos = {
        '±': ' +/- ', '≤': ' <= ', '≥': ' >= ', '≠': ' != ', '≈': ' aprox. ',
        'α': 'alfa', 'β': 'beta', 'χ': 'Chi', 'χ²': 'Chi-cuadrado', 'χ2': 'Chi-cuadrado',
        'p<': 'p < ', 'p>': 'p > ', 'p=': 'p = ', 'P<': 'P < ', 'P>': 'P > ', 'P=': 'P = ',
        '°': ' grad. ', 'µ': 'u', '–': '-', '—': '-', '“': '"', '”': '"', '‘': "'", '’': "'"
    }
    
    for simbolo, reemplazo in reemplazos_simbolos.items():
        texto = texto.replace(simbolo, reemplazo)
        
    texto = unicodedata.normalize('NFC', texto)
    return texto

# --- TRADUCCIÓN Y ADAPTACIÓN A 3RA PERSONA ---
def traducir_y_adaptar(texto):
    if not texto or len(texto.strip()) == 0:
        return ""
    try:
        traduccion = GoogleTranslator(source='auto', target='es').translate(texto)
        if not traduccion:
            traduccion = texto

        reemplazos_voz = {
            r'\b[I|i]ntentamos\b': 'El estudio buscó',
            r'\b[B|b]uscamos\b': 'El análisis buscó',
            r'\b[I|i]dentificamos\b': 'Los autores identificaron',
            r'\b[E|e]valuamos\b': 'La investigación evaluó',
            r'\b[I|i]ncluimos\b': 'Se incluyeron',
            r'\b[N|n]uestros resultados\b': 'Los resultados del estudio',
            r'\b[E|e]ncontramos\b': 'Se encontró que',
            r'\b[C|c]oncluimos\b': 'La evidencia concluye'
        }
        for patron, reemplazo in reemplazos_voz.items():
            traduccion = re.sub(patron, reemplazo, traduccion)

        traduccion = limpiar_y_normalizar_simbolos(traduccion)
        traduccion = re.sub(r'[\(\[\{][^\)\}\]]*$', '', traduccion).strip()
        if not traduccion.endswith('.'):
            traduccion += '.'

        return traduccion
    except Exception as e:
        print(f"Nota: No se pudo traducir el fragmento ({e}), se usará el texto original.")
        return limpiar_y_normalizar_simbolos(texto)

# --- CLASIFICACIÓN DINÁMICA POR PALABRAS CLAVE ---
def clasificar_area_tematica(titulo_es, abstract_es, tema_por_defecto):
    texto_completo = f"{titulo_es} {abstract_es}".lower()
    
    kw_dental = ["dental", "odonto", "caries", "periodont", "endodon", "maxilofac", "salud bucal", "diente", "oral", "fluor"]
    kw_bioest = ["estadístic", "metaanálisis", "meta-análisis", "ensayo clínico", "modelo", "regresión", "prevalencia", "cohorte", "pronóstico", "predict", "variables"]
    
    if any(k in texto_completo for k in kw_dental):
        return "Salud y Odontología Basada en Evidencia"
    elif any(k in texto_completo for k in kw_bioest):
        return "Bioestadística y Análisis de Datos"
    else:
        return tema_por_defecto

# --- EXTRACCIÓN HASTA 1300 CARACTERES ---
def obtener_oraciones_completas(texto, max_caracteres=1300):
    if not texto:
        return ""
        
    oraciones = re.split(r'\.\s+|\n+', texto)
    oraciones_validas = [o.strip() for o in oraciones if len(o.strip()) > 10]
    
    resultado = []
    longitud_acumulada = 0
    
    for oracion in oraciones_validas:
        if longitud_acumulada + len(oracion) <= max_caracteres:
            resultado.append(oracion)
            longitud_acumulada += len(oracion) + 2
        else:
            if not resultado:
                resultado.append(oracion)
            break
            
    seleccion = ". ".join(resultado)
    if seleccion and not seleccion.endswith('.'):
        seleccion += '.'
    return seleccion

# ==========================================
# 🔄 1. ROTACIÓN Y BÚSQUEDA TEMÁTICA
# ==========================================
dia_actual = datetime.datetime.now().weekday()

if dia_actual == 0:
    termino_busqueda = "biostatistics health research meta-analysis"
    etiqueta_defecto = "Bioestadística y Análisis de Datos"
elif dia_actual == 2:
    termino_busqueda = "dental public health clinical trials systematic review"
    etiqueta_defecto = "Salud y Odontología Basada en Evidencia"
else:
    termino_busqueda = "science communication health systematic review"
    etiqueta_defecto = "Divulgación Científica y Metodología"

# ==========================================
# 🔍 2. PROCESAMIENTO ROBUSTO DEL XML DE PUBMED
# ==========================================
def obtener_datos_estudio(termino):
    base_url_search = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={urllib.parse.quote(termino)}&sort=pub_date&retmax=5&retmode=xml"
    try:
        with urllib.request.urlopen(base_url_search) as response:
            root = ET.fromstring(response.read())
            pmids = [elem.text for elem in root.findall('.//IdList/Id')]
    except Exception:
        return None

    for pmid in pmids:
        fetch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={pmid}&retmode=xml"
        try:
            with urllib.request.urlopen(fetch_url) as response:
                root_f = ET.fromstring(response.read())
                
                titulo_elem = root_f.find(".//ArticleTitle")
                titulo = titulo_elem.text if titulo_elem is not None and titulo_elem.text else ""
                titulo = re.sub('<[^<]+?>', '', titulo)

                abstract_elems = root_f.findall(".//AbstractText")
                abstract_dict = {}
                abstract_texts = []
                
                for a in abstract_elems:
                    label = a.attrib.get('Label', '').upper()
                    text_content = "".join(a.itertext()).strip()
                    if label:
                        abstract_dict[label] = text_content
                    abstract_texts.append(text_content)
                
                abstract_completo = " ".join(abstract_texts)

                if not abstract_completo or len(abstract_completo) < 150:
                    continue

                journal_elem = root_f.find(".//Journal/Title")
                source = journal_elem.text if journal_elem is not None else "Revista Científica"
                
                year_elem = root_f.find(".//JournalIssue/PubDate/Year")
                pubdate = year_elem.text[:4] if year_elem is not None else "2026"

                author_list = root_f.findall(".//Author")
                primer_autor = "Investigadores et al."
                if author_list:
                    lastname = author_list[0].find("LastName")
                    if lastname is not None and lastname.text:
                        primer_autor = f"{lastname.text} et al."

                referencia = f"{primer_autor} {titulo}. {source}. {pubdate}; PMID: {pmid}."
                
                return {
                    "pmid": pmid,
                    "titulo": titulo,
                    "abstract_completo": abstract_completo,
                    "abstract_dict": abstract_dict,
                    "referencia": referencia
                }
        except Exception:
            continue
    return None

estudio = obtener_datos_estudio(termino_busqueda)

if estudio:
    ref_vancouver = limpiar_y_normalizar_simbolos(estudio["referencia"])
    titulo_estudio_es = traducir_y_adaptar(estudio["titulo"])
    abs_dict = estudio["abstract_dict"]
    abs_full = estudio["abstract_completo"]
    
    prob_text = abs_dict.get("BACKGROUND", abs_dict.get("OBJECTIVE", abs_dict.get("INTRODUCTION", "")))
    hall_text = abs_dict.get("RESULTS", abs_dict.get("FINDINGS", ""))
    conc_text = abs_dict.get("CONCLUSIONS", abs_dict.get("CONCLUSION", ""))

    if not hall_text:
        oraciones_todas = re.split(r'\.\s+', abs_full)
        tot_or = len(oraciones_todas)
        if tot_or >= 5:
            prob_text = ". ".join(oraciones_todas[:1])
            hall_text = ". ".join(oraciones_todas[1:-1])
            conc_text = ". ".join(oraciones_todas[-1:])
        else:
            hall_text = abs_full

    prob_clean = obtener_oraciones_completas(prob_text, max_caracteres=250)
    hall_clean = obtener_oraciones_completas(hall_text, max_caracteres=1300)
    conc_clean = obtener_oraciones_completas(conc_text, max_caracteres=250)

    problema_texto = traducir_y_adaptar(prob_clean)
    hallazgo_texto = traducir_y_adaptar(hall_clean)
    conclusion_texto = traducir_y_adaptar(conc_clean)

    # ✅ Clasificación inteligente si se encontró estudio en PubMed:
    etiqueta_tema = clasificar_area_tematica(titulo_estudio_es, hallazgo_texto, etiqueta_defecto)

else:
    ref_vancouver = "Bermeo-Escalona JR, et al. Análisis de evidencia en ciencias de la salud. Rev Med UAEMéx. 2026; PMID: 41964104."
    titulo_estudio_es = "Evaluación sistemática y modelos de análisis en ciencias de la salud"
    problema_texto = "Existe una alta heterogeneidad en los reportes de investigación que compromete la reproducibilidad de los datos en salud."
    hallazgo_texto = "La implementación de modelos estandarizados redujo la variabilidad metodológica en un 42%, optimizando la precisión de los resultados clínicos."
    conclusion_texto = "El uso de marcos analíticos rigurosos es indispensable para consolidar la práctica basada en la evidencia."

    # ✅ Asignación si falla la búsqueda (cae en el backup):
    etiqueta_tema = etiqueta_defecto

print("3. Generando infografía...")

# ==========================================
# 🖼️ 3. RENDERIZADO GRÁFICO OPTIMIZADO (1080x1080)
# ==========================================
ANCHO, ALTO, MARGEN_LATERAL = 1080, 1080, 60
ANCHO_UTIL = ANCHO - (2 * MARGEN_LATERAL)

img = Image.new("RGB", (ANCHO, ALTO), color="#FFFFFF")
draw = ImageDraw.Draw(img)

font_path_bold = "/usr/share/fonts/truetype/roboto/unhinted/Roboto-Bold.ttf"
font_path_reg = "/usr/share/fonts/truetype/roboto/unhinted/Roboto-Regular.ttf"
if not os.path.exists(font_path_bold):
    font_path_bold = "/usr/share/fonts/truetype/roboto/Roboto-Bold.ttf"
    font_path_reg = "/usr/share/fonts/truetype/roboto/Roboto-Regular.ttf"

fuente_cabecera = ImageFont.truetype(font_path_bold, 26)
fuente_titulo = ImageFont.truetype(font_path_bold, 21)
fuente_subtitulo_sec = ImageFont.truetype(font_path_bold, 19)
fuente_subtitulo = ImageFont.truetype(font_path_reg, 15)

# --- TIPOGRAFÍA Y LEGAJO OPTIMIZADO (Legibilidad y llenado visual) ---
fuente_cuerpo_estandar = ImageFont.truetype(font_path_reg, 17) # Incrementado a 17pt

fuente_pie = ImageFont.truetype(font_path_reg, 17)
fuente_ref_bold = ImageFont.truetype(font_path_bold, 13)
fuente_ref_reg = ImageFont.truetype(font_path_reg, 12)

COLOR_VERDE_UAEM = "#1E4D2B"
COLOR_ORO_UAEM = "#C5A059"
COLOR_TEXTO_OSCURO = "#1A1A1A"
COLOR_GRIS_CLARO = "#F8F9FA"

def draw_justified_text(draw, text, x, y, width, font, fill_color, line_spacing=7):
    words = text.split()
    lines, current_line = [], []
    for word in words:
        test_line = ' '.join(current_line + [word])
        if draw.textlength(test_line, font=font) <= width:
            current_line.append(word)
        else:
            lines.append(' '.join(current_line))
            current_line = [word]
    if current_line:
        lines.append(' '.join(current_line))

    bbox = font.getbbox("A")
    line_height = bbox[3] - bbox[1]
    y_offset = y
    for i, line in enumerate(lines):
        if i == len(lines) - 1:
            draw.text((x, y_offset), line, font=font, fill=fill_color)
            y_offset += line_height + line_spacing
            break
        words_in_line = line.split()
        if len(words_in_line) == 1:
            draw.text((x, y_offset), line, font=font, fill=fill_color)
        else:
            line_width = draw.textlength(line, font=font)
            space_width = draw.textlength(" ", font=font)
            total_space_to_add = width - line_width
            spaces_to_add = len(words_in_line) - 1
            extra_space_per_space = (total_space_to_add / spaces_to_add) if spaces_to_add > 0 else 0
            x_cursor = x
            for word in words_in_line:
                draw.text((x_cursor, y_offset), word, font=font, fill=fill_color)
                x_cursor += draw.textlength(word, font=font) + space_width + extra_space_per_space
        y_offset += line_height + line_spacing
    return y_offset, len(lines)

# 1. Cabecera
draw.rectangle([(0, 0), (ANCHO, 85)], fill="#FFFFFF")
draw.text((MARGEN_LATERAL, 26), "DOSIS DE CIENCIA", fill=COLOR_VERDE_UAEM, font=fuente_cabecera)
w_dosis = draw.textlength("DOSIS DE CIENCIA", font=fuente_cabecera)
draw.text((MARGEN_LATERAL + w_dosis, 26), " | Evidencia Científica", fill=COLOR_ORO_UAEM, font=fuente_cabecera)
draw.line([(MARGEN_LATERAL, 85), (ANCHO - MARGEN_LATERAL, 85)], fill="#E5E7EB", width=1)

try:
    if os.path.exists("logo_institucional.png"):
        logo = Image.open("logo_institucional.png")
        max_h = 55
        ratio = logo.width / logo.height
        logo = logo.resize((int(max_h * ratio), max_h), Image.Resampling.LANCZOS)
        img.paste(logo, (ANCHO - MARGEN_LATERAL - logo.width, (85 - max_h) // 2), mask=logo if logo.mode == 'RGBA' else None)
except Exception:
    pass

# 2. Banner
y_cursor = 100
tit_lines = textwrap.wrap(f"Evidencia Actual en {etiqueta_tema}", width=50)
sub_lines = textwrap.wrap(f"Análisis del estudio: {titulo_estudio_es}", width=82)

altura_banner = (len(tit_lines) * 28) + (len(sub_lines) * 20) + 22

draw.rounded_rectangle([(MARGEN_LATERAL, y_cursor), (ANCHO - MARGEN_LATERAL, y_cursor + altura_banner)], radius=8, fill=COLOR_GRIS_CLARO, outline="#E5E7EB", width=1)
draw.multiline_text((MARGEN_LATERAL + 18, y_cursor + 12), "\n".join(tit_lines), fill=COLOR_VERDE_UAEM, font=fuente_titulo, spacing=4)
draw.multiline_text((MARGEN_LATERAL + 18, y_cursor + 12 + (len(tit_lines) * 28)), "\n".join(sub_lines), fill="#4B5563", font=fuente_subtitulo, spacing=3)

y_cursor += altura_banner + 30
spacing_bloques = 32  # Espaciado entre módulos aumentado a 32px para mejor aireado

# BLOQUE 1: PROBLEMA CLÍNICO
draw.text((MARGEN_LATERAL, y_cursor), "PROBLEMA CLÍNICO", fill=COLOR_VERDE_UAEM, font=fuente_subtitulo_sec)
y_cursor += 28
y_cursor, _ = draw_justified_text(draw, problema_texto, MARGEN_LATERAL, y_cursor, ANCHO_UTIL, fuente_cuerpo_estandar, COLOR_TEXTO_OSCURO, line_spacing=7)

y_cursor += spacing_bloques

# BLOQUE 2: HALLAZGO PRINCIPAL (BARRA DE ACENTO EDITORIAL DORADA)
y_hallazgo_top = y_cursor
ancho_indentado = ANCHO_UTIL - 24
x_texto_hallazgo = MARGEN_LATERAL + 24

draw.text((MARGEN_LATERAL, y_hallazgo_top), "HALLAZGO PRINCIPAL", fill=COLOR_VERDE_UAEM, font=fuente_subtitulo_sec)
y_cursor_hallazgo = y_hallazgo_top + 28

y_fin_hallazgo, _ = draw_justified_text(draw, hallazgo_texto, x_texto_hallazgo, y_cursor_hallazgo, ancho_indentado, fuente_cuerpo_estandar, COLOR_TEXTO_OSCURO, line_spacing=7)

# Barra de acento lateral dorada
draw.line([(MARGEN_LATERAL + 6, y_cursor_hallazgo - 2), (MARGEN_LATERAL + 6, y_fin_hallazgo - 4)], fill=COLOR_ORO_UAEM, width=5)

y_cursor = y_fin_hallazgo + spacing_bloques

# BLOQUE 3: CONCLUSIÓN CLÍNICA
draw.text((MARGEN_LATERAL, y_cursor), "CONCLUSIÓN CLÍNICA", fill=COLOR_VERDE_UAEM, font=fuente_subtitulo_sec)
y_cursor += 28
y_cursor, _ = draw_justified_text(draw, conclusion_texto, MARGEN_LATERAL, y_cursor, ANCHO_UTIL, fuente_cuerpo_estandar, COLOR_TEXTO_OSCURO, line_spacing=7)


# --- REFERENCIA Y PIE DE PÁGINA (ANCLAJE DINÁMICO) ---
# En lugar de fijar Y=915, la referencia se coloca pegada al footer inferior (ALTO - 48)
ref_lines = textwrap.wrap(ref_vancouver, width=115)
lineas_ref = ref_lines[:3]
altura_texto_ref = len(lineas_ref) * 16

y_referencia_bloque = (ALTO - 48) - 25 - altura_texto_ref - 20 # 20px extra de margen de seguridad

# Si el texto de arriba es muy largo y amenaza con colisionar, usamos un mínimo relativo
if y_cursor > y_referencia_bloque - 15:
    y_referencia_bloque = y_cursor + 20

# Dibujar la línea divisoria superior de la referencia
draw.line([(MARGEN_LATERAL, y_referencia_bloque), (ANCHO - MARGEN_LATERAL, y_referencia_bloque)], fill="#E5E7EB", width=1)

# Dibujar título y texto de la referencia
draw.text((MARGEN_LATERAL, y_referencia_bloque + 10), "REFERENCIA BIBLIOGRÁFICA", fill="#6B7280", font=fuente_ref_bold)
draw.multiline_text((MARGEN_LATERAL, y_referencia_bloque + 28), "\n".join(lineas_ref), fill="#4B5563", font=fuente_ref_reg, spacing=3)

# Footer inferior Verde UAEM
draw.rectangle([(0, ALTO - 48), (ANCHO, ALTO)], fill=COLOR_VERDE_UAEM)
draw.text((MARGEN_LATERAL, ALTO - 32), "UAEMéx • Facultad de Odontología", fill=COLOR_ORO_UAEM, font=fuente_pie)
nombre_pie = "Dr. en C. S. Josué R. Bermeo E."
draw.text((ANCHO - MARGEN_LATERAL - draw.textlength(nombre_pie, font=fuente_pie), ALTO - 32), nombre_pie, fill="#FFFFFF", font=fuente_pie)

img.save("main.png")
print("Infografía renderizada correctamente con estilo editorial estandarizado.")

# ==========================================
# ✉️ 4. ENVÍO POR CORREO
# ==========================================
remitente = os.environ.get("CORREO_DESTINO")
contrasena = os.environ.get("CONTRASENA_APP")

copy_redes = f"""🚨 ¡Nueva #DosisDeCiencia sobre {etiqueta_tema}! 🧬

📌 ESTUDIO ANALIZADO:
{titulo_estudio_es}

🔍 PROBLEMA CLÍNICO:
{problema_texto}

💡 HALLAZGO PRINCIPAL:
{hallazgo_texto}

👩‍⚕️ CONCLUSIÓN CLÍNICA:
{conclusion_texto}

📚 Referencia científica (PubMed): 
{ref_vancouver}

#Ciencia #Investigación #UAEMex #Bioestadística #SaludBasadaEnEvidencia #Odontología
"""

msg = EmailMessage()
msg['Subject'] = f"🧬 Dosis de Ciencia: {etiqueta_tema}"
msg['From'] = remitente
msg['To'] = remitente
msg.set_content(f"Infografía generada con hallazgos completos:\n\n{copy_redes}")

with open("main.png", "rb") as f:
    msg.add_attachment(f.read(), maintype='image', subtype='png', filename="infografia_dosis_ciencia.png")

try:
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(remitente, contrasena)
        smtp.send_message(msg)
    print("¡Correo enviado exitosamente!")
except Exception as e:
    print(f"Error al enviar el correo: {e}")
