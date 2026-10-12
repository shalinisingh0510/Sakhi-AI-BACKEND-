"""
Populate Caregiver topic, subtopics, and comprehensive learning modules.
"""
from uuid import uuid4
from datetime import datetime
from app.core.config import settings
from app.db.session import init_db, get_session_factory
from app.models.learning import Topic, Subtopic, LearningContent

CAREGIVER_TOPIC_DATA = {
    "name": "Caregivers & Mentors",
    "slug": "caregivers",
    "icon": "👩‍👧",
    "description": "Pediatrician-backed scripts, age-banded puberty roadmaps, and compassionate guidance for parents, teachers, and guardians.",
    "display_order": 9,
    "is_active": True,
}

CAREGIVER_SUBTOPICS = [
    {
        "name": "Early Puberty (Ages 9–11)",
        "slug": "ages-9-11",
        "description": "Preparing before menarche: body changes, breast budding, and gentle baseline talks.",
        "display_order": 1,
    },
    {
        "name": "First Period & Hygiene (Ages 12–14)",
        "slug": "first-period-hygiene",
        "description": "Managing the first flow, packing school kits, choosing starter products, and hygiene.",
        "display_order": 2,
    },
    {
        "name": "Cycle Literacy & Emotions (Ages 15–18)",
        "slug": "cycle-literacy",
        "description": "Hormonal shifts, mood empathy, irregular cycles, and teenage reproductive health.",
        "display_order": 3,
    },
    {
        "name": "Fathers & Male Mentors Guide",
        "slug": "male-mentors",
        "description": "Practical, awkwardness-free guidance for dads, uncles, and male teachers.",
        "display_order": 4,
    },
    {
        "name": "Navigating Cultural Taboos & Myths",
        "slug": "cultural-taboos",
        "description": "Bridging generational traditions, domestic rules, and affirming bodily autonomy.",
        "display_order": 5,
    },
]

