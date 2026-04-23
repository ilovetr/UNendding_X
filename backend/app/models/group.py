"""Group model."""
import uuid
import secrets
import hashlib
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
import enum

from app.database import Base
from app.db_types import JsonField, UUIDField


class Privacy(str, enum.Enum):
    """Group privacy enum."""
    PUBLIC = "public"
    PRIVATE = "private"


class Category(str, enum.Enum):
    """Group category enum for marketplace filtering."""
    TECH = "tech"           # 技术开发
    AI = "ai"               # AI人工智能
    PRODUCT = "product"     # 产品设计
    MARKETING = "marketing"  # 市场营销
    EDUCATION = "education"  # 教育培训
    ENTERTAINMENT = "entertainment"  # 娱乐休闲
    FINANCE = "finance"      # 金融投资
    HEALTHCARE = "healthcare"  # 医疗健康
    GAMING = "gaming"       # 游戏电竞
    SOCIAL = "social"        # 社交聊天
    NEWS = "news"           # 新闻资讯
    OTHER = "other"         # 其他


# Category display names (zh-CN)
CATEGORY_LABELS: dict[str, str] = {
    "tech": "技术开发",
    "ai": "AI人工智能",
    "product": "产品设计",
    "marketing": "市场营销",
    "education": "教育培训",
    "entertainment": "娱乐休闲",
    "finance": "金融投资",
    "healthcare": "医疗健康",
    "gaming": "游戏电竞",
    "social": "社交聊天",
    "news": "新闻资讯",
    "other": "其他",
}

# Category display names (en-US)
CATEGORY_LABELS_EN: dict[str, str] = {
    "tech": "Tech & Development",
    "ai": "AI & Artificial Intelligence",
    "product": "Product Design",
    "marketing": "Marketing",
    "education": "Education & Training",
    "entertainment": "Entertainment",
    "finance": "Finance & Investment",
    "healthcare": "Healthcare",
    "gaming": "Gaming",
    "social": "Social",
    "news": "News",
    "other": "Other",
}


def hash_password(password: str) -> str:
    """Hash a password using SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash."""
    return hashlib.sha256(password.encode()).hexdigest() == password_hash


def generate_invite_code():
    """Generate a 6-character invite code."""
    return secrets.token_hex(3).upper()


class Group(Base):
    """Group model representing an interest group."""

    __tablename__ = "groups"

    id = Column(UUIDField, primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    privacy = Column(SQLEnum(Privacy), default=Privacy.PUBLIC, nullable=False)
    category = Column(SQLEnum(Category), default=Category.OTHER, nullable=False)
    password_hash = Column(String(64), nullable=True)  # only for private groups
    owner_id = Column(UUIDField, ForeignKey("agents.id"), nullable=False)
    invite_code = Column(String(6), unique=True, default=generate_invite_code, nullable=False)
    config = Column(JsonField, nullable=True, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("Agent", back_populates="owned_groups")
    members = relationship("GroupMember", back_populates="group", cascade="all, delete-orphan")
    abilities = relationship("Ability", back_populates="group", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Group(id={self.id}, name={self.name}, privacy={self.privacy})>"


class GroupMember(Base):
    """Group member association model."""

    __tablename__ = "group_members"

    id = Column(UUIDField, primary_key=True, default=uuid.uuid4)
    group_id = Column(UUIDField, ForeignKey("groups.id"), nullable=False)
    agent_id = Column(UUIDField, ForeignKey("agents.id"), nullable=False)
    role = Column(String(50), default="member", nullable=False)  # admin, member, guest
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    group = relationship("Group", back_populates="members")
    agent = relationship("Agent", back_populates="group_memberships")

    def __repr__(self):
        return f"<GroupMember(group_id={self.group_id}, agent_id={self.agent_id}, role={self.role})>"
