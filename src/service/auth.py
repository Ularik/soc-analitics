from fastapi import HTTPException
from datetime import timezone, datetime, timedelta
import bcrypt
import jwt
from src.config import settings
from concurrent.futures import ThreadPoolExecutor
import asyncio

class AuthService:
    executor = ThreadPoolExecutor(max_workers=4)

    async def start_in_another_loop(self, func, *args):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.executor, func, *args)

    @staticmethod
    async def create_access_token(data: dict) -> str:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt

    async def hash_pswd(self, password: str) -> bytes:
        is_valid = await self.start_in_another_loop(
            bcrypt.hashpw,
            password.encode('utf-8'),
            bcrypt.gensalt()
        )
        return is_valid

    async def verify_password(self, plain_password, hashed_password):
        return await self.start_in_another_loop(
            bcrypt.checkpw,
            plain_password.encode('utf-8'),
            hashed_password
        )

    @staticmethod
    async def encode_token(token) -> dict:
        try:
            user = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            return user
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Сессия истекла, войдите снова")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Некорректный токен доступа")
