from app import db
from models import Admin

# ---- Admin 1 ----
a1 = Admin(name="Ritika", email="ritika@zs.com")
a1.set_password("1q2w1q2w")   # hashes automatically
db.session.add(a1)

# ---- Admin 2 ----
a2 = Admin(name="Faraz", email="faraz@zs.com")
a2.set_password("1q2w1q2w")   # hashes automatically
db.session.add(a2)

db.session.commit()

print("Admins created successfully!")
