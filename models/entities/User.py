from werkzeug.security import check_password_hash

class User():
    def __init__(self, idUser, userName, pasword, email, IsAdmin) -> None:
        self.idUser = idUser
        self.userName = userName
        self.pasword = pasword
        self.email = email
        self.IsAdmin = IsAdmin

    @classmethod
    def check_password(self,hashed_password,password):
        return check_password_hash(hashed_password,password)
        if hashed_password == password:
           return True
        else:
            return False