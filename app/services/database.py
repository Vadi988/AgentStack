from typing import List, Optional
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import QueuePool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.config import Environment, settings
from app.core.config.logging import get_logger

from app.models.session import Session as ChatSession
from app.models.user import User

logger = get_logger(__name__)
# ==================================================
# Database Service
# ==================================================
class DatabaseService:
    """
    Singleton service handling all database interactions.
    Manages the connection pool and provides clean CRUD interfaces.
    """
    def __init__(self):
        """
        Initialize the engine with robust pooling settings.
        """
        try:
            # Create the connection URL from settings
            connection_url = (
                f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
                f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
            )
            # Configuring the QueuePool is critical for production.
            # pool_size: How many connections to keep open permanently.
            # max_overflow: How many temporary connections to allow during spikes.
            self.engine = create_engine(
                connection_url,
                pool_pre_ping=True,  # Check if connection is alive before using it
                poolclass=QueuePool,
                pool_size=settings.POSTGRES_POOL_SIZE,
                max_overflow=settings.POSTGRES_MAX_OVERFLOW,
                pool_timeout=30,     # Fail if no connection available after 30s
                pool_recycle=1800,   # Recycle connections every 30 mins to prevent stale sockets
            )
            # Create tables if they don't exist (Code-First migration)
            SQLModel.metadata.create_all(self.engine)
            logger.info("database_initialized", pool_size=settings.POSTGRES_POOL_SIZE)
        
        except SQLAlchemyError as e:
            logger.error("database_initialization_failed", error=str(e))
            # In Dev, we might want to crash. In Prod, maybe we want to retry.
            if settings.ENVIRONMENT != Environment.PRODUCTION:
                raise
    # --------------------------------------------------
    # User Management
    # --------------------------------------------------
    async def create_user(self, email: str, password_hash: str) -> User:
        """Create a new user with hashed password."""
        with Session(self.engine) as session:
            user = User(email=email, hashed_password=password_hash)
            session.add(user)
            session.commit()
            session.refresh(user)
            return user
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Fetch user by email for login flow."""
        with Session(self.engine) as session:
            statement = select(User).where(User.email == email)
            return session.exec(statement).first()
    # --------------------------------------------------
    # Session Management
    # --------------------------------------------------
    async def create_session(self, session_id: str, user_id: int, name: str = "") -> ChatSession:
        """Create a new chat session linked to a user."""
        with Session(self.engine) as session:
            chat_session = ChatSession(id=session_id, user_id=user_id, name=name)
            session.add(chat_session)
            session.commit()
            session.refresh(chat_session)
            return chat_session
    async def get_user_sessions(self, user_id: int) -> List[ChatSession]:
        """List all chat history for a specific user."""
        with Session(self.engine) as session:
            statement = select(ChatSession).where(ChatSession.user_id == user_id).order_by(ChatSession.created_at)
            return session.exec(statement).all()

# Create a global singleton instance
database_service = DatabaseService()