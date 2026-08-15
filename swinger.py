import copy
import time
import json
import os
from sqlalchemy import *
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.orm import *
from sqlalchemy.orm.attributes import flag_modified
from psycopg2 import *


from datetime import datetime

engine = create_engine("postgresql://postgres:root@localhost/swingerinchik", echo=False)
Base = declarative_base()

class State(Base):
    __tablename__ = "state"
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    status: Mapped[str] = mapped_column(String(), nullable=False)
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

class User(Base):
    __tablename__ = "users"  # Имя таблицы в БД
    
    # Поля таблицы
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    persons: Mapped[dict] = mapped_column(JSON, nullable=False) # Имена и возраста
    type: Mapped[str] = mapped_column(String(), nullable=False) # тип аккаунта Мужчина/Женщина/Пара
    want_type: Mapped[str] = mapped_column(String(), nullable=False) # тип аккаунта с которыми мы хотим знакомиться Мужчина/Женщина/Пара
    premium: Mapped[bool] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

class Likes(Base):
    __tablename__ = "likes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    superlike: Mapped[int]= mapped_column(String(), nullable=False)
    by: Mapped[int]= mapped_column(BigInteger, index=True, nullable=False)  # От кого
    to: Mapped[int]= mapped_column(BigInteger, index=True, nullable=False)  # Кому
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

class SuperLikes(Base):
    __tablename__ = "superlikes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    text: Mapped[str] = mapped_column(String(), nullable=False)
    photo: Mapped[str] = mapped_column(String(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

class Matches(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    like: Mapped[int] = mapped_column(Integer, nullable=False)
    first: Mapped[int] = mapped_column(BigInteger, nullable=False)
    two: Mapped[int] = mapped_column(BigInteger, nullable=False)

Base.metadata.create_all(engine)
print("✅ Таблицы созданы!")

Session = sessionmaker(bind=engine)
session = Session()

class Swinger:

    @staticmethod
    def checkAccount(user_id):
        user = session.query(User).filter(User.id == user_id).one_or_none()

        if user is not None:
            return True
        else:
            return False

    @staticmethod  
    def getUserState(user_id):
        state = session.query(State).filter(State.user_id == user_id).one_or_none()
        return state

    @staticmethod
    def setUserState(user_id, status , data={}):
        payload = copy.deepcopy(data)
        state = session.query(State).filter(State.user_id == user_id).one_or_none()
        
        if (state is not None):
            state.status = status
            if (data != {}):
                state.data = payload
            flag_modified(state, 'data')
        else: 
            new_state = State(user_id=user_id, status=status, data=payload)
            session.add(new_state)
        session.commit()
        session.expire_all()
        return status
    
    @staticmethod
    def createAccount(user_id, persons, type , want_type="Без разницы", premium=False): 
        new_user = User(id=user_id, persons=persons, type=type, want_type=want_type, premium=premium)
        session.add(new_user)
        session.commit()

        return new_user


