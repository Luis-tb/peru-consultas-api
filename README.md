# API Consulta RUC, DNI, Tipo de Cambio, AFP & CPE — Suite de Servicios Perú

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-Web%20Framework-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Selenium](https://img.shields.io/badge/Selenium-Headless%20Scraping-43B02A?style=for-the-badge&logo=selenium&logoColor=white)](https://www.selenium.dev/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![JWT](https://img.shields.io/badge/Auth-JWT%20Bearer-black?style=for-the-badge&logo=jsonwebtokens&logoColor=white)](https://jwt.io/)

---

## 📌 Descripción

Microservicio RESTful contenerizado desarrollado en **Python (Flask)** y **Selenium (Headless Chrome)** para la consulta, extracción y validación automatizada de información pública del Estado peruano (**SUNAT** y **SBS**).

Diseñado específicamente para integrarse con **sistemas ERP, plataformas de facturación electrónica, sistemas contables y módulos de Recursos Humanos (Planillas)**.

---

## ✨ Características Principales

- 🏢 **Consulta RUC + Padrones (SUNAT):** Estado, condición de domicilio fiscal (HABIDO), actividad económica (CIIU) y detección automática de agentes de retención, percepción o buen contribuyente.
- 🆔 **Consulta DNI (SUNAT):** Extrae nombres completos y RUC asociado a partir del documento de identidad.
- 💵 **Tipo de Cambio Oficial (SUNAT):** Cotización diaria oficial (Compra y Venta) del dólar estadounidense (USD) y calendario histórico mensual.
- 🏦 **Situación Previsional / AFP (SBS):** Identifica automáticamente la AFP (Habitat, Prima, Integra, Profuturo), CUSPP o estado sin afiliación privada (ONP).
- 🧾 **Validador de Comprobantes Electrónicos (CPE - SUNAT):** Verifica la validez y existencia de Facturas, Boletas, Recibos por Honorarios y Notas de Crédito.
- ⚡ **Medición de Tiempos de Respuesta:** Cada respuesta incluye el campo `tiempo_segundos` y la cabecera HTTP `X-Response-Time`.
- 🛡️ **Evasión Antibot y Cloudflare:** Automatización resiliente mediante Chrome Headless optimizado sin carga de imágenes para máxima velocidad.
- 🔒 **Seguridad con JWT:** Autenticación opcional mediante tokens Bearer (`PyJWT`).

---

## 🚀 Despliegue con Docker Compose (Recomendado)

### 1. Clonar el repositorio
```bash
git clone https://github.com/Luis-tb/CONSULTAR-RUC.git
cd CONSULTAR-RUC
```

### 2. Configurar variables de entorno
```bash
cp .env.example .env
```
*(Edita el archivo `.env` y define tu propio `JWT_SECRET` si deseas requerir autenticación).*

### 3. Construir y levantar el contenedor
```bash
docker-compose up -d --build
```
El servicio estará disponible en `http://localhost:5000`.

---

## 💻 Ejecución Local (Sin Docker)

### Requisitos:
* Python 3.10 o superior
* Google Chrome instalado

```bash
# 1. Crear y activar entorno virtual
python -m venv venv
# En Windows:
.\venv\Scripts\activate
# En Linux/macOS:
source venv/bin/activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Iniciar el servidor
python index.py
```

---

## 📖 Especificación de Endpoints

### 1. `GET /consulta-ruc/<numero_ruc>`
Consulta la ficha RUC y evalúa padrones tributarios.

**Ejemplo de Petición:**
```bash
curl -X GET "http://localhost:5000/consulta-ruc/10751037720"
```

**Respuesta (`200 OK`):**
```json
{
  "ruc": "10751037720",
  "razon_social": "TORRES BARRETO LUIS DAVID",
  "direccion": "-",
  "tipo_contribuyente": "PERSONA NATURAL CON NEGOCIO",
  "estado": "ACTIVO",
  "condicion": "HABIDO",
  "actividad_economica": "Principal - 6201 - PROGRAMACIÓN INFORMÁTICA",
  "padrones": {
    "descripcion": "NINGUNO",
    "es_agente_percepcion": false,
    "es_agente_retencion": false,
    "es_buen_contribuyente": false
  },
  "tiempo_segundos": 2.21,
  "detalle_completo": { ... }
}
```

---

### 2. `GET /consulta-dni/<numero_dni>`
Consulta los nombres y RUC asociado a partir del DNI de 8 dígitos.

**Ejemplo de Petición:**
```bash
curl -X GET "http://localhost:5000/consulta-dni/75103772"
```

**Respuesta (`200 OK`):**
```json
{
  "dni": "75103772",
  "nombres": "TORRES BARRETO LUIS DAVID",
  "ruc": "10751037720",
  "ubicacion": "TRUJILLO",
  "estado": "ACTIVO",
  "tiempo_segundos": 1.25
}
```

---

### 3. `GET /tipo-cambio` y `GET /tipo-cambio/mes`
Consulta la cotización oficial de la SUNAT para el dólar estadounidense.

* `GET /tipo-cambio`: Tipo de cambio del día vigente.
* `GET /tipo-cambio/mes`: Calendario completo del mes en curso.

**Respuesta (`200 OK`):**
```json
{
  "moneda": "USD",
  "fecha": "2026-10-11",
  "compra": 3.450,
  "venta": 3.457,
  "mes": "Octubre",
  "anio": 2026,
  "fuente": "SUNAT Oficial",
  "tiempo_segundos": 2.05
}
```

---

### 4. `GET /consulta-afp/<numero_dni>`
Consulta la situación previsional del trabajador en la SBS. Si no se envían nombres por parámetro (`?ap_pat=&ap_mat=&pri_nom=`), el sistema resuelve automáticamente los nombres con el scraper de DNI.

**Ejemplo de Petición:**
```bash
curl -X GET "http://localhost:5000/consulta-afp/75103772"
```

**Respuesta (`200 OK`):**
```json
{
  "dni": "75103772",
  "nombres": "TORRES BARRETO LUIS",
  "afiliado_spp": false,
  "mensaje": "No se encontraron resultados en el Sistema Privado de Pensiones (AFP). Puede corresponder a la ONP o sin registro.",
  "tiempo_segundos": 2.15
}
```

---

### 5. `POST /validar-cpe`
Valida si una Factura, Boleta, Recibo por Honorarios o Nota de Crédito está aceptada y registrada en SUNAT.

**Parámetros JSON requeridos:**
* `ruc_emisor`: RUC de 11 dígitos del emisor.
* `tipo_comprobante`: `'03'` o `'factura'`, `'06'` o `'boleta'`, `'01'` o `'recibo'`.
* `serie`: Serie del comprobante (ej. `F001`, `E001`).
* `numero`: Número del comprobante (ej. `123`).
* `fecha_emision`: Fecha en formato `DD/MM/AAAA`.
* `monto`: Importe total (ej. `150.00`).

**Ejemplo de Petición:**
```bash
curl -X POST "http://localhost:5000/validar-cpe" \
     -H "Content-Type: application/json" \
     -d '{
       "ruc_emisor": "20131312955",
       "tipo_comprobante": "factura",
       "serie": "F001",
       "numero": "1",
       "fecha_emision": "01/10/2026",
       "monto": "100.00"
     }'
```

**Respuesta (`200 OK`):**
```json
{
  "valido": false,
  "estado_comprobante": "NO_EXISTE",
  "mensaje": "El comprobante F001-1 no existe en los registros de SUNAT.",
  "ruc_emisor": "20131312955",
  "serie": "F001",
  "numero": "1",
  "fecha_emision": "01/10/2026",
  "monto": "100.00",
  "tiempo_segundos": 4.85
}
```

---

## ⚖️ Descargo de Responsabilidad (Disclaimer)

Este proyecto ha sido desarrollado con fines educativos, de integración técnica y de automatización para sistemas contables y ERPs. Las consultas se realizan sobre información de libre acceso público provista por los portales oficiales de la **SUNAT** y la **SBS**. Este software no guarda relación oficial con dichas entidades.

---

## 👤 Autor

**Luis David Torres Barreto**  
- **GitHub:** [@Luis-tb](https://github.com/Luis-tb)  
- **Email:** torresbarretoluisdavid@gmail.com
