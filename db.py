from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine


DATABASE_NAME = 'bot.db'


class Base(DeclarativeBase): 
    pass 


class User(Base): 
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    balance = Column(Integer)


engine = create_async_engine(f'sqlite+aiosqlite:///{DATABASE_NAME}')


async def create_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def find_user(id):
    async with AsyncSession(bind=engine) as db:
        result = await db.get(User, id)
    return result


async def create_user(id):
    async with AsyncSession(bind=engine) as db:
        user = User(id=id, balance=0)
        db.add(user)
        await db.commit()


async def charge_off_balance(id):
    async with AsyncSession(bind=engine) as db:
        user = await db.get(User, id)
        user.balance -= 1
        await db.commit()


async def top_up_balance(id, amount):
    async with AsyncSession(bind=engine) as db:
        user = await db.get(User, id)
        user.balance += amount
        await db.commit()
