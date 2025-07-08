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

load_dotenv()

resend.api_key = os.getenv('RESEND_API_KEY')

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
    conexion = conectar()  
    cursor = None
    try:
         # Obtener datos del formulario
        userName = request.form['userName']
        password = request.form['password']
        email = request.form['email']
        isAdmin = request.form['IsAdmin']
        
        # Validación del email
        email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        if not re.match(email_regex, email):
            return jsonify({'success': False, 'mensaje': "Correo electrónico no válido"}), 400
        
        # Encriptar la contraseña
        hashed_password = generate_password_hash(password)
        
        cursor = conexion.cursor()
        sql = """INSERT INTO User (userName, pasword, email, IsAdmin) 
                 VALUES (%s, %s, %s, %s)"""
        cursor.execute(sql, (userName, hashed_password, email, isAdmin))
        conexion.commit()  # Confirmar la inserción
        
        params: resend.Emails.SendParams = {
            "from": "PERI-CAR <onboarding@resend.dev>",
            "to": [request.form['email']],
            "subject": "Bienvenido a PERI-CAR",
            "html": "<strong>Bienvenido a PERI-CAR!</br> Te has registrado correctamente, ya puedes disfrutar de nuestra APP.</strong>",
        }
        
        resend.Emails.send(params)
        
        return jsonify({'success':True,'mensaje':"Usuario registrado"})
    except Exception as ex:
        print("ex")
        print(ex)
        error_message = str(ex)
        if 'Duplicate entry' in error_message and "for key 'User.userName_UNIQUE'" in error_message:
            cursor.close()
            return jsonify({'mensaje':"Nombre de usuario ya registrado",'error':str(ex)}),500
        if 'Duplicate entry' in error_message and "for key 'User.email_UNIQUE'" in error_message:
            cursor.close()
            return jsonify({'mensaje':"Email ya registrado",'error':str(ex)}),500
        else:
            cursor.close()
            return jsonify({'mensaje':"error en el registro",'error':str(ex)}),500
    finally:
        conexion.close()   

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
@app.route('/loadDatosCoche/<code>',methods=['GET'])
def loadDatosCoche(code):
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        sql="SELECT * FROM coches_peritaje WHERE idperitaje = '{0}'".format(code)
        cursor.execute(sql)
        datos=cursor.fetchone()

        if datos != None:
            datosCoche = {'idCoche':datos[0],'idperitaje':datos[1],'marca':datos[2],'modelo':datos[3],'matricula':datos[4],'version':datos[5],'fecha':datos[6],'chasis':datos[7],'kms':datos[8],'color':datos[9],'aseguradora':datos[10]}
            cursor.close()
            return jsonify({'success':True,'datos':datosCoche,'mensaje':"Datos del coche cargados"})
        else:
            cursor.close()
            return jsonify({'success':False,'mensaje':"Ningun coche guardado para este peritaje"})
    except Exception as ex:
        print(ex)
        return "error"
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
@app.route('/deletePeritaje/<code>',methods=['GET','POST'])
def deletePeritaje(code):
    conexion = conectar()
    try:
        
        cursor = conexion.cursor()
        sql = "DELETE FROM peritajes WHERE idperitajes = %s"
        cursor.execute(sql, (code,))
        conexion.commit()
        return jsonify({'success': True, 'mensaje': "Peritaje eliminado"})
    except Exception as ex:
        print(ex)
        return jsonify({'success': False, 'mensaje': "No se ha podido eliminar el peritaje"})
    
def pagina_no_encontrada(error):
    return "<h1>La página no existe</h1>", 404

if __name__=='__main__':
    conexion = conectar()
    app.config.from_object(config['development'])#pasamos la configuracion desde un objeto
    app.register_error_handler(404,pagina_no_encontrada)#para manejar errores
    app.register_error_handler(409,None)
    app.register_error_handler(500,None)
    app.run()