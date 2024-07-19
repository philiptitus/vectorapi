import re
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

user_data = [
    # {'name': 'JohnDoe0', 'email': 'mrphilv@outlook.com', 'password': 'Strovold2h.'},
    {'name': 'JohnDoe1', 'email': 'larryowade3@gmail.com', 'password': 'Strovold2Y.'},
    {'name': 'JohnDoe2', 'email': 'mrphils@outlook.com', 'password': 'Strovold2l.'},
    {'name': 'JohnDoe3', 'email': 'mrphily@outlook.com', 'password': 'Strovold2F.'},
    {'name': 'JohnDoe4', 'email': 'mrphila@outlook.com', 'password': 'Strovold2J.'},
    {'name': 'JohnDoe5', 'email': 'mrphilo@outlook.com', 'password': 'Strovold2k.'},
    {'name': 'JohnDoe6', 'email': 'mrphile@outlook.com', 'password': 'Strovold2x.'},
    {'name': 'JohnDoe7', 'email': 'mrphilu@outlook.com', 'password': 'Strovold2o.'},
    {'name': 'JohnDoe8', 'email': 'mrphiln@outlook.com', 'password': 'Strovold2w.'},
    {'name': 'JohnDoe9', 'email': 'mrphilf@outlook.com', 'password': 'Strovold2X.'},
    {'name': 'JohnDoe10', 'email': 'mrphilk@outlook.com', 'password': 'Strovold2Z.'},
    {'name': 'JohnDoe11', 'email': 'mrphild@outlook.com', 'password': 'Strovold2e.'},
    {'name': 'JohnDoe12', 'email': 'mrphill@outlook.com', 'password': 'Strovold2r.'},
    {'name': 'JohnDoe13', 'email': 'mrphild@outlook.com', 'password': 'Strovold2f.'},
    {'name': 'JohnDoe14', 'email': 'mrphilv@outlook.com', 'password': 'Strovold2K.'},
    {'name': 'JohnDoe15', 'email': 'mrphilq@outlook.com', 'password': 'Strovold2F.'},
    {'name': 'JohnDoe16', 'email': 'mrphils@outlook.com', 'password': 'Strovold2A.'},
    {'name': 'JohnDoe17', 'email': 'mrphilj@outlook.com', 'password': 'Strovold2y.'},
    {'name': 'JohnDoe18', 'email': 'mrphilb@outlook.com', 'password': 'Strovold2h.'},
    {'name': 'JohnDoe19', 'email': 'mrphilg@outlook.com', 'password': 'Strovold2V.'},
    {'name': 'JohnDoe20', 'email': 'mrphilq@outlook.com', 'password': 'Strovold2T.'},
    {'name': 'JohnDoe21', 'email': 'mrphild@outlook.com', 'password': 'Strovold2E.'},
    {'name': 'JohnDoe22', 'email': 'mrphilx@outlook.com', 'password': 'Strovold2r.'},
    {'name': 'JohnDoe23', 'email': 'mrphilr@outlook.com', 'password': 'Strovold2H.'},
    {'name': 'JohnDoe24', 'email': 'mrphili@outlook.com', 'password': 'Strovold2x.'},
    {'name': 'JohnDoe25', 'email': 'mrphila@outlook.com', 'password': 'Strovold2T.'},
    {'name': 'JohnDoe26', 'email': 'mrphilu@outlook.com', 'password': 'Strovold2m.'},
    {'name': 'JohnDoe27', 'email': 'mrphily@outlook.com', 'password': 'Strovold2k.'},
    {'name': 'JohnDoe28', 'email': 'mrphilt@outlook.com', 'password': 'Strovold2X.'},
    {'name': 'JohnDoe29', 'email': 'mrphilx@outlook.com', 'password': 'Strovold2S.'},
]


# Function to check password format
def check_password_format(password):
    if len(password) < 8:
        return False
    if not any(c.isupper() for c in password):
        return False
    if not any(c.islower() for c in password):
        return False
    if not any(c.isdigit() for c in password):
        return False
    if not any(not c.isalnum() for c in password):
        return False
    return True

# Function to validate email
def validate_email_format(email):
    try:
        validate_email(email)
        return True
    except ValidationError:
        return False

# Validate all passwords and emails in user_data
for user in user_data:
    if not check_password_format(user['password']):
        print(f"Password for user {user['name']} does not match the required format.")
    else:
        print(f"Password for user {user['name']} matches the required format.")
    
    if not validate_email_format(user['email']):
        print(f"Email for user {user['name']} is not valid.")
    else:
        print(f"Email for user {user['name']} is valid.")
