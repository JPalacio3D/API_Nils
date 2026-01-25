from flask import Flask,jsonify,request,render_template
#from flask_mysqldb import MySQL
from config import config
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
import pymysql
import datetime
import base64
import resend
import os
import requests
import re
#from src.database.db import get_connection

#Models
from models.ModelUser import ModelUser
from models.Security import Security

#Entities
from models.entities.User import User

load_dotenv('os.env')

resend.api_key = os.getenv('RESEND_API_KEY')

# Verificación de configuración
print("="*50)
print("🔧 VERIFICACIÓN DE CONFIGURACIÓN")
print("="*50)

if resend.api_key:
    print(f"✓ RESEND_API_KEY configurada: {resend.api_key[:10]}...")
else:
    print("⚠️ ADVERTENCIA: RESEND_API_KEY NO CONFIGURADA")
    print("   El envío de emails NO funcionará")

print("="*50)

app=Flask(__name__) #este parametro servira para saber si estamos ejecutando este archivo como principal
#conexion=MySQL(app)
# Define la función de conexión
def conectar():
    return pymysql.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        db=os.getenv('DB_NAME')
    )
#conexion = conectar()
# 1) HEALTH ultrarrápido (sin DB)
@app.route("/health", methods=["GET", "HEAD"])
def health():
    # Comprobación mínima: responder 200 OK
    return ("", 200)
@app.route('/resetPass', methods=['POST','GET'])
def resetPass():
    
    try:
        has_access = Security.verify_token_pass(request.args.get('token'));
        if has_access:
            #return jsonify({'mensaje':"puedes cambiar la contraseña"})
            return render_template('auth/reset.html')
        else:
            return jsonify({'mensaje':'no permitido'})
    except Exception as ex:
        print(ex)
        
@app.route('/verweb')
def verweb():
    return render_template('auth/confirmacion.html')
        
@app.route('/WebChangePass', methods=['POST'])
def wbechangepass():
    conexion=conectar()
    try:
        cursor=conexion.cursor()
        sql="""UPDATE User SET pasword = '{1}' 
        WHERE email = '{0}'""".format(
            request.form['email'],
            generate_password_hash(request.form['password']))
        cursor.execute(sql)
        conexion.commit() #confirma la accionde inserción
        cursor.close()
        return render_template('auth/confirmacion.html')
    except Exception as ex:
        print("ex")
        print(ex)
        return jsonify({'mensaje':"error",'error':str(ex)}),500
    finally:
        conexion.close()  
    
@app.route('/login', methods=['POST','GET'])
def login():
    conexion = conectar()
    try:
        identifier = request.form['username']  # Puede ser username o email
        password = request.form['password']
        
        # Verificar si el identificador es un email
        email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        is_email = re.match(email_regex, identifier)
        
        cursor = conexion.cursor()
        
        if is_email:
            sql = "SELECT idUser, userName, pasword, email, IsAdmin FROM User WHERE email = %s"
        else:
            sql = "SELECT idUser, userName, pasword, email, IsAdmin FROM User WHERE userName = %s"

        cursor.execute(sql, (identifier,))
        data = cursor.fetchone()
        
        if data:
            idUser, userName, pasword_hash, email, isAdmin = data
            user = User(idUser, userName, password, email, isAdmin)
            logged_user = ModelUser.login(conexion, user)

            if logged_user and logged_user.pasword:
                encoded_token = Security.generate_token(logged_user)
                data = {
                    'id': logged_user.idUser,
                    'username': logged_user.userName,
                    'email': logged_user.email,
                    'IsAdmin': logged_user.IsAdmin
                }
                return jsonify({'success': True, 'token': encoded_token, 'mensaje': "Logueado correctamente", 'data': data})
            else:
                return jsonify({'success': False, 'mensaje': "Contraseña inválida"})
        else:
            return jsonify({'success': False, 'mensaje': "Usuario no encontrado"})
    except Exception as ex:
        print(ex)
        return jsonify({'success':False,'mensaje':"Error de servidor"}), 500
    finally:
        conexion.close()   

@app.route('/cambiarPass/<code>',methods=['POST'])
def cambiarPass(code):
    conexion = conectar()
    try:
        cursor=conexion.cursor()
        sql="""UPDATE User SET pasword = '{1}' 
        WHERE idUser = '{0}'""".format(
            code,
            generate_password_hash(request.form['password']))
        cursor.execute(sql)
        conexion.commit() #confirma la accionde inserción
        cursor.close()
        return jsonify({'success':True,'mensaje':"Contraseña Cambiada"})
    except Exception as ex:
        print("ex")
        print(ex)
        return jsonify({'mensaje':"error",'error':str(ex)}),500
    finally:
        conexion.close()   
    

