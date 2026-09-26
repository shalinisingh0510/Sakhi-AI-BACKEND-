"""
Sakhi AI Bulk Content Ingestion Script
Generates and publishes articles for 5 topics in English + Hindi
Uses Gemini (primary) with Groq fallback
"""
import sys
import logging
import time
import json
import io
from pathlib import Path

# Force UTF-8 for Hindi output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.db.session import get_session_factory, init_db
from app.services.llm_manager.manager import LLMProviderManager
from app.services.content_ingestion_service import ContentIngestionService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("bulk_ingestion")

# =====================================================================
# CONTENT PLAN: 5 TOPICS × N ARTICLES
# Each article has a title and rich research context scraped from the
# internet so the LLM generates accurate, grounded content.
# =====================================================================
CONTENT_PLAN = [
    # ------------------------------------------------------------------
    # 1. PERIODS / MENSTRUAL HEALTH
    # ------------------------------------------------------------------
    {
        "topic_slug": "periods",
        "subtopic_slug": "basics",
        "articles": [
            {
                "title": "What Is Menstruation? A Complete Beginner's Guide",
                "research": (
                    "Menstruation is the monthly shedding of the uterine lining (endometrium) when pregnancy has not occurred. "
                    "The average cycle length is 21–35 days; bleeding lasts 2–7 days. The process is controlled by estrogen and progesterone. "
                    "Menarche (first period) typically occurs at ages 11–14. Menopause ends periods around age 51. "
                    "Common symptoms: cramping (dysmenorrhea), bloating, breast tenderness, headache, mood changes. "
                    "Moderate flow: 30–80 mL of blood per cycle. >80 mL is heavy menstrual bleeding (menorrhagia). "
                    "Source: WHO, MedlinePlus, ACOG"
                ),
            },
            {
                "title": "Period Pain (Dysmenorrhea): Causes, Relief, and When to See a Doctor",
                "research": (
                    "Primary dysmenorrhea: prostaglandin-induced uterine cramping without underlying disease. "
                    "Secondary dysmenorrhea: caused by endometriosis, fibroids, adenomyosis, or PID. "
                    "First-line relief: ibuprofen/naproxen (NSAIDs) taken 1–2 days before period, heat therapy, light exercise. "
                    "Warning signs needing medical attention: pain that disrupts daily life, worsens over time, or does not improve with NSAIDs. "
                    "Endometriosis affects ~10% of women globally. Average diagnostic delay is 7–10 years. "
                    "Source: ACOG, Endometriosis Foundation of America, NHS"
                ),
            },
            {
                "title": "Menstrual Hygiene: Safe Practices and Product Guide",
                "research": (
                    "Safe menstrual hygiene prevents infections (BV, TSS, UTIs). "
                    "Options: disposable pads (change every 4–6h), tampons (change every 4–8h, never >8h due to TSS risk), "
                    "menstrual cups (empty every 8–12h, sterilize between cycles), period underwear (wash after each use), "
                    "reusable cloth pads (common in India, wash with soap and dry in sunlight). "
                    "Menstrual cup use in India growing: WHO recognizes as safe, eco-friendly, and cost-effective over time. "
                    "Access to clean water essential for reusable products. "
                    "Source: WHO, UNICEF, MHM Alliance"
                ),
            },
            {
                "title": "Irregular Periods: What Counts as Irregular and What Causes It?",
                "research": (
                    "Irregular periods: cycle < 21 days or > 35 days, missed periods, very heavy/very light flow, or extremely painful periods. "
                    "Common causes: PCOS (most common hormonal cause), thyroid disorders, high stress/anxiety, sudden weight loss or gain, "
                    "excessive exercise, perimenopause, uterine polyps/fibroids, certain medications (e.g., antipsychotics, hormonal contraceptives). "
                    "Ruling out: pregnancy is first step. "
                    "Diagnostic workup: hormone panel (FSH, LH, estradiol, TSH, prolactin), pelvic ultrasound. "
                    "Treatment depends on root cause. Not all irregular periods require treatment. "
                    "Source: ACOG, NICE guidelines"
                ),
            },
            {
                "title": "PMS and PMDD: Understanding Premenstrual Symptoms",
                "research": (
                    "PMS (Premenstrual Syndrome): combination of emotional, behavioral, and physical symptoms 1–2 weeks before period. "
                    "Affects up to 75% of menstruating women in some form. "
                    "PMDD (Premenstrual Dysphoric Disorder): severe PMS with significant psychological symptoms (depression, anger, anxiety) impairing daily function. "
                    "Affects 3–8% of women. Classified as a depressive disorder in DSM-5. "
                    "Management PMS: lifestyle changes (exercise, reduce caffeine/salt/sugar, calcium 1200mg/day). "
                    "Management PMDD: SSRIs (fluoxetine, sertraline), hormonal contraceptives, CBT. "
                    "Source: ACOG, NIMH, Mayo Clinic"
                ),
            },
        ],
    },

    # ------------------------------------------------------------------
    # 2. PCOS / PCOD
    # ------------------------------------------------------------------
    {
        "topic_slug": "pcos",
        "subtopic_slug": "basics",
        "articles": [
            {
                "title": "What Is PCOS? Understanding Polycystic Ovary Syndrome",
                "research": (
                    "PCOS (Polycystic Ovary Syndrome) is the most common hormonal disorder in women of reproductive age, affecting 8–13% globally. "
                    "Diagnosis by Rotterdam criteria (at least 2 of 3): irregular/absent periods, clinical or biochemical signs of excess androgens (hyperandrogenism), "
                    "polycystic ovaries on ultrasound (≥12 follicles or ovarian volume >10mL). "
                    "Not all women with PCOS have cysts; the name is somewhat misleading. "
                    "Associated conditions: insulin resistance (70%), type 2 diabetes risk, cardiovascular disease, endometrial cancer risk, infertility, depression. "
                    "Source: ASRM, WHO, Endocrine Society"
                ),
            },
            {
                "title": "PCOS Symptoms: How to Recognize Polycystic Ovary Syndrome",
                "research": (
                    "Physical symptoms of PCOS: irregular or missed periods, excess facial/body hair (hirsutism) on face/chest/stomach, "
                    "acne (jawline, chest, back), hair loss/thinning (androgenic alopecia), darkening of skin creases (acanthosis nigricans), weight gain (especially abdomen). "
                    "Metabolic symptoms: fatigue, difficulty losing weight, cravings due to insulin resistance. "
                    "Emotional symptoms: anxiety, depression, low self-esteem often related to appearance symptoms. "
                    "Fertility: PCOS is a leading cause of female infertility; ovulation induction (clomiphene, letrozole) is often effective. "
                    "Source: NHS, ACOG, Jean Hailes Foundation"
                ),
            },
            {
                "title": "Managing PCOS with Diet and Lifestyle Changes",
                "research": (
                    "Lifestyle first approach is endorsed by ACOG, Endocrine Society for PCOS management. "
                    "Diet: low-glycaemic index (GI) diet reduces insulin resistance. Emphasize whole grains, legumes, non-starchy vegetables. "
                    "Reduce: refined carbohydrates, sugary drinks, processed foods, trans fats. "
                    "Exercise: 150 min/week moderate exercise improves insulin sensitivity, reduces androgens, restores ovulation. Even 5% weight loss in overweight women improves symptoms significantly. "
                    "Anti-inflammatory foods: omega-3 (fish, walnuts, flaxseed), turmeric, berries. "
                    "Sleep: poor sleep worsens insulin resistance. 7–9 hours recommended. "
                    "Stress management: chronic stress elevates cortisol, worsening PCOS. Yoga and mindfulness beneficial. "
                    "Source: Endocrine Society, Jean Hailes, PCOS Awareness Association"
                ),
            },
            {
                "title": "PCOS and Fertility: Can You Get Pregnant with PCOS?",
                "research": (
                    "PCOS causes irregular/absent ovulation (anovulation), which impairs fertility but does not cause infertility in most cases. "
                    "First-line treatment for ovulation induction: letrozole (superior to clomiphene per ACOG 2023 guidelines). "
                    "Second-line: clomiphene + metformin. Third-line: gonadotrophins (FSH injections). Fourth-line: IVF. "
                    "Metformin: reduces insulin resistance, can restore ovulation in some women. "
                    "Pre-conception: folic acid 400–800mcg/day, achieve healthy weight if overweight, manage blood sugar. "
                    "Pregnancy risks with PCOS: higher rates of gestational diabetes, preeclampsia, preterm birth. Requires careful monitoring. "
                    "Most women with PCOS can conceive with appropriate treatment. "
                    "Source: ACOG 2023, ASRM, NICE"
                ),
            },
            {
                "title": "PCOS vs PCOD: Are They the Same Thing?",
                "research": (
                    "PCOD (Polycystic Ovarian Disease) is a term commonly used in India and South Asia; globally, PCOS is the standard medical term. "
                    "Both refer to the same condition but PCOD is sometimes used colloquially for milder presentations. "
                    "Medically, there is no distinct separate condition called 'PCOD' - it is PCOS. "
                    "PCOS is a syndrome (collection of symptoms), not a disease. "
                    "Key difference from what people think: having cysts on ovaries alone does NOT mean PCOS. "
                    "Confusion perpetuated by misinformation; women in India are sometimes over-diagnosed based on ultrasound alone without hormonal confirmation. "
                    "Source: FOGSI (Federation of Obstetric and Gynaecological Societies of India), Endocrine Society"
                ),
            },
        ],
    },

    # ------------------------------------------------------------------
    # 3. NUTRITION (women-specific)
    # ------------------------------------------------------------------
    {
        "topic_slug": "nutrition",
        "subtopic_slug": "healthy-eating",
        "articles": [
            {
                "title": "Iron for Women: Why You Need It and How to Get Enough",
                "research": (
                    "Iron deficiency is the most common nutritional deficiency globally, disproportionately affecting women. "
                    "Women need 18mg/day (pre-menopause), 27mg/day (pregnancy), 8mg/day (post-menopause). "
                    "Iron deficiency anaemia symptoms: fatigue, weakness, pale skin, brittle nails, shortness of breath, cold hands/feet. "
                    "Haeme iron (animal sources, 15–35% absorbed): red meat, chicken, fish, eggs. "
                    "Non-haeme iron (plant sources, 2–20% absorbed): spinach, lentils, tofu, fortified cereals, pumpkin seeds. "
                    "Enhance absorption: eat non-haeme iron with vitamin C (lemon, amla, tomatoes). "
                    "Inhibit absorption: tea/coffee tannins, calcium, phytates (eaten simultaneously). "
                    "Ferritin test: best marker for iron stores. Serum iron alone insufficient. "
                    "Source: WHO, ICMR, NIH Office of Dietary Supplements"
                ),
            },
            {
                "title": "Nutrition During Your Period: What to Eat and What to Avoid",
                "research": (
                    "During menstruation, the body loses iron (especially with heavy flow). Iron-rich foods important. "
                    "Anti-inflammatory foods reduce prostaglandins causing cramps: omega-3 (mackerel, sardines, walnuts, flaxseed), turmeric, ginger, berries. "
                    "Magnesium (dark chocolate, nuts, leafy greens): reduces muscle cramps and mood symptoms. "
                    "Calcium: reduces PMS symptoms significantly. Dairy, fortified plant milks, ragi (finger millet). "
                    "Reduce: salt (reduces bloating), sugar (spikes then crashes worsen mood), caffeine (can worsen breast tenderness and anxiety), alcohol. "
                    "Stay hydrated: water reduces bloating. Chamomile and ginger teas have anti-inflammatory and antispasmodic properties. "
                    "Source: ACOG, Academy of Nutrition and Dietetics"
                ),
            },
            {
                "title": "Calcium and Vitamin D for Women's Bone Health",
                "research": (
                    "Women are at higher risk of osteoporosis than men due to lower peak bone mass and accelerated bone loss post-menopause. "
                    "Calcium needs: 1000mg/day (19–50 years), 1200mg/day (51+ years). "
                    "Sources: dairy, fortified plant milks, ragi, sesame seeds (til), amaranth, small fish eaten whole. "
                    "Vitamin D essential for calcium absorption. Deficiency extremely common in India (>70% of population). "
                    "Vitamin D RDA: 600 IU (15–70 years), 800 IU (71+). Sources: sunlight (15–20 min/day), fatty fish, egg yolks, fortified foods. "
                    "Sunlight exposure is primary source; food sources insufficient without supplementation if deficient. "
                    "Testing: 25-OH Vitamin D blood test. Sufficiency > 30 ng/mL; <20 ng/mL is deficiency. "
                    "Source: ICMR, IOF (International Osteoporosis Foundation), NIH"
                ),
            },
            {
                "title": "Folic Acid: The Essential Nutrient for Women of Reproductive Age",
                "research": (
                    "Folic acid (folate/vitamin B9) is critical for DNA synthesis and cell division. "
                    "Deficiency before/during early pregnancy causes neural tube defects (NTDs): spina bifida, anencephaly. "
                    "NTDs form in first 28 days of pregnancy – often before woman knows she is pregnant. "
                    "Recommended: all women of reproductive age take 400mcg folic acid daily. 600mcg during pregnancy. "
                    "Women with history of NTD-affected pregnancy or on certain medications: 4000mcg/day (requires prescription). "
                    "Food sources: green leafy vegetables (spinach, methi, palak), legumes (dal, rajma), citrus fruits, fortified cereals. "
                    "Cooking destroys folate; raw/lightly cooked vegetables better. Supplementation still recommended. "
                    "Source: WHO, ICMR, CDC"
                ),
            },
            {
                "title": "Eating for Hormonal Balance: Foods That Support Women's Health",
                "research": (
                    "Hormones (estrogen, progesterone, insulin, cortisol, thyroid) are heavily influenced by diet, body composition, and gut health. "
                    "Phytoestrogens (soy, flaxseed, sesame): modulate estrogen activity; beneficial for menopausal symptoms and may reduce breast cancer risk. "
                    "Cruciferous vegetables (broccoli, cauliflower, kale, cabbage): contain DIM (diindolylmethane) supporting healthy estrogen metabolism. "
                    "Fiber (25g/day): helps excrete excess estrogens through gut; fed gut microbiome influences hormone production. "
                    "Blood sugar regulation: avoid refined carbs/sugar spikes which drive insulin resistance, worsening PCOS and increasing cortisol. "
                    "Healthy fats (avocado, nuts, ghee, coconut oil in moderation): essential for steroid hormone synthesis. "
                    "Gut microbiome ('estrobolome'): diverse gut bacteria help metabolize estrogens; probiotics/prebiotics support this. "
                    "Source: Journal of Steroid Biochemistry, Endocrine Society, Frontiers in Endocrinology"
                ),
            },
        ],
    },

    # ------------------------------------------------------------------
    # 4. MENTAL WELLBEING
    # ------------------------------------------------------------------
    {
        "topic_slug": "mental-wellbeing",
        "subtopic_slug": "stress",
        "articles": [
            {
                "title": "Stress and Your Cycle: How Mental Health Affects Periods",
                "research": (
                    "The hypothalamic-pituitary-adrenal (HPA) axis and HPG (hypothalamic-pituitary-gonadal) axis are interconnected. "
                    "High cortisol (stress hormone) suppresses GnRH, disrupting LH/FSH, delaying or stopping ovulation. "
                    "Result: late, missed, or irregular periods. Can worsen PMS/PMDD symptoms. "
                    "Functional Hypothalamic Amenorrhea (FHA): periods stop due to extreme stress, excessive exercise, or low body weight. "
                    "Chronic stress raises inflammation, worsening endometriosis and PCOS symptoms. "
                    "Stress management improves cycle regularity: 8-week mindfulness programme shown to improve cycle regularity in studies. "
                    "Source: Journal of Clinical Endocrinology & Metabolism, ACOG"
                ),
            },
            {
                "title": "Anxiety and Depression in Women: Why Women Are More Vulnerable",
                "research": (
                    "Women are diagnosed with anxiety disorders at 2x the rate of men. Depression rates 1.7x higher in women. "
                    "Key biological factors: hormonal fluctuations across cycle, pregnancy, postpartum, perimenopause increase vulnerability. "
                    "Estrogen modulates serotonin, dopamine, GABA – neurotransmitters central to mood. "
                    "Social/psychological factors: higher rates of trauma, gender-based violence, caregiving burden, social perfectionism pressure. "
                    "Screening tools: PHQ-9 for depression, GAD-7 for anxiety. "
                    "Treatment: CBT (first-line for mild-moderate), SSRIs (sertraline, escitalopram first-line for moderate-severe), "
                    "exercise (as effective as antidepressants for mild-moderate depression in studies). "
                    "Source: WHO, APA, NIMH, Lancet Psychiatry"
                ),
            },
            {
                "title": "Sleep and Women's Health: Why Sleep Quality Matters for Hormones",
                "research": (
                    "Women are 40% more likely than men to suffer from insomnia. "
                    "Hormonal fluctuations across the cycle affect sleep: progesterone (sedating) peaks in luteal phase; "
                    "estrogen withdrawal before period disrupts sleep architecture. "
                    "Pregnancy: insomnia affects 78% of women. Postpartum sleep deprivation is severe. "
                    "Perimenopause/menopause: night sweats, hot flashes fragment sleep. "
                    "Poor sleep worsens insulin resistance (PCOS), increases cortisol, disrupts appetite hormones (ghrelin, leptin). "
                    "Sleep hygiene: consistent sleep/wake time, dark cool room, no screens 1h before bed, avoid caffeine after 2pm. "
                    "CBT-I (Cognitive Behavioural Therapy for Insomnia) is most effective long-term treatment; superior to sleep medications. "
                    "Source: Sleep Foundation, Journal of Clinical Sleep Medicine, ACOG"
                ),
            },
            {
                "title": "How to Practice Self-Care: Simple Daily Habits for Women's Wellbeing",
                "research": (
                    "Self-care is evidence-based: WHO definition includes activities individuals take to maintain health, prevent disease, cope with illness without clinical support. "
                    "Physical self-care: 150 min/week moderate exercise; 7–9 hours sleep; balanced nutrition; regular health screenings. "
                    "Mental self-care: journaling (reduces rumination); gratitude practice (improves mood within 2 weeks per studies); "
                    "social connection (reduces loneliness and depression risk); digital detox periods. "
                    "Emotional self-care: setting boundaries (reduces chronic stress); therapy/counselling; identifying and naming emotions. "
                    "Cultural context India: self-care often deprioritized by women who care for family first. "
                    "Spiritual self-care: prayer, meditation, time in nature – all shown to reduce stress and improve wellbeing. "
                    "Source: WHO, Greater Good Science Center, Harvard Health Publishing"
                ),
            },
            {
                "title": "Recognizing Burnout: Signs You're Running on Empty and How to Recover",
                "research": (
                    "Burnout: a state of chronic stress leading to physical/emotional exhaustion, cynicism, and sense of ineffectiveness. "
                    "WHO recognized burnout as an occupational phenomenon (ICD-11, 2019). "
                    "Burnout in women: higher rates due to double burden (work + domestic labour + caregiving). "
                    "3 stages: exhaustion, cynicism/detachment, reduced professional efficacy. "
                    "Physical symptoms: fatigue, headaches, frequent illness (immune suppression), sleep issues. "
                    "Emotional symptoms: dread going to work, feeling detached, irritability, crying spells, sense of failure. "
                    "Recovery: Requires actual rest (not just sleep), boundary-setting, reducing load, professional support if severe. "
                    "Prevention: regular breaks, realistic workload negotiation, social support, mindfulness. "
                    "Source: WHO, Christina Maslach Burnout Inventory research, Frontiers in Psychology"
                ),
            },
        ],
    },

    # ------------------------------------------------------------------
    # 5. PUBERTY
    # ------------------------------------------------------------------
    {
        "topic_slug": "puberty",
        "subtopic_slug": "basics",
        "articles": [
            {
                "title": "Puberty in Girls: What to Expect and When",
                "research": (
                    "Puberty in girls typically begins between ages 8–13. Average onset: 10–11 years in India/globally. "
                    "Sequence: breast development (thelarche) → pubic hair → growth spurt → underarm hair → menarche (first period). "
                    "Menarche usually occurs 2–3 years after thelarche, at Tanner Stage 4. Average age: 12.5 years (India range 11–14). "
                    "Driven by: hypothalamus releases GnRH → pituitary releases FSH/LH → ovaries produce estrogen. "
                    "Precocious puberty: onset before age 8 in girls. Requires medical evaluation. "
                    "Delayed puberty: no breast development by 13, no period by 15. Requires evaluation. "
                    "Emotional changes normal: mood swings, self-consciousness, interest in identity. "
                    "Source: AAP, IAP (Indian Academy of Pediatrics), NHS"
                ),
            },
            {
                "title": "Body Changes During Puberty: A Guide for Girls and Teens",
                "research": (
                    "Puberty body changes in girls: breast development (1–5 years, varies widely in size/shape – all normal); "
                    "body hair (underarms, legs, pubic area); growth spurt (5–7.5 cm/year peak); "
                    "widening of hips; increased body fat (normal, part of healthy development); "
                    "changes in vulva and vagina; onset of vaginal discharge (normal leucorrhoea) before periods; "
                    "skin changes – increased oil production leads to acne; increased sweating. "
                    "Brain development continues until age 25: impulse control, risk assessment still developing during teen years. "
                    "Weight gain of 7–25 kg over puberty is normal and expected. Dieting during puberty is harmful. "
                    "Source: AAP, NHS, Society for Adolescent Health and Medicine"
                ),
            },
            {
                "title": "Vaginal Discharge: What's Normal During Puberty and Beyond",
                "research": (
                    "Vaginal discharge (leucorrhoea) is a NORMAL sign of healthy hormonal activity and vaginal self-cleaning. "
                    "Normal: clear to white, no smell or mild smell, varies across cycle (more at ovulation, less before period). "
                    "Starts 6–12 months before menarche, is first sign of puberty for many girls. "
                    "Abnormal discharge warning signs: yellow/green/grey color, cottage-cheese texture, foul smell, itching, burning, swelling. "
                    "These may indicate: yeast infection (Candida), bacterial vaginosis, STI. Requires medical evaluation. "
                    "Hygiene: external washing with plain water only. Do NOT douche – disrupts healthy vaginal pH and flora. "
                    "Panty liners: acceptable for managing discharge. "
                    "Source: AAP, ACOG, NHS"
                ),
            },
            {
                "title": "Emotional Changes During Puberty: Mood Swings, Identity, and Self-Esteem",
                "research": (
                    "Puberty triggers significant emotional and psychological changes driven by hormonal, social, and neurological development. "
                    "Mood swings: normal. Estrogen and progesterone fluctuations affect serotonin and dopamine. "
                    "Identity formation (Erikson stage: identity vs role confusion): teens question 'who am I?', experiment with identity, peer groups important. "
                    "Body image: puberty is peak time for negative body image in girls. Social media exposure worsens this. "
                    "Social changes: shift from parents to peers for social validation. Romantic feelings normal. "
                    "Risk factors for poor mental health during puberty: bullying, academic pressure, family conflict, social isolation. "
                    "Protective factors: trusted adult relationships, body-positive messaging, extracurricular activities, open family communication. "
                    "Note for parents/carers: validate emotions, avoid shaming body changes, maintain open communication. "
                    "Source: AAP, WHO Adolescent Mental Health, UNICEF"
                ),
            },
            {
                "title": "Personal Hygiene During Puberty: A Practical Guide for Teens",
                "research": (
                    "Puberty brings new hygiene needs due to increased sweat gland activity and body hair growth. "
                    "Bathing: daily shower/bath recommended. Pay attention to underarms, groin, feet. "
                    "Deodorant vs antiperspirant: deodorant masks smell; antiperspirant reduces sweating. Alum stone is traditional Indian option. "
                    "Genital hygiene: external washing with warm water only. No soap inside vagina. Wear breathable cotton underwear. "
                    "Skin care: gentle cleanser for face (not harsh soaps). Non-comedogenic moisturizer if skin is dry. "
                    "Acne: do not pop pimples (increases infection and scarring risk). Benzoyl peroxide or salicylic acid mild products help. See dermatologist if severe. "
                    "Oral hygiene: brush twice daily, floss, use fluoride toothpaste. "
                    "Menstrual hygiene: taught as part of puberty education. Access to safe, affordable products essential. "
                    "Source: AAP, NHS, WHO Adolescent Health"
                ),
            },
        ],
    },
]


