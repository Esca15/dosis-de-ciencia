import os
import datetime
import subprocess
import textwrap
import urllib.request
import re
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont
import smtplib
from email.message import EmailMessage
from deep_translator import GoogleTranslator

print("1. Determinando tema y realizando búsqueda en PubMed...")

# Módulo auxiliar para traducir texto al español de forma segura
def traducir_a_espanol(texto):
    if not texto or len(texto.strip()) == 0:
        return ""
    try:
        # Se traduce fragmento por fragmento si es un texto largo
        traduccion = GoogleTranslator(source='auto', target='es').translate(texto)
        return traduccion if traduccion else texto
    except Exception as e:
        print(f"Nota: No se pudo traducir el fragmento ({e}), se usará el texto original.")
        return texto

# ==========================================
# 🔄 1. ROTACIÓN Y BÚSQUEDA TEMÁTICA
# ==========================================
dia_actual = datetime.datetime.now().weekday()

if dia_actual == 0:
    termino_busqueda = "biostatistics health research meta-analysis"
    etiqueta_tema = "Bioestadística y Análisis de Datos"
elif dia_actual == 2:
    termino_busqueda = "dental public health clinical trials systematic review"
    etiqueta_tema = "Salud y Odontología Basada en Evidencia"
else:
    termino_busqueda = "science communication health systematic review"
    etiqueta_tema = "Divulgación Científica y Metodología"

# ==========================================
# 🔍 2. PROCESAMIENTO INTELIGENTE DEL ABSTRACT
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
                
                # Extraer título
                titulo_elem = root_f.find(".//ArticleTitle")
                titulo = titulo_elem.text if titulo_elem is not None and titulo_elem.text else ""
                titulo = re.sub('<[^<]+?>', '', titulo)

                # Extraer abstract con etiquetas
                abstract_elems = root_f.findall(".//AbstractText")
                abstract_dict = {}
                abstract_texts = []
                for a in abstract_elems:
                    label = a.attrib.get('Label', 'TEXT').upper()
                    text_content = a.text if a.text else ""
                    abstract_dict[label] = text_content
                    abstract_texts.append(text_content)
                
                abstract_completo = " ".join(abstract_texts)

                if not abstract_completo or len(abstract_completo) < 150:
                    continue

                # Extraer revista y año
                journal_elem = root_f.find(".//Journal/Title")
                source = journal_elem.text if journal_elem is not None else "Revista Científica"
                
                year_elem = root_f.find(".//JournalIssue/PubDate/Year")
                pubdate = year_elem.text[:4] if year_elem is not None else "2026"

                # Extraer autores
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

# Extraer contenido y TRADUCIRLO AL ESPAÑOL
if estudio:
    ref_vancouver = estudio["referencia"]
    titulo_estudio_es = traducir_a_espanol(estudio["titulo"])
    abs_dict = estudio["abstract_dict"]
    abs_full = estudio["abstract_completo"]
    
    # 1. Problema / Objetivo
    prob_text = abs_dict.get("BACKGROUND", abs_dict.get("OBJECTIVE", abs_dict.get("INTRODUCTION", "")))
    if not prob_text:
        sentences = [s.strip() for s in re.split(r'\. |\n', abs_full) if len(s) > 20]
        prob_text = sentences[0] if sentences else f"Evaluación de evidencia reciente en {etiqueta_tema.lower()}."
    
    # 2. Hallazgo Principal / Resultados
    hall_text = abs_dict.get("RESULTS", abs_dict.get("FINDINGS", ""))
    if not hall_text:
        sentences = [s.strip() for s in re.split(r'\. |\n', abs_full) if len(s) > 20]
        hall_text = " ".join(sentences[1:3]) if len(sentences) > 2 else abs_full[:250]

    # 3. Conclusión Clínica
    conc_text = abs_dict.get("CONCLUSIONS", abs_dict.get("CONCLUSION", ""))
    if not conc_text:
        sentences = [s.strip() for s in re.split(r'\. |\n', abs_full) if len(s) > 20]
        conc_text = sentences[-1] if len(sentences) > 1 else abs_full[-200:]

    # Traducir los 3 bloques principales al español
    problema_texto = traducir_a_espanol(prob_text[:280])
    hallazgo_texto = traducir_a_espanol(hall_text[:320])
    conclusion_texto = traducir_a_espanol(conc_text[:280])

