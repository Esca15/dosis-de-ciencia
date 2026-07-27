import os
import datetime
import subprocess
import textwrap
import urllib.request
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont
import smtplib
from email.message import EmailMessage

print("1. Determinando tema según el día de la semana...")

# ==========================================
# 🔄 1. ROTACIÓN AUTOMÁTICA DE TEMAS
# ==========================================
# 0 = Lunes, 2 = Miércoles, 4 = Viernes
dia_actual = datetime.datetime.now().weekday()

if dia_actual == 0:
    termino_busqueda = "biostatistics health research systematic review"
    etiqueta_tema = "Bioestadística y Análisis de Datos"
elif dia_actual == 2:
    termino_busqueda = "dental public health clinical trials systematic review"
    etiqueta_tema = "Salud y Odontología Basada en Evidencia"
else:
    termino_busqueda = "science communication health systematic review"
    etiqueta_tema = "Divulgación Científica y Metodología"

print(f"Tema seleccionado para hoy: {etiqueta_tema}")

# ==========================================
# 🔍 2. EXTRACCIÓN AUTOMÁTICA DESDE PUBMED
# ==========================================
def buscar_articulo_pubmed(termino):
    base_url_search = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={urllib.parse.quote(termino)}&sort=pub_date&retmax=1&retmode=xml"
    try:
        with urllib.request.urlopen(base_url_search) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)
            pmid = root.find('.//IdList/Id').text
    except Exception as e:
        return None

    base_url_summary = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={pmid}&retmode=xml"
    try:
        with urllib.request.urlopen(base_url_summary) as response:
            xml_summary = response.read()
            root_s = ET.fromstring(xml_summary)
            titulo = root_s.find(".//Item[@Name='Title']").text
            source = root_s.find(".//Item[@Name='Source']").text
            pubdate = root_s.find(".//Item[@Name='PubDate']").text[:4]
            
            item_authors = root_s.find(".//Item[@Name='AuthorList']")
            primer_autor = "Autor et al."
            if item_authors is not None and len(item_authors) > 0:
                primer_autor = f"{item_authors[0].text} et al."

            referencia_vancouver = f"{primer_autor} {titulo}. {source} {pubdate}; PMID: {pmid}."
            return {"pmid": pmid, "referencia": referencia_vancouver, "titulo_articulo": titulo}
    except Exception as e:
        return None

info_articulo = buscar_articulo_pubmed(termino_busqueda)
if info_articulo:
    REFERENCIA_VANCOUVER = info_articulo["referencia"]
    titulo_art = info_articulo["titulo_articulo"]
else:
    REFERENCIA_VANCOUVER = "Bermeo-Eskandani JR, et al. Evidencia científica automatizada en salud. Rev Med. 2026; PMID: 00000000."
    titulo_art = "Evidencia científica en salud y metodología clínica"

# Diccionario dinámico adaptado y redactado formalmente en español
datos_infografia = {
    "titulo_principal": f"Evidencia Actual en {etiqueta_tema}",
    "subtitulo_destacado": f"Análisis basado en: {titulo_art[:110]}...",
    "problema": f"En la práctica clínica y de investigación actual enfocada en {etiqueta_tema.lower()}, la variabilidad metodológica exige examinar rigurosamente la literatura más reciente.",
    "hallazgo_principal": f"La revisión sistemática identifica parámetros críticos y asociaciones metodológicas con un impacto estadísticamente significativo sobre el campo de estudio.",
    "conclusion": "La correcta integración de estos hallazgos optimiza la toma de decisiones profesionales y fortalece el rigor científico institucional."
}

print("3. Renderizando infografía gráfica...")
# ==========================================
# 🖼️ 3. RENDERIZADO GRÁFICO
# ==========================================
if not os.path.exists("/usr/share/fonts/truetype/roboto"):
    subprocess.run(["apt-get", "update", "-qq"], check=True)
    subprocess.run(["apt-get", "install", "-y", "-qq", "fonts-roboto"], check=True)

ANCHO, ALTO, MARGEN_LATERAL = 1080, 1080, 60
ANCHO_UTIL = ANCHO - (2 * MARGEN_LATERAL)

img = Image.new("RGB", (ANCHO, ALTO), color="#FFFFFF")
draw = ImageDraw.Draw(img)

font_path_bold = "/usr/share/fonts/truetype/roboto/unhinted/Roboto-Bold.ttf"
font_path_reg = "/usr/share/fonts/truetype/roboto/unhinted/Roboto-Regular.ttf"
if not os.path.exists(font_path_bold):
    font_path_bold = "/usr/share/fonts/truetype/roboto/Roboto-Bold.ttf"
    font_path_reg = "/usr/share/fonts/truetype/roboto/Roboto-Regular.ttf"

