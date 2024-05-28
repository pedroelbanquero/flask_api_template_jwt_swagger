#!/bin/bash

# Conectarse a MongoDB y crear la base de datos y las colecciones
mongo <<EOF
use bcnc

# Crear la colección 'usuarios'
db.createCollection("usuarios")

# Crear la colección 'viviendas'
db.createCollection("viviendas")

# Mostrar las colecciones creadas
show collections
EOF

echo "Base de datos 'bcnc' y colecciones 'usuarios' y 'viviendas' creadas correctamente."