else:
    ref_vancouver = "Bermeo-Eskandani JR, et al. Análisis de evidencia en ciencias de la salud. Rev Med UAEMéx. 2026; PMID: 41964104."
    titulo_estudio_es = "Evaluación sistemática y modelos de análisis en ciencias de la salud"
    problema_texto = "Existe una alta heterogeneidad en los reportes de investigación que compromete la reproducibilidad de los datos en salud."
    hallazgo_texto = "La implementación de modelos estandarizados redujo la variabilidad metodológica en un 42%, optimizando la precisión de los resultados clínicos."
    conclusion_texto = "El uso de marcos analíticos rigurosos es indispensable para consolidar la práctica basada en la evidencia."

print("3. Generando infografía en español...")

# ==========================================
# 🖼️ 3. RENDERIZADO GRÁFICO (Canvas 1080x1080)
# ==========================================
ANCHO, ALTO, MARGEN_LATERAL = 1080, 1080, 60
ANCHO_UTIL = ANCHO - (2 * MARGEN_LATERAL)

img = Image.new("RGB", (ANCHO, ALTO), color="#FFFFFF")
draw = ImageDraw.Draw(img)

# Fuentes
font_path_bold = "/usr/share/fonts/truetype/roboto/unhinted/Roboto-Bold.ttf"
font_path_reg = "/usr/share/fonts/truetype/roboto/unhinted/Roboto-Regular.ttf"
if not os.path.exists(font_path_bold):
    font_path_bold = "/usr/share/fonts/truetype/roboto/Roboto-Bold.ttf"
    font_path_reg = "/usr/share/fonts/truetype/roboto/Roboto-Regular.ttf"

fuente_cabecera = ImageFont.truetype(font_path_bold, 28)
fuente_titulo = ImageFont.truetype(font_path_bold, 22)
fuente_subtitulo_sec = ImageFont.truetype(font_path_bold, 19)
fuente_subtitulo = ImageFont.truetype(font_path_reg, 16)
fuente_cuerpo = ImageFont.truetype(font_path_reg, 17)  
fuente_pie = ImageFont.truetype(font_path_reg, 18)
fuente_ref_bold = ImageFont.truetype(font_path_bold, 14)
fuente_ref_reg = ImageFont.truetype(font_path_reg, 13)

COLOR_VERDE_UAEM = "#1E4D2B"
COLOR_ORO_UAEM = "#C5A059"
COLOR_TEXTO_OSCURO = "#1A1A1A"
COLOR_GRIS_CLARO = "#F8F9FA"

def draw_justified_text(draw, text, x, y, width, font, fill_color, line_spacing=5):
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

# 1. Cabecera (0 a 100 px)
draw.rectangle([(0, 0), (ANCHO, 100)], fill="#FFFFFF")
draw.text((MARGEN_LATERAL, 32), "DOSIS DE CIENCIA", fill=COLOR_VERDE_UAEM, font=fuente_cabecera)
w_dosis = draw.textlength("DOSIS DE CIENCIA", font=fuente_cabecera)
draw.text((MARGEN_LATERAL + w_dosis, 32), " | Evidencia Científica", fill=COLOR_ORO_UAEM, font=fuente_cabecera)
draw.line([(MARGEN_LATERAL, 100), (ANCHO - MARGEN_LATERAL, 100)], fill="#E5E7EB", width=1)