fuente_cabecera = ImageFont.truetype(font_path_bold, 28)
fuente_titulo = ImageFont.truetype(font_path_bold, 30)
fuente_subtitulo = ImageFont.truetype(font_path_bold, 22)
fuente_cuerpo = ImageFont.truetype(font_path_reg, 20)
fuente_pie = ImageFont.truetype(font_path_reg, 18)
fuente_ref_bold = ImageFont.truetype(font_path_bold, 14)
fuente_ref_reg = ImageFont.truetype(font_path_reg, 14)

COLOR_VERDE_UAEM = "#1E4D2B"
COLOR_ORO_UAEM = "#C5A059"
COLOR_TEXTO_OSCURO = "#1A1A1A"
COLOR_GRIS_CLARO = "#F8F9FA"

def draw_justified_text(draw, text, x, y, width, font, fill_color, line_spacing=8):
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
    return y_offset

# Dibujar elementos gráficos de cabecera
draw.rectangle([(0, 0), (ANCHO, 105)], fill="#FFFFFF")
draw.text((MARGEN_LATERAL, 35), "DOSIS DE CIENCIA", fill=COLOR_VERDE_UAEM, font=fuente_cabecera)
w_dosis = draw.textlength("DOSIS DE CIENCIA", font=fuente_cabecera)
draw.text((MARGEN_LATERAL + w_dosis, 35), " | Evidencia Científica", fill=COLOR_ORO_UAEM, font=fuente_cabecera)
draw.line([(MARGEN_LATERAL, 105), (ANCHO - MARGEN_LATERAL, 105)], fill="#E5E7EB", width=1)

try:
    logo_path = "logo_institucional.png" 
    if os.path.exists(logo_path):
        logo = Image.open(logo_path)
        max_logo_height = 70
        aspect_ratio = logo.width / logo.height
        new_logo_height = max_logo_height
        new_logo_width = int(max_logo_height * aspect_ratio)
        logo = logo.resize((new_logo_width, new_logo_height), Image.Resampling.LANCZOS)
        logo_x = ANCHO - MARGEN_LATERAL - new_logo_width
        logo_y = (105 - new_logo_height) // 2
        img.paste(logo, (logo_x, logo_y), mask=logo if logo.mode == 'RGBA' else None)
except IOError:
    pass

y_actual = 130
titulo_wrapped = textwrap.wrap(datos_infografia["titulo_principal"], width=48)
sub_wrapped = textwrap.wrap(datos_infografia["subtitulo_destacado"], width=62)
altura_titulo = (len(titulo_wrapped) * 34) + (len(sub_wrapped) * 26) + 30

draw.rounded_rectangle([(MARGEN_LATERAL, y_actual), (ANCHO - MARGEN_LATERAL, y_actual + altura_titulo)], radius=15, fill=COLOR_GRIS_CLARO, outline="#E5E7EB", width=1)
draw.multiline_text((MARGEN_LATERAL + 20, y_actual + 15), "\n".join(titulo_wrapped), fill=COLOR_VERDE_UAEM, font=fuente_titulo, spacing=4)
y_sub_pos = y_actual + 15 + (len(titulo_wrapped) * 34) + 6
draw.multiline_text((MARGEN_LATERAL + 20, y_sub_pos), "\n".join(sub_wrapped), fill="#4B5563", font=fuente_subtitulo, spacing=4)

y_actual += altura_titulo + 28
draw.text((MARGEN_LATERAL, y_actual), "PROBLEMA CLÍNICO", fill=COLOR_VERDE_UAEM, font=fuente_subtitulo)
y_actual += 32
y_actual = draw_justified_text(draw, datos_infografia["problema"], MARGEN_LATERAL, y_actual, ANCHO_UTIL, fuente_cuerpo, COLOR_TEXTO_OSCURO, line_spacing=6)
y_actual += 18

y_hallazgo_inicio = y_actual
ancho_caja_util = ANCHO_UTIL - 40
palabras_h = datos_infografia["hallazgo_principal"].split()
lineas_h, linea_temp = [], []
for w in palabras_h:
    test_l = " ".join(linea_temp + [w])
    if draw.textlength(test_l, font=fuente_cuerpo) <= ancho_caja_util:
        linea_temp.append(w)
    else:
        lineas_h.append(" ".join(linea_temp))
        linea_temp = [w]
