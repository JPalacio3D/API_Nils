from config import config
import datetime
import pytz
import jwt

class Security():
    
    secret=config['JWT_KEY']
    tz=pytz.timezone("Europe/Madrid")
    
    @classmethod
    def generate_token(cls, authenticated_user):
        payload={
            'iat':datetime.datetime.now(tz=cls.tz),#fecha de creacion del token
            'exp':datetime.datetime.now(tz=cls.tz) + datetime.timedelta(minutes=10),
            'userName':authenticated_user.userName,
            'roles': authenticated_user.IsAdmin#['Administrator', 'Editor']
        }
        return jwt.encode(payload,str(cls.secret),algorithm="HS256")
    
    @classmethod
    def verify_token(cls,headers):
        if 'Authorization' in headers.keys():
            authorization = headers['Authorization']
            encouded_token=authorization.split(" ")[1]
            
            try:
                payload=jwt.decode(encouded_token,cls.secret,algorithms=["HS256"])
                roles=list(payload['roles'])
                
                if '1' in roles or 'contraseña' in roles:
                    return True
                return False
            except(jwt.ExpiredSignatureError,jwt.InvalidSignatureError):
                return False
        return False
    
    @classmethod
    def generate_token_pass(cls,email):
        payload={
            'iat':datetime.datetime.now(tz=cls.tz),#fecha de creacion del token
            'exp':datetime.datetime.now(tz=cls.tz) + datetime.timedelta(minutes=10),
            'email':email,
            'roles': ['contraseña']
        }
        return jwt.encode(payload,str(cls.secret),algorithm="HS256")
    
    
    @classmethod
    def verify_token_pass(cls,token):
        if not token:
            return False
        
        try:
            print(token)
            payload = jwt.decode(token, str(cls.secret), algorithms=["HS256"])
            roles = payload.get('roles', [])
            print(f"Roles: {roles}")
            
            if '1' in roles or 'contraseña' in roles:
                return True
            else:
                print("sin roles")
                return False
        except jwt.ExpiredSignatureError:
            # El token ha expirado
            print("El token ha expirado")
            return False
        except (jwt.InvalidSignatureError, jwt.InvalidTokenError):
            # El token es inválido
            print(Exception)
            print("El token es inválido")
            return False