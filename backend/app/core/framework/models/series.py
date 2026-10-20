from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class Series(Base):
    __tablename__ = "series"
    
    name: Mapped[str] = mapped_column(String(50), primary_key=True)
    current: Mapped[int] = mapped_column(Integer, default=0)
