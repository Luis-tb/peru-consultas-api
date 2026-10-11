import traceback
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import UnexpectedAlertPresentException, TimeoutException

def get_chrome_options():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--blink-settings=imagesEnabled=false')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    return options

def consultar_ruc(numero_ruc):
    """
    Consulta un RUC en el portal de la SUNAT utilizando Selenium en modo headless.
    Retorna una tupla: (tipo_respuesta, mensaje_respuesta)
    - tipo_respuesta: 'C' (Correcto) o 'E' (Error)
    - mensaje_respuesta: Diccionario con datos si 'C', o mensaje de error string si 'E'
    """
    numero_ruc = str(numero_ruc).strip()
    if not (len(numero_ruc) == 11 and numero_ruc.isdigit()):
        return "E", f"El RUC '{numero_ruc}' debe contener exactamente 11 dígitos numéricos."

    driver = None
    try:
        options = get_chrome_options()
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(20)

        url_sunat = "https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsruc/jcrS00Alias"
        driver.get(url_sunat)

        wait = WebDriverWait(driver, 8)
        txt_ruc = wait.until(EC.element_to_be_clickable((By.ID, "txtRuc")))
        txt_ruc.clear()
        txt_ruc.send_keys(numero_ruc)

        btn_buscar = driver.find_element(By.ID, "btnAceptar")
        btn_buscar.click()

        # Verificar si aparece alerta JS (por ejemplo número inválido)
        try:
            alert = driver.switch_to.alert
            alert_text = alert.text
            alert.accept()
            return "E", f"SUNAT: {alert_text}"
        except Exception:
            pass

        # Esperar respuesta
        try:
            wait.until(
                lambda d: d.find_elements(By.CLASS_NAME, "list-group-item")
                or "no existe" in d.page_source.lower()
                or "no registra" in d.page_source.lower()
            )
        except TimeoutException:
            return "E", f"Tiempo de espera agotado al consultar el RUC {numero_ruc} en SUNAT."

        page_source = driver.page_source
        if "el ruc ingresado no existe" in page_source.lower() or "no registra" in page_source.lower():
            return "E", f"El RUC {numero_ruc} no existe en la base de datos de la SUNAT."

        soup = BeautifulSoup(page_source, "html.parser")
        items = soup.select(".list-group-item")

        if not items:
            return "E", f"No se encontraron datos para el RUC {numero_ruc}."

        # Palabras clave de botones y acciones del pie de página que no son datos
        BLACKLIST_KEYWORDS = [
            "información histórica",
            "imprimir",
            "e-mail",
            "deuda coactiva",
            "omisiones tributarias",
            "reactiva perú",
            "actas probatorias",
            "facturas fisicas",
            "cantidad de trabajadores"
        ]

        datos_ruc = {}
        for item in items:
            # Si el elemento contiene botones de acción, omitir
            if item.find("button") or item.find("a", class_="btn"):
                continue

            text = item.get_text(separator="|", strip=True)
            parts = [p.strip() for p in text.split("|") if p.strip()]
            if len(parts) >= 2:
                clave = parts[0]
                clave_lower = clave.lower()

                # Ignorar si coincide con botones o enlaces
                if any(kw in clave_lower for kw in BLACKLIST_KEYWORDS):
                    continue

                valor = " ".join(parts[1:])
                # Limpiar espacios repetidos y saltos de línea
                valor = re.sub(r'\s+', ' ', valor).strip()
                datos_ruc[clave] = valor

        # Normalizar claves para compatibilidad
        if "Número de RUC:" in datos_ruc:
            datos_ruc["RUC:"] = datos_ruc["Número de RUC:"]
        if "Domicilio Fiscal:" not in datos_ruc:
            datos_ruc["Domicilio Fiscal:"] = "-"

        return "C", datos_ruc

    except UnexpectedAlertPresentException as e:
        return "E", f"Alerta de SUNAT: {e.alert_text}"
    except Exception as e:
        tbinfo = traceback.format_exc()
        return "E", f"Error al intentar consultar el RUC {numero_ruc}:\r\n{tbinfo}"
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
