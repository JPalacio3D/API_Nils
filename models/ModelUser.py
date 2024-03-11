from .entities.User import User
import pymysql

class ModelUser():
    @classmethod
    def login(cls, conexion, user):
        try:
            cursor = conexion.cursor()
            sql = """SELECT * FROM User 
                     WHERE userName = '{}'""".format(
                user.userName
            )
            cursor.execute(sql)
            row = cursor.fetchone()
            # Verificamos que existe el usuario
            if row != None:
                user = User(int(row[0]), row[1], user.check_password(row[2], user.pasword), row[3], row[4])
                cursor.close()
                return user
            else:
                cursor.close()
                return None
        except pymysql.MySQLError as ex:
            print("Error de conexión:", ex)
            # Si hay un error de conexión, intenta reconectar y ejecutar la consulta nuevamente
            if execute_query(conexion, sql):
                return cls.login(conexion, user)
            else:
                raise Exception("No se pudo reconectar y ejecutar la consulta SQL")

def execute_query(conexion, sql):
    max_retries = 3
    retry_count = 0
    while retry_count < max_retries:
        try:
            conexion.ping(reconnect=True)  # Verifica la conexión y reconecta si es necesario
            cursor = conexion.cursor()
            cursor.execute(sql)
            conexion.commit()
            cursor.close()
            return True
        except pymysql.MySQLError as ex:
            print("Error de conexión:", ex)
            # Intenta reconectar
            retry_count += 1
            if retry_count == max_retries:
                return False
            else:
                print("Intentando reconectar...")
                conexion = conectar()  # Reconecta
    return False