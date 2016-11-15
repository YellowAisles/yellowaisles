from lib.db import Database


if __name__ == "__main__":
    db = Database()
    users = {'micha': None, 'luke': None, 'steven': None}
    for user in users:
        print("Inserting user: ", user)
        uid = db.new_user(user, user+"@example.com")
        users[user] = uid
    db.new_conversation(users['micha'], users['luke'])
    db.new_message(users['luke'], users['micha'], "Hi micha... this is luke")
    db.deanonymize_user(users['luke'])

    db.new_conversation(users['micha'], users['steven'])
    db.new_message(users['micha'], users['steven'], "hey steven... how are you?")
    db.new_message(users['steven'], users['micha'], "good! what about you?")