CAREGIVER_ARTICLES = [
    {
        "title": "Empowering the Next Generation: A Caregiver's Guide to Puberty & Period Literacy",
        "subtopic_slug": "ages-9-11",
        "content_type": "ARTICLE",
        "duration_minutes": 7,
        "thumbnail_url": "https://images.unsplash.com/photo-1544717305-2782549b5136?auto=format&fit=crop&w=900&q=80",
        "description": "Practical conversation starters, age-appropriate guidance, and stigma-free advice for parents navigating growing years.",
        "body": [
            {
                "type": "heading",
                "content": "Why Proactive Conversations Change Everything"
            },
            {
                "type": "paragraph",
                "content": "Research published in the Journal of Adolescent Health reveals that girls who learn about menstruation prior to menarche experience significantly lower panic, shame, and school absenteeism compared to those who discover it on the day of their first period."
            },
            {
                "type": "callout",
                "title": "Pediatric Rule of Thumb",
                "content": "Talk before the blood arrives. Starting conversations around age 9 normalizes bodily autonomy and ensures school rumors do not distort biology into fear."
            },
            {
                "type": "heading",
                "content": "The Three Pillars of Compassionate Mentorship"
            },
            {
                "type": "list",
                "items": [
                    "Language of Biology, Not Morality: Use correct anatomical terms (vulva, uterus, endometrium) without whispering.",
                    "Normalize Discomfort: Acknowledge cramps and emotional swings as biological responses, never dramatization.",
                    "Practical Preparedness: Practice putting a pad on underwear in the bedroom before an emergency happens at school."
                ]
            }
        ]
    },
    {
        "title": "Explaining Menstrual Blood Without Fear: The Anatomy of a Gentle Talk",
        "subtopic_slug": "ages-9-11",
        "content_type": "ARTICLE",
        "duration_minutes": 5,
        "thumbnail_url": "https://images.unsplash.com/photo-1509062522246-3755977927d7?auto=format&fit=crop&w=900&q=80",
        "description": "De-linking bleeding from trauma: How to explain why the body bleeds every month in words that calm a young nervous system.",
        "body": [
            {
                "type": "heading",
                "content": "Breaking the Blood-Trauma Association"
            },
            {
                "type": "paragraph",
                "content": "Since toddlerhood, children associate bleeding with scrapes, cuts, pain, and hospitals. When menstruation arrives with no visible wound, young brains default to catastrophe: 'Am I bleeding to death?'"
            },
            {
                "type": "callout",
                "title": "The Golden Script",
                "content": "Whenever you see blood from a scraped knee, it means you got hurt. But the blood during a period is completely different. It is a sign of immense health. Your uterus built a warm, nutrient-rich nest. When it isn't needed, your body gently washes it away to start fresh."
            },
            {
                "type": "paragraph",
                "content": "By describing menstrual blood as self-cleaning tissue renewal rather than a wound, children feel reassured that their body is functioning brilliantly."
            }
        ]
    },
    {
        "title": "Packing the First Period School Kit: Tactical Checklist & Locker Setup",
        "subtopic_slug": "first-period-hygiene",
        "content_type": "ARTICLE",
        "duration_minutes": 6,
        "thumbnail_url": "https://images.unsplash.com/photo-1588072432836-e10032774350?auto=format&fit=crop&w=900&q=80",
        "description": "How to assemble a discrete, confidence-boosting school pouch together so your child feels in complete control in class.",
        "body": [
            {
                "type": "heading",
                "content": "The Power of an Emergency Pouch"
            },
            {
                "type": "paragraph",
                "content": "Fear of leaking onto school uniforms is one of the highest reported adolescent stressors. Having a prepared kit transforms vulnerability into readiness."
            },
            {
                "type": "list",
                "items": [
                    "2 regular cotton sanitary pads with wings",
                    "1 spare pair of cotton underwear packed in a discrete zip pouch",
                    "Unscented gentle soothing wipes",
                    "A dark cardigan or sweater to tie around the waist if an unexpected stain occurs",
                    "A comforting handwritten index card with emergency contacts and a note: 'You are safe, call me anytime.'"
                ]
            }
        ]
    },
    {
        "title": "Fathers & Male Guardians: How to Support Puberty Without Awkwardness",
        "subtopic_slug": "male-mentors",
        "content_type": "ARTICLE",
        "duration_minutes": 6,
        "thumbnail_url": "https://images.unsplash.com/photo-1492562080023-ab3db95bfbce?auto=format&fit=crop&w=900&q=80",
        "description": "A straightforward guide for dads, uncles, and male mentors to normalize pads, cramps, and emotional safety at home.",
        "body": [
            {
                "type": "heading",
                "content": "Fatherhood in the Menstrual Conversation"
            },
            {
                "type": "paragraph",
                "content": "Dads often retreat when daughters hit puberty, believing it is strictly a mother's domain. When a father withdraws, children can internalize that periods are something dirty to hide from men."
            },
            {
                "type": "callout",
                "title": "Three Actionable Habits for Dads",
                "content": "1. Buy sanitary pads without making a joke at the store checkout.\n2. Keep a hot water bottle ready on crampy days without interrogating.\n3. Never use PMS as an insult during an argument."
            }
        ]
    },
    {
        "title": "Navigating Cultural Taboos: Bridging Modern Health and Elder Traditions",
        "subtopic_slug": "cultural-taboos",
        "content_type": "ARTICLE",
        "duration_minutes": 7,
        "thumbnail_url": "https://images.unsplash.com/photo-1517486808906-6ca8b3f04846?auto=format&fit=crop&w=900&q=80",
        "description": "How to handle generational domestic exclusions, pickle myths, and religious rules while validating a young girl's dignity.",
        "body": [
            {
                "type": "heading",
                "content": "Understanding the Origin of Traditions"
            },
            {
                "type": "paragraph",
                "content": "In previous eras before modern plumbing, hygiene products, and pain medication, traditional practices of rest during menstruation protected women from grueling agricultural and household labor."
            },
            {
                "type": "paragraph",
                "content": "Over generations, this protective rest became distorted into notions of 'impurity' or 'uncleanliness'. When daughters question these rules, caregivers must clarify: 'The ritual was created to honor rest, but you are never impure or dirty.'"
            }
        ]
    },
    {
        "title": "What If She Starts Before Age 10? Recognizing Early Puberty (Precocious Puberty)",
        "subtopic_slug": "ages-9-11",
        "content_type": "ARTICLE",
        "duration_minutes": 6,
        "thumbnail_url": "https://images.unsplash.com/photo-1579684385127-1ef15d508118?auto=format&fit=crop&w=900&q=80",
        "description": "Pediatric benchmarks: distinguishing normal secular trend from central precocious puberty and when to consult an endocrinologist.",
        "body": [
            {
                "type": "heading",
                "content": "When Does Puberty Usually Begin?"
            },
            {
                "type": "paragraph",
                "content": "While average menarche occurs between ages 11.5 and 13, onset of breast development before age 8 or menarche before age 9 warrants evaluation by a pediatric endocrinologist."
            },
            {
                "type": "list",
                "items": [
                    "Breast budding (thelarche) typically precedes menarche by 2 to 2.5 years.",
                    "Growth velocity peaks just before menstruation begins.",
                    "Bone age X-rays and hormonal profiles provide peace of mind and prevent early growth plate closure."
                ]
            }
        ]
    },
    {
        "title": "Mood Swings, Emotional Waves & Brain Remodeling in Teenage Girls",
        "subtopic_slug": "cycle-literacy",
        "content_type": "ARTICLE",
        "duration_minutes": 8,
        "thumbnail_url": "https://images.unsplash.com/photo-1516585427167-9f4af9627e6c?auto=format&fit=crop&w=900&q=80",
        "description": "Neurobiology of the adolescent brain: how fluctuating estrogen and progesterone influence mood and how caregivers can anchor calm.",
        "body": [
            {
                "type": "heading",
                "content": "Brain Architecture During Hormonal Surges"
            },
            {
                "type": "paragraph",
                "content": "During the luteal phase (the 7-10 days before menstruation), rapid drops in progesterone and estrogen impact serotonin receptors in the amygdala. For a teenage brain where the prefrontal cortex is still developing, emotions feel overwhelming."
            },
            {
                "type": "callout",
                "title": "The De-escalation Strategy",
                "content": "Do not teach lessons during a meltdown. Validate first: 'I can see how overwhelming everything feels right now. Let's get you something warm to drink and talk when your nervous system feels settled.'"
            }
        ]
    },
    {
        "title": "Starter Products Compared: Pads, Period Underwear, and Reusable Cups",
        "subtopic_slug": "first-period-hygiene",
        "content_type": "VIDEO",
        "duration_minutes": 9,
        "thumbnail_url": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=900&q=80",
        "description": "A pediatric breakdown of beginner-friendly menstrual products: absorbency, skin safety, changing frequency, and school convenience.",
        "body": [
            {
                "type": "heading",
                "content": "Choosing the Right Product for Her Lifestyle"
            },
            {
                "type": "paragraph",
                "content": "For 10 to 13 year olds, period underwear and organic cotton pads with wings provide the highest ease of use and zero insertion anxiety. We review absorbency tests and tips for preventing leaks."
            }
        ]
    }
]

