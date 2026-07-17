import asyncio
import getpass
import sys
from pathlib import Path

from sqlalchemy import select

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.core.security import hash_password

async def create_superuser():
    print("Crear superusuario/admin")
    print("------------------------")

    email = input("Email: ").strip().lower()
    username = input("Username: ").strip()
    first_name = input("First name: ").strip()
    last_name = input("Last name: ").strip()
    password = getpass.getpass("Password: ")

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.email == email)
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            print("Ya existe un usuario con ese email.")

            if existing_user.role != "admin":
                answer = input("¿Quieres convertirlo en admin? (s/n): ").strip().lower()

                if answer == "s":
                    existing_user.role = "admin"
                    await session.commit()
                    print("Usuario actualizado a admin.")
                else:
                    print("No se hizo ningún cambio.")

            return

        user = User(
            email=email,
            username=username,
            first_name=first_name,
            last_name=last_name,
            hashed_password=hash_password(password),
            role="admin",
            is_active=True,
            is_verified=True,
        )

        session.add(user)
        await session.commit()

        print("Superusuario creado correctamente.")


if __name__ == "__main__":
    asyncio.run(create_superuser())