@app.route('/singin', methods=['POST'])   
def singin():   
    """
    Endpoint mejorado para registro de usuarios
    Validaciones completas y manejo de errores detallado
    """
    conexion = None
    cursor = None
    
    try:
        # ═══════════════════════════════════════════════════
        # 1. OBTENER Y LIMPIAR DATOS
        # ═══════════════════════════════════════════════════
        userName = request.form.get('userName', '').strip()
        password = request.form.get('password', '')
        email = request.form.get('email', '').strip().lower()
        isAdmin = request.form.get('IsAdmin', 0)
        
        print(f"📝 Intento de registro: {userName} ({email})")
        
        # ═══════════════════════════════════════════════════
        # 2. VALIDACIONES DE CAMPOS VACÍOS
        # ═══════════════════════════════════════════════════
        if not userName:
            print("❌ Error: Username vacío")
            return jsonify({
                'success': False, 
                'mensaje': 'El nombre de usuario es obligatorio'
            }), 400
            
        if not password:
            print("❌ Error: Password vacío")
            return jsonify({
                'success': False, 
                'mensaje': 'La contraseña es obligatoria'
            }), 400
            
        if not email:
            print("❌ Error: Email vacío")
            return jsonify({
                'success': False, 
                'mensaje': 'El email es obligatorio'
            }), 400
        
        # ═══════════════════════════════════════════════════
        # 3. VALIDACIÓN DEL USERNAME
        # ═══════════════════════════════════════════════════
        if len(userName) < 4:
            print(f"❌ Error: Username muy corto ({len(userName)} caracteres)")
            return jsonify({
                'success': False, 
                'mensaje': 'El nombre de usuario debe tener al menos 4 caracteres'
            }), 400
            
        if len(userName) > 16:
            print(f"❌ Error: Username muy largo ({len(userName)} caracteres)")
            return jsonify({
                'success': False, 
                'mensaje': 'El nombre de usuario no puede tener más de 16 caracteres'
            }), 400
        
        if not re.match(r'^[a-zA-Z0-9_]+$', userName):
            print(f"❌ Error: Username con caracteres inválidos: {userName}")
            return jsonify({
                'success': False, 
                'mensaje': 'El nombre de usuario solo puede contener letras, números y guiones bajos'
            }), 400
        
        # ═══════════════════════════════════════════════════
        # 4. VALIDACIÓN DEL EMAIL
        # ═══════════════════════════════════════════════════
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            print(f"❌ Error: Email con formato inválido: {email}")
            return jsonify({
                'success': False, 
                'mensaje': 'El formato del email no es válido'
            }), 400
        
        # ═══════════════════════════════════════════════════
        # 5. VALIDACIÓN DE LA CONTRASEÑA
        # ═══════════════════════════════════════════════════
        if len(password) < 8:
            print(f"❌ Error: Password muy corta ({len(password)} caracteres)")
            return jsonify({
                'success': False, 
                'mensaje': 'La contraseña debe tener al menos 8 caracteres'
            }), 400
        
        if not re.search(r'[a-z]', password):
            print("❌ Error: Password sin minúsculas")
            return jsonify({
                'success': False, 
                'mensaje': 'La contraseña debe contener al menos una letra minúscula'
            }), 400
        
        if not re.search(r'[A-Z]', password):
            print("❌ Error: Password sin mayúsculas")
            return jsonify({
                'success': False, 
                'mensaje': 'La contraseña debe contener al menos una letra mayúscula'
            }), 400
        
        if not re.search(r'[0-9]', password):
            print("❌ Error: Password sin números")
            return jsonify({
                'success': False, 
                'mensaje': 'La contraseña debe contener al menos un número'
            }), 400
        
        # ═══════════════════════════════════════════════════
        # 6. CONECTAR A LA BASE DE DATOS
        # ═══════════════════════════════════════════════════
        conexion = conectar()
        cursor = conexion.cursor()
        print("✓ Conexión a BD establecida")
        
        # ═══════════════════════════════════════════════════
        # 7. VERIFICAR SI EL USERNAME YA EXISTE
        # ═══════════════════════════════════════════════════
        cursor.execute("SELECT idUser FROM User WHERE userName = %s", (userName,))
        if cursor.fetchone():
            print(f"❌ Error: Username duplicado: {userName}")
            return jsonify({
                'success': False, 
                'mensaje': 'El nombre de usuario ya está registrado'
            }), 409
        
        # ═══════════════════════════════════════════════════
        # 8. VERIFICAR SI EL EMAIL YA EXISTE
        # ═══════════════════════════════════════════════════
        cursor.execute("SELECT idUser FROM User WHERE email = %s", (email,))
        if cursor.fetchone():
            print(f"❌ Error: Email duplicado: {email}")
            return jsonify({
                'success': False, 
                'mensaje': 'El email ya está registrado'
            }), 409
        
        # ═══════════════════════════════════════════════════
        # 9. ENCRIPTAR CONTRASEÑA
        # ═══════════════════════════════════════════════════
        hashed_password = generate_password_hash(password)
        print("✓ Contraseña encriptada")
        
        # ═══════════════════════════════════════════════════
        # 10. INSERTAR USUARIO EN LA BASE DE DATOS
        # ═══════════════════════════════════════════════════
        sql = """INSERT INTO User (userName, pasword, email, IsAdmin) 
                 VALUES (%s, %s, %s, %s)"""
        cursor.execute(sql, (userName, hashed_password, email, isAdmin))
        conexion.commit()
        
        print(f"✓ Usuario registrado en BD: {userName} ({email})")
        
        # ═══════════════════════════════════════════════════
        # 11. ENVIAR EMAIL DE BIENVENIDA
        # ═══════════════════════════════════════════════════
        try:
            enviar_email_bienvenida(email, userName)
            print(f"✓ Email de bienvenida enviado a: {email}")
        except Exception as email_error:
            print(f"⚠️ Error al enviar email: {email_error}")
            # No bloqueamos el registro si falla el email
        
        # ═══════════════════════════════════════════════════
        # 12. RESPUESTA EXITOSA
        # ═══════════════════════════════════════════════════
        return jsonify({
            'success': True,
            'mensaje': 'Cuenta creada correctamente. Revisa tu email para más información.'
        }), 201
        
    except pymysql.Error as db_error:
        print(f"❌ Error de base de datos: {db_error}")
        if conexion:
            conexion.rollback()
        return jsonify({
            'success': False,
            'mensaje': 'Error al conectar con la base de datos'
        }), 500
        
    except Exception as ex:
        print(f"❌ Error inesperado: {ex}")
        if conexion:
            conexion.rollback()
        return jsonify({
            'success': False,
            'mensaje': 'Error inesperado al crear la cuenta'
        }), 500
        
    finally:
        if cursor:
            cursor.close()
        if conexion:
            conexion.close()
            print("✓ Conexión cerrada")

