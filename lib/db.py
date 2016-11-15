import sqlite3
import datetime
from contextlib import contextmanager


class NoConversation(Exception):
    pass


class ArchivedConversation(Exception):
    pass


class InvalidSender(Exception):
    pass


class UserAlreadyExists(Exception):
    pass


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


@contextmanager
def sqlcloser(c):
    try:
        yield c.cursor()
    finally:
        c.commit()


class Database(object):
    def __init__(self, dbfile='crosstheaisle.db'):
        self._con = sqlite3.connect(dbfile)
        self._con.row_factory = dict_factory
        self.dbfile = dbfile
        try:
            self.create_tables()
        except sqlite3.OperationalError:
            pass

    @property
    def con(self):
        return sqlcloser(self._con)

    def create_tables(self):
        with self.con as c:
            c.execute("create table user(userid integer primary key autoincrement, "
                      "name text, email text, facebookauth blob, curconv int)")
            c.execute("create table conversations(convid integer primary key, "
                      "user1 integer, user2 integer, user1_name text, user2_name text, "
                      "archived int)")
            c.execute("create table chat(msgid integer primary key, "
                      "convid int, sentts timestamp, sender int, "
                      "reciever int, message blob, recievedts timestamp)")
            c.execute("create index if not exists convid on chat(convid)")
            c.execute("create index if not exists email on user(email)")

    def new_message(self, sender, reciever, message):
        with self.con as c:
            c.execute('SELECT convid FROM conversations WHERE '
                      '((user1 == ? AND user2 == ?) OR'
                      ' (user2 == ? AND user1 == ?)) AND '
                      'archived == 0',
                      (sender, reciever)*2)
            try:
                convid = c.fetchone()['convid']
            except TypeError as e:
                raise NoConversation() from e
        return self._add_message(convid, sender, reciever, message)

    def new_message_user(self, convid, sender, message):
        with self.con as c:
            c.execute('SELECT * FROM conversations WHERE convid == ?',
                      (convid,))
            conv = c.fetchone()
        if conv['archived']:
            raise ArchivedConversation()
        if sender not in (conv['user1'], conv['user2']):
            raise InvalidSender()
        if sender == conv['user1']:
            reciever = conv['user1']
        else:
            reciever = conv['user2']
        return self._add_message(convid, sender, reciever, message)

    def _add_message(self, convid, sender, reciever, message):
        data = (convid, datetime.datetime.now(), sender, reciever,
                message, None)
        with self.con as c:
            r = c.execute("insert into chat"
                          "(convid, sentts, sender, reciever, message, "
                          "recievedts) values (?, ?, ?, ?, ?, ?)", (data))
            return r.lastrowid

    def new_user(self, name, email, userid=None, facebookauth=None):
        try:
            with self.con as c:
                r = c.execute("insert into user(userid, name, email, "
                              "facebookauth) values (?, ?, ?, ?)",
                              (userid, name, email, facebookauth))
                return userid or r.lastrowid
        except sqlite3.IntegrityError as e:
            raise UserAlreadyExists() from e

    def new_conversation(self, user1, user2):
        with self.con as c:
            c.execute('UPDATE conversations SET archived = 1 WHERE '
                      'user1 == ? OR user2 == ? OR '
                      'user1 == ? OR user2 == ?',
                      (user1, user1, user2, user2))
            r = c.execute('INSERT INTO conversations(user1, user2, '
                          'user1_name, user2_name, archived) '
                          'VALUES (?, ?, "anonymous", "anonymous", 0)',
                          (user1, user2))
            convid = r.lastrowid
            c.execute('UPDATE user SET curconv = ? WHERE '
                      '(userid == ? OR userid == ?)', (convid, user1, user2))
            return convid

    def deanonymize_user(self, userid):
        user = self.get_user(userid)
        name = user['name']
        convid = user['curconv']
        if not convid:
            return False
        with self.con as c:
            c.execute('UPDATE conversations SET user1_name = ? WHERE '
                      'user1 == ? AND convid == ?', (name, userid, convid))
            c.execute('UPDATE conversations SET user2_name = ? WHERE '
                      'user2 == ? AND convid == ?', (name, userid, convid))
        return True

    def get_conversation(self, convid, userid=None):
        if userid is not None:
            with self.con as c:
                c.execute('SELECT * FROM conversations WHERE convid == ?',
                          (convid,))
                conv = c.fetchone()
                if not conv:
                    return []
                if userid != conv['user1'] and userid != conv['user2']:
                    return []
        with self.con as c:
            c.execute('SELECT * FROM chat WHERE convid == ? ORDER BY sentts',
                      (convid,))
            return c.fetchall()

    def list_user_conversations(self, userid):
        with self.con as c:
            c.execute('SELECT * FROM conversations WHERE user1 == ? '
                      'OR user2 == ?', (userid,userid))
            return c.fetchall()

    def set_conversation_read(self, userid, convid):
        now = datetime.datetime.now()
        with self.con as c:
            c.execute('UPDATE chat SET recievedts = ? WHERE reciever == ? AND '
                      'convid == ? AND recievedts is NULL',
                      (now, userid, convid))

    def get_user_from_email(self, email):
        with self.con as c:
            c.execute('SELECT * FROM user WHERE email == ?', (email,))
            return c.fetchone()

    def get_user_current_convid(self, userid):
        with self.con as c:
            c.execute('SELECT curconv FROM user WHERE userid == ?', (userid,))
            curconv = c.fetchone()['curconv']
        return curconv

    def get_user(self, userid):
        with self.con as c:
            c.execute('SELECT * FROM user WHERE userid == ?', (userid,))
            return c.fetchone()


if __name__ == "__main__":
    import string
    import random

    db = Database(":memory:")
    users = {'micha': None, 'luke': None, 'steven': None}
    for user in users:
        print("Adding user:", user)
        uid = db.new_user(user, user + "@example.com")
        print("uid:", uid)
        users[user] = uid

    uid = db.new_user('test', 'test@example.com', 666)
    print("Tried to create user with uid 666:", uid)

    convid = db.new_conversation(users['micha'], users['steven'])
    print("New conversation ebtween micha and steven: ", convid)

    msgid = db.new_message(users['micha'], users['steven'], 'hello')
    print("New message micha -> steven:", msgid)

    print("Filling conversation with more messages")
    conv_users = (users['micha'], users['steven'])
    for _ in range(10):
        message = "".join(random.sample(string.ascii_letters, 28))
        db.new_message(conv_users[0], conv_users[1], message)
        conv_users = list(reversed(conv_users))

    print("Full conversation:")
    print(db.get_conversation(convid))

    print("New message micha -> luke:", msgid)
    try:
        msgid = db.new_message(users['micha'], users['luke'], 'hello')
    except NoConversation:
        print("Raised NoConversation")

    print("Fetching user by email micha@example.com:",
          db.get_user_from_email('micha@example.com'))
