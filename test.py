import unittest
import requests
import random
import string
import jwt
import json

home_id2 = None

class TestAPI(unittest.TestCase):
    base_url = "http://localhost:5000"
    created_user = None
    token = None
    user_id = None
    home_id= None

    @classmethod
    def setUpClass(cls):
        # Creamos un usuario para probar los métodos que lo requieren
        cls.created_user = cls.create_user()
        if cls.created_user:
            cls.token = cls.login_user(cls.created_user["usuario"], cls.created_user["password"])

            # Decodificar el token para obtener el user_id
            decoded_token = jwt.decode(cls.token, 'clave_secreta', algorithms=['HS256'])
            cls.user_id = decoded_token.get('user_id')

    @classmethod
    def tearDownClass(cls):
        # Borrar el usuario creado después de que todos los métodos de prueba se completen
        if cls.created_user:
            #cls.delete_user(cls.user_id)
            print("")
    @staticmethod
    def random_string(length=8):
        # Genera una cadena aleatoria para nombres de usuario y contraseñas
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

    @staticmethod
    def create_user():
        # Crea un nuevo usuario con un nombre de usuario y contraseña aleatorios
        username = TestAPI.random_string()
        password = TestAPI.random_string()
        data = {"usuario": username, "password": password}
        response = requests.post(f"{TestAPI.base_url}/usuarios", json=data)
        if response.status_code == 201:
            return {"_id": response.json().get("_id"), "usuario": username, "password": password}
        return None
    
    #@staticmethod
    #def delete_user(user_id):
        # Elimina un usuario por ID
    #    response = requests.delete(f"{TestAPI.base_url}/usuarios/{user_id}")
    #    return response.status_code == 200
    

    @staticmethod
    def login_user(username, password):
        # Inicia sesión y devuelve el token
        data = {"username": username, "password": password}
        response = requests.post(f"{TestAPI.base_url}/login", json=data)
        if response.status_code == 200:
            return response.json().get("token")
        return None

    def add_token_header(self, headers=None):
        if headers is None:
            headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def print_response_message(self, response):
        print("Response Message:")
        try:
            print(response.json())
        except ValueError:
            print(response.text)

    def assert_response_status(self, response, expected_status):
        self.assertEqual(response.status_code, expected_status)
        if response.status_code == expected_status:
            print("\033[92mPASS\033[0m - Status code is as expected:", expected_status)
        else:
            print("\033[91mFAIL\033[0m - Expected status code:", expected_status, "but received:", response.status_code)
        self.print_response_message(response)

    def test_login_success(self):
        headers = self.add_token_header()
        # Prueba el inicio de sesión exitoso con el usuario creado
        if self.created_user:
            data = {"username": self.created_user["usuario"], "password": self.created_user["password"]}
            response = requests.post(f"{self.base_url}/login", json=data, headers=headers)
            self.assert_response_status(response, 200)

    def test_login_failure(self):
        headers = self.add_token_header()
        # Prueba el inicio de sesión fallido con una contraseña incorrecta
        if self.created_user:
            data = {"username": self.created_user["usuario"], "password": "contraseñaIncorrecta"}
            response = requests.post(f"{self.base_url}/login", json=data, headers=headers)
            self.assert_response_status(response, 401)

    def test_get_all_users(self):
        headers = self.add_token_header()
        # Prueba obtener todos los usuarios
        response = requests.get(f"{self.base_url}/usuarios", headers=headers)
        self.assert_response_status(response, 200)
        self.assertIsInstance(response.json(), list)

    def test_get_user_by_id(self):
        headers = self.add_token_header()
        # Prueba obtener un usuario por ID
        if self.user_id:
            response = requests.get(f"{self.base_url}/usuarios/{self.user_id}", headers=headers)
            self.assert_response_status(response, 200)
            self.assertIsInstance(response.json(), dict)

    def test_update_user_partial(self):
        headers = self.add_token_header()
        # Prueba actualizar parcialmente un usuario por ID
        if self.user_id:
            new_username = self.random_string()
            data = {"usuario": new_username}
            response = requests.patch(f"{self.base_url}/usuarios/{self.user_id}", json=data, headers=headers)
            self.assert_response_status(response, 200)

    def test_update_user_full(self):
        headers = self.add_token_header()
        # Prueba actualizar completamente un usuario por ID
        if self.user_id:
            new_username = self.random_string()
            data = {"usuario": new_username, "password": self.random_string()}
            response = requests.put(f"{self.base_url}/usuarios/{self.user_id}", json=data, headers=headers)
            self.assert_response_status(response, 200)

    def test_get_all_user_homes(self):
        headers = self.add_token_header()
        # Prueba obtener todas las viviendas de un usuario
        print("GET ALL USER HOMES",self.user_id)
        if self.user_id:
            response = requests.get(f"{self.base_url}/usuarios/{self.user_id}/viviendas", headers=headers)
            global home_id2
            home_id2 = response.json()[0]["_id"]["$oid"]
            print("HOME ID LOAD",home_id2)
            self.assert_response_status(response, 200)
            #self.assertIsInstance(response.json(), list)

    def test_create_user_home(self):
        headers = self.add_token_header()
        # Prueba crear una nueva vivienda para un usuario
        if self.user_id:
            data = {"nombre":"Los Jardines 2","direccion":"av las americas 789 4A","habitaciones":5,"precio":247000,"espacio":"200m2",}  # Proporciona los datos de la vivienda según sea necesario
            response = requests.post(f"{self.base_url}/usuarios/{self.user_id}/viviendas", json=data, headers=headers)
            self.assert_response_status(response, 201)

    def test_update_user_home_partial(self):
        headers = self.add_token_header()
        # Prueba actualizar parcialmente una vivienda de un usuario
        if self.user_id:
            print("UPDATE PARTIAL HOME",home_id2)
            data = {"nombre":"Los Jardines 3","direccion":"av las americas 789 4A","habitaciones":5,"precio":227000,"espacio":"220m2",}  # Proporciona los datos de la vivienda según sea necesario
            response = requests.patch(f"{self.base_url}/usuarios/{self.user_id}/viviendas/{home_id2}", json=data, headers=headers)
            self.assert_response_status(response, 200)

    #def test_delete_user(self):
    #    headers = self.add_token_header()
    #    # Prueba borrar un usuario por ID
    #    if self.user_id:
    #        response = requests.delete(f"{self.base_url}/usuarios/{self.user_id}", headers=headers)
    #        self.assert_response_status(response, 200)


if __name__ == '__main__':
    unittest.main()

