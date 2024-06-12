from flask import Flask,jsonify,request,render_template
#from flask_mysqldb import MySQL
from config import config
from werkzeug.security import generate_password_hash
import pymysql
import datetime
import base64
import resend
import os
import requests
#from src.database.db import get_connection

#Models
from models.ModelUser import ModelUser
from models.Security import Security

#Entities
from models.entities.User import User

resend.api_key='re_6aRbi2A2_6YdBXZoKJzorDonsnCxLhsUe'

app=Flask(__name__) #este parametro servira para saber si estamos ejecutando este archivo como principal
#conexion=MySQL(app)
# Define la función de conexión
def conectar():
    return pymysql.connect(
        host='b5xjtjc7ljbwo9pqw9ds-mysql.services.clever-cloud.com',
        user='ugxkrton3nwnoe1m',
        password='CnqN1HBzgsypNbZkldpd',
        db='b5xjtjc7ljbwo9pqw9ds'
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
    
@app.route('/login', methods=['POST','GET'])
def login():
    conexion = conectar()
    try:
        username = request.form['username']
        password = request.form['password']
        user = User(0,username,password,None,None)
        logged_user=ModelUser.login(conexion,user)
        if logged_user!=None:
            if logged_user.pasword:
                encoded_token = Security.generate_token(logged_user)
                data = {'id':logged_user.idUser,'username':logged_user.userName,'email':logged_user.email,'IsAdmin':logged_user.IsAdmin}
                return jsonify({'success': True, 'token': encoded_token,'mensaje':"loged",'data':data})
            else:
                return jsonify({'success': False,'mensaje':"Invalid password"})
        else:
            return jsonify({'success': False,'mensaje':"User not found"})
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
    try:
        cursor=conexion.cursor()
        sql="""INSERT INTO User (userName, pasword, email, IsAdmin)
          VALUES ('{0}', '{1}', '{2}', '{3}')""".format(
              request.form['userName'],
              generate_password_hash(request.form['password']),
              request.form['email'],
              request.form['IsAdmin'])
        cursor.execute(sql)
        conexion.commit() #confirma la accionde inserción
        cursor.close()
        
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
            return jsonify({'mensaje':"error",'error':str(ex)}),500
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
@app.route('/save',methods=['POST'])
def save():
    conexion = conectar()
    try:
        cursor=conexion.cursor()
        #CREAMOS "LA FICHA" DE PERITAJE
        sql="""INSERT INTO peritajes (iduserP, idcliente, fecha_creacion) 
        VALUES ('{0}', '{1}', '{2}')""".format(
            request.form['iduser'],
            request.form['idcliente'],
            request.form['fecha'])
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
        sql="UPDATE peritajes SET fecha_creacion = '{0}' WHERE idperitajes = '{1}' ".format(
            request.form['fecha'],
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
                datosPeritaje={'id':fila[0],'Cliente':fila[2],'fecha':fila[3]}
                peritajes.append(datosPeritaje)
            
            for id in peritajes:
                idCliente = id['Cliente']
                sql_cliente = "SELECT nombre FROM Clientes WHERE idClientes = '{0}'".format(idCliente)
                cursor.execute(sql_cliente)
                nombre_cliente = cursor.fetchone()[0]
                idperitaje = id['id']
                sql_matricula = "SELECT matricula FROM coches_peritaje WHERE idperitaje = '{0}'".format(idperitaje)
                cursor.execute(sql_matricula)
                matricula = cursor.fetchone()[0]
                datosCompletos={'id':id['id'],'cliente':nombre_cliente,'matricula':matricula,'fecha':id['fecha']}
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
@app.route('/buscarPeritaje/<code>',methods=['GET'])
def buscarPeritaje(code):
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        name = request.args.get('name')
        print(name)
        
        sql="SELECT idClientes FROM Clientes WHERE iduser = '{0}' AND nombre = '{1}'".format(
            code,
            name
        )
        cursor.execute(sql)
        idcliente = cursor.fetchone()[0]
        #print(f"ID: {idcliente}")
        if idcliente != None:
            sql="SELECT * FROM peritajes WHERE iduserP = '{0}' AND idcliente = '{1}'".format(
                code,
                idcliente
            )
            cursor.execute(sql)
            datos = cursor.fetchall()
            print(f"Datos: {datos}")
            peritajes=[]
            peritajesCompletos=[]
            if datos != None:
                for fila in datos:
                    datosPeritaje={'id':fila[0],'Cliente':fila[2],'fecha':fila[3]}
                    peritajes.append(datosPeritaje)
                
                for id in peritajes:
                    idCliente = id['Cliente']
                    sql_cliente = "SELECT nombre FROM Clientes WHERE idClientes = '{0}'".format(idCliente)
                    cursor.execute(sql_cliente)
                    nombre_cliente = cursor.fetchone()[0]
                    idperitaje = id['id']
                    sql_matricula = "SELECT matricula FROM coches_peritaje WHERE idperitaje = '{0}'".format(idperitaje)
                    cursor.execute(sql_matricula)
                    matricula = cursor.fetchone()[0]
                    datosCompletos={'id':id['id'],'cliente':nombre_cliente,'matricula':matricula,'fecha':id['fecha']}
                    peritajesCompletos.append(datosCompletos)
                cursor.close()
                return jsonify({'success':True,'datos':peritajesCompletos})
            else:
                cursor.close()
                return jsonify({'success': False, 'mensaje': "Nungun peritaje guardado con ese nombre"})
        else:
            cursor.close()
            return jsonify({'success': False, 'mensaje': "Nungun peritaje guardado con ese nombre"})
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
                "from": "PERI-CAR <onboarding@resend.dev>",
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
    
def pagina_no_encontrada(error):
    return "<h1>La página no existe</h1>", 404

if __name__=='__main__':
    conexion = conectar()
    app.config.from_object(config['development'])#pasamos la configuracion desde un objeto
    app.register_error_handler(404,pagina_no_encontrada)#para manejar errores
    app.register_error_handler(409,None)
    app.register_error_handler(500,None)
    app.run()