import traceback
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from consulta_dni import consultar_dni

def get_chrome_options():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    return options

def separar_nombre_peruano(nombre_completo):
    """
    Separa un nombre completo peruano en:
    (apellido_paterno, apellido_materno, primer_nombre, segundo_nombre)
    """
    if "," in nombre_completo:
        apellidos, nombres = nombre_completo.split(",", 1)
        aps = apellidos.strip().split()
        noms = nombres.strip().split()
        ap_pat = aps[0] if len(aps) > 0 else ""
        ap_mat = aps[1] if len(aps) > 1 else ""
        pri_nom = noms[0] if len(noms) > 0 else ""
        seg_nom = noms[1] if len(noms) > 1 else ""
    else:
        parts = nombre_completo.strip().split()
        ap_pat = parts[0] if len(parts) > 0 else ""
        ap_mat = parts[1] if len(parts) > 1 else ""
        pri_nom = parts[2] if len(parts) > 2 else ""
        seg_nom = parts[3] if len(parts) > 3 else ""
    return ap_pat, ap_mat, pri_nom, seg_nom

def consultar_afp(numero_dni, ap_pat=None, ap_mat=None, pri_nom=None):
    """
    Consulta la situación previsional de un ciudadano en el portal de la SBS.
    Si no se proporcionan los apellidos/nombres, se resuelven primero mediante la consulta DNI.
    Retorna tupla: (tipo_respuesta, datos_o_error)
    """
    numero_dni = str(numero_dni).strip()
    if not (len(numero_dni) == 8 and numero_dni.isdigit()):
        return "E", f"El DNI '{numero_dni}' debe contener exactamente 8 dígitos numéricos."

    # Si faltan apellidos/nombres, resolverlos vía consulta_dni
    if not (ap_pat and ap_mat and pri_nom):
        tipo_dni, res_dni = consultar_dni(numero_dni)
        if tipo_dni == "C" and "nombres" in res_dni and res_dni["nombres"]:
            ap_pat, ap_mat, pri_nom, _ = separar_nombre_peruano(res_dni["nombres"])
        else:
            return "E", f"No se pudieron obtener los nombres para el DNI {numero_dni}. Por favor proporcione apellido paterno, materno y primer nombre."

    driver = None
    try:
        options = get_chrome_options()
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(20)

        url_sbs = "https://servicios.sbs.gob.pe/ReporteSituacionPrevisional/Afil_Consulta.aspx"
        driver.get(url_sbs)

        wait = WebDriverWait(driver, 8)
        sel_doc = wait.until(EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_cboTipoDoc")))
        Select(sel_doc).select_by_value("00") # DNI

        txt_doc = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtNumeroDoc")
        txt_doc.clear()
        txt_doc.send_keys(numero_dni)

        driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtAp_pat").send_keys(ap_pat)
        driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtAp_mat").send_keys(ap_mat)
        driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtPri_nom").send_keys(pri_nom)

        time.sleep(0.5)
        btn_buscar = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_btnBuscar")
        driver.execute_script("arguments[0].click();", btn_buscar)
        time.sleep(2)

        body_text = driver.find_element(By.TAG_NAME, "body").text
        soup = BeautifulSoup(driver.page_source, "html.parser")

        if "no se encontraron resultados" in body_text.lower():
            return "C", {
                "dni": numero_dni,
                "nombres": f"{ap_pat} {ap_mat} {pri_nom}".strip(),
                "afiliado_spp": False,
                "mensaje": "No se encontraron resultados en el Sistema Privado de Pensiones (AFP). Puede corresponder a la ONP o sin registro."
            }

        # Si hay errores de validación
        if "debe ingresar el apellido" in body_text.lower() or "caracteres inválido" in body_text.lower():
            return "E", "Los datos ingresados no superaron la validación del portal de la SBS."

        datos_afiliacion = {
            "dni": numero_dni,
            "nombres": f"{ap_pat} {ap_mat} {pri_nom}".strip(),
            "afiliado_spp": True,
            "detalles": {}
        }

        tablas = soup.find_all("table")
        for tbl in tablas:
            filas = tbl.find_all("tr")
            for f in filas:
                cols = f.find_all(["td", "th"])
                if len(cols) >= 2:
                    k = cols[0].get_text(strip=True).replace(":", "")
                    v = cols[1].get_text(strip=True)
                    if k and v and len(k) < 50 and not any(ign in k.lower() for ign in ["tipo de documento", "número de documento", "aviso importante", "le informamos"]):
                        datos_afiliacion["detalles"][k] = v

        return "C", datos_afiliacion

    except Exception as e:
        tbinfo = traceback.format_exc()
        return "E", f"Error al consultar afiliación AFP en la SBS:\r\n{tbinfo}"
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