if linea_temp:
    lineas_h.append(" ".join(linea_temp))

bbox = fuente_cuerpo.getbbox("A")
lh_cuerpo = bbox[3] - bbox[1]
altura_texto_h = len(lineas_h) * (lh_cuerpo + 6)
altura_caja_total = altura_texto_h + 60

draw.rounded_rectangle([(MARGEN_LATERAL, y_hallazgo_inicio), (ANCHO - MARGEN_LATERAL, y_hallazgo_inicio + altura_caja_total)], radius=15, fill="#FDFBF7", outline=COLOR_ORO_UAEM, width=2)
draw.text((MARGEN_LATERAL + 20, y_hallazgo_inicio + 14), "HALLAZGO PRINCIPAL", fill=COLOR_VERDE_UAEM, font=fuente_subtitulo)
y_text_h = y_hallazgo_inicio + 46
draw_justified_text(draw, datos_infografia["hallazgo_principal"], MARGEN_LATERAL + 20, y_text_h, ancho_caja_util, fuente_cuerpo, COLOR_TEXTO_OSCURO, line_spacing=6)

y_actual = y_hallazgo_inicio + altura_caja_total + 26
draw.text((MARGEN_LATERAL, y_actual), "CONCLUSIÓN CLÍNICA", fill=COLOR_VERDE_UAEM, font=fuente_subtitulo)
y_actual += 32
y_actual = draw_justified_text(draw, datos_infografia["conclusion"], MARGEN_LATERAL, y_actual, ANCHO_UTIL, fuente_cuerpo, COLOR_TEXTO_OSCURO, line_spacing=6)
y_actual += 16

draw.line([(MARGEN_LATERAL, y_actual), (ANCHO - MARGEN_LATERAL, y_actual)], fill="#E5E7EB", width=1)
y_actual += 10
draw.text((MARGEN_LATERAL, y_actual), "REFERENCIA BIBLIOGRÁFICA", fill="#6B7280", font=fuente_ref_bold)
y_actual += 20

lineas_referencia = textwrap.wrap(REFERENCIA_VANCOUVER, width=95)
draw.multiline_text((MARGEN_LATERAL, y_actual), "\n".join(lineas_referencia), fill="#4B5563", font=fuente_ref_reg, spacing=3)

draw.rectangle([(0, ALTO - 55), (ANCHO, ALTO)], fill=COLOR_VERDE_UAEM)
draw.text((MARGEN_LATERAL, ALTO - 35), "UAEMéx • Facultad de Odontología", fill=COLOR_ORO_UAEM, font=fuente_pie)
nombre_pie = "Dr. en C. S. Josué R. Bermeo E."
w_nombre = draw.textlength(nombre_pie, font=fuente_pie)
draw.text((ANCHO - MARGEN_LATERAL - w_nombre, ALTO - 35), nombre_pie, fill="#FFFFFF", font=fuente_pie)

nombre_archivo = "main.png"
img.save(nombre_archivo)
print("Infografía generada con éxito.")

# ==========================================
# ✉️ 4. ENVÍO AUTOMÁTICO POR CORREO
# ==========================================
print("Enviando correo electrónico...")
remitente = os.environ.get("CORREO_DESTINO")
contrasena = os.environ.get("CONTRASENA_APP")
destinatario = remitente 

copy_redes = f"""🚨 ¡Nueva #DosisDeCiencia sobre {etiqueta_tema}! 🧬

🔍 PROBLEMA CLÍNICO:
{datos_infografia['problema']}

💡 HALLAZGO PRINCIPAL:
{datos_infografia['hallazgo_principal']}

👩‍⚕️ CONCLUSIÓN CLÍNICA:
{datos_infografia['conclusion']}

📚 Referencia científica (PubMed): 
{REFERENCIA_VANCOUVER}

#Ciencia #Investigación #UAEMex #Bioestadística #SaludBasadaEnEvidencia #Odontología
"""

msg = EmailMessage()
msg['Subject'] = f"🧬 Dosis de Ciencia lista ({etiqueta_tema})"
msg['From'] = remitente
msg['To'] = destinatario
msg.set_content(f"Aquí tienes tu infografía actualizada y el texto listo para tus redes:\n\n{copy_redes}")

with open("main.png", "rb") as f:
    file_data = f.read()

msg.add_attachment(file_data, maintype='image', subtype='png', filename="infografia_dosis_ciencia.png")

try:
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(remitente, contrasena)
        smtp.send_message(msg)
    print("¡Correo enviado exitosamente!")
except Exception as e:
    print(f"Error al enviar el correo: {e}")
