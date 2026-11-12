"""
Database Connection
PostgreSQL mit SQLAlchemy Async
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import get_settings

settings = get_settings()

# Async Engine erstellen
engine = create_async_engine(
    settings.DATABASE_URL,
    **settings.database_pool_settings,
    echo=settings.DEBUG,
)

# Async Session Maker
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Declarative Base für Models
Base = declarative_base()


async def get_db() -> AsyncSession:
    """Dependency für DB-Session in FastAPI Endpoints"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Erstellt alle Tabellen (Migrationen werden separat durchgeführt)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
