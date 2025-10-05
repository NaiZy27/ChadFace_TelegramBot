from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, Boolean, BigInteger, String, select, func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from dotenv import load_dotenv
import os

load_dotenv()

DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_NAME = os.getenv('DB_NAME')

DATABASE_URL = f'mysql+asyncmy://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}?charset=utf8mb4'


class Base(DeclarativeBase): 
    pass


class User(Base): 
    __tablename__ = 'users'
    id = Column(BigInteger, primary_key=True, index=True)
    balance = Column(Integer)
    unlimit = Column(Boolean, default=False)
    referal = Column(String(100), nullable=True)
    income = Column(Integer)


engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=300,
)


async def create_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def find_user(id):
    async with AsyncSession(bind=engine) as db:
        result = await db.get(User, id)
    return result


async def create_user(id):
    async with AsyncSession(bind=engine) as db:
        user = User(id=id, balance=0, unlimit=False, income=0)
        db.add(user)
        await db.commit()


async def adjust_referal(id, ref_code):
    async with AsyncSession(bind=engine) as db:
        user = await db.get(User, id)
        if user:
            user.referal = ref_code
            await db.commit()


async def count_referal(ref_code):
    async with AsyncSession(bind=engine) as db:
        result = await db.execute(
            select(
                func.count(User.id),
                func.sum(User.income)
            ).filter(User.referal == ref_code)
        )
        count, total_income = result.fetchone()
        total_income = total_income
        return (count, total_income)


async def charge_off_balance(id):
    async with AsyncSession(bind=engine) as db:
        user = await db.get(User, id)
        if user:
            if not user.unlimit:
                user.balance -= 1
                await db.commit()


async def top_up_balance(id, amount, value):
    async with AsyncSession(bind=engine) as db:
        user = await db.get(User, id)
        if user:
            user.income += value
            if amount == 0:
                user.unlimit = True
            else:
                user.balance += amount
                await db.commit()