def run():
    init_db(settings.database_url)
    db = get_session_factory()()
    try:
        # 1. Create or get Caregiver topic
        topic = db.query(Topic).filter(Topic.slug == CAREGIVER_TOPIC_DATA["slug"]).first()
        if not topic:
            topic = Topic(
                id=str(uuid4()),
                name=CAREGIVER_TOPIC_DATA["name"],
                slug=CAREGIVER_TOPIC_DATA["slug"],
                icon=CAREGIVER_TOPIC_DATA["icon"],
                description=CAREGIVER_TOPIC_DATA["description"],
                display_order=CAREGIVER_TOPIC_DATA["display_order"],
                is_active=True,
            )
            db.add(topic)
            db.commit()
            db.refresh(topic)
            print(f"Created topic: {topic.name} ({topic.slug})")
        else:
            print(f"Found existing topic: {topic.name}")

        # 2. Create subtopics
        subtopic_map = {}
        for sdata in CAREGIVER_SUBTOPICS:
            sub = db.query(Subtopic).filter(
                Subtopic.topic_id == topic.id,
                Subtopic.slug == sdata["slug"]
            ).first()
            if not sub:
                sub = Subtopic(
                    id=str(uuid4()),
                    topic_id=topic.id,
                    name=sdata["name"],
                    slug=sdata["slug"],
                    description=sdata["description"],
                    display_order=sdata["display_order"],
                    is_active=True,
                )
                db.add(sub)
                db.commit()
                db.refresh(sub)
                print(f"Created subtopic: {sub.name}")
            subtopic_map[sdata["slug"]] = sub.id

        # 3. Create learning modules
        created_count = 0
        for item in CAREGIVER_ARTICLES:
            existing = db.query(LearningContent).filter(
                LearningContent.title == item["title"]
            ).first()
            if existing:
                continue

            sub_id = subtopic_map.get(item["subtopic_slug"])
            content = LearningContent(
                id=str(uuid4()),
                title=item["title"],
                description=item["description"],
                content_type=item["content_type"],
                source_type="INTERNAL",
                category="caregivers",
                topic_id=topic.id,
                subtopic_id=sub_id,
                audience="ALL",
                language="en",
                status="PUBLISHED",
                is_featured=False,
                duration_minutes=item["duration_minutes"],
                thumbnail_url=item["thumbnail_url"],
                body=item["body"],
                medical_review_status="MEDICALLY_REVIEWED",
                tags=["caregiver", "parenting", "puberty", "guidance"],
                author_id="dr-sunita-md",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(content)
            created_count += 1

        db.commit()
        print(f"Successfully populated {created_count} Caregiver modules in PostgreSQL!")

    except Exception as e:
        db.rollback()
        print(f"Error populating caregiver modules: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    run()
