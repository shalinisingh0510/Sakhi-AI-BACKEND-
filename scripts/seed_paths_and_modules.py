"""
Seed script to create Learning Paths & Modules and link published LearningContent items.
This connects all articles and videos into structured UI modules so they display on the frontend.
"""
import sys
import io
from pathlib import Path
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.db.session import get_session_factory, init_db
from app.models.learning import (
    Topic, Subtopic, LearningContent,
    LearningPath, LearningModule, LearningModuleItem
)
from sqlalchemy import select, func, delete

def seed():
    init_db(settings.database_url)
    db = get_session_factory()()

    print("=== SEEDING LEARNING PATHS & MODULES ===")

    # Define paths structure for topics
    PATH_CONFIGS = [
        {
            "topic_slug": "periods",
            "title": "Mastering Menstrual Health & Hygiene",
            "slug": "mastering-menstrual-health",
            "description": "A comprehensive guide to understanding your period, managing pain, choosing safe products, and tracking your cycle.",
            "modules": [
                {
                    "title": "Module 1: Understanding Your Cycle",
                    "description": "Learn what happens during your cycle, normal vs irregular periods, and PMS symptoms.",
                    "match_keywords": ["Menstruation", "Period", "Cycle", "Irregular"]
                },
                {
                    "title": "Module 2: Pain Relief & Menstrual Hygiene",
                    "description": "Evidence-based ways to relieve cramps, plus safe practices for pads, tampons, and cups.",
                    "match_keywords": ["Pain", "Dysmenorrhea", "Hygiene", "cramps", "cup", "panty", "Painkillers", "Chocolate"]
                }
            ]
        },
        {
            "topic_slug": "pcos",
            "title": "Living Well with PCOS & PCOD",
            "slug": "living-well-with-pcos",
            "description": "Empower yourself with clear facts on PCOS symptoms, diet, lifestyle management, and fertility options.",
            "modules": [
                {
                    "title": "Module 1: What is PCOS?",
                    "description": "Understanding symptoms, hormonal root causes, and how PCOS differs from PCOD.",
                    "match_keywords": ["What Is PCOS", "Symptoms", "PCOS vs PCOD"]
                },
                {
                    "title": "Module 2: Diet, Lifestyle & Fertility",
                    "description": "Managing PCOS with anti-inflammatory nutrition, exercise, and pre-conception guidance.",
                    "match_keywords": ["Managing", "Fertility", "Diet"]
                }
            ]
        },
        {
            "topic_slug": "nutrition",
            "title": "Essential Nutrition & Hormonal Health for Women",
            "slug": "essential-nutrition-for-women",
            "description": "Nutritional guidance tailored for women's unique needs: iron, calcium, vitamin D, folic acid, and eating for hormonal balance.",
            "modules": [
                {
                    "title": "Module 1: Key Micronutrients",
                    "description": "Why women need specific levels of iron, calcium, vitamin D, and folic acid.",
                    "match_keywords": ["Iron", "Calcium", "Folic", "Vitamin D"]
                },
                {
                    "title": "Module 2: Eating for Hormone Balance & Periods",
                    "description": "What to eat during your period and daily foods that support endocrine balance.",
                    "match_keywords": ["Nutrition During", "Hormonal Balance", "Eating"]
                }
            ]
        },
        {
            "topic_slug": "mental-wellbeing",
            "title": "Nurturing Mental Wellbeing & Stress Relief",
            "slug": "nurturing-mental-wellbeing",
            "description": "Practical tools for stress reduction, emotional wellness, self-care, and healthy sleep habits.",
            "modules": [
                {
                    "title": "Module 1: Stress, Sleep & Your Hormones",
                    "description": "How mind and body interact across your cycle, and daily practices for recovery.",
                    "match_keywords": ["Stress", "Anxiety", "Sleep", "Self-Care", "Burnout"]
                }
            ]
        }
    ]

    for p_cfg in PATH_CONFIGS:
        topic_slug = p_cfg["topic_slug"]
        topic = db.scalar(select(Topic).where(Topic.slug == topic_slug))
        if not topic:
            print(f"[SKIP] Topic '{topic_slug}' not found in DB.")
            continue

        # Check existing path
        path = db.scalar(select(LearningPath).where(LearningPath.slug == p_cfg["slug"]))
        if not path:
            path = LearningPath(
                title=p_cfg["title"],
                slug=p_cfg["slug"],
                description=p_cfg["description"],
                topic_id=topic.id,
                language="en",
                audience="ALL",
                status="PUBLISHED",
                published_at=datetime.utcnow()
            )
            db.add(path)
            db.commit()
            db.refresh(path)
            print(f"[CREATED PATH] '{path.title}' (ID: {path.id})")
        else:
            path.status = "PUBLISHED"
            db.commit()
            print(f"[EXISTING PATH] '{path.title}' (ID: {path.id})")

        # Fetch published content for this topic
        topic_contents = db.execute(
            select(LearningContent).where(
                (LearningContent.topic_id == topic.id) | (LearningContent.topic_id.is_(None)),
                LearningContent.status == 'PUBLISHED'
            )
        ).scalars().all()

        for m_idx, m_cfg in enumerate(p_cfg["modules"]):
            module = db.scalar(
                select(LearningModule).where(
                    LearningModule.path_id == path.id,
                    LearningModule.title == m_cfg["title"]
                )
            )
            if not module:
                module = LearningModule(
                    path_id=path.id,
                    title=m_cfg["title"],
                    description=m_cfg["description"],
                    display_order=m_idx + 1
                )
                db.add(module)
                db.commit()
                db.refresh(module)
                print(f"  [CREATED MODULE] '{module.title}'")

            # Link matching contents
            item_order = 1
            for content in topic_contents:
                matches = any(kw.lower() in content.title.lower() for kw in m_cfg["match_keywords"])
                if matches:
                    existing_item = db.scalar(
                        select(LearningModuleItem).where(
                            LearningModuleItem.module_id == module.id,
                            LearningModuleItem.content_id == content.id
                        )
                    )
                    if not existing_item:
                        item = LearningModuleItem(
                            module_id=module.id,
                            content_id=content.id,
                            display_order=item_order,
                            is_required=True
                        )
                        db.add(item)
                        item_order += 1
                        print(f"    + Linked item: '{content.title}' ({content.language})")

            db.commit()

    print("\n=== SUCCESS: LEARNING PATHS & MODULES SEEDED! ===")

if __name__ == "__main__":
    seed()
