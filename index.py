from flask import Flask, request, jsonify
from flask_cors import CORS
import jwt
import os
import re
import time
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from dotenv import load_dotenv

from consulta_ruc import consultar_ruc
from consulta_dni import consultar_dni
from consulta_tipo_cambio import consultar_tipo_cambio
from consulta_afp import consultar_afp
from consulta_cpe import consultar_cpe

load_dotenv()

app = Flask(__name__)
CORS(app, supports_credentials=True)
JWT_SECRET = os.getenv('JWT_SECRET')
ALGORITHM = 'HS256'


@app.before_request
def iniciar_cronometro():
    request.start_time = time.time()


@app.after_request
def agregar_cabecera_tiempo(response):
    if hasattr(request, 'start_time'):
        duracion = round(time.time() - request.start_time, 2)
        response.headers['X-Response-Time'] = f"{duracion}s"
    return response


def verificar_token(token):
    if not JWT_SECRET:
        return None
    try:
        jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        return None
    except ExpiredSignatureError:
        return jsonify({"valido": False, "error": "Token expirado"}), 401
    except InvalidTokenError:
        return jsonify({"valido": False, "error": "Token inválido"}), 401


def autenticar_peticion():
    if not JWT_SECRET:
        return None
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Falta el token Bearer en la cabecera"}), 401
    token = auth_header.split(" ")[1]
    return verificar_token(token)


# -------------------------------------------------------------
# 1. Consulta RUC (SUNAT)
# -------------------------------------------------------------
@app.route('/consulta-ruc/<numero_ruc>', methods=['GET'])
def consulta_ruc_route(numero_ruc):
    error_auth = autenticar_peticion()
    if error_auth:
        return error_auth

    t0 = time.time()
    tipo_respuesta, mensaje_respuesta = consultar_ruc(numero_ruc)
    duracion = round(time.time() - t0, 2)

    if tipo_respuesta == "C":
        try:
            ruc_raw = mensaje_respuesta.get("RUC:") or mensaje_respuesta.get("Número de RUC:") or ""
            if " - " in ruc_raw:
                nombre_contribuyente = ruc_raw.split(" - ", 1)[1].strip()
            else:
                nombre_contribuyente = ruc_raw.strip()

            domicilio_fiscal = re.sub(r'\s+', ' ', mensaje_respuesta.get("Domicilio Fiscal:", "-")).strip()

            padrones_raw = mensaje_respuesta.get("Padrones:", "NINGUNO")
            es_agente_retencion = "retenci" in padrones_raw.lower()
            es_agente_percepcion = "percepci" in padrones_raw.lower()
            es_buen_contribuyente = "buen contribuyente" in padrones_raw.lower()

            respuesta = {
                "ruc": numero_ruc,
                "razon_social": nombre_contribuyente,
                "direccion": domicilio_fiscal,
                "tipo_contribuyente": mensaje_respuesta.get("Tipo Contribuyente:", "-"),
                "estado": mensaje_respuesta.get("Estado del Contribuyente:", "-"),
                "condicion": mensaje_respuesta.get("Condición del Contribuyente:", "-"),
                "actividad_economica": mensaje_respuesta.get("Actividad(es) Económica(s):", "-"),
                "padrones": {
                    "descripcion": padrones_raw,
                    "es_agente_retencion": es_agente_retencion,
                    "es_agente_percepcion": es_agente_percepcion,
                    "es_buen_contribuyente": es_buen_contribuyente
                },
                "tiempo_segundos": duracion,
                "detalle_completo": mensaje_respuesta
            }
            return jsonify(respuesta), 200

        except Exception as e:
            return jsonify({"error": "Error al procesar los datos", "detalle": str(e), "tiempo_segundos": duracion}), 500
    else:
        return jsonify({"error": mensaje_respuesta, "tiempo_segundos": duracion}), 404


