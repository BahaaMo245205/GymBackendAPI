from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean,Integer
from sqlalchemy.orm import DeclarativeBase, relationship
from collections.abc import AsyncGenerator
import os 
import uuid
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


class Base(DeclarativeBase):
    pass


class Users(Base):
    __tablename__ = "users"

    UserID = Column(String(60), nullable=False, unique=True, default=lambda:uuid.uuid4().hex, primary_key=True)
    UserName = Column(String(45), nullable=False)
    email = Column(String(45), nullable=False, unique=True)
    password = Column(String(160), nullable=False)

    profile = relationship("UserProfile", back_populates="author", cascade="all, delete-orphan", uselist=False)

    def __init__(self, username, email, password):
        self.UserName = username
        self.email = email
        self.password = password

class UserProfile(Base):
    __tablename__ = "user_profiles"

    UserProfileID = Column(String(60), nullable=False, unique=True, default=lambda:uuid.uuid4().hex, primary_key=True)
    UserID = Column(String(60), ForeignKey("users.UserID"), nullable=False, unique=True)
    Phone = Column(String(45), nullable=False)
    Address = Column(Text, nullable=False)
    gender = Column(String(45), nullable=False)
    Role = Column(String(45), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    author = relationship("Users", back_populates="profile")

    def __init__(self, userid, phone, address, gender, role, is_active=True):
        self.UserID = userid
        self.Phone = phone
        self.Address = address
        self.gender = gender
        self.Role = role
        self.is_active = is_active

class Memberships(Base):
    __tablename__ = "memberships"
    
    MembershipsID = Column(String(60), primary_key=True, unique=True, nullable=False, default=lambda:uuid.uuid4().hex)
    Price = Column(Integer, nullable=False) 
    duration_months = Column(Integer, nullable=False) 
    walk_machine = Column(Boolean, nullable=False, default=False)
    deduct = Column(Integer, nullable=False, default=0) 
    is_active = Column(Boolean, nullable=False, default=True)
    description = Column(Text, nullable=True)
    
    def __init__(self, price, duration_months, walk_machine, deduct, is_active, description):
        self.Price = price
        self.duration_months = duration_months
        self.walk_machine = walk_machine
        self.deduct = deduct
        self.is_active = is_active
        self.description = description

class Classes(Base): 
    __tablename__ = "classes"
    
    ClassesID = Column(String(60), primary_key=True, unique=True, nullable=False, default=lambda:uuid.uuid4().hex)
    ClassName = Column(String(60), nullable=False)
    TypeClass = Column(String(60), nullable=False)
    Price = Column(Integer, nullable=False)
    Date = Column(DateTime, nullable=False)
    Start_time = Column(String(60), nullable=False)
    End_time = Column(String(60), nullable=False)
    Trainer_id = Column(String(60), ForeignKey("users.UserID"), nullable=False) 
    Is_active = Column(Boolean, nullable=False, default=True)
    
    def __init__(self, classname, typeclass, price, date, starttime, endtime, trainerid, is_active=True):
        self.ClassName = classname
        self.TypeClass = typeclass
        self.Price = price
        self.Date = date
        self.Start_time = starttime
        self.End_time = endtime
        self.Trainer_id = trainerid
        self.Is_active = is_active

class Subscriptions(Base):
    __tablename__ = "subscriptions"
    
    SubscriptionsID = Column(String(60), primary_key=True, unique=True, nullable=False, default=lambda:uuid.uuid4().hex)
    UserID = Column(String(60), ForeignKey("users.UserID"), nullable=False)
    membershipsID = Column(String(60), ForeignKey("memberships.MembershipsID"), nullable=False)
    StartDate = Column(DateTime, nullable=False)
    EndDate = Column(DateTime, nullable=False)
    status = Column(String(45), nullable=False, default="active")
    
    def __init__(self, userid, membershipsid, startdate, enddate, status="active"):
        self.UserID = userid
        self.membershipsID = membershipsid
        self.StartDate = startdate
        self.EndDate = enddate
        self.status = status

class Payments(Base): 
    __tablename__ = "payments"
    
    PaymentsID = Column(String(60), primary_key=True, unique=True, nullable=False, default=lambda:uuid.uuid4().hex)
    Subscription_id = Column(String(60), ForeignKey("subscriptions.SubscriptionsID"), nullable=False)
    Date = Column(DateTime, nullable=False)
    Price = Column(Integer, nullable=False)
    Typepay = Column(String(45), nullable=False) 
    
    def __init__(self, subscription_id, date, price, typepay):
        self.Subscription_id = subscription_id
        self.Date = date
        self.Price = price
        self.Typepay = typepay

class Booking(Base):
    __tablename__ = "booking"

    BookingID = Column(String(60), primary_key=True, unique=True, nullable=False, default=lambda:uuid.uuid4().hex)
    ClassID = Column(String(60), ForeignKey("classes.ClassesID"), nullable=False)
    UserID = Column(String(60), ForeignKey("users.UserID"), nullable=False)
    Is_active = Column(Boolean, nullable=False, default=True)
    Date = Column(DateTime, nullable=False)
    
    def __init__(self, classid, userid, date, is_active=True):
        self.ClassID = classid
        self.UserID = userid
        self.Is_active = is_active
        self.Date = date

engin = create_async_engine(DATABASE_URL)
async_session_maker = async_sessionmaker(engin, expire_on_commit=False)


async def create_db_and_table():
    async with engin.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_async_session()-> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