def enviar_email_bienvenida(email, userName):
    """
    Envía email de bienvenida usando dominio verificado
    Dominio: imjpalacio.com
    """
    try:
        print("="*50)
        print(f"📧 ENVIANDO EMAIL DE BIENVENIDA")
        print(f"   Destinatario: {email}")
        print(f"   Usuario: {userName}")
        print("="*50)
        
        params = {
            "from": "PERI-CAR <noreply@imjpalacio.com>",  # 🔹 TU DOMINIO VERIFICADO
            "to": [email],
            "subject": "¡Bienvenido a PERI-CAR! 🚗",
            "html": f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        background-color: #f4f4f4;
                        margin: 0;
                        padding: 0;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 40px auto;
                        background-color: white;
                        border-radius: 10px;
                        overflow: hidden;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    }}
                    .header {{
                        background: linear-gradient(135deg, #4A5FD9 0%, #3645B8 100%);
                        color: white;
                        padding: 40px 20px;
                        text-align: center;
                    }}
                    .header h1 {{
                        margin: 0;
                        font-size: 28px;
                    }}
                    .header p {{
                        margin: 10px 0 0 0;
                        font-size: 14px;
                        opacity: 0.9;
                    }}
                    .content {{
                        padding: 40px 30px;
                    }}
                    .content h2 {{
                        color: #333;
                        margin-top: 0;
                    }}
                    .content p {{
                        color: #666;
                        line-height: 1.6;
                        font-size: 15px;
                    }}
                    .cta-button {{
                        display: inline-block;
                        background-color: #4A5FD9;
                        color: white;
                        text-decoration: none;
                        padding: 14px 32px;
                        border-radius: 6px;
                        font-weight: bold;
                        margin: 20px 0;
                    }}
                    .features {{
                        background-color: #f9f9f9;
                        padding: 20px;
                        border-radius: 6px;
                        margin: 20px 0;
                    }}
                    .features ul {{
                        margin: 0;
                        padding-left: 20px;
                    }}
                    .features li {{
                        color: #666;
                        margin: 8px 0;
                    }}
                    .account-box {{
                        background-color: #f0f4ff;
                        border-left: 4px solid #4A5FD9;
                        padding: 15px;
                        margin: 20px 0;
                    }}
                    .footer {{
                        background-color: #f4f4f4;
                        padding: 20px;
                        text-align: center;
                        font-size: 12px;
                        color: #999;
                    }}
                    @media only screen and (max-width: 600px) {{
                        .container {{
                            margin: 0;
                            border-radius: 0;
                        }}
                        .content {{
                            padding: 30px 20px;
                        }}
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🚗 PERI-CAR</h1>
                        <p>Gestión del Futuro</p>
                    </div>
                    
                    <div class="content">
                        <h2>¡Bienvenido, {userName}! 👋</h2>
                        
                        <p>Tu cuenta ha sido creada correctamente. Ya puedes empezar a utilizar <strong>PERI-CAR</strong> para gestionar tus peritajes de manera profesional.</p>
                        
                        <div class="features">
                            <strong>Con PERI-CAR puedes:</strong>
                            <ul>
                                <li>📋 Crear y gestionar peritajes completos</li>
                                <li>📸 Documentar daños con fotos de alta calidad</li>
                                <li>📊 Generar informes profesionales en PDF</li>
                                <li>☁️ Sincronizar tus datos en la nube</li>
                                <li>👥 Gestionar múltiples clientes</li>
                            </ul>
                        </div>
                        
                        <div class="account-box">
                            <p style="margin: 0;"><strong>📌 Datos de tu cuenta:</strong></p>
                            <p style="margin: 10px 0 0 0;">
                                📧 Email: <strong>{email}</strong><br>
                                👤 Usuario: <strong>{userName}</strong>
                            </p>
                        </div>
                        
                        <p style="margin-top: 30px; font-size: 13px; color: #999;">
                            Si tienes alguna pregunta, no dudes en contactarnos respondiendo a este email.
                        </p>
                    </div>
                    
                    <div class="footer">
                        <p style="margin: 0;"><strong>© 2025 PERI-CAR.</strong> Todos los derechos reservados.</p>
                        <p style="margin: 10px 0 0 0;">Si no solicitaste esta cuenta, puedes ignorar este mensaje.</p>
                    </div>
                </div>
            </body>
            </html>
            """
        }
        
        print("📤 Llamando a Resend API...")
        result = resend.Emails.send(params)
        
        print("✅ EMAIL ENVIADO EXITOSAMENTE")
        print(f"   Email ID: {result.get('id', 'N/A')}")
        print(f"   Destinatario: {email}")
        print("="*50 + "\n")
        
        return True
        
    except Exception as e:
        print("="*50)
        print(f"❌ ERROR AL ENVIAR EMAIL")
        print(f"   Error: {e}")
        print(f"   Tipo: {type(e).__name__}")
        print("="*50 + "\n")
        raise e
    
@app.route('/usuario',methods=['GET'])
def usuario():
    conexion = conectar()
    try:
        cursor=conexion.cursor()
        sql="SELECT * FROM User"
        cursor.execute(sql)
        datos=cursor.fetchall()
        usuarios=[]
        for fila in datos:
            usuario={'id':fila[0],'userName':fila[1],'pass':fila[2],'email':fila[3],'IsAdmin':fila[4]}
            usuarios.append(usuario)
        cursor.close()
        return jsonify({'usuarios':usuarios,'mensaje':"usuario"})
    except Exception as ex:
        cursor.close()
        return jsonify({'mensaje':"error"})
    finally:
        conexion.close()   
#BUSCA TODOS LOS CLIENTES DE UN USUARIO
@app.route('/clientes/<codigo>',methods=['GET'])
def obtenerClientes(codigo):
    conexion = conectar()
    try:
        cursor=conexion.cursor()
        sql="SELECT idClientes, nombre, direccion, nif, cif, telef, precio FROM Clientes WHERE iduser = '{0}'".format(codigo)
        cursor.execute(sql)
        print("cliente")
        datos=cursor.fetchall()
        clientes=[]
        if datos != None:
            for fila in datos:
                datoscliente = {'idCliente':fila[0],'nombre':fila[1],'direccion':fila[2],'nif':fila[3],'cif':fila[4],'telef':fila[5],'precio':fila[6]}
                clientes.append(datoscliente)
            cursor.close()
            return jsonify({'clientes': clientes, 'mensaje': "Clientes encontrados."})
        else:
            cursor.close()
            return jsonify({'mensaje': "Clientes no encontrados."})
    except Exception as ex:
        print(ex)
        return "error"
    finally:
        conexion.close()   
#BUSCA UN CLIENTE
@app.route('/cliente/<codigo>',methods=['GET'])
def buscarCliente(codigo):
    conexion = conectar()
    try:
        cursor=conexion.cursor()
        sql="SELECT nombre, direccion, nif, cif, telef, precio FROM Clientes WHERE idClientes = '{0}'".format(codigo)
        cursor.execute(sql)
        print("cliente")
        datos=cursor.fetchone()
        if datos != None:
            cliente={'nombre':datos[0],'direccion':datos[1],'nif':datos[2],'cif':datos[3],'telef':datos[4],'precio':datos[5]}
            cursor.close()
            return jsonify({'cliente': cliente, 'mensaje': "Cliente encontrado."})
        else:
            cursor.close()
            return jsonify({'mensaje': "Cliente no encontrado."})
    except Exception as ex:
        print(ex)
        return "error"
    finally:
        conexion.close()   

@app.route('/cliente',methods=['POST','GET'])
def crear_cliente():
    conexion = conectar()
    try:
        cursor=conexion.cursor()
        sql="SELECT * FROM Clientes WHERE nombre = '{0}' AND iduser = '{1}'".format(
            request.form['nombre'],
            request.form['iduser']
        )
        print(sql)
        cursor.execute(sql)
        print("0k")
        datos=cursor.fetchone()
        print(datos)
        if datos == None:
            sql="""INSERT INTO Clientes (iduser, nombre, direccion, nif, cif, telef, precio)
            VALUES ('{0}', '{1}', '{2}', '{3}', '{4}','{5}', '{6}')""".format(
                request.form['iduser'],
                request.form['nombre'],
                request.form['direccion'],
                request.form['nif'],
                request.form['cif'],
                request.form['telef'],
                request.form['precio'])
            cursor.execute(sql)
            conexion.commit() #confirma la accionde inserción
            cursor.execute("SELECT LAST_INSERT_ID()")
            idCliente = cursor.fetchone()[0]
            cursor.close()
            return jsonify({'success': True,'mensaje':"Cliente registrado",'id':idCliente})
        else:
            cursor.close()
            return jsonify({'success': False,'mensaje': "Cliente ya existe.",'IdCliente':datos[0]})
    except Exception as ex:
        print(ex)
        return jsonify(jsonify({'success': False,'mensaje': "ERROR: "+ex}))
    finally:
        conexion.close()

@app.route('/updateCliente',methods=['POST','GET'])
def actualizar_cliente():
    conexion = conectar()
    try:
        cursor=conexion.cursor()
        
        sql="""UPDATE Clientes SET nombre = '{1}', direccion = '{2}', nif = '{3}', cif = '{4}', telef = '{5}', precio = '{6}' WHERE idclientes = '{0}'
        """.format(
            request.form['idcliente'],
            request.form['nombre'],
            request.form['direccion'],
            request.form['nif'],
            request.form['cif'],
            request.form['telef'],
            request.form['precio'])
        cursor.execute(sql)
        conexion.commit() #confirma la accionde inserción
        cursor.close()
        return jsonify({'success': True,'mensaje':"Cliente atualizado"})
    except Exception as ex:
        print(ex)
        return jsonify(jsonify({'success': False,'mensaje': "ERROR: "+ex}))
    finally:
        conexion.close()      

@app.route('/datos/<codigo>',methods=['GET'])
def obtenerDatos(codigo):
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        sql="SELECT idDatos, name, dirección, nif, cif, telefono, email FROM Datos WHERE userid = '{0}'".format(codigo)
        cursor.execute(sql)
        print("Datos")
        datos=cursor.fetchone()
        if datos != None:
            Datos={'id':datos[0],'nombre':datos[1],'direccion':datos[2],'nif':datos[3],'cif':datos[4],'telefono':datos[5],'email':datos[6]}
            cursor.close()
            return jsonify({'success': True,'Datos': Datos, 'mensaje': "Datos encontrados."})
        else:
            cursor.close()
            return jsonify({'success': False,'mensaje': "Datos no encontrados."})
    except Exception as ex:
        print(ex)
        return "error"
    finally:
        conexion.close()   
@app.route('/guardarDatos',methods=['POST'])
def guardarDatos():
    conexion = conectar()
    try:
        cursor=conexion.cursor()
        sql="SELECT * FROM Datos WHERE userid = '{0}'".format(
            request.form['userid']
        )
        print(sql)
        cursor.execute(sql)
        print("0k")
        datos=cursor.fetchone()
        print(datos)
        if datos == None:
            sql="""INSERT INTO Datos (userid, name, dirección, nif, cif, telefono, email)
            VALUES ('{0}', '{1}', '{2}', '{3}', '{4}','{5}', '{6}')""".format(
                request.form['userid'],
                request.form['name'],
                request.form['direccion'],
                request.form['nif'],
                request.form['cif'],
                request.form['telefono'],
                request.form['email'])
            cursor.execute(sql)
            conexion.commit() #confirma la accionde inserción
            cursor.close()
            return jsonify({'success': True,'mensaje':"Datos Guardados"})
        else:
            #si ya hay datos, actualizamos la información
            sql="""UPDATE Datos
                SET name = '{1}', dirección = '{2}', nif = '{3}', cif = '{4}', telefono = '{5}', email = '{6}'
                WHERE userid = '{0}'""".format(
                    request.form['userid'],
                    request.form['name'],
                    request.form['direccion'],
                    request.form['nif'],
                    request.form['cif'],
                    request.form['telefono'],
                    request.form['email'])
            cursor.execute(sql)
            conexion.commit()
            cursor.close()
            return jsonify({'success': True,'mensaje': "Datos actualizados."})
    except Exception as ex:
        print(ex)
        return "error"
    finally:
        conexion.close() 

def contar_peritajes_hoy(iduser, conexion):
    cursor = conexion.cursor()

    hoy = datetime.date.today()
    mañana = hoy + datetime.timedelta(days=1)

    sql = """SELECT COUNT(*) FROM peritajes 
             WHERE iduserP = %s AND fecha_creacion >= %s AND fecha_creacion < %s"""
    cursor.execute(sql, (iduser, hoy, mañana))
    resultado = cursor.fetchone()[0]
    cursor.close()
    return resultado
  
@app.route('/save',methods=['POST'])
def save():
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        iduser = request.form['iduser']
        app_key = request.headers.get('Z-APP-KEY', 'GRATIS-1234')  # valor por defecto: gratuita
        fecha_creacion = datetime.datetime.now()

        # Si es app gratuita (por defecto o explícitamente)
        if app_key != 'PREMIUM-5678':
            max_por_dia = 15  # límite configurable
            creados = contar_peritajes_hoy(iduser, conexion)
            if creados >= max_por_dia:
                return jsonify({
                    'success': False,
                    'mensaje': f'Límite diario de {max_por_dia} peritajes alcanzado. Usa la versión premium para ilimitados.'
                })
        #CREAMOS "LA FICHA" DE PERITAJE
        sql="""INSERT INTO peritajes (iduserP, idcliente, fecha_creacion, descuento) 
        VALUES ('{0}', '{1}', '{2}', '{3}')""".format(
            request.form['iduser'],
            request.form['idcliente'],
            fecha_creacion,
            float(request.form['descuento']))
        cursor.execute(sql)
        conexion.commit()
        # Obtienes el ID del último registro insertado
        cursor.execute("SELECT LAST_INSERT_ID()")
        id_peritaje = cursor.fetchone()[0]
        #GUARDAMOS LOS DATOS DEL COCHE
        
        sql="""INSERT INTO coches_peritaje (idperitaje, idcoche, modelo, matricula, version, fecha_matriculacion, N_chasis, kms, color, aseguradora)
        VALUES ('{0}', '{1}', '{2}', '{3}', '{4}','{5}', '{6}', '{7}', '{8}','{9}')""".format(
            id_peritaje,
            request.form['idcoche'],
            request.form['modelo'],
            request.form['matricula'],
            request.form['version'],
            request.form['fecha_matriculacion'],
            request.form['N_chasis'],
            request.form['kms'],
            request.form['color'],
            request.form['aseguradora'])
        cursor.execute(sql)
        conexion.commit()
        cursor.close()
        return jsonify({'success': True,'mensaje':"ficha y coche creados",'idPeritaje':id_peritaje})       
    except Exception as ex:
        print(ex)
        return "error"
    finally:
        conexion.close()   
@app.route('/saveImpactos',methods=['POST'])
def saveImpactos():
    conexion = conectar()
    try:
        cursor=conexion.cursor()
        sql="SELECT idImpactos FROM Impactos WHERE zona = '{1}' AND peritajesId = '{0}'".format(
            request.form['idperitaje'],
            request.form['zona']
        )
        cursor.execute(sql)
        datos=cursor.fetchone()
        print(datos)
        if datos == None:
            #CREAMOS "LA FICHA" DE PERITAJE
            sql="""INSERT INTO Impactos (peritajesId, zona, peq, med, grd, mgrd, reparacion, material, posibledpp) 
            VALUES ('{0}', '{1}', '{2}', '{3}', '{4}','{5}', '{6}', '{7}', '{8}')""".format(
                request.form['idperitaje'],
                request.form['zona'],
                request.form['peq'],
                request.form['med'],
                request.form['grd'],
                request.form['mgrd'],
                request.form['reparacion'],
                request.form['material'],
                request.form['posibledpp'])
        else:
            sql="""UPDATE Impactos SET
            peq = '{1}', med = '{2}', grd = '{3}', mgrd = '{4}', reparacion = '{5}', material = '{6}', posibledpp = '{7}'
            WHERE peritajesId = '{0}' AND idImpactos = '{8}'""".format(
                request.form['idperitaje'],
                request.form['peq'],
                request.form['med'],
                request.form['grd'],
                request.form['mgrd'],
                request.form['reparacion'],
                request.form['material'],
                request.form['posibledpp'],
                datos[0]
            )
        cursor.execute(sql)
        conexion.commit()
        cursor.close()
        return jsonify({'success': True,'mensaje':"Impactos guardados"})        
    except Exception as ex:
        print(ex)
        return "error"
    finally:
        conexion.close()   
    
@app.route('/update/<code>',methods=['POST'])
def update(code):
    conexion = conectar()
    try:
        cursor=conexion.cursor()
        sql="UPDATE peritajes SET fecha_creacion = '{0}', descuento = '{1}' WHERE idperitajes = '{2}' ".format(
            request.form['fecha'],
            float(request.form['descuento']),
            code
        )
        cursor.execute(sql)
        conexion.commit()
        sql="""UPDATE coches_peritaje SET
        idcoche = '{0}', modelo = '{1}', matricula = '{2}', version = '{3}', fecha_matriculacion = '{4}', N_chasis = '{5}', kms = '{6}', color = '{7}', aseguradora = '{8}'
        WHERE idperitaje = '{9}'""".format(
            request.form['idcoche'],
            request.form['modelo'],
            request.form['matricula'],
            request.form['version'],
            request.form['fecha_matriculacion'],
            request.form['N_chasis'],
            request.form['kms'],
            request.form['color'],
            request.form['aseguradora'],
            code
        )
        cursor.execute(sql)
        conexion.commit()
        cursor.close()
        return jsonify({'success':True,'mensaje':"fecha y coche actualizados"})
    except Exception as ex:
        print(ex)
        return "error"
    finally:
        conexion.close()   
@app.route('/load/<code>',methods=['GET'])
def load(code):
    conexion = conectar()
    try:
        cursor=conexion.cursor()
        
        #añadimos argumento de limite (load/code?limit=x)
        limit = request.args.get('limit')
        
        sql="SELECT * FROM peritajes WHERE iduserP = '{0}'".format(code)
        #añadimos el limite si esta el argumento
        if limit and limit.isdigit():
            sql += " LIMIT '{0}'".format(limit)
        
        cursor.execute(sql)
        datos=cursor.fetchall()
        peritajes=[]
        peritajesCompletos=[]
        if datos != None:
            for fila in datos:
                datosPeritaje={'id':fila[0],'Cliente':fila[2],'descuento':fila[3],'fecha':fila[4]}
                peritajes.append(datosPeritaje)
            
            for id in peritajes:
                idCliente = id['Cliente']
                sql_cliente = "SELECT nombre FROM Clientes WHERE idClientes = %s"
                cursor.execute(sql_cliente, (idCliente,))
                result_cliente = cursor.fetchone()
                
                if result_cliente is None:
                    continue  # Si no se encuentra el cliente, continuar con el siguiente

                nombre_cliente = result_cliente[0]
                idperitaje = id['id']
                sql_matricula = "SELECT matricula FROM coches_peritaje WHERE idperitaje = %s"
                cursor.execute(sql_matricula, (idperitaje,))
                result_matricula = cursor.fetchone()

                if result_matricula is None:
                    continue  # Si no se encuentra la matrícula, continuar con el siguiente

                matricula = result_matricula[0]
                # Formateamos la fecha en formato dd/MM/yyyy para Unity
                try:
                    fecha_raw = id['fecha']
                    fecha_str = "00/00/0000"

                    try:
                        if isinstance(fecha_raw, datetime.datetime):
                            fecha_str = fecha_raw.strftime('%d/%m/%Y')
                        elif isinstance(fecha_raw, str):
                            try:
                                # Intentar formato ISO: '2025-05-19T14:35:00'
                                fecha_obj = datetime.datetime.fromisoformat(fecha_raw)
                                fecha_str = fecha_obj.strftime('%d/%m/%Y')
                            except ValueError:
                                try:
                                    # Intentar formato antiguo: '19/05/2025'
                                    fecha_obj = datetime.datetime.strptime(fecha_raw, "%d/%m/%Y")
                                    fecha_str = fecha_obj.strftime('%d/%m/%Y')
                                except ValueError:
                                    print("Formato de fecha no reconocido:", fecha_raw)
                    except Exception as e:
                        print("Error al procesar fecha:", fecha_raw, e)
                except Exception as e:
                    print("Error al formatear fecha:", e)
                    fecha_str = "00/00/0000"

                datosCompletos = {
                    'id': id['id'],
                    'cliente': nombre_cliente,
                    'matricula': matricula,
                    'fecha': fecha_str,
                    'descuento': id['descuento']
                }
                peritajesCompletos.append(datosCompletos)
            cursor.close()
            return jsonify({'success':True,'datos':peritajesCompletos})
        else:
            cursor.close()
            return jsonify({'success':False,'mensaje':"Ningun peritaje guardado"})
    except Exception as ex:
        print(ex)
        return "error"
    finally:
        conexion.close()   
    
@app.route('/marcasCoche',methods=['GET'])
def marcas():
    conexion = conectar()
    try:
        cursor=conexion.cursor()
        #CREAMOS "LA FICHA" DE PERITAJE
        sql="SELECT * FROM DBcoches"
        cursor.execute(sql)
        print("coches")
        datos=cursor.fetchall()
        coches=[]
        if datos != None:
            for fila in datos:
                datoscoche = {'idCoche':fila[0],'Marca':fila[1]}
                coches.append(datoscoche)
            cursor.close()
            return jsonify({'success':True, 'coches': coches, 'mensaje': "Coches encontrados."})
        else:
            cursor.close()
            return jsonify({'success':False,'mensaje': "Coches no encontrados."})    
    except Exception as ex:
        print(ex)
        return "error"
    finally:
        conexion.close()   
        
@app.route('/loadDatosCoche/<code>', methods=['GET'])
def loadDatosCoche(code):
    conexion = conectar()
    try:
        cursor = conexion.cursor()

        sql = """
            SELECT 
                c.idcochePeritaje,
                c.idperitaje,
                d.Marca,
                c.modelo,
                c.matricula,
                c.version,
                c.fecha_matriculacion,
                c.N_chasis,
                c.kms,
                c.color,
                c.aseguradora
            FROM coches_peritaje c
            JOIN DBcoches d ON c.idcoche = d.idDBcoches
            WHERE c.idperitaje = %s
        """
        cursor.execute(sql, (code,))
        datos = cursor.fetchone()

        if datos:
            datosCoche = {
                'idCoche': datos[0],
                'idperitaje': datos[1],
                'marca': datos[2],  # ahora es el nombre, no el id
                'modelo': datos[3],
                'matricula': datos[4],
                'version': datos[5],
                'fecha': datos[6],
                'chasis': datos[7],
                'kms': datos[8],
                'color': datos[9],
                'aseguradora': datos[10]
            }
            cursor.close()
            return jsonify({'success': True, 'datos': datosCoche, 'mensaje': "Datos del coche cargados"})
        else:
            cursor.close()
            return jsonify({'success': False, 'mensaje': "Ningún coche guardado para este peritaje"})
    except Exception as ex:
        print(ex)
        return jsonify({'success': False, 'mensaje': 'Error en el servidor'})
    finally:
        conexion.close()

@app.route('/loadImpactos/<code>',methods=['GET'])
def loadImpactos(code):
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        sql="SELECT * FROM Impactos WHERE peritajesId = '{0}'".format(code)
        cursor.execute(sql)
        datos=cursor.fetchall()
        impactos=[]
        if datos != None:
            for fila in datos:
                datosImpacto = {'zona':fila[2],'peq':fila[3],'med':fila[4],'grd':fila[5],'mgrd':fila[6],'reparacion':fila[7],'material':fila[8],'posibledpp':fila[9]}
                impactos.append(datosImpacto)
            cursor.close()
            return jsonify({'success':True,'datos':impactos,'mensaje':"Impactos cargados"})
        else:
            cursor.close()
            return jsonify({'success':False,'mensaje':"Ningun Impacto guardado para este peritaje"})
    except Exception as ex:
        print(ex)
        return "error"
    finally:
        conexion.close()   
@app.route('/buscarPeritaje/<code>', methods=['GET'])
def buscarPeritaje(code):
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        name = request.args.get('name')
        print(name)
        
        # Obtener id del cliente
        sql = "SELECT idClientes FROM Clientes WHERE iduser = %s AND nombre = %s"
        cursor.execute(sql, (code, name))
        idcliente = cursor.fetchone()[0]
        
        if idcliente is not None:
            sql = "SELECT * FROM peritajes WHERE iduserP = %s AND idcliente = %s"
            cursor.execute(sql, (code, idcliente))
            datos = cursor.fetchall()

            peritajes = []
            peritajesCompletos = []

            if datos is not None:
                for fila in datos:
                    datosPeritaje = {
                        'id': fila[0],
                        'Cliente': fila[2],
                        'fecha': fila[4],
                        'descuento': fila[3]
                    }
                    peritajes.append(datosPeritaje)
                
                for id in peritajes:
                    idCliente = id['Cliente']
                    sql_cliente = "SELECT nombre FROM Clientes WHERE idClientes = %s"
                    cursor.execute(sql_cliente, (idCliente,))
                    result_cliente = cursor.fetchone()
                    
                    if result_cliente is None:
                        continue

                    nombre_cliente = result_cliente[0]
                    idperitaje = id['id']
                    sql_matricula = "SELECT matricula FROM coches_peritaje WHERE idperitaje = %s"
                    cursor.execute(sql_matricula, (idperitaje,))
                    result_matricula = cursor.fetchone()

                    if result_matricula is None:
                        continue

                    matricula = result_matricula[0]

                    # 🔁 TRATAMIENTO DE FECHA
                    fecha_raw = id['fecha']
                    fecha_str = "00/00/0000"
                    try:
                        if isinstance(fecha_raw, datetime.datetime):
                            fecha_str = fecha_raw.strftime('%d/%m/%Y')
                        elif isinstance(fecha_raw, str):
                            try:
                                fecha_obj = datetime.datetime.fromisoformat(fecha_raw)
                                fecha_str = fecha_obj.strftime('%d/%m/%Y')
                            except ValueError:
                                try:
                                    fecha_obj = datetime.datetime.strptime(fecha_raw, "%d/%m/%Y")
                                    fecha_str = fecha_obj.strftime('%d/%m/%Y')
                                except ValueError:
                                    print("Formato no reconocido:", fecha_raw)
                    except Exception as e:
                        print("Error al procesar fecha:", fecha_raw, e)

                    datosCompletos = {
                        'id': id['id'],
                        'cliente': nombre_cliente,
                        'matricula': matricula,
                        'fecha': fecha_str,
                        'descuento': id['descuento']
                    }
                    peritajesCompletos.append(datosCompletos)

                cursor.close()
                return jsonify({'success': True, 'datos': peritajesCompletos})
            else:
                cursor.close()
                return jsonify({'success': False, 'mensaje': "Ningún peritaje guardado con ese nombre"})
        else:
            cursor.close()
            return jsonify({'success': False, 'mensaje': "Cliente no encontrado"})
    except Exception as ex:
        print(ex)
        return "error"
    finally:
        conexion.close()

@app.route('/añadirMarcaCoche',methods=['POST'])
def añadirMarcaCoche():
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        sql = "SELECT * FROM DBcoches WHERE Marca = '{0}'".format(request.form['marca'])
        cursor.execute(sql)
        datos=cursor.fetchone()
        if datos == None:
            sql = "INSERT INTO DBcoches (Marca) VALUES ('{0}')".format(
                request.form['marca']
            )
            cursor.execute(sql)
            conexion.commit()
            cursor.close()
            return jsonify({'success':True,'mensaje':"Marca añadida con exito"})   
        else:
            return jsonify({'success': False,'mensaje': "La marca ya existe"})  
    except Exception as ex:
        print(ex)
        return "error"
    finally:
        conexion.close()     

@app.route('/uploadImagen/<code>',methods=['POST'])
def uploadImagen(code):
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        imagen_base64 = request.form['imagen']
        imagen_bytes = base64.b64decode(imagen_base64)
        
        sql="SELECT * FROM Datos WHERE userid = '{0}'".format(
            code
        )
        print(sql)
        cursor.execute(sql)
        print("0k")
        datos=cursor.fetchone()
        print(datos)
        if datos == None:
            cursor.execute("INSERT INTO Datos (Logo, userid) VALUES (%s, %s)", (imagen_bytes, code))
            conexion.commit()
            cursor.close()
        else:
            cursor.execute("UPDATE Datos SET Logo = %s WHERE userid = %s", (imagen_bytes, code))
            conexion.commit()
            cursor.close()
        return jsonify({'success':True,'mensaje':"Imagen actualizada"})
    except Exception as ex:
        print(ex)
        return jsonify({'success':False,'mensaje':"No se ha podido actualizar la imagen"})
    finally:
        conexion.close() 
        
@app.route('/obtenerImagen/<code>', methods=['GET'])
def obtenerImagen(code):
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute("SELECT Logo FROM Datos WHERE userid = %s", (code,))
        imagen_bytes = cursor.fetchone()[0]

        # Convertir los bytes de la imagen a una cadena Base64
        imagen_base64 = base64.b64encode(imagen_bytes).decode('utf-8')

        return jsonify({'success': True, 'imagen': imagen_base64})
    except Exception as ex:
        print(ex)
        return jsonify({'success': False, 'mensaje': "No se ha podido obtener la imagen"})
    finally:
        conexion.close()
        
@app.route('/olvidopass',methods=['GET','POST'])
def olvidopass():
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        
        cursor.execute("SELECT * FROM User WHERE email = %s", (request.form['email']))
        datos=cursor.fetchall()
        if datos!=None:
            encoded_token = Security.generate_token_pass(request.form['email'])
            url="https://api-nils.onrender.com/resetPass"
            headers={
                "Authorization": f"Bearer {encoded_token}"
            }
            print("encoded token")
            print(encoded_token)

            url_token=f"{url}?token={encoded_token}"
            
            params: resend.Emails.SendParams = {
                "from": "PERI-CAR <info@imjpalacio.com>",
                "to": [request.form['email']],
                "subject": "Cambiar contraseña",
                "html": f"""
                <strong>Se ha solicitado un cambio de contraseña. Si has sido tú, haz click </strong>
                <a href={url_token}>AQUI</a>
                """,
            }
            
            resend.Emails.send(params)
            
            return jsonify({'success': True, 'mensaje':"Comprueba tu email." })
        else:
            return jsonify({'success': False,'mensaje':"No existe nungun usuario con este correo."})
    except Exception as ex:
        print(ex)
        return jsonify({'success': False, 'mensaje': "No se ha podido comprobar el email"})
    finally:
        conexion.close()
@app.route('/eliminar_cuenta')
def webDelete():
    return render_template('auth/eliminarCuenta.html')
@app.route('/delete',methods=['GET','POST'])
def delete():
    conexion = conectar()
    try:
         # Primero verificamos las credenciales del usuario
        username = request.form['username']
        password = request.form['password']
        user = User(0, username, password, None, None)
        logged_user = ModelUser.login(conexion, user)
        
        if logged_user is not None:
            if logged_user.pasword:  # Verificamos la contraseña
                # Procedemos con la eliminación de la cuenta
                cursor = conexion.cursor()
                sql = "DELETE FROM User WHERE idUser = %s"
                cursor.execute(sql, (logged_user.idUser,))
                conexion.commit()
                return jsonify({'success': True, 'mensaje': "Cuenta eliminada con éxito"})
            else:
                return jsonify({'success': False, 'mensaje': "Contraseña incorrecta"})
        else:
            return jsonify({'success': False, 'mensaje': "Usuario no encontrado"})
    except Exception as ex:
        print(ex)
        return jsonify({'success': False, 'mensaje': "No se ha podido eliminar la cuenta"})
@app.route('/deletePeritajes/<code>',methods=['GET','POST'])
def deletePeritaje(code):
    conexion = conectar()
    try:
        
        cursor = conexion.cursor()
        sql = "DELETE FROM peritajes WHERE idperitajes = %s"
        cursor.execute(sql, (code))
        conexion.commit()
        return jsonify({'success': True, 'mensaje': "Peritaje eliminado"})
    except Exception as ex:
        print(ex)
        return jsonify({'success': False, 'mensaje': "No se ha podido eliminar el peritaje"})

# GET: devolver notas
@app.route('/peritajes/<int:idp>', methods=['GET'])
def get_peritaje(idp):
    con = conectar()
    try:
        cur = con.cursor(dictionary=True)
        cur.execute("""SELECT idperitajes,iduserP,idcliente,descuento,fecha_creacion,notas
                       FROM peritajes WHERE idperitajes=%s""", (idp,))
        row = cur.fetchone()
        return jsonify(success=bool(row), datos=row)
    finally:
        con.close()

# PUT: actualizar notas
@app.route('/peritajes/<int:idp>/notas', methods=['PUT'])
def update_notas(idp):
    data = request.get_json(force=True) or {}
    notas = (data.get('notas') or '').strip()
    con = conectar()
    try:
        cur = con.cursor()
        cur.execute("UPDATE peritajes SET notas=%s WHERE idperitajes=%s", (notas, idp))
        con.commit()
        return jsonify(success=True, mensaje="Notas actualizadas")
    finally:
        con.close()
    
def pagina_no_encontrada(error):
    return "<h1>La página no existe</h1>", 404

if __name__=='__main__':
    conexion = conectar()
    app.config.from_object(config['development'])#pasamos la configuracion desde un objeto
    app.register_error_handler(404,pagina_no_encontrada)#para manejar errores
    app.register_error_handler(409,None)
    app.register_error_handler(500,None)
    app.run()