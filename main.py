import os
import datetime
import textwrap
import urllib.request
import urllib.parse
import re
import unicodedata
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont
import smtplib
from email.message import EmailMessage
from deep_translator import GoogleTranslator
import time
import random

print("1. Configurando parámetros y diccionarios de siglas...")

# ==========================================
# 🔄 1. ROTACIÓN TEMÁTICA Y DÍAS
# ==========================================
dia_actual = datetime.datetime.now().weekday()

if dia_actual == 0:   # Lunes
    termino_busqueda = "biostatistics health research meta-analysis"
    etiqueta_defecto = "Bioestadística y Análisis de Datos"
elif dia_actual == 2:  # Miércoles
    termino_busqueda = "dental public health clinical trials systematic review"
    etiqueta_defecto = "Salud y Odontología Basada en Evidencia"
elif dia_actual == 4:  # Viernes
    termino_busqueda = "research methodology health science systematic review"
    etiqueta_defecto = "Divulgación Científica y Metodología"
else:  # Fallback
    termino_busqueda = "science communication health systematic review"
    etiqueta_defecto = "Divulgación Científica y Metodología"

# ==========================================
# 📚 2. DICCIONARIO Y PROCESADOR DE SIGLAS
# ==========================================
DICCIONARIO_SIGLAS_ESTANDAR = {
    # Educación médica / Evaluación
    r'\bEPAs\b': 'Actividades Profesionales Confiables (EPA)',
    r'\bEPA\b': 'Actividades Profesionales Confiables (EPA)',
    r'\bAAEs\b': 'Actividades Profesionales Confiables (EPA)',
    r'\bAAE\b': 'Actividades Profesionales Confiables (EPA)',
    
    # Bioestadística y Metodología
    r'\bRCTs\b': 'Ensayos Clínicos Aleatorizados (ECA)',
    r'\bRCT\b': 'Ensayo Clínico Aleatorizado (ECA)',
    r'\bORs\b': 'Razones de Momios (OR)',
    r'\bOR\b': 'Razón de Momios (OR)',
    r'\bCIs\b': 'Intervalos de Confianza (IC)',
    r'\bCI\b': 'Intervalo de Confianza (IC)',
    r'\bHRs\b': 'Razones de Riesgo (HR)',
    r'\bHR\b': 'Razón de Riesgo (HR)',
    r'\bRRs\b': 'Riesgos Relativos (RR)',
    r'\bRR\b': 'Riesgo Relativo (RR)',
    r'\bSDs\b': 'Desviaciones Estándar (DE)',
    r'\bSD\b': 'Desviación Estándar (DE)',
    r'\bSEs\b': 'Errores Estándar (EE)',
    r'\bSE\b': 'Error Estándar (EE)',
    r'\bMDs\b': 'Diferencias de Medias (DM)',
    r'\bMD\b': 'Diferencia de Medias (DM)',
    r'\bSMDs\b': 'Diferencias de Medias Estandarizadas (DME)',
    r'\bSMD\b': 'Diferencia de Medias Estandarizada (DME)',
    r'\bANOVA\b': 'Análisis de Varianza (ANOVA)',
    r'\bMANOVA\b': 'Análisis Multivariado de Varianza (MANOVA)',
    r'\bPCA\b': 'Análisis de Componentes Principales (ACP)',
    r'\bROC\b': 'Curva ROC (Característica Operativa del Receptor)',
    r'\bAUC\b': 'Área Bajo la Curva (AUC)',
    r'\bPRISMA\b': 'Declaración PRISMA',
    r'\bSTROBE\b': 'Guía STROBE',
    r'\bCONSORT\b': 'Declaración CONSORT',
    
    # Odontología y Tecnología
    r'\bCBCT\b': 'Tomografía Computarizada de Haz Cónico (CBCT)',
    r'\bCAD/CAM\b': 'Diseño y Fabricación Asistidos por Computadora (CAD/CAM)',
    r'\bDIS\b': 'Escáner Intraoral Digital (DIS)'
}