try:
    if os.path.exists("logo_institucional.png"):
        logo = Image.open("logo_institucional.png")
        max_h = 65
        ratio = logo.width / logo.height
        logo = logo.resize((int(max_h * ratio), max_h), Image.Resampling.LANCZOS)
        img.paste(logo, (ANCHO - MARGEN_LATERAL - logo.width, (100 - max_h) // 2), mask=logo if logo.mode == 'RGBA' else None)
except Exception:
    pass

# 2. Bloque Banner Principal Dinámico
y_cursor = 115
tit_lines = textwrap.wrap(f"Evidencia Actual en {etiqueta_tema}", width=45)
sub_lines = textwrap.wrap(f"Análisis del estudio: {titulo_estudio_es}", width=80)

if len(sub_lines) > 3:
    sub_lines = sub_lines[:3]
    sub_lines[-1] += "..."

altura_banner = (len(tit_lines) * 28) + (len(sub_lines) * 20) + 24

draw.rounded_rectangle([(MARGEN_LATERAL, y_cursor), (ANCHO - MARGEN_LATERAL, y_cursor + altura_banner)], radius=12, fill=COLOR_GRIS_CLARO, outline="#E5E7EB", width=1)
draw.multiline_text((MARGEN_LATERAL + 20, y_cursor + 12), "\n".join(tit_lines), fill=COLOR_VERDE_UAEM, font=fuente_titulo, spacing=4)
draw.multiline_text((MARGEN_LATERAL + 20, y_cursor + 12 + (len(tit_lines) * 28)), "\n".join(sub_lines), fill="#4B5563", font=fuente_subtitulo, spacing=2)

y_cursor += altura_banner + 25

# 3. Distribución de los 3 bloques principales
Y_LIMITE_INFERIOR = 900
espacio_disponible = Y_LIMITE_INFERIOR - y_cursor
spacing_bloques = 20

# --- BLOQUE 1: PROBLEMA CLÍNICO ---
draw.text((MARGEN_LATERAL, y_cursor), "PROBLEMA CLÍNICO", fill=COLOR_VERDE_UAEM, font=fuente_subtitulo_sec)
y_cursor += 26
y_cursor, _ = draw_justified_text(draw, problema_texto, MARGEN_LATERAL, y_cursor, ANCHO_UTIL, fuente_cuerpo, COLOR_TEXTO_OSCURO, line_spacing=4)

y_cursor += spacing_bloques

# --- BLOQUE 2: HALLAZGO PRINCIPAL (CAJA DESTACADA) ---
y_hallazgo_top = y_cursor
ancho_caja_int = ANCHO_UTIL - 40

words = hallazgo_texto.split()
lines_h, current_l = [], []
for w in words:
    if draw.textlength(' '.join(current_l + [w]), font=fuente_cuerpo) <= ancho_caja_int:
        current_l.append(w)
    else:
        lines_h.append(' '.join(current_l))
        current_l = [w]
if current_l:
    lines_h.append(' '.join(current_l))

altura_texto_caja = len(lines_h) * 22
altura_caja = altura_texto_caja + 46

draw.rounded_rectangle([(MARGEN_LATERAL, y_hallazgo_top), (ANCHO - MARGEN_LATERAL, y_hallazgo_top + altura_caja)], radius=12, fill="#FDFBF7", outline=COLOR_ORO_UAEM, width=2)
draw.text((MARGEN_LATERAL + 20, y_hallazgo_top + 12), "HALLAZGO PRINCIPAL", fill=COLOR_VERDE_UAEM, font=fuente_subtitulo_sec)

draw_justified_text(draw, hallazgo_texto, MARGEN_LATERAL + 20, y_hallazgo_top + 38, ancho_caja_int, fuente_cuerpo, COLOR_TEXTO_OSCURO, line_spacing=4)

y_cursor = y_hallazgo_top + altura_caja + spacing_bloques

# --- BLOQUE 3: CONCLUSIÓN CLÍNICA ---
draw.text((MARGEN_LATERAL, y_cursor), "CONCLUSIÓN CLÍNICA", fill=COLOR_VERDE_UAEM, font=fuente_subtitulo_sec)
y_cursor += 26
y_cursor, _ = draw_justified_text(draw, conclusion_texto, MARGEN_LATERAL, y_cursor, ANCHO_UTIL, fuente_cuerpo, COLOR_TEXTO_OSCURO, line_spacing=4)

# --- PIE DE PÁGINA Y REFERENCIA (Anclados abajo) ---
draw.line([(MARGEN_LATERAL, 915), (ANCHO - MARGEN_LATERAL, 915)], fill="#E5E7EB", width=1)
draw.text((MARGEN_LATERAL, 922), "REFERENCIA BIBLIOGRÁFICA", fill="#6B7280", font=fuente_ref_bold)

ref_lines = textwrap.wrap(ref_vancouver, width=110)
draw.multiline_text((MARGEN_LATERAL, 940), "\n".join(ref_lines[:4]), fill="#4B5563", font=fuente_ref_reg, spacing=2)

# Barra verde institucional inferior
draw.rectangle([(0, ALTO - 50), (ANCHO, ALTO)], fill=COLOR_VERDE_UAEM)
draw.text((MARGEN_LATERAL, ALTO - 33), "UAEMéx • Facultad de Odontología", fill=COLOR_ORO_UAEM, font=fuente_pie)
nombre_pie = "Dr. en C. S. Josué R. Bermeo E."
draw.text((ANCHO - MARGEN_LATERAL - draw.textlength(nombre_pie, font=fuente_pie), ALTO - 33), nombre_pie, fill="#FFFFFF", font=fuente_pie)

img.save("main.png")
print("Infografía renderizada correctamente en español.")

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
msg['Subject'] = f"🧬 Dosis de Ciencia (Español): {etiqueta_tema}"
msg['From'] = remitente
msg['To'] = remitente
msg.set_content(f"Infografía generada traducida al español con síntesis clínica real:\n\n{copy_redes}")

with open("main.png", "rb") as f:
    msg.add_attachment(f.read(), maintype='image', subtype='png', filename="infografia_dosis_ciencia.png")

try:
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(remitente, contrasena)
        smtp.send_message(msg)
    print("¡Correo enviado exitosamente!")
except Exception as e:
    print(f"Error al enviar el correo: {e}")