def run_bulk_ingestion(languages=("en", "hi"), publish=True):
    logger.info("=" * 60)
    logger.info("SAKHI AI BULK CONTENT INGESTION")
    logger.info(f"Languages: {list(languages)} | Publish: {publish}")
    logger.info("=" * 60)

    init_db(settings.database_url)
    SessionLocal = get_session_factory()
    db = SessionLocal()

    llm_manager = LLMProviderManager(settings)

    logger.info("\nProvider Status:")
    for provider, status in llm_manager.get_provider_status().items():
        logger.info(f"  {provider}: {status}")

    service = ContentIngestionService(db=db, llm_manager=llm_manager)

    total_success = 0
    total_skipped = 0
    total_failed = 0

    for topic_plan in CONTENT_PLAN:
        topic_slug = topic_plan["topic_slug"]
        subtopic_slug = topic_plan.get("subtopic_slug", "basics")
        articles = topic_plan["articles"]

        logger.info(f"\n{'=' * 50}")
        logger.info(f"TOPIC: {topic_slug.upper()}")
        logger.info(f"{'=' * 50}")

        for i, article_def in enumerate(articles):
            title = article_def["title"]
            research = article_def["research"]
            logger.info(f"\n[{i+1}/{len(articles)}] {title}")

            try:
                # Check if article already exists
                from sqlalchemy import select
                from app.models.learning import LearningContent
                existing = db.scalar(
                    select(LearningContent).where(
                        LearningContent.title == title,
                        LearningContent.language == "en"
                    )
                )
                if existing:
                    logger.info(f"  [SKIP] Already exists, skipping.")
                    total_skipped += 1
                    continue

                # Patch the research into the service for this article
                original_research_fn = service._perform_research
                service._perform_research = lambda t, r=research: r

                results = service.ingest_article(
                    topic_slug=topic_slug,
                    article_title=title,
                    languages=list(languages),
                    publish=publish,
                    dry_run=False
                )

                service._perform_research = original_research_fn

                if results.get("status") == "skipped":
                    logger.info(f"  [SKIP] Already exists.")
                    total_skipped += 1
                else:
                    logger.info(f"  [OK] Published in {list(languages)}")
                    logger.info(f"       EN provider: {results.get('provider_en', 'n/a')}")
                    total_success += 1

                # Small delay to respect rate limits
                time.sleep(3)

            except Exception as e:
                logger.error(f"  [FAIL] {e}", exc_info=True)
                total_failed += 1
                # Continue with other articles; don't abort the whole run
                time.sleep(5)

    logger.info("\n" + "=" * 60)
    logger.info("INGESTION COMPLETE")
    logger.info(f"  Success : {total_success}")
    logger.info(f"  Skipped : {total_skipped}")
    logger.info(f"  Failed  : {total_failed}")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_bulk_ingestion(languages=["en", "hi"], publish=True)

