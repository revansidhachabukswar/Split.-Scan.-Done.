"""
One-off CLI to create an admin user (for accessing /api/admin/* rule-management
endpoints). There is no public admin-registration endpoint by design — run this
on the server / in the container instead.

Usage:
    python create_admin.py --mobile 9000000000 --password "StrongPass123" --name "Admin"
"""
import argparse

from app.auth import hash_password
from app.database import Base, SessionLocal, engine
from app.models import RoleEnum, User


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mobile", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--name", default="Admin")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.mobile_number == args.mobile).first()
        if existing:
            existing.role = RoleEnum.admin
            existing.password_hash = hash_password(args.password)
            db.commit()
            print(f"Updated existing user {args.mobile} to admin role.")
            return

        user = User(
            full_name=args.name,
            mobile_number=args.mobile,
            password_hash=hash_password(args.password),
            role=RoleEnum.admin,
        )
        db.add(user)
        db.commit()
        print(f"Admin user created: {args.mobile}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
