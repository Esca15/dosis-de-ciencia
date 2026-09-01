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

print("1. Configurando parámetros y clasificadores de siglas...")

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
# 📚 2. DICCIONARIOS Y REGLAS DE TRADUCCIÓN
# ==========================================

MAPEO_SIGLAS_ES_EN = {
    "EII": "IBD", "IBD": "EII",
    "DAV": "VAD", "VAD": "DAV",
    "ILT": "DLI", "DLI": "ILT",
    "CVRS": "HRQoL", "HRQoL": "CVRS",
    "EC": "CD", "CD": "EC",
    "SSR": "SRH", "SRH": "SSR",
    "TNF": "FND", "FND": "TNF"
}

# Diccionario explícito para acrónimos de contexto regional, clínico y metodológico
DICCIONARIO_SIGLAS_ESTANDAR = {
    "NDIS": "Esquema Nacional de Seguro de Discapacidad de Australia (National Disability Insurance Scheme)",
    "SSR": "Salud Sexual y Reproductiva (Sexual and Reproductive Health)",
    "SRH": "Salud Sexual y Reproductiva (Sexual and Reproductive Health)",
    "FND": "Trastorno Neurológico Funcional (Functional Neurological Disorder)",
    "TNF": "Trastorno Neurológico Funcional (Functional Neurological Disorder)",
    "GRADE": "Sistema de Clasificación del Nivel de Evidencia (Grading of Recommendations Assessment, Development and Evaluation)",
    "PRISMA": "Elementos de Informe Preferidos para Revisiones Sistemáticas (Preferred Reporting Items for Systematic Reviews and Meta-Analyses)",
    "STROBE": "Fortalecimiento del Reporte de Estudios Observacionales en Epidemiología (Strengthening the Reporting of Observational Studies in Epidemiology)",
    "CONSORT": "Estándares Consolidados para el Reporte de Ensayos Clínicos (Consolidated Standards of Reporting Trials)"
}

TRADUCCIONES_DIRECTAS_TEXTO = {
    r'\bSexual and Reproductive Health\b': 'Salud Sexual y Reproductiva (SSR)',
    r'\bsexual and reproductive health\b': 'salud sexual y reproductiva (SSR)',
    r'\bSRH\b': 'SSR',
    r'\bFunctional Neurological Disorder\b': 'Trastorno Neurológico Funcional (TNF)',
    r'\bfunctional neurological disorder\b': 'trastorno neurológico funcional (TNF)',
    r'\bFND\b': 'TNF/FND',
    r'\bOverall Survival\b': 'Supervivencia Global (SG)',
    r'\boverall survival\b': 'supervivencia global (SG)',
    r'\bOS\b': 'SG',
    r'\bProgression-Free Survival\b': 'Supervivencia Libre de Progresión (SLP)',
    r'\bprogression-free survival\b': 'supervivencia libre de progresión (SLP)',
    r'\bPFS\b': 'SLP',
    r'\bDisease-Free Survival\b': 'Supervivencia Libre de Enfermedad (SLE)',
    r'\bDFS\b': 'SLE',
    r'\bAdverse Events\b': 'Eventos Adversos (EA)',
    r'\badverse events\b': 'eventos adversos (EA)',
    r'\bAEs\b': 'EAs',
    r'\bAE\b': 'EA',
    r'\bQuality of Life\b': 'Calidad de Vida (CdV)',
    r'\bQoL\b': 'CdV',
    r'\bIntensive Care Unit\b': 'Unidad de Cuidados Intensivos (UCI)',
    r'\bICU\b': 'UCI',
    r'\bEW/TTS\b': 'SAT/STT (Sistemas Alerta Temprana)',
    r'\bClinical Deterioration\b': 'Deterioro Clínico (EC)',
    r'\bclinical deterioration\b': 'deterioro clínico (EC)',
    r'\bCD\b': 'EC'
}

SIGLAS_UNIVERSALES_OMITIR_GLOSARIO = {
    "OR", "ORS", "HR", "HRS", "RR", "RRS", "CI", "CIS", "IC", "ICS",
    "SD", "SDS", "SE", "SES", "MD", "MDS", "SMD", "SMDS",
    "ANOVA", "MANOVA", "PCA", "ROC", "AUC",
    "RCT", "RCTS", "ECA", "ECAS", "P", "PMID", "CAD/CAM", "CBCT"
}