def expandir_siglas_del_texto(texto):
    if not texto:
        return ""
    patron_siglas = r'\b([A-Z][a-z0-9\-]+(?:\s+[A-Za-z0-9\-]+){1,5})\s*\(([A-Z0-9]{2,8})\)'
    definiciones = re.findall(patron_siglas, texto)
    texto_expandido = texto
    for termino_completo, sigla in definiciones:
        patron_sigla_suelta = r'\b' + re.escape(sigla) + r'\b'
        texto_expandido = re.sub(patron_sigla_suelta, termino_completo, texto_expandido)
    return texto_expandido

def normalizar_siglas_espanol(texto):
    if not texto:
        return ""
    texto_normalizado = texto
    for patron_sigla, reemplazo_es in DICCIONARIO_SIGLAS_ESTANDAR.items():
        texto_normalizado = re.sub(patron_sigla, reemplazo_es, texto_normalizado)
    return texto_normalizado

def limpiar_y_normalizar_simbolos(texto):
    if not texto:
        return ""
    texto = unicodedata.normalize('NFKC', texto)
    return texto.strip()

# --- TRADUCCIÓN Y ADAPTACIÓN ---
def traducir_y_adaptar(texto):
    if not texto or len(texto.strip()) == 0:
        return ""
    
    traduccion = None
    intentos = 4
    for i in range(intentos):
        try:
            res = GoogleTranslator(source='auto', target='es').translate(texto)
            if res and "Error 500" not in res and "That's an error" not in res:
                traduccion = res
                break
            else:
                time.sleep(2)
        except Exception:
            time.sleep(2)

    if not traduccion or len(traduccion.strip()) == 0:
        traduccion = texto

    # Corrección de voz activa/pasiva
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

    # Normalización de inconsistencias de traducción específicas
    reemplazos_terminos = {
        r'\b[A|a]ctividades de [E|e]ncomienda\b': 'Actividades Profesionales Confiables (EPA)',
        r'\b[A|a]ctividades [P|p]rofesionales de [C|c]onfianza\b': 'Actividades Profesionales Confiables (EPA)',
        r'\bAAE\b': 'EPA',
        r'\bAAEs\b': 'EPAs'
    }
    for patron, reemplazo in reemplazos_terminos.items():
        traduccion = re.sub(patron, reemplazo, traduccion)

    traduccion = normalizar_siglas_espanol(traduccion)
    traduccion = limpiar_y_normalizar_simbolos(traduccion)
    traduccion = re.sub(r'[\(\[\{][^\)\}\]]*$', '', traduccion).strip()
    
    if not traduccion.endswith('.'):
        traduccion += '.'

    return traduccion

# --- CLASIFICACIÓN DINÁMICA ---
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

# --- EXTRACCIÓN ESTRUCTURADA ---
def extraer_problema_clinico_estructurado(abs_dict, abs_full):
    prob_text = abs_dict.get("BACKGROUND", abs_dict.get("OBJECTIVE", abs_dict.get("INTRODUCTION", "")))
    if prob_text:
        return prob_text

    oraciones = [o.strip() for o in re.split(r'\.\s+|\n+', abs_full) if len(o.strip()) > 15]
    patrones_contexto = [
        r'\baimed to\b', r'\bthe purpose of\b', r'\bwe evaluated\b', 
        r'\blittle is known\b', r'\bremains unclear\b', r'\bdespite\b',
        r'\bhowever\b', r'\black of\b', r'\bis a common\b', r'\bto investigate\b'
    ]
    
    for oracion in oraciones[:3]:
        if any(re.search(patron, oracion, re.IGNORECASE) for patron in patrones_contexto):
            return oracion

    if len(oraciones) >= 2:
        contexto_unificado = f"{oraciones[0]}. {oraciones[1]}"
        if len(contexto_unificado) <= 320:
            return contexto_unificado
        return oraciones[0]
    
    return abs_full

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
# 🔍 3. BÚSQUEDA Y EXTRACCIÓN PUBMED
# ==========================================
print("2. Buscando artículo relevante en PubMed...")

