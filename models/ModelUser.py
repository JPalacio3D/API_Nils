from .entities.User import User

class ModelUser():
    @classmethod
    def login(self,db,user):
        try:
            cursor=db.cursor()
            sql="""SELECT * FROM User 
                    WHERE userName = '{}'""".format(
                        user.userName
                    )
            cursor.execute(sql)
            row=cursor.fetchone()
            #verificamos que existe el usuario
            if row != None:
                user=User(int(row[0]),row[1],user.check_password(row[2], user.pasword),row[3],row[4])
                cursor.close()
                return user
            else:
                cursor.close()
                return None
        except Exception as ex:
            raise Exception(ex)