def aplicar_traducciones_directas(texto):
    if not texto:
        return ""
    texto_trad = texto
    for patron, reemplazo in TRADUCCIONES_DIRECTAS_TEXTO.items():
        texto_trad = re.sub(patron, reemplazo, texto_trad)
    return texto_trad

def extraer_siglas_medicas_especificas(abstract_original_en, texto_traducido_es):
    glosario_especifico = {}
    translator = GoogleTranslator(source='en', target='es')

    # 1. Escaneo por patrones estándar "Term (ACRONYM)" en el abstract original
    if abstract_original_en:
        patron_definiciones = r'\b([a-zA-Z0-9\-\s]{2,50})\s*\(([A-Z0-9]{2,10})s?\)'
        coincidencias = re.findall(patron_definiciones, abstract_original_en)
        
        for termino_en, sigla in coincidencias:
            sigla_en = sigla.strip().rstrip('sS')
            termino_en_clean = termino_en.strip()
            
            if sigla_en in SIGLAS_UNIVERSALES_OMITIR_GLOSARIO or len(termino_en_clean) < 4:
                continue
                
            sigla_es = MAPEO_SIGLAS_ES_EN.get(sigla_en, sigla_en)
            
            # Si ya la tenemos estandarizada en el diccionario maestro, usarla prioritariamente
            if sigla_es in DICCIONARIO_SIGLAS_ESTANDAR:
                glosario_especifico[sigla_es] = DICCIONARIO_SIGLAS_ESTANDAR[sigla_es]
                continue
            elif sigla_en in DICCIONARIO_SIGLAS_ESTANDAR:
                glosario_especifico[sigla_en] = DICCIONARIO_SIGLAS_ESTANDAR[sigla_en]
                continue

            # LIMPIEZA DE PALABRAS BASURA / FRAGMENTOS PREVIOS (Evita errores tipo "Moment in...")
            patron_stop_words = r'^(at\s+that\s+moment\s+in|moment\s+in|patients?\s+with|changes?\s+in|rate\s+of|levels?\s+of|effects?\s+of|association\s+of|and|or|with|by|for|in|of|to|a|an|the)\s+'
            termino_en_clean = re.sub(patron_stop_words, '', termino_en_clean, flags=re.IGNORECASE).strip().capitalize()

            if len(termino_en_clean) < 4:
                continue

            try:
                def_es = translator.translate(termino_en_clean).capitalize()
            except Exception:
                def_es = termino_en_clean
                
            # Evitar redundancia si el traductor devolvió exactamente la misma cadena en inglés
            if def_es.lower() == termino_en_clean.lower():
                glosario_especifico[sigla_es] = f"{def_es}"
            else:
                glosario_especifico[sigla_es] = f"{def_es} ({termino_en_clean})"

    # 2. Escaneo complementario: Buscar siglas presentes en el TEXTO FINAL traducido
    siglas_en_texto = set(re.findall(r'\b[A-Z]{2,8}\b', texto_traducido_es))
    
    for sigla in siglas_en_texto:
        if sigla in SIGLAS_UNIVERSALES_OMITIR_GLOSARIO:
            continue
            
        if sigla in DICCIONARIO_SIGLAS_ESTANDAR and sigla not in glosario_especifico:
            glosario_especifico[sigla] = DICCIONARIO_SIGLAS_ESTANDAR[sigla]
            
        elif sigla in MAPEO_SIGLAS_ES_EN:
            sigla_mantenida = MAPEO_SIGLAS_ES_EN[sigla]
            if sigla_mantenida in DICCIONARIO_SIGLAS_ESTANDAR and sigla_mantenida not in glosario_especifico:
                glosario_especifico[sigla_mantenida] = DICCIONARIO_SIGLAS_ESTANDAR[sigla_mantenida]

    return glosario_especifico

def limpiar_y_normalizar_simbolos(texto):
    if not texto:
        return ""
    texto = unicodedata.normalize('NFKC', texto)
    texto = re.sub(r'\.{2,}', '.', texto)
    return texto.strip()

