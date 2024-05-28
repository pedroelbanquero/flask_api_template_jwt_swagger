from flask import Flask,session,flash, request, jsonify
from flask_swagger_ui import get_swaggerui_blueprint
import bcrypt
import jwt
import datetime
from pymongo import MongoClient
from bson.objectid import ObjectId
from functools import wraps
import json
from bson import json_util
import pyotp
import time

app = Flask(__name__)

# Configuración de la base de datos MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['bcnc']
usuarios_collection = db['usuarios']
viviendas_collection = db['viviendas']

# Clave secreta para firmar los tokens JWT
app.config['SECRET_KEY'] = 'clave_secreta'

secret_otp = pyotp.random_base32()

print("OTP KEY",secret_otp)

@app.route('/generate-otp', methods=['GET'])
def generate_otp():
    totp = pyotp.TOTP(secret_otp)
    otp = totp.now()
    return jsonify({'otp': otp, 'valid_for': totp.interval}), 200

@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.get_json()
    otp = data.get('otp')
    totp = pyotp.TOTP(secret_otp)
    if totp.verify(otp):
        return jsonify({'status': 'success', 'message': 'OTP is valid'}), 200
    else:
        return jsonify({'status': 'fail', 'message': 'OTP is invalid'}), 400


# Función para generar tokens JWT
def generate_token(user_id):
    token = jwt.encode({'user_id': str(user_id), 'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)}, app.config['SECRET_KEY'])
    print("TOKEN",token)
    print(verify_token(token))
    return token

# Middleware para verificar el token JWT
def verify_token(token):
    try:
        data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        return data
    except jwt.DecodeError as e:
        print("Decode Error: ", e)
        return None

# Función para cifrar contraseñas
def encrypt_password(password):
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed_password.decode('utf-8')

# Verificar si el usuario y contraseña son correctos
def verify_password(user, password):
    user_document = usuarios_collection.find_one({"usuario": user})
    if not user_document:
        return False
    hashed_password = user_document['password']
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

# Ruta para autenticar y obtener el token JWT
@app.route('/login', methods=['POST'])
def login():
    auth = request.json
    print(auth)
    if not auth or not auth["username"] or not auth["password"]:
        return jsonify({'message': 'Credenciales inválidas'}), 401

    if not verify_password(auth["username"], auth["password"]):
        return jsonify({'message': 'Credenciales inválidas'}), 401

    user = usuarios_collection.find_one({"usuario": auth["username"]})
    token = generate_token(str(user['_id']))
    return jsonify({'token': token})



# Ruta para crear un nuevo usuario
@app.route('/usuarios', methods=['POST'])
def crear_usuario():
    try:
        nuevo_usuario = request.json
        if not nuevo_usuario:
            return jsonify({"error": "Se requiere un cuerpo JSON válido"}), 400

        if 'usuario' not in nuevo_usuario or 'password' not in nuevo_usuario:
            return jsonify({"error": "Faltan campos obligatorios"}), 400

        if usuarios_collection.find_one({"usuario": nuevo_usuario['usuario']}):
            return jsonify({"error": "El nombre de usuario ya está en uso"}), 400

        nuevo_usuario['password'] = encrypt_password(nuevo_usuario['password'])
        usuarios_collection.insert_one(nuevo_usuario)
        return jsonify({"mensaje": "Usuario creado correctamente"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Middleware para verificar el token en cada solicitud
#@app.before_request
def before_request():
    excluded_paths = ['/login/', '/api/docs/', '/static/swagger6.json']
    if request.path not in excluded_paths:
        token = request.headers.get('Authorization')
        if not token or not verify_token(token):
            return jsonify({'message': 'Token inválido'}), 401

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get("Authorization")
        print("TOKEN",token)
        if token!=None:
            verify = verify_token(token.split("Bearer ")[1])
        else:
            verify=None
        print(verify)
        if None==verify:
            flash('You need to login first.')
            return jsonify({"message":"Token inválido"}),401
        return f(*args, **kwargs)
    return decorated_function

# Configuración de Swagger
SWAGGER_URL = '/api/docs'  # URL para acceder a la documentación de Swagger
API_URL = '/static/swagger6.json'  # URL de la especificación OpenAPI

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={'app_name': "API de Usuarios y Viviendas"}
)

# Registrar la documentación de Swagger en la aplicación
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)


@app.route('/usuarios', methods=['GET'])
@login_required
def get_usuario():

# Serialize the list of dictionaries into JSON
    json_data = json_util.dumps(usuarios_collection.find())
    return json_data,200



# Actualizar parcialmente un usuario
@app.route('/usuarios/<string:usuario_id>', methods=['PATCH'])
@login_required
def actualizar_usuario(usuario_id):
    try:
        if not usuarios_collection.find_one({"_id": ObjectId(usuario_id)}):
            return jsonify({"error": "Usuario no encontrado"}), 404

        if not request.json:
            return jsonify({"error": "Se requiere un cuerpo JSON válido"}), 400

        usuarios_collection.update_one({"_id": ObjectId(usuario_id)}, {"$set": request.json})
        return jsonify({"mensaje": "Usuario actualizado correctamente"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Actualizar completamente un usuario
@app.route('/usuarios/<string:usuario_id>', methods=['PUT'])
@login_required
def actualizar_usuario_completo(usuario_id):
    try:
        if not usuarios_collection.find_one({"_id": ObjectId(usuario_id)}):
            return jsonify({"error": "Usuario no encontrado"}), 404

        if not request.json:
            return jsonify({"error": "Se requiere un cuerpo JSON válido"}), 400

        usuarios_collection.replace_one({"_id": ObjectId(usuario_id)}, request.json)
        return jsonify({"mensaje": "Usuario actualizado completamente"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Borrar un usuario
@app.route('/usuarios/<string:usuario_id>', methods=['DELETE'])
@login_required
def borrar_usuario(usuario_id):
    try:
        if not usuarios_collection.find_one({"_id": ObjectId(usuario_id)}):
            return jsonify({"error": "Usuario no encontrado"}), 404

        if viviendas_collection.count_documents({"usuario_id": usuario_id}) > 0:
            return jsonify({"error": "El usuario tiene viviendas asociadas"}), 400

        usuarios_collection.delete_one({"_id": ObjectId(usuario_id)})
        return jsonify({"mensaje": "Usuario borrado correctamente"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener un único usuario
@app.route('/usuarios/<string:usuario_id>', methods=['GET'])
@login_required
def obtener_usuario(usuario_id):
    print("GET USER",usuario_id)
    try:
        usuario = usuarios_collection.find_one({"_id": ObjectId(usuario_id)})
        print(usuario)
        if usuario:
            return json_util.dumps(usuario) 
        else:
            return jsonify({"error": "Usuario no encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener todas las viviendas de un usuario
@app.route('/usuarios/<string:usuario_id>/viviendas', methods=['GET'])
@login_required
def obtener_viviendas_usuario(usuario_id):
    print("USER_ID_VIVIENDAS",usuario_id)
    try:
        viviendas = viviendas_collection.find({"usuario_id": usuario_id})
        print(viviendas)
        return json_util.dumps(viviendas)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Crear una nueva vivienda para un usuario
@app.route('/usuarios/<string:usuario_id>/viviendas', methods=['POST'])
@login_required
def crear_vivienda(usuario_id):
    print("CREANDO VIVIENDA")
    try:
        nueva_vivienda = request.json
        if not nueva_vivienda:
            return jsonify({"error": "Se requiere un cuerpo JSON válido"}), 400

        nueva_vivienda['usuario_id'] = usuario_id
        viviendas_collection.insert_one(nueva_vivienda)
        return jsonify({"mensaje": "Vivienda creada correctamente"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Actualizar parcialmente una vivienda de un usuario
@app.route('/usuarios/<string:usuario_id>/viviendas/<string:vivienda_id>', methods=['PATCH'])
@login_required
def actualizar_vivienda(usuario_id, vivienda_id):
    print("UPDATING VIVIENDA",usuario_id, vivienda_id,request.json)
    try:
        print("entra")
        #if not viviendas_collection.find_one({"_id": ObjectId(vivienda_id), "usuario_id": usuario_id}):
        #    return jsonify({"error": "Vivienda no encontrada"}), 404
        print("entra2")
        #if not request.json:
        #    return jsonify({"error": "Se requiere un cuerpo JSON válido"}), 400
        print("entra3")
        viviendas_collection.update_one({"_id": ObjectId(vivienda_id), "usuario_id": usuario_id}, {"$set": request.json})
        print("entra4")
        return jsonify({"mensaje": "Vivienda actualizada correctamente"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Borrar una vivienda de un usuario
@app.route('/usuarios/<string:usuario_id>/viviendas/<string:vivienda_id>', methods=['DELETE'])
@login_required
def borrar_vivienda(usuario_id, vivienda_id):
    try:
        if not viviendas_collection.find_one({"_id": ObjectId(vivienda_id), "usuario_id": usuario_id}):
            return jsonify({"error": "Vivienda no encontrada"}), 404

        viviendas_collection.delete_one({"_id": ObjectId(vivienda_id), "usuario_id": usuario_id})
        return jsonify({"mensaje": "Vivienda borrada correctamente"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)