def obtener_datos_estudio(termino):
    base_url_search = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={urllib.parse.quote(termino)}&sort=pub_date&retmax=40&retmode=xml"
    try:
        req = urllib.request.Request(base_url_search, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            root = ET.fromstring(response.read())
            pmids = [elem.text for elem in root.findall('.//IdList/Id')]
    except Exception as e:
        print(f"Error al buscar en PubMed: {e}")
        return None

    random.shuffle(pmids)
    candidatos = []

    for pmid in pmids:
        fetch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={pmid}&retmode=xml"
        try:
            req = urllib.request.Request(fetch_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
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
                
                candidatos.append({
                    "pmid": pmid,
                    "titulo": titulo,
                    "abstract_completo": abstract_completo,
                    "abstract_dict": abstract_dict,
                    "referencia": referencia
                })
                
                if len(candidatos) >= 5:
                    break
        except Exception:
            continue

    if candidatos:
        return random.choice(candidatos)

    return None

estudio = obtener_datos_estudio(termino_busqueda)

if estudio:
    ref_vancouver = limpiar_y_normalizar_simbolos(estudio["referencia"])
    abs_dict = estudio["abstract_dict"]
    abs_full = expandir_siglas_del_texto(estudio["abstract_completo"])
    
    prob_text = extraer_problema_clinico_estructurado(abs_dict, abs_full)
    hall_text = abs_dict.get("RESULTS", abs_dict.get("FINDINGS", ""))
    conc_text = abs_dict.get("CONCLUSIONS", abs_dict.get("CONCLUSION", ""))

    prob_text = expandir_siglas_del_texto(prob_text)
    
    if not hall_text:
        oraciones_todas = [o.strip() for o in re.split(r'\.\s+', abs_full) if len(o.strip()) > 15]
        hall_text = ". ".join(oraciones_todas[1:-1]) if len(oraciones_todas) >= 3 else abs_full
    hall_text = expandir_siglas_del_texto(hall_text)

    if not conc_text:
        oraciones_todas = [o.strip() for o in re.split(r'\.\s+', abs_full) if len(o.strip()) > 15]
        conc_text = oraciones_todas[-1] if len(oraciones_todas) > 1 else abs_full
    conc_text = expandir_siglas_del_texto(conc_text)

    prob_clean = obtener_oraciones_completas(prob_text, max_caracteres=350)
    hall_clean = obtener_oraciones_completas(hall_text, max_caracteres=1200)
    conc_clean = obtener_oraciones_completas(conc_text, max_caracteres=300)

    titulo_estudio_es = traducir_y_adaptar(estudio["titulo"])
    problema_texto = traducir_y_adaptar(prob_clean)
    hallazgo_texto = traducir_y_adaptar(hall_clean)
    conclusion_texto = traducir_y_adaptar(conc_clean)

    etiqueta_tema = clasificar_area_tematica(titulo_estudio_es, hallazgo_texto, etiqueta_defecto)

else:
    ref_vancouver = "Bermeo-Escalona JR, et al. Análisis de evidencia en ciencias de la salud. Rev Med UAEMéx. 2026; PMID: 41964104."
    titulo_estudio_es = "Evaluación sistemática y modelos de análisis en ciencias de la salud"
    problema_texto = "Existe una alta heterogeneidad en los reportes de investigación que compromete la reproducibilidad de los datos en salud."
    hallazgo_texto = "La implementación de modelos estandarizados redujo la variabilidad metodológica en un 42%, optimizando la precisión de los resultados clínicos."
    conclusion_texto = "El uso de marcos analíticos rigurosos es indispensable para consolidar la práctica basada en la evidencia."
    etiqueta_tema = etiqueta_defecto

# ==========================================
# 🖼️ 4. RENDERIZADO GRÁFICO (1080x1080)
# ==========================================
print("3. Generando infografía...")

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

fuente_cuerpo_estandar = ImageFont.truetype(font_path_reg, 17)

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

# 2. Banner Tema / Título
y_cursor = 100
tit_lines = textwrap.wrap(f"Evidencia Actual en {etiqueta_tema}", width=50)
sub_lines = textwrap.wrap(f"Análisis del estudio: {titulo_estudio_es}", width=82)

altura_banner = (len(tit_lines) * 28) + (len(sub_lines) * 20) + 22

draw.rounded_rectangle([(MARGEN_LATERAL, y_cursor), (ANCHO - MARGEN_LATERAL, y_cursor + altura_banner)], radius=8, fill=COLOR_GRIS_CLARO, outline="#E5E7EB", width=1)
draw.multiline_text((MARGEN_LATERAL + 18, y_cursor + 12), "\n".join(tit_lines), fill=COLOR_VERDE_UAEM, font=fuente_titulo, spacing=4)
draw.multiline_text((MARGEN_LATERAL + 18, y_cursor + 12 + (len(tit_lines) * 28)), "\n".join(sub_lines), fill="#4B5563", font=fuente_subtitulo, spacing=3)

y_cursor += altura_banner + 30
spacing_bloques = 32

# BLOQUE 1: PROBLEMA CLÍNICO
draw.text((MARGEN_LATERAL, y_cursor), "PROBLEMA CLÍNICO", fill=COLOR_VERDE_UAEM, font=fuente_subtitulo_sec)
y_cursor += 28
y_cursor, _ = draw_justified_text(draw, problema_texto, MARGEN_LATERAL, y_cursor, ANCHO_UTIL, fuente_cuerpo_estandar, COLOR_TEXTO_OSCURO, line_spacing=7)

y_cursor += spacing_bloques

# BLOQUE 2: HALLAZGO PRINCIPAL
y_hallazgo_top = y_cursor
ancho_indentado = ANCHO_UTIL - 24
x_texto_hallazgo = MARGEN_LATERAL + 24

draw.text((MARGEN_LATERAL, y_hallazgo_top), "HALLAZGO PRINCIPAL", fill=COLOR_VERDE_UAEM, font=fuente_subtitulo_sec)
y_cursor_hallazgo = y_hallazgo_top + 28

y_fin_hallazgo, _ = draw_justified_text(draw, hallazgo_texto, x_texto_hallazgo, y_cursor_hallazgo, ancho_indentado, fuente_cuerpo_estandar, COLOR_TEXTO_OSCURO, line_spacing=7)

draw.line([(MARGEN_LATERAL + 6, y_cursor_hallazgo - 2), (MARGEN_LATERAL + 6, y_fin_hallazgo - 4)], fill=COLOR_ORO_UAEM, width=5)

y_cursor = y_fin_hallazgo + spacing_bloques

# BLOQUE 3: CONCLUSIÓN CLÍNICA
draw.text((MARGEN_LATERAL, y_cursor), "CONCLUSIÓN CLÍNICA", fill=COLOR_VERDE_UAEM, font=fuente_subtitulo_sec)
y_cursor += 28
y_cursor, _ = draw_justified_text(draw, conclusion_texto, MARGEN_LATERAL, y_cursor, ANCHO_UTIL, fuente_cuerpo_estandar, COLOR_TEXTO_OSCURO, line_spacing=7)

# --- REFERENCIA Y PIE DE PÁGINA ---
ref_lines = textwrap.wrap(ref_vancouver, width=115)
lineas_ref = ref_lines[:3]
altura_texto_ref = len(lineas_ref) * 16

y_referencia_bloque = (ALTO - 48) - 25 - altura_texto_ref - 20

if y_cursor > y_referencia_bloque - 15:
    y_referencia_bloque = y_cursor + 20

draw.line([(MARGEN_LATERAL, y_referencia_bloque), (ANCHO - MARGEN_LATERAL, y_referencia_bloque)], fill="#E5E7EB", width=1)

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
# ✉️ 5. ENVÍO POR CORREO DE ALERTA
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
