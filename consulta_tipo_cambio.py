import traceback
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

MESES_NUM = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "setiembre": 9, "septiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12
}

def get_chrome_options():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--blink-settings=imagesEnabled=false')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    return options

def consultar_tipo_cambio(incluir_historial=False):
    """
    Consulta el Tipo de Cambio Oficial (Dólar USD) publicado por la SUNAT.
    Retorna una tupla: (tipo_respuesta, mensaje_respuesta)
    - tipo_respuesta: 'C' (Correcto) o 'E' (Error)
    - mensaje_respuesta: Diccionario con datos si 'C', o mensaje de error string si 'E'
    """
    driver = None
    try:
        options = get_chrome_options()
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(20)

        url_tc = "https://e-consulta.sunat.gob.pe/cl-at-ittipcam/tcS01Alias"
        driver.get(url_tc)

        wait = WebDriverWait(driver, 8)
        # Buscar y hacer clic en el botón Buscar
        btns = driver.find_elements(By.TAG_NAME, "button")
        clicked = False
        for b in btns:
            if "Buscar" in b.text:
                b.click()
                clicked = True
                break

        # Esperar a que la tabla del calendario cargue
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "calendar-table")))

        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Extraer mes y año del encabezado del calendario
        mes_texto = ""
        anio_texto = ""
        btn_mes = soup.find("button", {"data-mode": "year"})
        if btn_mes:
            mes_texto = btn_mes.get_text(strip=True)
        btn_anio = soup.find("button", class_="js-cal-years")
        if btn_anio:
            anio_texto = btn_anio.get_text(strip=True)

        mes_num = MESES_NUM.get(mes_texto.lower(), 1)
        anio_num = int(anio_texto) if anio_texto.isdigit() else 2026

        # Extraer todos los días registrados en el mes
        dias = []
        patron = re.compile(r'(\d+)\s+Compra\s+([\d\.]+)\s+Venta\s+([\d\.]+)')
        for td in soup.find_all(["td", "div"]):
            texto = td.get_text(separator=" ", strip=True)
            m = patron.search(texto)
            if m:
                dia = int(m.group(1))
                compra = float(m.group(2))
                venta = float(m.group(3))
                if not any(d["dia"] == dia for d in dias):
                    dias.append({
                        "dia": dia,
                        "fecha": f"{anio_num}-{mes_num:02d}-{dia:02d}",
                        "compra": compra,
                        "venta": venta
                    })

        dias.sort(key=lambda x: x["dia"])

        if not dias:
            return "E", "No se encontraron cotizaciones publicadas para el mes actual en SUNAT."

        # El último día publicado es el tipo de cambio vigente
        ultimo = dias[-1]

        resultado = {
            "moneda": "USD",
            "fecha": ultimo["fecha"],
            "compra": ultimo["compra"],
            "venta": ultimo["venta"],
            "mes": mes_texto,
            "anio": anio_num,
            "fuente": "SUNAT Oficial"
        }

        if incluir_historial:
            resultado["historial_mes"] = dias

        return "C", resultado

    except Exception as e:
        tbinfo = traceback.format_exc()
        return "E", f"Error al consultar el tipo de cambio en SUNAT:\r\n{tbinfo}"
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
