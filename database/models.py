import bcrypt
import logging
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship, declarative_base
from config.settings import DATABASE_URL

Base = declarative_base()
logger_models = logging.getLogger(__name__)

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    queries = relationship("QueryHistory", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        self.password_hash = hashed_pw.decode('utf-8')

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"

class QueryHistory(Base):
    __tablename__ = 'query_history'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    query_text = Column(String(500), nullable=False, index=True)
    timestamp = Column(String(50), nullable=False)
    user = relationship("User", back_populates="queries")

    def __repr__(self):
        return f"<QueryHistory(id={self.id}, query='{self.query_text[:30]}...')>"

class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    marketplace = Column(String(50), nullable=False, index=True)
    price = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    image_url = Column(String(500), nullable=True)
    delivery_time = Column(String(100), nullable=True)
    rating = Column(Float, default=0.0)
    reviews_count = Column(Integer, default=0)
    product_url = Column(String(500), nullable=True)

    def __repr__(self):
        return f"<Product(name='{self.name[:30]}...')>"

engine = create_engine(DATABASE_URL)

def create_db_and_tables() -> None:
    try:
        Base.metadata.create_all(bind=engine)
        logger_models.info("DB tables checked/created (models.py).")
    except Exception as e:
        logger_models.critical(f"DB creation error: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    create_db_and_tables()