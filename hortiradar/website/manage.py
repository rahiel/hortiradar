import argparse
import sys

from sqlalchemy.orm.exc import NoResultFound

from app import db
from models import Role, User


parser = argparse.ArgumentParser()
parser.add_argument("--init-db", help="Initialize user db", action="store_true")
parser.add_argument("--make-admin", type=str, help="Give user admin rights")
parser.add_argument("--delete", type=str, help="Delete user")
args = parser.parse_args()


if args.init_db:
    db.create_all()

if args.make_admin:
    try:
        user = User.query.filter(User.username == args.make_admin).one()
    except NoResultFound:
        print("User with username %s not found!" % args.make_admin)
        sys.exit(1)

    try:
        admin_role = Role.query.filter(Role.name == "admin").one()
    except NoResultFound:
        admin_role = Role(name="admin")
        db.session.add(admin_role)

    if admin_role in user.roles:
        print("Already part of the admin group.")
    else:
        user.roles.append(admin_role)
        db.session.add(user)

    db.session.commit()

if args.delete:
    user = User.query.filter(User.username == args.delete).one()
    db.session.delete(user)
    db.session.commit()
