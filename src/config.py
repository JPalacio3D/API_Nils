#CONFIGURACION DEL PROYECTO
class config():
    #SECRET_KEY = 'ijIyl7^Tsu#0dOA!'
    JWT_KEY = 'qJVZ#FfNTw!*z5S9'

class DevelopmentConfig(config):
    DEBUG=True
    MYSQL_HOST = 'b5xjtjc7ljbwo9pqw9ds-mysql.services.clever-cloud.com'
    MYSQL_USER = 'ugxkrton3nwnoe1m'
    MYSQL_PASSWORD = 'CnqN1HBzgsypNbZkldpd'
    MYSQL_DB = 'b5xjtjc7ljbwo9pqw9ds'
    #MYSQL_PORT = '3306'

config = {
    'development': DevelopmentConfig,
    'JWT_KEY':config
}