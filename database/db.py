import pymysql

def get_connection():
    try:
        return pymysql.connect(
            host='b5xjtjc7ljbwo9pqw9ds-mysql.services.clever-cloud.com',
            user='ugxkrton3nwnoe1m',
            password='CnqN1HBzgsypNbZkldpd',
            db='b5xjtjc7ljbwo9pqw9ds'            
        )
    except Exception as ex:
        return "error"