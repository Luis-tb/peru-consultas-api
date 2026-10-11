import traceback
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

TIPOS_COMPROBANTE = {
    "01": "01", # Recibo por Honorarios Electrónico
    "recibo": "01",
    "rhe": "01",
    "03": "03", # Factura Electrónica
    "factura": "03",
    "factura electronica": "03",
    "06": "06", # Boleta Electrónica
    "boleta": "06",
    "boleta electronica": "06",
    "04": "04", # Nota de Crédito Factura
    "05": "05", # Nota de Débito Factura
    "11": "11", # Nota de Crédito Boleta
    "12": "12", # Nota de Débito Boleta
    "07": "07", # Guía de Remisión Remitente
    "09": "09", # Guía de Remisión Transportista
    "20": "20", # Comprobante de Retención
    "40": "40", # Comprobante de Percepción
}

def get_chrome_options():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    return options

def consultar_cpe(ruc_emisor, tipo_comprobante, serie, numero, fecha_emision, monto, tipo_doc_receptor="-", num_doc_receptor=""):
    """
    Valida la existencia y estado de un Comprobante de Pago Electrónico en SUNAT.
    - ruc_emisor: RUC de 11 dígitos
    - tipo_comprobante: '01' (RHE), '03' o 'factura', '06' o 'boleta', etc.
    - serie: Serie del comprobante (ej: F001, E001, B001)
    - numero: Número o correlativo (ej: 1, 1420)
    - fecha_emision: Fecha en formato DD/MM/AAAA (ej: 01/10/2026)
    - monto: Monto total con decimales (ej: 150.00 o 150)
    """
    ruc_emisor = str(ruc_emisor).strip()
    if not (len(ruc_emisor) == 11 and ruc_emisor.isdigit()):
        return "E", f"El RUC del emisor '{ruc_emisor}' debe contener exactamente 11 dígitos."

    tipo_str = str(tipo_comprobante).strip().lower()
    tipo_codigo = TIPOS_COMPROBANTE.get(tipo_str, tipo_str)

    serie = str(serie).strip().upper()
    numero = str(numero).strip()
    fecha_emision = str(fecha_emision).strip()
    
    # Formatear monto a 2 decimales si es numérico
    try:
        monto_num = float(str(monto).replace(",", "."))
        monto_str = f"{monto_num:.2f}"
    except Exception:
        monto_str = str(monto).strip()

    driver = None
    try:
        options = get_chrome_options()
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(20)

        url_valicpe = "https://ww1.sunat.gob.pe/ol-ti-itconsvalicpe/ConsValiCpe.htm"
        driver.get(url_valicpe)

        wait = WebDriverWait(driver, 8)
        txt_ruc = wait.until(EC.presence_of_element_located((By.NAME, "num_ruc")))
        txt_ruc.clear()
        txt_ruc.send_keys(ruc_emisor)

        Select(driver.find_element(By.NAME, "tipocomprobante")).select_by_value(tipo_codigo)
        driver.find_element(By.NAME, "num_serie").send_keys(serie)
        driver.find_element(By.NAME, "num_comprob").send_keys(numero)

        if tipo_doc_receptor and tipo_doc_receptor != "-":
            try:
                Select(driver.find_element(By.NAME, "cod_docide")).select_by_value(str(tipo_doc_receptor))
                driver.find_element(By.NAME, "num_docide").send_keys(str(num_doc_receptor))
            except Exception:
                pass

        # Llenar fecha y monto vía JavaScript para evitar que el popup datetimepicker intercepte el clic
        driver.execute_script(f"document.getElementsByName('fec_emision')[0].value = '{fecha_emision}';")
        driver.execute_script(f"document.getElementsByName('cantidad')[0].value = '{monto_str}';")

        # Ejecutar validación
        driver.execute_script("opcGrabar();")

        # Verificar si aparece alerta JS
        try:
            alert = driver.switch_to.alert
            alert_text = alert.text
            alert.accept()
            return "E", f"SUNAT: {alert_text}"
        except Exception:
            pass

        # Esperar a que la página de respuesta cargue
        wait.until(lambda d: "resultado de la consulta" in d.page_source.lower()
                   or "no existe" in d.page_source.lower()
                   or "comprobante" in d.page_source.lower())

        page_source = driver.page_source
        soup = BeautifulSoup(page_source, "html.parser")
        body_text = driver.find_element(By.TAG_NAME, "body").text

        # Evaluar resultado
        if "no existe en los registros de sunat" in body_text.lower():
            return "C", {
                "valido": False,
                "estado_comprobante": "NO_EXISTE",
                "mensaje": f"El comprobante {serie}-{numero} no existe en los registros de SUNAT.",
                "ruc_emisor": ruc_emisor,
                "serie": serie,
                "numero": numero,
                "fecha_emision": fecha_emision,
                "monto": monto_str
            }

        # Extraer tabla de datos si fue aceptado
        resultado = {
            "valido": True,
            "ruc_emisor": ruc_emisor,
            "serie": serie,
            "numero": numero,
            "fecha_emision": fecha_emision,
            "monto": monto_str,
            "estado_comprobante": "REGISTRADO",
            "detalles": {}
        }

        tablas = soup.find_all("table", class_="form-table")
        for tbl in tablas:
            filas = tbl.find_all("tr")
            for f in filas:
                cols = f.find_all(["td", "th"])
                if len(cols) >= 2:
                    k = cols[0].get_text(strip=True).replace(":", "")
                    v = cols[1].get_text(strip=True)
                    if k and v:
                        resultado["detalles"][k] = v

        if not resultado["detalles"]:
            resultado["detalles"]["mensaje"] = body_text.strip()

        return "C", resultado

    except Exception as e:
        tbinfo = traceback.format_exc()
        return "E", f"Error al validar comprobante en SUNAT:\r\n{tbinfo}"
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
