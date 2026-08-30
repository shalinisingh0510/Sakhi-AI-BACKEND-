"""Add Topic/Subtopic taxonomy and extend LearningContent with Phase 1 fields.

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2026-08-30 16:00:00.000000

Creates:
  - topics table (id, name, slug, description, icon, display_order, is_active, created_at, updated_at)
  - subtopics table (id, topic_id FK, name, slug, description, display_order, is_active, created_at, updated_at)

Modifies learning_content (all nullable — fully backward compatible):
  - topic_id (FK to topics.id, SET NULL on delete)
  - subtopic_id (FK to subtopics.id, SET NULL on delete)
  - audience (VARCHAR 10, default 'ALL')
  - featured_rank (INTEGER, nullable)
  - translation_group_id (VARCHAR 36, nullable)

Seeds initial taxonomy:
  - 8 topics with 25+ subtopics

Maps existing category strings to topic_id where possible.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "c3d4e5f6g7h8"
down_revision = "b2c3d4e5f6g7"
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# Taxonomy seed data
# ---------------------------------------------------------------------------

TOPICS = [
    {
        "id": str(uuid.uuid4()),
        "slug": "periods",
        "name": "Periods",
        "description": "Everything about menstrual health, cycle tracking, and period care.",
        "icon": "🌿",
        "display_order": 1,
        "category_mappings": ["menstrual-health", "periods", "menstruation", "period"],
    },
    {
        "id": str(uuid.uuid4()),
        "slug": "pcos",
        "name": "PCOS",
        "description": "Understanding Polycystic Ovary Syndrome — symptoms, lifestyle, and nutrition.",
        "icon": "🩺",
        "display_order": 2,
        "category_mappings": ["pcos", "pcod", "polycystic-ovary"],
    },
    {
        "id": str(uuid.uuid4()),
        "slug": "pregnancy",
        "name": "Pregnancy",
        "description": "Pregnancy basics, nutrition, and prenatal care.",
        "icon": "🤰",
        "display_order": 3,
        "category_mappings": ["pregnancy", "prenatal", "maternity"],
    },
    {
        "id": str(uuid.uuid4()),
        "slug": "nutrition",
        "name": "Nutrition",
        "description": "Healthy eating, vitamins, minerals, and general nutrition guidance.",
        "icon": "🥗",
        "display_order": 4,
        "category_mappings": ["nutrition", "nutrition-health", "diet", "food", "eating"],
    },
    {
        "id": str(uuid.uuid4()),
        "slug": "mental-wellbeing",
        "name": "Mental Wellbeing",
        "description": "Stress, emotional wellbeing, sleep, and self-care.",
        "icon": "🧠",
        "display_order": 5,
        "category_mappings": ["mental-wellbeing", "mental-health", "mental", "stress", "anxiety"],
    },
    {
        "id": str(uuid.uuid4()),
        "slug": "reproductive-health",
        "name": "Reproductive Health",
        "description": "General reproductive health, sexual health, and fertility.",
        "icon": "💫",
        "display_order": 6,
        "category_mappings": ["reproductive-health", "sexual-health", "fertility", "safety-consent"],
    },
    {
        "id": str(uuid.uuid4()),
        "slug": "fitness",
        "name": "Fitness",
        "description": "Exercise, movement, and physical wellness.",
        "icon": "🏃‍♀️",
        "display_order": 7,
        "category_mappings": ["fitness", "exercise", "workout", "movement", "yoga"],
    },
    {
        "id": str(uuid.uuid4()),
        "slug": "puberty",
        "name": "Puberty & Growing Up",
        "description": "Puberty basics, personal hygiene, and growing up.",
        "icon": "🌸",
        "display_order": 8,
        "category_mappings": ["puberty-basics", "puberty", "personal-hygiene", "hygiene"],
    },
]

# Map slug → topic_id for subtopic creation
TOPIC_BY_SLUG: dict[str, str] = {}

SUBTOPICS_BY_TOPIC: dict[str, list[dict]] = {
    "periods": [
        {"slug": "basics", "name": "Basics", "display_order": 1},
        {"slug": "menstrual-hygiene", "name": "Menstrual Hygiene", "display_order": 2},
        {"slug": "pms", "name": "PMS", "display_order": 3},
        {"slug": "period-pain", "name": "Period Pain", "display_order": 4},
    ],
    "pcos": [
        {"slug": "basics", "name": "Basics", "display_order": 1},
        {"slug": "symptoms", "name": "Symptoms", "display_order": 2},
        {"slug": "lifestyle", "name": "Lifestyle", "display_order": 3},
        {"slug": "nutrition", "name": "Nutrition & PCOS", "display_order": 4},
    ],
    "pregnancy": [
        {"slug": "basics", "name": "Basics", "display_order": 1},
        {"slug": "nutrition", "name": "Nutrition in Pregnancy", "display_order": 2},
        {"slug": "pregnancy-care", "name": "Pregnancy Care", "display_order": 3},
    ],
    "nutrition": [
        {"slug": "healthy-eating", "name": "Healthy Eating", "display_order": 1},
        {"slug": "vitamins-minerals", "name": "Vitamins & Minerals", "display_order": 2},
        {"slug": "iron", "name": "Iron & Anaemia", "display_order": 3},
        {"slug": "general-nutrition", "name": "General Nutrition", "display_order": 4},
    ],
    "mental-wellbeing": [
        {"slug": "stress", "name": "Stress", "display_order": 1},
        {"slug": "emotional-wellbeing", "name": "Emotional Wellbeing", "display_order": 2},
        {"slug": "sleep", "name": "Sleep", "display_order": 3},
        {"slug": "self-care", "name": "Self Care", "display_order": 4},
    ],
    "reproductive-health": [
        {"slug": "general", "name": "General Reproductive Health", "display_order": 1},
        {"slug": "sexual-health", "name": "Sexual Health", "display_order": 2},
        {"slug": "fertility", "name": "Fertility", "display_order": 3},
    ],
    "fitness": [
        {"slug": "exercise", "name": "Exercise", "display_order": 1},
        {"slug": "movement", "name": "Movement & Yoga", "display_order": 2},
        {"slug": "wellness", "name": "Wellness", "display_order": 3},
    ],
    "puberty": [
        {"slug": "basics", "name": "Puberty Basics", "display_order": 1},
        {"slug": "personal-hygiene", "name": "Personal Hygiene", "display_order": 2},
    ],
}


def upgrade() -> None:
    now = datetime.utcnow()

    # ----- Create topics table -----
    op.create_table(
        "topics",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("icon", sa.String(10), nullable=True),
        sa.Column("display_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_topics_slug", "topics", ["slug"])
    op.create_index("ix_topics_is_active", "topics", ["is_active"])

    # ----- Create subtopics table -----
    op.create_table(
        "subtopics",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("topic_id", sa.String(36), sa.ForeignKey("topics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("display_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("topic_id", "slug", name="uq_subtopic_topic_slug"),
    )
    op.create_index("ix_subtopics_topic_id", "subtopics", ["topic_id"])
    op.create_index("ix_subtopics_slug", "subtopics", ["slug"])

    # ----- Add columns to learning_content -----
    op.add_column("learning_content", sa.Column(
        "topic_id", sa.String(36),
        sa.ForeignKey("topics.id", ondelete="SET NULL"),
        nullable=True
    ))
    op.add_column("learning_content", sa.Column(
        "subtopic_id", sa.String(36),
        sa.ForeignKey("subtopics.id", ondelete="SET NULL"),
        nullable=True
    ))
    op.add_column("learning_content", sa.Column(
        "audience", sa.String(10), nullable=False, server_default="ALL"
    ))
    op.add_column("learning_content", sa.Column(
        "featured_rank", sa.Integer, nullable=True
    ))
    op.add_column("learning_content", sa.Column(
        "translation_group_id", sa.String(36), nullable=True
    ))

    # Create indexes for new columns
    op.create_index("ix_learning_content_topic_id", "learning_content", ["topic_id"])
    op.create_index("ix_learning_content_subtopic_id", "learning_content", ["subtopic_id"])
    op.create_index("ix_learning_content_language", "learning_content", ["language"])
    op.create_index("ix_learning_content_audience", "learning_content", ["audience"])
    op.create_index("ix_learning_content_published_at", "learning_content", ["published_at"])

    # ----- Seed taxonomy data -----
    conn = op.get_bind()

    # Insert topics and collect id mapping
    topic_id_map: dict[str, str] = {}
    topic_category_map: dict[str, str] = {}  # category_value → topic_id

    for topic_data in TOPICS:
        topic_id = topic_data["id"]
        topic_slug = topic_data["slug"]
        topic_id_map[topic_slug] = topic_id

        conn.execute(
            sa.text(
                "INSERT INTO topics (id, name, slug, description, icon, display_order, is_active, created_at, updated_at) "
                "VALUES (:id, :name, :slug, :description, :icon, :display_order, :is_active, :created_at, :updated_at)"
            ),
            {
                "id": topic_id,
                "name": topic_data["name"],
                "slug": topic_slug,
                "description": topic_data.get("description"),
                "icon": topic_data.get("icon"),
                "display_order": topic_data["display_order"],
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            }
        )

        # Register category → topic mappings
        for cat in topic_data.get("category_mappings", []):
            topic_category_map[cat] = topic_id

    # Insert subtopics
    for topic_slug, subtopics in SUBTOPICS_BY_TOPIC.items():
        topic_id = topic_id_map.get(topic_slug)
        if not topic_id:
            continue
        for sub in subtopics:
            conn.execute(
                sa.text(
                    "INSERT INTO subtopics (id, topic_id, name, slug, display_order, is_active, created_at, updated_at) "
                    "VALUES (:id, :topic_id, :name, :slug, :display_order, :is_active, :created_at, :updated_at)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "topic_id": topic_id,
                    "name": sub["name"],
                    "slug": sub["slug"],
                    "display_order": sub["display_order"],
                    "is_active": True,
                    "created_at": now,
                    "updated_at": now,
                }
            )

    # ----- Map existing content categories → topic_id -----
    for category_value, topic_id in topic_category_map.items():
        conn.execute(
            sa.text(
                "UPDATE learning_content SET topic_id = :topic_id "
                "WHERE LOWER(category) = LOWER(:category) AND topic_id IS NULL"
            ),
            {"topic_id": topic_id, "category": category_value}
        )


def downgrade() -> None:
    # Remove indexes
    op.drop_index("ix_learning_content_published_at", "learning_content")
    op.drop_index("ix_learning_content_audience", "learning_content")
    op.drop_index("ix_learning_content_language", "learning_content")
    op.drop_index("ix_learning_content_subtopic_id", "learning_content")
    op.drop_index("ix_learning_content_topic_id", "learning_content")

    # Remove columns from learning_content
    op.drop_column("learning_content", "translation_group_id")
    op.drop_column("learning_content", "featured_rank")
    op.drop_column("learning_content", "audience")
    op.drop_column("learning_content", "subtopic_id")
    op.drop_column("learning_content", "topic_id")

    # Drop tables
    op.drop_index("ix_subtopics_slug", "subtopics")
    op.drop_index("ix_subtopics_topic_id", "subtopics")
    op.drop_table("subtopics")

    op.drop_index("ix_topics_is_active", "topics")
    op.drop_index("ix_topics_slug", "topics")
    op.drop_table("topics")