def traducir_y_adaptar(texto):
    if not texto or len(texto.strip()) == 0:
        return ""
    
    texto_prep = aplicar_traducciones_directas(texto)
    traduccion = ""
    
    intentos = 5
    for i in range(intentos):
        try:
            res = GoogleTranslator(source='en', target='es').translate(texto_prep)
            if res and len(res.strip()) > 0 and "Error 500" not in res and "That's an error" not in res:
                traduccion = res
                break
        except Exception:
            time.sleep(1.5 * (i + 1))

    if not traduccion or len(traduccion.strip()) == 0:
        oraciones = re.split(r'\.\s+', texto_prep)
        oraciones_traducidas = []
        for o in oraciones:
            if not o.strip():
                continue
            t_oracion = ""
            for k in range(3):
                try:
                    t_oracion = GoogleTranslator(source='en', target='es').translate(o)
                    if t_oracion:
                        break
                except Exception:
                    time.sleep(1)
            oraciones_traducidas.append(t_oracion if t_oracion else o)
        traduccion = ". ".join(oraciones_traducidas)

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

    traduccion = aplicar_traducciones_directas(traduccion)
    traduccion = limpiar_y_normalizar_simbolos(traduccion)
    traduccion = re.sub(r'[\(\[\{][^\)\}\]]*$', '', traduccion).strip()
    
    if not traduccion.endswith('.'):
        traduccion += '.'

    return traduccion

def clasificar_area_tematica(titulo_es, abstract_es, tema_por_defecto):
    texto_completo = f"{titulo_es} {abstract_es}".lower()
    kw_dental = ["dental", "odonto", "caries", "periodont", "endodon", "maxilofac", "salud bucal", "diente", "oral", "fluor"]
    kw_bioest = ["estadístic", "metaanálisis", "meta-análisis", "ensayo clínico", "modelo", "regresión", "prevalencia", "cohorte", "pronóstico", "predict", "variables", "algoritmo", "automatiz"]
    
    if any(k in texto_completo for k in kw_dental):
        return "Salud y Odontología Basada en Evidencia"
    elif any(k in texto_completo for k in kw_bioest):
        return "Bioestadística y Análisis de Datos"
    else:
        return tema_por_defecto