# -------------------------------------------------------------
# 2. Consulta DNI (SUNAT)
# -------------------------------------------------------------
@app.route('/consulta-dni/<numero_dni>', methods=['GET'])
def consulta_dni_route(numero_dni):
    error_auth = autenticar_peticion()
    if error_auth:
        return error_auth

    t0 = time.time()
    tipo_respuesta, mensaje_respuesta = consultar_dni(numero_dni)
    duracion = round(time.time() - t0, 2)

    if tipo_respuesta == "C":
        mensaje_respuesta["tiempo_segundos"] = duracion
        return jsonify(mensaje_respuesta), 200
    else:
        return jsonify({"error": mensaje_respuesta, "tiempo_segundos": duracion}), 404


# -------------------------------------------------------------
# 3. Tipo de Cambio Oficial (SUNAT)
# -------------------------------------------------------------
@app.route('/tipo-cambio', methods=['GET'])
def tipo_cambio_route():
    error_auth = autenticar_peticion()
    if error_auth:
        return error_auth

    t0 = time.time()
    tipo_respuesta, mensaje_respuesta = consultar_tipo_cambio(incluir_historial=False)
    duracion = round(time.time() - t0, 2)

    if tipo_respuesta == "C":
        mensaje_respuesta["tiempo_segundos"] = duracion
        return jsonify(mensaje_respuesta), 200
    else:
        return jsonify({"error": mensaje_respuesta, "tiempo_segundos": duracion}), 500


@app.route('/tipo-cambio/mes', methods=['GET'])
def tipo_cambio_mes_route():
    error_auth = autenticar_peticion()
    if error_auth:
        return error_auth

    t0 = time.time()
    tipo_respuesta, mensaje_respuesta = consultar_tipo_cambio(incluir_historial=True)
    duracion = round(time.time() - t0, 2)

    if tipo_respuesta == "C":
        mensaje_respuesta["tiempo_segundos"] = duracion
        return jsonify(mensaje_respuesta), 200
    else:
        return jsonify({"error": mensaje_respuesta, "tiempo_segundos": duracion}), 500


# -------------------------------------------------------------
# 4. Consulta Situación Previsional / AFP (SBS)
# -------------------------------------------------------------
@app.route('/consulta-afp/<numero_dni>', methods=['GET'])
def consulta_afp_route(numero_dni):
    error_auth = autenticar_peticion()
    if error_auth:
        return error_auth

    ap_pat = request.args.get('ap_pat')
    ap_mat = request.args.get('ap_mat')
    pri_nom = request.args.get('pri_nom')

    t0 = time.time()
    tipo_respuesta, mensaje_respuesta = consultar_afp(numero_dni, ap_pat, ap_mat, pri_nom)
    duracion = round(time.time() - t0, 2)

    if tipo_respuesta == "C":
        mensaje_respuesta["tiempo_segundos"] = duracion
        return jsonify(mensaje_respuesta), 200
    else:
        return jsonify({"error": mensaje_respuesta, "tiempo_segundos": duracion}), 400


# -------------------------------------------------------------
# 5. Validación de Comprobantes de Pago CPE (SUNAT)
# -------------------------------------------------------------
@app.route('/validar-cpe', methods=['POST'])
def validar_cpe_route():
    error_auth = autenticar_peticion()
    if error_auth:
        return error_auth

    data = request.get_json(silent=True) or request.form

    ruc_emisor = data.get('ruc_emisor')
    tipo_comprobante = data.get('tipo_comprobante') or data.get('tipo', '03')
    serie = data.get('serie')
    numero = data.get('numero')
    fecha_emision = data.get('fecha_emision') or data.get('fecha')
    monto = data.get('monto')

    if not all([ruc_emisor, tipo_comprobante, serie, numero, fecha_emision, monto]):
        return jsonify({
            "error": "Faltan parámetros obligatorios: ruc_emisor, tipo_comprobante, serie, numero, fecha_emision, monto"
        }), 400

    t0 = time.time()
    tipo_respuesta, mensaje_respuesta = consultar_cpe(
        ruc_emisor=ruc_emisor,
        tipo_comprobante=tipo_comprobante,
        serie=serie,
        numero=numero,
        fecha_emision=fecha_emision,
        monto=monto
    )
    duracion = round(time.time() - t0, 2)

    if tipo_respuesta == "C":
        mensaje_respuesta["tiempo_segundos"] = duracion
        return jsonify(mensaje_respuesta), 200
    else:
        return jsonify({"error": mensaje_respuesta, "tiempo_segundos": duracion}), 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
