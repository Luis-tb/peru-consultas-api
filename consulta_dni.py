import traceback
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

def consultar_dni(numero_dni):
    """
    Consulta un DNI en el portal de la SUNAT utilizando la búsqueda por documento.
    Retorna una tupla: (tipo_respuesta, mensaje_respuesta)
    - tipo_respuesta: 'C' (Correcto) o 'E' (Error)
    - mensaje_respuesta: Diccionario con datos si 'C', o mensaje de error string si 'E'
    """
    numero_dni = str(numero_dni).strip()
    if not (len(numero_dni) == 8 and numero_dni.isdigit()):
        return "E", f"El DNI '{numero_dni}' debe contener exactamente 8 dígitos numéricos."

    driver = None
    try:
        options = get_chrome_options()
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(20)

        url_sunat = "https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsruc/jcrS00Alias"
        driver.get(url_sunat)

        wait = WebDriverWait(driver, 8)
        btn_doc = wait.until(EC.element_to_be_clickable((By.ID, "btnPorDocumento")))
        btn_doc.click()

        txt_doc = wait.until(EC.element_to_be_clickable((By.ID, "txtNumeroDocumento")))
        txt_doc.clear()
        txt_doc.send_keys(numero_dni)

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
                or "no registra" in d.page_source.lower()
                or "no existe" in d.page_source.lower()
            )
        except TimeoutException:
            return "E", f"Tiempo de espera agotado al consultar el DNI {numero_dni} en SUNAT."

        page_source = driver.page_source
        if "no registra un número de ruc" in page_source.lower() or "no existe" in page_source.lower():
            return "E", f"El DNI {numero_dni} no registra información de contribuyente en SUNAT."

        soup = BeautifulSoup(page_source, "html.parser")
        items = soup.select(".list-group-item.aRucs")

        if not items:
            return "E", f"No se encontraron registros para el DNI {numero_dni} en SUNAT."

        item = items[0]
        headings = item.select(".list-group-item-heading")
        ruc_text = (
            headings[0].get_text(strip=True).replace("RUC:", "").strip()
            if len(headings) > 0
            else item.get("data-ruc", "")
        )
        nombre_completo = headings[1].get_text(strip=True) if len(headings) > 1 else ""

        ubicacion = ""
        estado = ""
        for p in item.select(".list-group-item-text"):
            txt = p.get_text(strip=True)
            if "Ubicación:" in txt:
                ubicacion = txt.replace("Ubicación:", "").strip()
            elif "Estado:" in txt:
                estado = txt.replace("Estado:", "").strip()

        resultado = {
            "dni": numero_dni,
            "ruc": ruc_text,
            "nombres": nombre_completo,
            "ubicacion": ubicacion,
            "estado": estado
        }

        return "C", resultado

    except UnexpectedAlertPresentException as e:
        return "E", f"Alerta de SUNAT: {e.alert_text}"
    except Exception as e:
        tbinfo = traceback.format_exc()
        return "E", f"Error al intentar consultar el DNI {numero_dni}:\r\n{tbinfo}"
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