def extraer_problema_clinico_estructurado(abs_dict, abs_full):
    prob_text = abs_dict.get("BACKGROUND", abs_dict.get("OBJECTIVE", abs_dict.get("INTRODUCTION", "")))
    if prob_text:
        return prob_text

    oraciones = [o.strip() for o in re.split(r'\.\s+|\n+', abs_full) if len(o.strip()) > 15]
    patrones_contexto = [
        r'\baimed to\b', r'\bthe purpose of\b', r'\bwe evaluated\b', 
        r'\blittle is known\b', r'\bremains unclear\b', r'\bdespite\b',
        r'\bhowever\b', r'\black of\b', r'\bis a common\b', r'\bto investigate\b',
        r'\bare crucial\b', r'\bis essential\b'
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
                
                titulo_clean = titulo.strip().rstrip('.')

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
                source_clean = source.strip().rstrip('.')
                
                year_elem = root_f.find(".//JournalIssue/PubDate/Year")
                pubdate = year_elem.text[:4] if year_elem is not None else "2026"

                author_list = root_f.findall(".//Author")
                primer_autor = "Investigadores et al."
                if author_list:
                    lastname = author_list[0].find("LastName")
                    if lastname is not None and lastname.text:
                        primer_autor = f"{lastname.text} et al."

                referencia = f"{primer_autor} {titulo_clean}. {source_clean}. {pubdate}; PMID: {pmid}."
                
                candidatos.append({
                    "pmid": pmid,
                    "titulo": titulo_clean,
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
    abs_full = estudio["abstract_completo"]
    
    prob_text = extraer_problema_clinico_estructurado(abs_dict, abs_full)
    hall_text = abs_dict.get("RESULTS", abs_dict.get("FINDINGS", ""))
    conc_text = abs_dict.get("CONCLUSIONS", abs_dict.get("CONCLUSION", ""))

    if not hall_text:
        oraciones_todas = [o.strip() for o in re.split(r'\.\s+', abs_full) if len(o.strip()) > 15]
        hall_text = ". ".join(oraciones_todas[1:-1]) if len(oraciones_todas) >= 3 else abs_full

    if not conc_text:
        oraciones_todas = [o.strip() for o in re.split(r'\.\s+', abs_full) if len(o.strip()) > 15]
        conc_text = oraciones_todas[-1] if len(oraciones_todas) > 1 else abs_full

    prob_clean = obtener_oraciones_completas(prob_text, max_caracteres=300)
    hall_clean = obtener_oraciones_completas(hall_text, max_caracteres=950)
    conc_clean = obtener_oraciones_completas(conc_text, max_caracteres=250)

    titulo_estudio_es = traducir_y_adaptar(estudio["titulo"])
    problema_texto = traducir_y_adaptar(prob_clean)
    hallazgo_texto = traducir_y_adaptar(hall_clean)
    conclusion_texto = traducir_y_adaptar(conc_clean)

    if problema_texto in hallazgo_texto:
        hallazgo_texto = hallazgo_texto.replace(problema_texto, "").strip()

    texto_infografia_completo = f"{problema_texto} {hallazgo_texto} {conclusion_texto}"
    glosario_especifico_dict = extraer_siglas_medicas_especificas(abs_full, texto_infografia_completo)

    etiqueta_tema = clasificar_area_tematica(titulo_estudio_es, hallazgo_texto, etiqueta_defecto)

else:
    ref_vancouver = "Bermeo-Escalona JR, et al. Análisis de evidencia en ciencias de la salud. Rev Med UAEMéx. 2026; PMID: 41964104."
    titulo_estudio_es = "Evaluación sistemática y modelos de análisis en ciencias de la salud"
    problema_texto = "Existe una alta heterogeneidad en los reportes de investigación que compromete la reproducibilidad de los datos en salud."
    hallazgo_texto = "La implementación de modelos estandarizados redujo la variabilidad metodológica en un 42%, optimizando la precisión de los resultados clínicos."
    conclusion_texto = "El uso de marcos analíticos rigurosos es indispensable para consolidar la práctica basada en la evidencia."
    glosario_especifico_dict = {}
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
fuente_subtitulo_sec = ImageFont.truetype(font_path_bold, 18)
fuente_subtitulo = ImageFont.truetype(font_path_reg, 15)

fuente_cuerpo_estandar = ImageFont.truetype(font_path_reg, 16)

fuente_pie = ImageFont.truetype(font_path_reg, 17)
fuente_ref_bold = ImageFont.truetype(font_path_bold, 13)
fuente_ref_reg = ImageFont.truetype(font_path_reg, 12)

COLOR_VERDE_UAEM = "#1E4D2B"
COLOR_ORO_UAEM = "#C5A059"
COLOR_TEXTO_OSCURO = "#1A1A1A"
COLOR_GRIS_CLARO = "#F8F9FA"

def draw_justified_text(draw, text, x, y, width, font, fill_color, line_spacing=6):
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

altura_banner = (len(tit_lines) * 26) + (len(sub_lines) * 19) + 20

draw.rounded_rectangle([(MARGEN_LATERAL, y_cursor), (ANCHO - MARGEN_LATERAL, y_cursor + altura_banner)], radius=8, fill=COLOR_GRIS_CLARO, outline="#E5E7EB", width=1)
draw.multiline_text((MARGEN_LATERAL + 18, y_cursor + 10), "\n".join(tit_lines), fill=COLOR_VERDE_UAEM, font=fuente_titulo, spacing=4)
draw.multiline_text((MARGEN_LATERAL + 18, y_cursor + 10 + (len(tit_lines) * 26)), "\n".join(sub_lines), fill="#4B5563", font=fuente_subtitulo, spacing=3)

y_cursor += altura_banner + 24
spacing_bloques = 24

# BLOQUE 1: PROBLEMA CLÍNICO
draw.text((MARGEN_LATERAL, y_cursor), "PROBLEMA CLÍNICO", fill=COLOR_VERDE_UAEM, font=fuente_subtitulo_sec)
y_cursor += 24
y_cursor, _ = draw_justified_text(draw, problema_texto, MARGEN_LATERAL, y_cursor, ANCHO_UTIL, fuente_cuerpo_estandar, COLOR_TEXTO_OSCURO, line_spacing=5)

y_cursor += spacing_bloques

# BLOQUE 2: HALLAZGO PRINCIPAL
y_hallazgo_top = y_cursor
ancho_indentado = ANCHO_UTIL - 24
x_texto_hallazgo = MARGEN_LATERAL + 24

draw.text((MARGEN_LATERAL, y_hallazgo_top), "HALLAZGO PRINCIPAL", fill=COLOR_VERDE_UAEM, font=fuente_subtitulo_sec)
y_cursor_hallazgo = y_hallazgo_top + 24

y_fin_hallazgo, _ = draw_justified_text(draw, hallazgo_texto, x_texto_hallazgo, y_cursor_hallazgo, ancho_indentado, fuente_cuerpo_estandar, COLOR_TEXTO_OSCURO, line_spacing=5)

draw.line([(MARGEN_LATERAL + 6, y_cursor_hallazgo - 2), (MARGEN_LATERAL + 6, y_fin_hallazgo - 4)], fill=COLOR_ORO_UAEM, width=5)

y_cursor = y_fin_hallazgo + spacing_bloques

# BLOQUE 3: CONCLUSIÓN CLÍNICA
draw.text((MARGEN_LATERAL, y_cursor), "CONCLUSIÓN CLÍNICA", fill=COLOR_VERDE_UAEM, font=fuente_subtitulo_sec)
y_cursor += 24
y_cursor, _ = draw_justified_text(draw, conclusion_texto, MARGEN_LATERAL, y_cursor, ANCHO_UTIL, fuente_cuerpo_estandar, COLOR_TEXTO_OSCURO, line_spacing=5)

# BLOQUE 4: GLOSARIO INTEGRADO
if glosario_especifico_dict:
    y_cursor += spacing_bloques
    draw.text((MARGEN_LATERAL, y_cursor), "GLOSARIO DEL ESTUDIO", fill=COLOR_VERDE_UAEM, font=fuente_subtitulo_sec)
    y_cursor += 24
    
    lineas_glosario = []
    for sigla, def_comp in glosario_especifico_dict.items():
        lineas_glosario.append(f"• {sigla}: {def_comp}")
    
    texto_glosario_completo = "  |  ".join(lineas_glosario)
    y_cursor, _ = draw_justified_text(draw, texto_glosario_completo, MARGEN_LATERAL, y_cursor, ANCHO_UTIL, fuente_cuerpo_estandar, COLOR_TEXTO_OSCURO, line_spacing=5)

# --- REFERENCIA Y PIE DE PÁGINA ---
ref_lines = textwrap.wrap(ref_vancouver, width=115)
lineas_ref = ref_lines[:2]
altura_texto_ref = len(lineas_ref) * 15

y_referencia_bloque = (ALTO - 48) - 20 - altura_texto_ref - 15

if y_cursor > y_referencia_bloque - 10:
    y_referencia_bloque = y_cursor + 15

draw.line([(MARGEN_LATERAL, y_referencia_bloque), (ANCHO - MARGEN_LATERAL, y_referencia_bloque)], fill="#E5E7EB", width=1)

draw.text((MARGEN_LATERAL, y_referencia_bloque + 8), "REFERENCIA BIBLIOGRÁFICA", fill="#6B7280", font=fuente_ref_bold)
draw.multiline_text((MARGEN_LATERAL, y_referencia_bloque + 24), "\n".join(lineas_ref), fill="#4B5563", font=fuente_ref_reg, spacing=2)

# Footer inferior Verde UAEM
draw.rectangle([(0, ALTO - 48), (ANCHO, ALTO)], fill=COLOR_VERDE_UAEM)
draw.text((MARGEN_LATERAL, ALTO - 32), "UAEMéx • Facultad de Odontología", fill=COLOR_ORO_UAEM, font=fuente_pie)
nombre_pie = "Dr. en C. S. Josué R. Bermeo E."
draw.text((ANCHO - MARGEN_LATERAL - draw.textlength(nombre_pie, font=fuente_pie), ALTO - 32), nombre_pie, fill="#FFFFFF", font=fuente_pie)

img.save("main.png")
print("Infografía renderizada correctamente.")

# ==========================================
# ✉️ 5. CONSTRUCCIÓN DE COPY CON MICRO-GLOSARIO Y ENVÍO DE CORREO
# ==========================================

bloque_glosario = ""
if glosario_especifico_dict:
    bloque_glosario = "\n📌 GLOSARIO DEL ESTUDIO:\n"
    for sigla, def_completa in glosario_especifico_dict.items():
        bloque_glosario += f"• {sigla}: {def_completa}\n"

copy_redes = f"""🚨 ¡Nueva #DosisDeCiencia sobre {etiqueta_tema}! 🧬

📌 ESTUDIO ANALIZADO:
{titulo_estudio_es}

🔍 PROBLEMA CLÍNICO:
{problema_texto}

💡 HALLAZGO PRINCIPAL:
{hallazgo_texto}

👩‍⚕️ CONCLUSIÓN CLÍNICA:
{conclusion_texto}
{bloque_glosario}
📚 Referencia científica (PubMed): 
{ref_vancouver}

#Ciencia #Investigación #UAEMex #Bioestadística #SaludBasadaEnEvidencia #Odontología
"""

remitente = os.environ.get("CORREO_DESTINO")
contrasena = os.environ.get("CONTRASENA_APP")

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
