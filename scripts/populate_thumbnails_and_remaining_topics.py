"""
Populate Thumbnails for all existing learning content, Learning Paths,
and generate rich comprehensive articles for the 3 remaining topics:
1. Pregnancy (slug: pregnancy)
2. Reproductive Health (slug: reproductive-health)
3. Fitness (slug: fitness)
Both English and Hindi editions with verified medical structure and curated Unsplash thumbnails.
"""
from __future__ import annotations

import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# Ensure backend root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import select, update
from app.db.session import init_db, get_session_factory
from app.core.config import settings
from app.models.learning import (
    LearningContent,
    LearningPath,
    Topic,
    Subtopic,
    extract_youtube_id,
)

# Curated high-res Unsplash photos tailored for women's healthcare
TOPIC_IMAGE_POOLS = {
    "periods": [
        "https://images.unsplash.com/photo-1518611012118-696072aa579a?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1506126613408-eca07ce68773?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1516549655169-df83a0774514?auto=format&fit=crop&w=800&q=80",
    ],
    "pcos": [
        "https://images.unsplash.com/photo-1576091160550-2173dba999ef?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1505751172876-fa1923c5c528?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1579684385127-1ef15d508118?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1532938911079-1b06ac7ceec7?auto=format&fit=crop&w=800&q=80",
    ],
    "nutrition": [
        "https://images.unsplash.com/photo-1490645935967-10de6ba17061?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1498837167922-ddd27525d352?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1540420773420-3366772f4999?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1505576399279-565b52d4ac71?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1494390248081-4e521a5940db?auto=format&fit=crop&w=800&q=80",
    ],
    "mental-wellbeing": [
        "https://images.unsplash.com/photo-1506126613408-eca07ce68773?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1515377905703-c4788e51af15?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1499209974431-9dddcece7f88?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1474418397713-7ede21d49118?auto=format&fit=crop&w=800&q=80",
    ],
    "puberty": [
        "https://images.unsplash.com/photo-1529156069898-49953e39b3ac?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1556911220-e15b29be8c8f?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1517486808906-6ca8b3f04846?auto=format&fit=crop&w=800&q=80",
    ],
    "pregnancy": [
        "https://images.unsplash.com/photo-1555252333-9f8e92e65df9?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1516627145497-ae6968895b74?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1584515979956-d9f6e5d09982?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1531746020798-e6953c6e8e04?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1576765608535-5f04d1e3f289?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1544126592-807ade215a0b?auto=format&fit=crop&w=800&q=80",
    ],
    "reproductive-health": [
        "https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1631815589968-fdb09a223b1e?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1588776814546-1ffcf47267a5?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1559839734-2b71ea197ec2?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1583912267550-d44d9c9a2958?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?auto=format&fit=crop&w=800&q=80",
    ],
    "fitness": [
        "https://images.unsplash.com/photo-1518611012118-696072aa579a?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1517838277536-f5f99be501cd?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1506126613408-eca07ce68773?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1574680096145-d05b474e2155?auto=format&fit=crop&w=800&q=80",
    ]
}

PATH_THUMBNAILS = {
    "mastering-menstrual-health": "https://images.unsplash.com/photo-1518611012118-696072aa579a?auto=format&fit=crop&w=1200&q=80",
    "living-well-with-pcos": "https://images.unsplash.com/photo-1505751172876-fa1923c5c528?auto=format&fit=crop&w=1200&q=80",
    "essential-nutrition-for-women": "https://images.unsplash.com/photo-1490645935967-10de6ba17061?auto=format&fit=crop&w=1200&q=80",
    "nurturing-mental-wellbeing": "https://images.unsplash.com/photo-1506126613408-eca07ce68773?auto=format&fit=crop&w=1200&q=80",
}

# The 3 remaining topics articles data definition
NEW_TOPICS_CONTENT = [
    # =========================================================================
    # PREGNANCY (6 articles)
    # =========================================================================
    {
        "topic_slug": "pregnancy",
        "subtopic_slug": "basics",
        "title_en": "First Trimester Journey: Symptoms, Milestones and Essential Doctor Visits",
        "title_hi": "पहली तिमाही (फर्स्ट ट्राइमेस्टर): लक्षण, विकास के पड़ाव और जरूरी डॉक्टर चेकअप",
        "desc_en": "A week-by-week medical guide to weeks 1 through 12 of pregnancy, managing early symptoms, and navigating prenatal screening.",
        "desc_hi": "गर्भावस्था के पहले 12 हफ्तों की पूरी जानकारी, शुरुआती लक्षणों का प्रबंधन और जरूरी प्रसवपूर्व जांचें।",
        "thumbnail_url": TOPIC_IMAGE_POOLS["pregnancy"][0],
        "category": "Pregnancy",
        "tags": ["Pregnancy", "First Trimester", "Prenatal Care", "Motherhood"],
        "body_en": {
            "tldr": "The first trimester (weeks 1–12) is the most critical developmental phase. Key focus areas include taking 400–600 mcg folic acid daily, attending your first ultrasound (dating scan), and managing fatigue and nausea.",
            "introduction": "Discovering you are pregnant initiates a cascade of rapid physical and hormonal transformations. From conception through week 12, your baby transitions from a fertilized egg into a fully formed fetus with developing organs, heartbeats, and facial features. Understanding what is happening inside your body gives you confidence and peace of mind.",
            "sections": [
                {
                    "heading": "Hormonal Shifts and Common First Trimester Symptoms",
                    "content": "Surging human chorionic gonadotropin (hCG) and progesterone support early pregnancy but also cause noticeable physical symptoms. Typical experiences include morning sickness (nausea with or without vomiting), tender and swollen breasts, frequent urination as blood volume expands, heightened sensitivity to smells, and overwhelming fatigue. While uncomfortable, these symptoms generally reflect healthy placental development."
                },
                {
                    "heading": "Key Milestones in Fetal Organogenesis",
                    "content": "By week 5, the embryo forms the neural tube, which later becomes the brain and spinal cord. Around week 6, cardiac activity can be detected via transvaginal ultrasound. By week 10, all vital organs—including kidneys, liver, brain, and intestines—are formed and beginning to function. By the end of week 12, your baby measures about 5–6 cm and has fingernails, reflex movements, and distinct facial contours."
                },
                {
                    "heading": "Essential First Trimester Clinical Checkups",
                    "content": "Your initial prenatal visit should occur between weeks 6 and 8. Key tests include complete blood count (CBC) to screen for anaemia, blood typing and Rh factor check, rubella immunity, infectious disease panels, and thyroid testing. An early dating ultrasound confirms intrauterine implantation and estimates gestational age. Between weeks 11 and 13, a nuchal translucency (NT) scan combined with a maternal blood test screens for chromosomal anomalies."
                },
                {
                    "heading": "Nutritional and Lifestyle Priorities for Early Pregnancy",
                    "content": "Daily supplementation of 400 to 600 mcg of folic acid is non-negotiable to prevent neural tube defects. If morning sickness makes big meals difficult, switch to frequent, small protein-rich snacks like nuts, roasted chana, and curd. Avoid raw meats, unpasteurized dairy, and excess caffeine (limit to under 200 mg/day). Avoid all alcohol and smoking."
                }
            ],
            "key_takeaways": [
                "Daily folic acid (400–600 mcg) is vital before conception and throughout the first trimester.",
                "First prenatal checkup with dating ultrasound is recommended between weeks 6 and 8.",
                "Morning sickness peaks around weeks 8–10 and typically subsides by weeks 12–14.",
                "Stay hydrated and consume small, frequent meals to counter nausea.",
                "Seek immediate emergency care for heavy bleeding, severe one-sided pelvic pain, or fever."
            ],
            "myths_vs_facts": [
                {"myth": "You need to eat for two right from the first trimester.", "fact": "Your caloric requirement barely increases in the first trimester; the focus is on nutrient quality (folate, iron, calcium), not excess calorie intake."},
                {"myth": "Morning sickness only happens early in the morning.", "fact": "Pregnancy nausea can occur at any time of day or night due to steady hormone elevations."},
                {"myth": "Exercise during the first trimester causes miscarriage.", "fact": "Moderate exercise like brisk walking and prenatal yoga is safe and beneficial for uncomplicated pregnancies."}
            ],
            "faqs": [
                {"question": "When does morning sickness usually start and end?", "answer": "It typically begins around week 6, peaks between weeks 8 and 10, and resolves for most women by weeks 12 to 14."},
                {"question": "Is light spotting normal in the first trimester?", "answer": "Light spotting can occur during implantation or cervical sensitivity. However, any vaginal bleeding should be evaluated by your obstetrician to rule out ectopic pregnancy or threatened miscarriage."},
                {"question": "Can I continue working out in the first trimester?", "answer": "Yes, moderate low-impact exercises like walking, swimming, and prenatal yoga are safe unless your doctor advises pelvic rest."}
            ],
            "sources": [
                {"name": "American College of Obstetricians and Gynecologists (ACOG)", "url": "https://www.acog.org"},
                {"name": "World Health Organization (WHO) - Antenatal Care Guidelines", "url": "https://www.who.int"},
                {"name": "ICMR Guidelines on Maternal and Child Health", "url": "https://www.icmr.nic.in"}
            ],
            "medical_disclaimer": "This article is for educational purposes only. Every pregnancy is unique. Consult your healthcare provider for personalized medical advice and prenatal screening."
        },
        "body_hi": {
            "tldr": "पहली तिमाही (हफ्ते 1–12) शिशु के अंगों के निर्माण का सबसे अहम चरण है। प्रतिदिन 400-600 माइक्रोग्राम फोलिक एसिड लेना, पहली अल्ट्रासाउंड जांच कराना और खानपान का ध्यान रखना बेहद जरूरी है।",
            "introduction": "गर्भावस्था की खबर मिलते ही शरीर में कई बदलाव शुरू होते हैं। पहले 12 हफ्तों में शिशु के मस्तिष्क, हृदय और मुख्य अंगों का निर्माण होता है। इन शुरुआती महीनों में सही जानकारी और देखभाल आपको स्वस्थ और निश्चिंत रखती है।",
            "sections": [
                {
                    "heading": "हार्मोनल बदलाव और शुरुआती लक्षण",
                    "content": "hCG और प्रोजेस्टेरोन हार्मोन के तेजी से बढ़ने के कारण जी मिचलाना, उल्टी आना, स्तनों में भारीपन, थकान और बार-बार पेशाब आने जैसे लक्षण सामान्य हैं। ये लक्षण स्वस्थ गर्भनाल के विकास का संकेत होते हैं।"
                },
                {
                    "heading": "शिशु के विकास के मुख्य पड़ाव",
                    "content": "5वें हफ्ते में न्यूरल ट्यूब बनती है जिससे मस्तिष्क और रीढ़ की हड्डी विकसित होती है। छठे हफ्ते के आसपास दिल की धड़कन अल्ट्रासाउंड में देखी जा सकती है। 12वें हफ्ते तक शिशु के सभी महत्वपूर्ण अंग बन चुके होते हैं।"
                },
                {
                    "heading": "जरूरी डॉक्टर चेकअप और जांचें",
                    "content": "हफ्ते 6 से 8 के बीच पहली बार डॉक्टर से मिलें। ब्लड ग्रुप, हीमोग्लोबिन, थायरॉइड, ब्लड शुगर और डेटिंग अल्ट्रासाउंड कराएं। 11 से 13 हफ्ते के बीच डाउन सिंड्रोम और जेनेटिक जांच (NT स्कैन) करवाई जाती है।"
                },
                {
                    "heading": "आहार और जीवनशैली की सावधानियां",
                    "content": "रोजाना फोलिक एसिड की गोली जरूर लें। एक बार में ज्यादा खाने के बजाय दिनभर में 5-6 बार हल्का और पौष्टिक खाना खाएं। पर्याप्त पानी पिएं और बिना डॉक्टर की सलाह के कोई भी दवा न लें।"
                }
            ],
            "key_takeaways": [
                "पहले तीन महीनों में रोजाना फोलिक एसिड सप्लीमेंट लेना अत्यंत आवश्यक है।",
                "शुरुआती 6-8 हफ्तों में पहला प्रसवपूर्व चेकअप और सोनोग्राफी जरूर कराएं।",
                "मतली से बचने के लिए थोड़ा-थोड़ा और बार-बार हल्का आहार लें।",
                "भारी रक्तस्राव या तेज पेट दर्द होने पर तुरंत अस्पताल जाएं।"
            ],
            "myths_vs_facts": [
                {"myth": "गर्भावस्था के पहले दिन से ही दो लोगों का खाना खाना चाहिए।", "fact": "पहली तिमाही में अतिरिक्त कैलोरी की जरूरत नहीं होती, केवल पौष्टिक तत्वों (आयरन, फोलेट) की गुणवत्ता पर ध्यान देना होता है।"},
                {"myth": "मॉर्निंग सिकनेस केवल सुबह के समय ही होती है।", "fact": "यह दिन या रात में किसी भी समय हो सकती है क्योंकि हार्मोन पूरे 24 घंटे सक्रिय रहते हैं।"}
            ],
            "faqs": [
                {"question": "जी मिचलाना कब बंद होता है?", "answer": "आमतौर पर 12 से 14 हफ्ते पूरे होने के बाद मॉर्निंग सिकनेस अपने आप काफी कम हो जाती है।"},
                {"question": "क्या शुरुआती दिनों में हल्का खून का धब्बा (स्पॉटिंग) सामान्य है?", "answer": "हल्की स्पॉटिंग इम्प्लांटेशन की वजह से हो सकती है, लेकिन किसी भी प्रकार के रक्तस्राव पर तुरंत डॉक्टर की सलाह लेना जरूरी है।"}
            ],
            "sources": [
                {"name": "World Health Organization (WHO)", "url": "https://www.who.int"},
                {"name": "FOGSI (फेडरेशन ऑफ ऑब्सटेट्रिक्स एंड गायनेकोलॉजिकल सोसाइटीज ऑफ इंडिया)", "url": "https://www.fogsi.org"}
            ],
            "medical_disclaimer": "यह सामग्री केवल सामान्य स्वास्थ्य शिक्षा के लिए है। किसी भी स्वास्थ्य समस्या के लिए योग्य स्त्री रोग विशेषज्ञ से परामर्श अवश्य लें।"
        }
    },
    {
        "topic_slug": "pregnancy",
        "subtopic_slug": "basics",
        "title_en": "Second & Third Trimesters: Baby's Growth, Body Changes and Labor Prep",
        "title_hi": "दूसरी और तीसरी तिमाही: शिशु का विकास, शारीरिक बदलाव और प्रसव की तैयारी",
        "desc_en": "Navigate weeks 13 through 40 with clinical clarity: anatomy ultrasound, gestational diabetes screening, fetal kicks, and labor signs.",
        "desc_hi": "13वें से 40वें हफ्ते तक का सम्पूर्ण मार्गदर्शन: एनोमली स्कैन, जेस्टेशनल डायबिटीज टेस्ट, बच्चे की हलचल और लेबर के लक्षण।",
        "thumbnail_url": TOPIC_IMAGE_POOLS["pregnancy"][1],
        "category": "Pregnancy",
        "tags": ["Pregnancy", "Trimesters", "Labor Preparation", "Fetal Movement"],
        "body_en": {
            "tldr": "The second trimester (weeks 13–27) brings renewed energy, the anomaly scan (week 18–20), and first fetal movements. The third trimester (weeks 28–40) focuses on kick counting, growth scans, and birth preparation.",
            "introduction": "Often hailed as the 'golden period' of pregnancy, the second trimester provides relief from early nausea, while the third brings anticipation and physical readiness for childbirth. Tracking both maternal changes and fetal milestones ensures a healthy delivery.",
            "sections": [
                {
                    "heading": "The Golden Second Trimester (Weeks 13 to 27)",
                    "content": "Energy levels rebound as placental hormones stabilize. You will likely feel your baby's first fluttery movements (quickening) between weeks 18 and 22. Between weeks 18 and 20, the detailed Level II anomaly scan evaluates the baby's brain, heart, spine, kidneys, and limbs. Between weeks 24 and 28, an oral glucose tolerance test (OGTT) screens for gestational diabetes."
                },
                {
                    "heading": "The Third Trimester and Fetal Maturation (Weeks 28 to 40)",
                    "content": "During the final stretch, the baby gains rapid weight and lays down brown fat for temperature regulation. Lungs mature by week 36. Mothers often encounter backache, mild ankle swelling, heartburn, and Braxton Hicks (practice) contractions. Daily fetal kick counts become essential: expect at least 10 kicks or distinct movements within two hours during active periods."
                },
                {
                    "heading": "Recognizing Real Labor vs Braxton Hicks",
                    "content": "Braxton Hicks contractions are irregular, painless or mildly tight, and usually stop with rest or hydration. True labor contractions occur at regular intervals, progressively become closer together (e.g., every 5 minutes), grow stronger and longer (lasting 45–60 seconds), and do not subside when changing posture. Other signs include losing the mucus plug ('show') or rupture of membranes ('water breaking')."
                },
                {
                    "heading": "Hospital Bag and Birth Planning",
                    "content": "Prepare your hospital bag by week 35. Pack medical records, ID proofs, loose cotton nursing outfits, sanitary maternity pads, newborn clothing, swaddling blankets, and feeding supplies. Discuss your birth preferences with your obstetrician, including pain relief options and emergency protocols."
                }
            ],
            "key_takeaways": [
                "Anomaly scan (18–20 weeks) and Glucose tolerance test (24–28 weeks) are essential milestones.",
                "Start daily fetal movement tracking from week 28 onward.",
                "Braxton Hicks contractions are irregular; true labor contractions grow stronger, longer, and closer together.",
                "Pack your hospital bag and finalize logistics around week 35.",
                "Contact your doctor immediately if fetal kicks decrease significantly or if water breaks."
            ],
            "myths_vs_facts": [
                {"myth": "Heartburn means your baby will be born with a full head of hair.", "fact": "Heartburn is caused by high progesterone relaxing the lower esophageal sphincter, allowing stomach acid to creep up."},
                {"myth": "Fetal movements naturally slow down close to delivery.", "fact": "While the nature of movements shifts from flips to jabs as space tightens, the overall frequency should remain steady. Decreased movement is always a medical warning sign."}
            ],
            "faqs": [
                {"question": "How many baby kicks should I feel each day in the third trimester?", "answer": "A standard benchmark is feeling at least 10 distinct movements within a 2-hour window when resting comfortably on your left side after a meal."},
                {"question": "What is the difference between water breaking and urinary incontinence?", "answer": "Amniotic fluid is clear or pale straw-colored, odorless or slightly sweet-smelling, and continues to leak continuously despite pelvic floor squeezing."}
            ],
            "sources": [
                {"name": "American College of Obstetricians and Gynecologists (ACOG)", "url": "https://www.acog.org"},
                {"name": "National Health Service (NHS) - Pregnancy Guide", "url": "https://www.nhs.uk"}
            ],
            "medical_disclaimer": "This content is educational. Consult your gynecologist for specific concerns regarding labor symptoms, fetal movements, or medical anomalies."
        },
        "body_hi": {
            "tldr": "दूसरी तिमाही में ऊर्जा वापस आती है और 18-20 हफ्तों में एनोमली स्कैन होता है। तीसरी तिमाही में बच्चे की हलचल गिनना और प्रसव की तैयारी करना मुख्य प्राथमिकताएं हैं।",
            "introduction": "दूसरी तिमाही को गर्भावस्था का सबसे सुखद समय माना जाता है, जबकि तीसरी तिमाही में प्रसव की तैयारी शुरू हो जाती है। बच्चे के विकास और डिलीवरी के लक्षणों की सही जानकारी हर माँ के लिए जरूरी है।",
            "sections": [
                {
                    "heading": "दूसरी तिमाही: ऊर्जा और पहली हलचल",
                    "content": "18 से 22 हफ्ते के बीच माँ को बच्चे की पहली हलचल महसूस होती है। 18-20 हफ्ते में एनोमली सोनोग्राफी कराई जाती है जिससे बच्चे के सभी अंगों की संपूर्ण जांच होती है। 24 से 28 हफ्ते में जेस्टेशनल डायबिटीज की जांच आवश्यक है।"
                },
                {
                    "heading": "तीसरी तिमाही: बच्चे का वजन और किक काउंट",
                    "content": "28वें हफ्ते से बच्चे का वजन तेजी से बढ़ता है। रोजाना बच्चे की हलचल (किक काउंट) गिनें—2 घंटे में कम से कम 10 हलचलें महसूस होनी चाहिए। अगर बच्चे की हलचल कम लगे तो तुरंत डॉक्टर को दिखाएं।"
                },
                {
                    "heading": "सच्चे लेबर पेन और फॉल्स पेन में अंतर",
                    "content": "फॉल्स पेन (ब्रेक्सटन हिक्स) अनियमित होते हैं और आराम करने से ठीक हो जाते हैं। असली लेबर पेन हर 5-10 मिनट में आते हैं, समय के साथ तेज होते जाते हैं और दर्द पीठ से पेट की ओर बढ़ता है।"
                },
                {
                    "heading": "हॉस्पिटल बैग की तैयारी",
                    "content": "35वें हफ्ते तक हॉस्पिटल बैग तैयार रखें। इसमें मेडिकल रिपोर्ट्स, ढीले सूती कपड़े, मैटरनिटी पैड्स, नवजात शिशु के कपड़े और जरूरी दस्तावेज रखें।"
                }
            ],
            "key_takeaways": [
                "18-20 हफ्ते का लेवल-2 स्कैन शिशु के अंगों की सुरक्षा के लिए सबसे जरूरी है।",
                "तीसरी तिमाही में रोजाना बच्चे की हलचल गिनने की आदत डालें।",
                "लेबर पेन नियमित अंतराल पर आते हैं और आराम करने से बंद नहीं होते।",
                "35वें हफ्ते तक डिलीवरी बैग और डॉक्टर की संपर्क सूची तैयार रखें।"
            ],
            "myths_vs_facts": [
                {"myth": "डिलीवरी के नजदीक आने पर बच्चे की हलचल कम हो जाती है।", "fact": "बच्चे की हलचल का प्रकार बदल सकता है, लेकिन उसकी संख्या कम नहीं होनी चाहिए। हलचल कम होना खतरे की घंटी है।"}
            ],
            "faqs": [
                {"question": "2 घंटे में कितनी किक्स सामान्य मानी जाती हैं?", "answer": "खाना खाने के बाद बाईं करवट लेटकर गिनने पर 2 घंटे में कम से कम 10 किक्स या हलचल महसूस होनी चाहिए।"}
            ],
            "sources": [
                {"name": "FOGSI", "url": "https://www.fogsi.org"},
                {"name": "NHS Maternity Services", "url": "https://www.nhs.uk"}
            ],
            "medical_disclaimer": "यह जानकारी केवल सामान्य जागरूकता हेतु है। किसी भी जटिलता पर अपनी डॉक्टर से संपर्क करें।"
        }
    },
    {
        "topic_slug": "pregnancy",
        "subtopic_slug": "nutrition",
        "title_en": "Pregnancy Diet & Nutrition: Key Nutrients, Meal Planning and Foods to Avoid",
        "title_hi": "गर्भावस्था में संपूर्ण आहार: जरूरी पोषक तत्व, डाइट चार्ट और क्या न खाएं",
        "desc_en": "Evidence-based maternal nutrition guidelines covering iron, calcium, DHA, protein requirements, and food safety standards.",
        "desc_hi": "गर्भावस्था में पोषण का संपूर्ण गाइड: आयरन, कैल्शियम, प्रोटीन, डीएचए और खाद्य सुरक्षा के जरूरी नियम।",
        "thumbnail_url": TOPIC_IMAGE_POOLS["pregnancy"][2],
        "category": "Pregnancy",
        "tags": ["Pregnancy", "Nutrition", "Diet Plan", "Vitamins"],
        "body_en": {
            "tldr": "Maternal nutrition fuels fetal organ formation and protects against gestational anaemia. Focus on 27 mg iron daily, 1000 mg calcium, 60–75 g protein, and strictly avoid unpasteurized dairy, raw eggs, and high-mercury fish.",
            "introduction": "What you eat during pregnancy directly shapes your baby's growth, brain development, and birth weight, while protecting you from anaemia, bone depletion, and gestational diabetes. A thoughtful, balanced Indian diet provides virtually all the nutrients you and your baby need.",
            "sections": [
                {
                    "heading": "Essential Micronutrients for Fetal Development",
                    "content": "Iron (27 mg/day) supports maternal blood volume expansion and prevents preterm delivery. Pair plant iron (spinach, lentils, methi) with Vitamin C (amla, lemon juice). Calcium (1000 mg/day) builds fetal bones and teeth without depleting maternal skeleton—sources include paneer, curd, ragi, and sesame. DHA (Omega-3, 200–300 mg/day) is critical for fetal brain and retinal development."
                },
                {
                    "heading": "Protein Goals: Building Blocks for Placenta and Fetus",
                    "content": "Protein needs rise to 60–75 grams daily across the second and third trimesters. In an Indian vegetarian diet, combine cereals and pulses (such as dal with rice, or rajma with roti) to create complete amino acid profiles. Add curd, paneer, sprouts, eggs, tofu, or lean fish."
                },
                {
                    "heading": "Foods to Strictly Avoid for Maternal Safety",
                    "content": "To prevent Listeria, Salmonella, and Toxoplasma infections, strictly avoid raw or undercooked eggs, raw papaya (latex can trigger uterine contractions), unpasteurized milk and soft cheeses, unwashed raw greens, and predatory fish high in mercury (king mackerel, swordfish). Limit tea and coffee to under 200 mg caffeine daily."
                },
                {
                    "heading": "Managing Blood Sugar and Gestational Diabetes Prevention",
                    "content": "Opt for low-glycaemic complex carbohydrates such as whole oats, brown rice, millets (jowar, bajra, ragi), and whole wheat over maida and refined sugars. High fibre intake (28–30 g/day) helps stabilize post-meal glucose and alleviates pregnancy constipation."
                }
            ],
            "key_takeaways": [
                "Aim for 27 mg of elemental iron and 1000 mg of calcium daily from diet and supplements.",
                "Target 60–75 grams of protein daily through lentils, dairy, eggs, and nuts.",
                "Avoid raw meats, unpasteurized milk, raw papaya, and excess caffeine.",
                "Do not take iron and calcium tablets at the same time, as calcium blocks iron absorption.",
                "Drink 2.5 to 3 liters of clean water daily to support amniotic fluid levels."
            ],
            "myths_vs_facts": [
                {"myth": "Eating saffron (kesar) milk guarantees a fair baby.", "fact": "Skin pigmentation is governed solely by genetics; saffron has antioxidant qualities but does not alter fetal skin tone."},
                {"myth": "Ghee in the 9th month lubricates the birth canal for easier delivery.", "fact": "Ghee goes into the digestive tract, not the birth canal. Excess ghee simply causes maternal weight gain and digestive distress."}
            ],
            "faqs": [
                {"question": "Can I take iron and calcium supplements together?", "answer": "No. Calcium competes with iron for absorption in the intestines. Take iron in the morning with citrus juice, and calcium at night after dinner."},
                {"question": "How much weight gain is healthy during pregnancy?", "answer": "For a woman with normal pre-pregnancy BMI, 11 to 16 kg (25–35 lbs) is standard and healthy across 40 weeks."}
            ],
            "sources": [
                {"name": "ICMR-NIN Dietary Guidelines for Pregnant Women", "url": "https://www.nin.res.in"},
                {"name": "WHO Maternal Nutrition Recommendations", "url": "https://www.who.int"}
            ],
            "medical_disclaimer": "Dietary requirements vary based on maternal BMI, blood counts, and metabolic health. Review your nutrition plan with your doctor or clinical nutritionist."
        },
        "body_hi": {
            "tldr": "गर्भावस्था में रोज 27 मिलीग्राम आयरन, 1000 मिलीग्राम कैल्शियम और 60-75 ग्राम प्रोटीन की आवश्यकता होती है। कच्चा पपीता, अधपका भोजन और अधिक चाय-कॉफी से बचें।",
            "introduction": "गर्भावस्था में सही खानपान शिशु के स्वस्थ मस्तिष्क और अंगों के विकास की नींव है। संतुलित भारतीय थाली माँ और बच्चे दोनों को स्वस्थ रखने के लिए सर्वोत्तम पोषण प्रदान करती है।",
            "sections": [
                {
                    "heading": "जरूरी विटामिन और खनिज",
                    "content": "आयरन की कमी से एनीमिया होता है, इसलिए पालक, मेथी, गुड़, चना और अनार का सेवन करें। हड्डियों के लिए कैल्शियम जरूरी है जो दूध, दही, पनीर और रागी में भरपूर होता है। आयरन और कैल्शियम की गोलियां एक साथ न खाएं।"
                },
                {
                    "heading": "प्रोटीन की मात्रा और स्रोत",
                    "content": "शिशु की कोशिकाओं के निर्माण के लिए रोज 60-70 ग्राम प्रोटीन चाहिए। दालें, राजमा, छोले, पनीर, सोयाबीन, अंडे और मेवे प्रोटीन के बेहतरीन स्रोत हैं।"
                },
                {
                    "heading": "किन चीजों से पूरी तरह परहेज करें",
                    "content": "कच्चा पपीता (गर्भाशय में संकुचन ला सकता है), कच्चा दूध, बिना धुली सब्जियां और ज्यादा कैफीन से बचें। बाहर का खुला खाना न खाएं।"
                },
                {
                    "heading": "पानी और फाइबर का महत्व",
                    "content": "दिनभर में कम से कम 2.5 से 3 लीटर पानी पिएं। छिलके वाले अनाज, फल और हरी सब्जियों का सेवन कब्ज से बचाता है।"
                }
            ],
            "key_takeaways": [
                "आयरन और कैल्शियम सप्लीमेंट के बीच कम से कम 2-3 घंटे का अंतर रखें।",
                "दालें, दही और मेवे अपने दैनिक आहार में अनिवार्य रूप से शामिल करें।",
                "दिन में 8-10 गिलास पानी पिएं ताकि एम्नियोटिक फ्लूइड का स्तर बना रहे।"
            ],
            "myths_vs_facts": [
                {"myth": "केसर वाला दूध पीने से बच्चा गोरा पैदा होता है।", "fact": "त्वचा का रंग आनुवंशिकी (जींस) पर निर्भर करता है, केसर से रंग पर कोई असर नहीं पड़ता।"},
                {"myth": "9वें महीने में घी पीने से नॉर्मल डिलीवरी आसान होती है।", "fact": "घी पाचन तंत्र में जाता है गर्भाशय में नहीं। ज्यादा घी केवल वजन बढ़ाता है।"}
            ],
            "faqs": [
                {"question": "क्या प्रेगनेंसी में चाय या कॉफी पी सकते हैं?", "answer": "हाँ, लेकिन सीमित मात्रा में (दिन में 1 कप से ज्यादा नहीं)। कैफीन की अधिक मात्रा शिशु के लिए नुकसानदेह हो सकती है।"}
            ],
            "sources": [
                {"name": "NIN / ICMR भारत", "url": "https://www.nin.res.in"},
                {"name": "FOGSI दिशानिर्देश", "url": "https://www.fogsi.org"}
            ],
            "medical_disclaimer": "यह सलाह केवल सामान्य पोषण जानकारी के लिए है। व्यक्तिगत डाइट चार्ट हेतु डॉक्टर से सलाह लें।"
        }
    },
    {
        "topic_slug": "pregnancy",
        "subtopic_slug": "pregnancy-care",
        "title_en": "High-Risk Pregnancy Warnings: Red Flag Symptoms You Should Never Ignore",
        "title_hi": "गर्भावस्था में खतरे के संकेत: वो लक्षण जिन्हें कभी नजरअंदाज न करें",
        "desc_en": "Recognize critical maternal red flags: preeclampsia, gestational hypertension, bleeding, fluid leaks, and reduced fetal movement.",
        "desc_hi": "प्री-एक्लेमप्सिया, हाई बीपी, ब्लीडिंग और पानी रिसने जैसे गंभीर लक्षणों की तुरंत पहचान और प्राथमिक कदम।",
        "thumbnail_url": TOPIC_IMAGE_POOLS["pregnancy"][3],
        "category": "Pregnancy",
        "tags": ["Pregnancy", "Emergency", "Preeclampsia", "Maternal Health"],
        "body_en": {
            "tldr": "Immediate medical attention is required for vaginal bleeding, severe persistent headaches with vision changes, sudden facial swelling, leaking amniotic fluid, or marked reduction in fetal movements.",
            "introduction": "While most pregnancies proceed smoothly, knowing potential complications and their early warning signals empowers mothers and families to take swift action, protecting both maternal and fetal lives.",
            "sections": [
                {
                    "heading": "Preeclampsia and Gestational Hypertension",
                    "content": "Preeclampsia affects 5–8% of pregnancies and involves high blood pressure after 20 weeks accompanied by organ strain. Red flag symptoms include throbbing headaches that do not respond to paracetamol, visual disturbances (blurriness, flashing lights, floaters), sudden swelling of the face and hands, and severe pain directly below the right ribs. Left untreated, it can lead to eclampsia (seizures) or placental abruption."
                },
                {
                    "heading": "Vaginal Bleeding at Any Gestational Stage",
                    "content": "While light implantation spotting in early weeks is common, significant bright red bleeding, passing clots, or bleeding accompanied by abdominal cramps warrants emergency evaluation. In later pregnancy, bleeding can signify placenta previa (placenta covering cervix) or placental abruption (premature detachment of placenta)."
                },
                {
                    "heading": "Premature Rupture of Membranes and Infection Risks",
                    "content": "A sudden gush or steady trickle of clear fluid from the vagina before 37 weeks suggests preterm premature rupture of membranes (PPROM). This increases the risk of intrauterine infection and preterm birth. Avoid inserting anything into the vagina and proceed to labor and delivery immediately."
                },
                {
                    "heading": "Reduced Fetal Movements",
                    "content": "Fetal movements reflect fetal oxygenation and well-being. If your baby's kicks drop below 10 in 2 hours when resting after a cold drink or meal, contact your delivery unit immediately for a non-stress test (NST) and biophysical profile ultrasound."
                }
            ],
            "key_takeaways": [
                "Severe headache with vision changes and facial puffiness indicates possible preeclampsia.",
                "Any bright red vaginal bleeding requires urgent hospital triage.",
                "Do not wait until morning if you notice a steep drop in fetal movements.",
                "Leaking fluid before labor requires immediate sterile medical assessment."
            ],
            "myths_vs_facts": [
                {"myth": "Swelling in the feet is always a medical emergency.", "fact": "Mild ankle swelling late in the day is normal dependent edema. Sudden swelling of the face, hands, and eyelids accompanied by high BP is the true red flag."},
                {"myth": "You should wait 24 hours to see if baby kicks return.", "fact": "Never wait 24 hours. Early intervention within hours can prevent stillbirth."}
            ],
            "faqs": [
                {"question": "What blood pressure reading is considered dangerous in pregnancy?", "answer": "A reading of 140/90 mmHg or higher on two separate occasions 4 hours apart requires prompt medical evaluation. A reading over 160/110 mmHg is an acute hypertensive emergency."},
                {"question": "Can preeclampsia develop after delivery?", "answer": "Yes. Postpartum preeclampsia can emerge up to 6 weeks following birth, presenting with severe headaches and elevated blood pressure."}
            ],
            "sources": [
                {"name": "ACOG Practice Bulletin: Gestational Hypertension and Preeclampsia", "url": "https://www.acog.org"},
                {"name": "WHO Recommendations for Prevention and Treatment of Pre-eclampsia", "url": "https://www.who.int"}
            ],
            "medical_disclaimer": "This information does not replace clinical triage. In the event of acute bleeding, severe pain, or fever, proceed to the nearest emergency obstetric unit immediately."
        },
        "body_hi": {
            "tldr": "तेज सिरदर्द, आंखों के आगे धुंधलापन, चेहरे पर अचानक सूजन, योनि से रक्तस्राव या बच्चे की हलचल में भारी कमी होने पर बिना देर किए अस्पताल जाएं।",
            "introduction": "गर्भावस्था के दौरान शरीर के संकेतों को समझना जीवन रक्षक साबित हो सकता है। कुछ लक्षण ऐसे होते हैं जिन्हें सामान्य मानकर नजरअंदाज करना माँ और बच्चे दोनों के लिए जोखिम भरा हो सकता है।",
            "sections": [
                {
                    "heading": "प्री-एक्लेमप्सिया (हाई ब्लड प्रेशर का खतरा)",
                    "content": "20 हफ्ते के बाद तेज सिरदर्द होना, आंखों के सामने तारे या रोशनी चमकना, चेहरे और हाथों पर अचानक सूजन आना और पसलियों के नीचे तेज दर्द होना हाई बीपी के गंभीर संकेत हैं। इसका तुरंत इलाज जरूरी है।"
                },
                {
                    "heading": "रक्तस्राव (ब्लीडिंग) और पेट में तेज ऐंठन",
                    "content": "किसी भी महीने में तेज लाल खून आना या थक्के गिरना सामान्य नहीं है। यह प्लेसेंटा के खिसकने या अलग होने का संकेत हो सकता है।"
                },
                {
                    "heading": "समय से पहले पानी की थैली फटना",
                    "content": "अगर 37 हफ्ते से पहले योनि से लगातार पानी जैसा तरल बहने लगे, तो यह संक्रमण और समय पूर्व प्रसव का जोखिम बढ़ा सकता है।"
                },
                {
                    "heading": "बच्चे की हलचल में अचानक भारी कमी",
                    "content": "यदि बच्चा सामान्य से बहुत कम हलचल कर रहा हो, तो अगले दिन का इंतजार किए बिना तुरंत डॉक्टर से संपर्क करें और सीटीजी (दिल की धड़कन की जांच) कराएं।"
                }
            ],
            "key_takeaways": [
                "तेज सिरदर्द और नजर में धुंधलापन हाई ब्लड प्रेशर का गंभीर लक्षण हो सकता है।",
                "ब्लीडिंग होने पर तुरंत इमरजेंसी में डॉक्टर को दिखाएं।",
                "बच्चे की हलचल कम होने पर तुरंत अस्पताल जाएं, सुबह का इंतजार न करें।"
            ],
            "myths_vs_facts": [
                {"myth": "पैरों में हल्की सूजन हमेशा खतरनाक होती है।", "fact": "शाम के समय पैरों में हल्की सूजन सामान्य है, लेकिन चेहरे और आंखों के आसपास अचानक सूजन आना खतरे का संकेत है।"}
            ],
            "faqs": [
                {"question": "गर्भावस्था में कौन सा बीपी खतरनाक माना जाता है?", "answer": "140/90 mmHg या इससे अधिक का बीपी तुरंत डॉक्टर को दिखाना चाहिए। 160/110 mmHg इमरजेंसी स्थिति है।"}
            ],
            "sources": [
                {"name": "WHO Maternal Health", "url": "https://www.who.int"},
                {"name": "FOGSI Guidelines", "url": "https://www.fogsi.org"}
            ],
            "medical_disclaimer": "यह जानकारी आपातकालीन चिकित्सा का विकल्प नहीं है। गंभीर लक्षणों पर नजदीकी मैटरनिटी अस्पताल जाएं।"
        }
    },
    {
        "topic_slug": "pregnancy",
        "subtopic_slug": "pregnancy-care",
        "title_en": "The Fourth Trimester: Physical Recovery, Mental Health & Postpartum Healing",
        "title_hi": "चौथी तिमाही (पोस्टपार्टम रिकवरी): शारीरिक स्वास्थ्य, मानसिक सेहत और देखभाल",
        "desc_en": "Essential care for weeks 1 through 12 after childbirth: lochia bleeding, perineal care, c-section healing, breastfeeding, and postpartum depression.",
        "desc_hi": "डिलीवरी के बाद के 12 हफ्तों की पूरी देखभाल: टांके भरना, ब्लीडिंग (लोचिया), स्तनपान और पोस्टपार्टम डिप्रेशन से बचाव।",
        "thumbnail_url": TOPIC_IMAGE_POOLS["pregnancy"][4],
        "category": "Pregnancy",
        "tags": ["Postpartum", "Fourth Trimester", "Mental Health", "Newborn Care"],
        "body_en": {
            "tldr": "The postpartum period demands as much care as pregnancy. Key milestones include managing lochia discharge (lasts 4–6 weeks), caring for c-section or perineal incisions, establishing breastfeeding, and monitoring for postpartum depression (PPD).",
            "introduction": "Childbirth is not the finish line; it is the start of the 'fourth trimester.' As your body undergoes steep hormonal drops and begins tissue repair, prioritizing maternal rest and mental wellbeing is essential for the entire family's health.",
            "sections": [
                {
                    "heading": "Uterine Involution and Lochia Bleeding",
                    "content": "After delivery, the uterus contracts back to its pre-pregnancy size over 6 weeks. You will experience vaginal bleeding (lochia), progressing from bright red (lochia rubra) for the first few days, to brownish-pink (lochia serosa), and finally yellowish-white (lochia alba) for up to 6 weeks. Saturating more than one pad an hour or passing golf-ball sized clots requires immediate medical attention."
                },
                {
                    "heading": "Perineal Care and C-Section Wound Healing",
                    "content": "For vaginal births with tears or episiotomies, use warm water peri-bottles after urinating, take sitz baths, and use chilled witch hazel pads. For caesarean births, keep the incision line clean and dry, avoid lifting anything heavier than your baby for 6 weeks, and watch for redness, warmth, foul discharge, or opening of surgical stitches."
                },
                {
                    "heading": "Distinguishing 'Baby Blues' from Postpartum Depression (PPD)",
                    "content": "Up to 80% of new mothers experience 'baby blues'—mood swings, weepiness, and anxiety that peak around day 4–5 and resolve within 2 weeks as hormones stabilize. If depressive symptoms, overwhelming guilt, inability to bond with baby, or intrusive thoughts persist beyond 2 weeks, it indicates postpartum depression (affecting 1 in 7 mothers). PPD is medical and highly treatable with therapy and safe medications."
                },
                {
                    "heading": "Rest, Pelvic Recovery and Nutrition",
                    "content": "Resist societal pressure to 'bounce back.' Continue iron, calcium, and vitamin D supplementation while breastfeeding. Consume nutrient-dense, easily digestible foods like dalia, moong dal khichdi, nuts, and soups. Delay rigorous abdominal exercises until cleared at your 6-week postpartum review."
                }
            ],
            "key_takeaways": [
                "Lochia bleeding normally lasts 4 to 6 weeks, gradually lightening in color and volume.",
                "Baby blues resolve within 14 days; persistent sadness or anxiety warrants screening for PPD.",
                "Keep caesarean incisions dry and clean; avoid lifting heavy items for 6 weeks.",
                "Maintain high hydration and iron-rich nutrition while lactating.",
                "Attend your mandatory 6-week postpartum maternal checkup."
            ],
            "myths_vs_facts": [
                {"myth": "Postpartum depression means you don't love your baby.", "fact": "PPD is a neurobiological and hormonal disorder, not a character flaw or a measure of maternal love."},
                {"myth": "Breastfeeding acts as a 100% reliable contraceptive.", "fact": "While lactational amenorrhea offers some protection if feeding exclusively every 3–4 hours, ovulation can precede your first period. Reliable postpartum contraception should be discussed with your doctor."}
            ],
            "faqs": [
                {"question": "When can I resume sexual intercourse after giving birth?", "answer": "Obstetricians generally recommend waiting until the 6-week postpartum checkup to allow the cervix to close and perineal or uterine wounds to heal completely."},
                {"question": "What are the warning signs of postpartum infection?", "answer": "Fever above 100.4°F (38°C), foul-smelling lochia discharge, severe abdominal tenderness, or localized redness and pain in the breast (mastitis)."}
            ],
            "sources": [
                {"name": "ACOG Committee Opinion: Optimizing Postpartum Care", "url": "https://www.acog.org"},
                {"name": "WHO Postpartum Maternal Care Guidelines", "url": "https://www.who.int"}
            ],
            "medical_disclaimer": "This content is educational. If experiencing thoughts of self-harm, severe sadness, or fever after birth, contact your doctor or helpline immediately."
        },
        "body_hi": {
            "tldr": "डिलीवरी के बाद 4-6 हफ्ते तक ब्लीडिंग (लोचिया) होना सामान्य है। टांकों की सफाई, पौष्टिक आहार, पर्याप्त आराम और मानसिक स्वास्थ्य का ध्यान रखना उतना ही जरूरी है जितना प्रेगनेंसी के दौरान।",
            "introduction": "डिलीवरी के बाद के पहले 12 हफ्तों को चौथी तिमाही कहा जाता है। इस दौरान शरीर अपने पहले वाले रूप में लौटने की प्रक्रिया शुरू करता है और माँ को विशेष देखभाल की आवश्यकता होती है।",
            "sections": [
                {
                    "heading": "डिलीवरी के बाद ब्लीडिंग (लोचिया)",
                    "content": "डिलीवरी के बाद 4 से 6 हफ्ते तक रक्तस्राव होता है। शुरुआत में यह गहरा लाल होता है और धीरे-धीरे हल्का होकर सफेद-पीला हो जाता है। अगर 1 घंटे में 1 से ज्यादा पैड भीग जाए या बड़े थक्के आएं तो तुरंत डॉक्टर को बताएं।"
                },
                {
                    "heading": "टांकों की देखभाल (नॉर्मल और सिजेरियन)",
                    "content": "सिजेरियन डिलीवरी के टांकों को सूखा और साफ रखें। 6 हफ्ते तक भारी वजन न उठाएं। नॉर्मल डिलीवरी के टांकों के लिए गुनगुने पानी का सिट्ज़ बाथ लें और ढीले सूती अंतःवस्त्र पहनें।"
                },
                {
                    "heading": "बेबी ब्लूज और पोस्टपार्टम डिप्रेशन (PPD)",
                    "content": "डिलीवरी के शुरुआती 10-14 दिनों में रोना आना और चिड़चिड़ापन होना सामान्य 'बेबी ब्लूज' है। लेकिन अगर उदासी 2 हफ्ते से ज्यादा रहे, बच्चे से जुड़ाव न महसूस हो या घबराहट बढ़े, तो यह पोस्टपार्टम डिप्रेशन हो सकता है। इसमें मनोचिकित्सक की मदद लेना जरूरी है।"
                },
                {
                    "heading": "आहार और आराम की जरूरत",
                    "content": "दूध पिलाने वाली माताओं को रोज 500 अतिरिक्त कैलोरी और पर्याप्त तरल पदार्थों की जरूरत होती है। दलिया, हरी सब्जियां, मेवे, दूध और सूप पिएं। जब बच्चा सोए, तब आराम करें।"
                }
            ],
            "key_takeaways": [
                "डिलीवरी के बाद 6 हफ्ते तक शरीर को पूरा आराम और पौष्टिक भोजन दें।",
                "टांकों में पस, लाली या तेज दर्द होने पर तुरंत डॉक्टर से मिलें।",
                "2 हफ्ते से ज्यादा उदासी रहने पर डॉक्टर से खुलकर बात करें—डिप्रेशन का इलाज संभव है।",
                "6 हफ्ते पूरे होने पर डॉक्टर से पोस्टपार्टम जांच जरूर कराएं।"
            ],
            "myths_vs_facts": [
                {"myth": "डिप्रेशन होना कमजोरी या बुरी माँ होने की निशानी है।", "fact": "यह हार्मोनल और जैविक बदलावों की वजह से होता है। इसका इलाज संभव है और इसमें माँ की कोई गलती नहीं होती।"}
            ],
            "faqs": [
                {"question": "क्या स्तनपान कराने से प्रेगनेंसी नहीं होती?", "answer": "स्तनपान से कुछ हद तक सुरक्षा मिलती है, लेकिन यह 100% सुरक्षित गर्भनिरोधक नहीं है। पहली माहवारी से पहले भी गर्भ ठहर सकता है।"}
            ],
            "sources": [
                {"name": "WHO Postpartum Guidelines", "url": "https://www.who.int"},
                {"name": "FOGSI", "url": "https://www.fogsi.org"}
            ],
            "medical_disclaimer": "यह जानकारी सामान्य देखभाल के लिए है। किसी भी स्वास्थ्य समस्या पर अपने डॉक्टर से संपर्क करें।"
        }
    },

    # =========================================================================
    # REPRODUCTIVE HEALTH (6 articles)
    # =========================================================================
    {
        "topic_slug": "reproductive-health",
        "subtopic_slug": "general",
        "title_en": "Female Pelvic and Reproductive Anatomy: An Empowering Guide to Your Body",
        "title_hi": "महिला प्रजनन और पेल्विक शारीरिक संरचना: अपने शरीर को समझें",
        "desc_en": "Clear, stigma-free medical explanation of the vulva, vagina, cervix, uterus, fallopian tubes, and ovaries.",
        "desc_hi": "स्त्री जननांगों की संरचना: वल्वा, योनि, गर्भाशय, फैलोपियन ट्यूब और अंडाशय का सरल वैज्ञानिक विवरण।",
        "thumbnail_url": TOPIC_IMAGE_POOLS["reproductive-health"][0],
        "category": "Reproductive Health",
        "tags": ["Reproductive Health", "Anatomy", "Women's Health", "Pelvic Health"],
        "body_en": {
            "tldr": "Understanding the difference between the external vulva and internal vagina, cervix, uterus, and ovaries fosters body literacy, reduces stigma, and helps you notice anatomical red flags early.",
            "introduction": "For generations, female reproductive anatomy has been shrouded in euphemisms and embarrassment. In reality, the female reproductive system is a remarkable, self-regulating biological system. Knowing how each structure functions allows you to advocate for your healthcare with confidence.",
            "sections": [
                {
                    "heading": "External Anatomy: The Vulva",
                    "content": "The vulva encompasses all external genitalia: the labia majora (outer lips), labia minora (inner lips), clitoris (a sensitive organ with over 8,000 nerve endings dedicated to sexual pleasure), urethra (opening for urination), and vaginal opening. The vulva is external; confusing it with the vagina is a widespread anatomical misconception."
                },
                {
                    "heading": "Internal Canal: The Self-Cleaning Vagina",
                    "content": "The vagina is an elastic muscular canal connecting the vulva to the cervix. It maintains an acidic pH (3.8–4.5) populated by beneficial Lactobacillus bacteria that ward off pathogens. The vagina is self-cleaning through natural physiological discharge. Douching or using internal chemical washes disrupts this microbiome and causes bacterial vaginosis."
                },
                {
                    "heading": "The Gatekeeper and Womb: Cervix and Uterus",
                    "content": "The cervix is the lower, narrow neck of the uterus projecting into the vagina. It produces mucus that changes texture across your cycle (thin and stretchy during ovulation to facilitate sperm transport, thick and acidic during the luteal phase to block bacteria). The uterus (womb) is a hollow, pear-shaped muscular organ where a fertilized egg implants and develops during pregnancy."
                },
                {
                    "heading": "Ovaries and Fallopian Tubes",
                    "content": "Women have two ovaries located on either side of the uterus. They produce hormones (estrogen and progesterone) and store hundreds of thousands of immature follicles. Each month, one mature egg is released during ovulation and travels down the fallopian tube, where fertilization typically occurs."
                }
            ],
            "key_takeaways": [
                "The vulva is external; the vagina is internal and self-cleaning.",
                "Healthy vaginal pH is naturally acidic (3.8–4.5) maintained by Lactobacillus bacteria.",
                "Never douche or wash inside the vagina; external washing with plain water is sufficient.",
                "The cervix changes position and mucus consistency across your menstrual cycle.",
                "Ovaries govern both hormonal equilibrium and fertility."
            ],
            "myths_vs_facts": [
                {"myth": "The vagina needs scented feminine washes to stay clean.", "fact": "The vagina is entirely self-cleaning. Chemical soaps disrupt healthy flora, causing odor, infections, and irritation."},
                {"myth": "All women have identical vulva appearances.", "fact": "Vulvas naturally vary widely in size, color, asymmetry, and shape; diversity is completely normal."}
            ],
            "faqs": [
                {"question": "How should I clean my genital area properly?", "answer": "Wash only the external vulva with warm water or a gentle fragrance-free soap. Never wash or douche inside the vaginal canal."},
                {"question": "Where does vaginal discharge come from?", "answer": "It is produced by glands in the cervix and vaginal walls to flush out dead cells and keep the vaginal ecosystem healthy."}
            ],
            "sources": [
                {"name": "American College of Obstetricians and Gynecologists (ACOG)", "url": "https://www.acog.org"},
                {"name": "Mayo Clinic Female Reproductive System Overview", "url": "https://www.mayoclinic.org"}
            ],
            "medical_disclaimer": "This content is educational. Consult a gynecologist if you observe abnormal lumps, persistent itching, or unexplained pelvic pain."
        },
        "body_hi": {
            "tldr": "वल्वा बाहरी जननांग है और योनि (वजाइना) अंदरूनी मार्ग है जो अपने आप साफ होती है। अंदरूनी साबुन या डूश का इस्तेमाल संक्रमण को बढ़ावा देता है।",
            "introduction": "महिला प्रजनन अंगों की सही जानकारी संकोच और भ्रांतियों को दूर करती है। अपने शरीर की बनावट और कार्यप्रणाली को जानकर आप अपनी सेहत की बेहतर देखभाल कर सकती हैं।",
            "sections": [
                {
                    "heading": "बाहरी अंग: वल्वा (Vulva)",
                    "content": "बाहरी जननांगों को वल्वा कहा जाता है, जिसमें लेबिया (होंठ), क्लिटोरिस (संवेदनशील अंग) और मूत्र मार्ग शामिल हैं। हर महिला के वल्वा का आकार और रंग प्राकृतिक रूप से अलग होता है।"
                },
                {
                    "heading": "अंदरूनी मार्ग: योनि (वजाइना)",
                    "content": "योनि एक लचीली नली है जो गर्भाशय ग्रीवा (सर्विक्स) से जुड़ती है। यह एसिडिक (पीएच 3.8-4.5) होती है और अच्छे बैक्टीरिया (लैक्टोबैसिलस) संक्रमण से रक्षा करते हैं। योनि खुद को प्राकृतिक स्राव से साफ रखती है।"
                },
                {
                    "heading": "सर्विक्स और गर्भाशय (बच्चेदानी)",
                    "content": "सर्विक्स गर्भाशय का निचला मुख है जो संक्रमण को अंदर जाने से रोकता है। गर्भाशय एक नाशपाती के आकार का अंग है जिसमें बच्चा 9 महीने तक पलता और बढ़ता है।"
                },
                {
                    "heading": "अंडाशय (ओवरीज) और फैलोपियन ट्यूब",
                    "content": "ओवरीज में अंडे बनते हैं और यह एस्ट्रोजन और प्रोजेस्टेरोन हार्मोन बनाती हैं। महीने में एक बार अंडा निकलकर फैलोपियन ट्यूब में आता है जहाँ गर्भधारण होता है।"
                }
            ],
            "key_takeaways": [
                "योनि अंदर से खुद साफ होती है, इसे किसी खुशबूदार साबुन से धोने की जरूरत नहीं होती।",
                "बाहरी हिस्से को केवल सादे गुनगुने पानी से धोना सबसे सुरक्षित है।",
                "सामान्य सफेद पानी (डिस्चार्ज) संक्रमण से बचाने का प्राकृतिक तरीका है।"
            ],
            "myths_vs_facts": [
                {"myth": "योनि को साफ रखने के लिए इंटिमेट वॉश का अंदरूनी इस्तेमाल जरूरी है।", "fact": "अंदरूनी साबुन प्राकृतिक पीएच और अच्छे बैक्टीरिया को नष्ट कर देता है जिससे संक्रमण बढ़ जाता है।"}
            ],
            "faqs": [
                {"question": "जननांगों की सही सफाई कैसे करें?", "answer": "केवल बाहरी हिस्से को हल्के गुनगुने पानी से धोएं। अंदर कुछ भी न डालें और सूती अंडरवियर पहनें।"}
            ],
            "sources": [
                {"name": "ACOG Patient Education", "url": "https://www.acog.org"},
                {"name": "FOGSI", "url": "https://www.fogsi.org"}
            ],
            "medical_disclaimer": "यह सामग्री शैक्षिक उद्देश्य के लिए है। किसी भी असामान्यता पर गायनेकोलॉजिस्ट से परामर्श लें।"
        }
    },
    {
        "topic_slug": "reproductive-health",
        "subtopic_slug": "general",
        "title_en": "Vaginal Infections Demystified: Yeast Infection vs Bacterial Vaginosis (BV)",
        "title_hi": "योनि संक्रमण की पहचान: यीस्ट इन्फेक्शन बनाम बैक्टीरियल वेजिनोसिस (BV)",
        "desc_en": "Learn symptoms, causes, discharge differences, and medical treatments for the two most common vaginal conditions.",
        "desc_hi": "सफेद पानी, खुजली और बदबू के कारण: यीस्ट और BV के बीच अंतर, जांच और सुरक्षित डॉक्टरी उपचार।",
        "thumbnail_url": TOPIC_IMAGE_POOLS["reproductive-health"][1],
        "category": "Reproductive Health",
        "tags": ["Infections", "Yeast Infection", "Bacterial Vaginosis", "Hygiene"],
        "body_en": {
            "tldr": "Yeast infections cause intense itching and thick, white 'cottage cheese' discharge without odor. Bacterial Vaginosis (BV) causes thin, grayish-white discharge with a distinct fishy odor. Both are non-STIs and treatable.",
            "introduction": "Almost every woman experiences vaginal itching, discharge changes, or irritation at some point in her life. The two most common causes—Candida yeast overgrowth and Bacterial Vaginosis—have distinctly different treatments. Misidentifying them leads to ineffective over-the-counter treatment and chronic recurrence.",
            "sections": [
                {
                    "heading": "Yeast Infections (Vaginal Candidiasis)",
                    "content": "Caused by an overgrowth of Candida albicans fungus when normal balance is disturbed (often post-antibiotics, during pregnancy, with high blood sugar, or from wearing damp synthetic clothing). Cardinal signs: intense vulvar itching, burning during urination, redness, and thick, clumpy white discharge resembling cottage cheese without a strong odor. Treatment requires oral fluconazole or antifungal pessaries (clotrimazole)."
                },
                {
                    "heading": "Bacterial Vaginosis (BV)",
                    "content": "BV occurs when protective Lactobacillus bacteria are outnumbered by anaerobic bacteria (like Gardnerella vaginalis). Symptoms include thin, watery grayish-white discharge and a prominent 'fishy' odor that worsens after intercourse or menstruation. BV is rarely itchy. Treatment requires prescription antibiotics (oral metronidazole or clindamycin cream); antifungals will not cure BV."
                },
                {
                    "heading": "When Discharge Indicates Trichomoniasis or STIs",
                    "content": "If discharge is frothy, greenish-yellow, accompanied by strawberry cervix spots, painful intercourse, or severe pelvic ache, it may indicate Trichomoniasis (a parasitic STI) or Chlamydia/Gonorrhea. These require dual-partner antibiotic treatment."
                },
                {
                    "heading": "Prevention and Protecting Vaginal Flora",
                    "content": "Wear breathable 100% cotton underwear. Change out of sweaty gym wear or wet swimsuits promptly. Wipe from front to back after using the toilet. Avoid scented pads, panty liners with perfumes, and vaginal steaming. Consider oral probiotics containing Lactobacillus rhamnosus GR-1 and Lactobacillus reuteri RC-14."
                }
            ],
            "key_takeaways": [
                "Yeast infections feature intense itch and thick cottage-cheese discharge without odor.",
                "Bacterial Vaginosis features thin grayish discharge and a strong fishy odor without severe itch.",
                "Antifungals do not treat BV, and antibiotics do not treat yeast.",
                "Always consult a doctor for microscopic or swab confirmation before self-treating.",
                "Wipe front to back and wear breathable cotton underwear to prevent recurrences."
            ],
            "myths_vs_facts": [
                {"myth": "Vaginal infections always mean you have an STI or were unfaithful.", "fact": "Neither yeast infections nor BV are classified as STIs; they result from internal microbiome imbalances."},
                {"myth": "Inserting garlic cloves or tea tree oil cures yeast infections.", "fact": "Placing household items into the vagina causes chemical burns, severe allergic dermatitis, and exacerbates infection."}
            ],
            "faqs": [
                {"question": "Why do I get a yeast infection every time I take antibiotics?", "answer": "Broad-spectrum antibiotics kill beneficial bacteria in your vagina alongside target bacteria, allowing Candida yeast to multiply unchecked."},
                {"question": "Can BV affect pregnancy?", "answer": "Yes, untreated BV during pregnancy increases the risk of preterm labor and low birth weight, making medical treatment crucial."}
            ],
            "sources": [
                {"name": "Centers for Disease Control and Prevention (CDC) - Vaginitis", "url": "https://www.cdc.gov"},
                {"name": "NHS Guide to Vaginal Discharge and Thrush", "url": "https://www.nhs.uk"}
            ],
            "medical_disclaimer": "Self-diagnosis of vaginal infections is inaccurate in over 50% of cases. Consult your doctor for an accurate diagnosis."
        },
        "body_hi": {
            "tldr": "यीस्ट इन्फेक्शन में तेज खुजली और बिना गंध वाला दही जैसा गाढ़ा स्राव होता है। BV में पतला स्राव और मछली जैसी तेज बदबू आती है। दोनों का इलाज अलग-अलग दवाओं से होता है।",
            "introduction": "सफेद पानी में बदलाव, खुजली और दुर्गंध महिलाओं में होने वाली आम समस्याएं हैं। यीस्ट और बैक्टीरियल वेजिनोसिस दो अलग संक्रमण हैं, और सही पहचान के बिना गलत दवा लेना समस्या को बढ़ा सकता है।",
            "sections": [
                {
                    "heading": "यीस्ट इन्फेक्शन (कैंडिडा फंगल संक्रमण)",
                    "content": "यह फंगस के बढ़ने से होता है, खासकर एंटीबायोटिक दवा लेने के बाद या गीले कपड़े पहनने से। इसके मुख्य लक्षण हैं: तेज खुजली, पेशाब में जलन, और बिना किसी गंध का दही जैसा सफेद गाढ़ा डिस्चार्ज। इसका इलाज एंटीफंगल दवाओं से होता है।"
                },
                {
                    "heading": "बैक्टीरियल वेजिनोसिस (BV)",
                    "content": "यह तब होता है जब योनि के अच्छे बैक्टीरिया कम हो जाते हैं और हानिकारक बैक्टीरिया बढ़ जाते हैं। इसमें पतला धूसर-सफेद डिस्चार्ज होता है और मछली जैसी तेज बदबू आती है। इसमें खुजली कम होती है। इसका इलाज एंटीबायोटिक दवाओं से होता है।"
                },
                {
                    "heading": "किन लक्षणों पर तुरंत डॉक्टर से मिलें",
                    "content": "अगर डिस्चार्ज हरा या पीला हो, झागदार हो, पेट के निचले हिस्से में दर्द हो या संबंध बनाते समय तेज दर्द हो, तो यह अन्य संक्रमणों का संकेत हो सकता है।"
                },
                {
                    "heading": "बचाव के आसान घरेलू नियम",
                    "content": "सूती (कॉटन) अंडरवियर पहनें। पसीने वाले कपड़े तुरंत बदलें। शौच के बाद हमेशा आगे से पीछे की तरफ धोएं। खुशबूदार पैड्स या साबुन का उपयोग न करें।"
                }
            ],
            "key_takeaways": [
                "दही जैसा डिस्चार्ज और तेज खुजली यीस्ट संक्रमण के लक्षण हैं।",
                "पतला डिस्चार्ज और तेज बदबू बैक्टीरियल वेजिनोसिस का संकेत है।",
                "बिना डॉक्टर को दिखाए मेडिकल स्टोर से कोई भी क्रीम या गोली न लें।"
            ],
            "myths_vs_facts": [
                {"myth": "सफेद पानी आना हमेशा गुप्त रोग या कमजोरी का लक्षण है।", "fact": "हल्का पारदर्शी या सफेद स्राव बिल्कुल सामान्य और प्राकृतिक है। केवल बदबू, रंग बदलने या खुजली पर ही इलाज की जरूरत होती है।"}
            ],
            "faqs": [
                {"question": "एंटीबायोटिक लेने के बाद खुजली क्यों होती है?", "answer": "दवाएं अच्छे बैक्टीरिया को मार देती हैं, जिससे फंगस तेजी से बढ़ जाती है और यीस्ट संक्रमण हो जाता है।"}
            ],
            "sources": [
                {"name": "CDC Vaginitis Guidelines", "url": "https://www.cdc.gov"},
                {"name": "FOGSI", "url": "https://www.fogsi.org"}
            ],
            "medical_disclaimer": "यह सामग्री केवल जागरूकता के लिए है। उचित इलाज के लिए डॉक्टर से जांच करवाएं।"
        }
    },
    {
        "topic_slug": "reproductive-health",
        "subtopic_slug": "sexual-health",
        "title_en": "Cervical Health & Pap Tests: HPV Vaccination, Screening and Cancer Prevention",
        "title_hi": "सर्वाइकल स्वास्थ्य और पैप स्मीयर: HPV वैक्सीन और सर्वाइकल कैंसर से बचाव",
        "desc_en": "How HPV causes cervical abnormalities, why routine Pap smears save lives, and the truth about HPV vaccines for women and girls.",
        "desc_hi": "सर्वाइकल कैंसर की रोकथाम: HPV टीका कब लगवाएं, पैप स्मीयर जांच क्यों जरूरी है और शुरुआती लक्षण।",
        "thumbnail_url": TOPIC_IMAGE_POOLS["reproductive-health"][2],
        "category": "Reproductive Health",
        "tags": ["Cervical Health", "HPV Vaccine", "Pap Smear", "Cancer Prevention"],
        "body_en": {
            "tldr": "Cervical cancer is almost 100% preventable through HPV vaccination and regular Pap/HPV DNA screening every 3–5 years starting at age 21–25.",
            "introduction": "Cervical cancer is the second most common cancer among Indian women, claiming over 75,000 lives annually in India alone. The tragedy is that cervical cancer is almost entirely preventable. With modern HPV vaccination and routine cervical screening, no woman should lose her life to this disease.",
            "sections": [
                {
                    "heading": "Understanding HPV and Cervical Carcinogenesis",
                    "content": "Nearly all cervical cancers (>99%) are triggered by persistent infection with high-risk strains of Human Papillomavirus (chiefly HPV 16 and 18). HPV is an extremely common sexually transmitted virus; in most people, the immune system clears it within two years. In a small fraction, however, high-risk HPV persists and causes gradual precancerous changes (dysplasia or CIN) over 10 to 15 years before turning malignant."
                },
                {
                    "heading": "The Life-Saving Power of Screening: Pap Smear and HPV DNA",
                    "content": "Because cervical cancer takes a decade to develop, routine screening detects cellular changes years before cancer develops. A Pap smear collects cells from the cervix to detect abnormalities. An HPV DNA test checks directly for the virus. International guidelines recommend screening every 3 years (for Pap smear alone) or every 5 years (for HPV DNA co-testing) starting at age 21 or 25."
                },
                {
                    "heading": "The HPV Vaccine: Safe, Powerful Cancer Prevention",
                    "content": "The HPV vaccine protects against high-risk strains (types 16, 18, and others). It is recommended for girls and boys starting at age 9 to 14 (2 doses), and up to age 26 (3 doses). Women up to age 45 can also receive the vaccine after consulting their doctor. Indigenous vaccines like Cervavac have made protection affordable in India."
                },
                {
                    "heading": "Warning Signs That Demand Clinical Review",
                    "content": "Early cervical precancers cause zero symptoms—which is why screening is vital. When symptoms do emerge, they include abnormal bleeding between periods, bleeding after sexual intercourse, postmenopausal bleeding, and persistent foul-smelling vaginal discharge."
                }
            ],
            "key_takeaways": [
                "Cervical cancer is caused by persistent infection with high-risk HPV strains.",
                "Vaccination protects best when administered between ages 9 and 14, but is approved up to age 45.",
                "Routine Pap smears or HPV DNA tests are recommended every 3 to 5 years.",
                "Bleeding after intercourse or post-menopausal bleeding is a red flag requiring immediate investigation."
            ],
            "myths_vs_facts": [
                {"myth": "Only women with multiple partners need HPV screening.", "fact": "HPV is so prevalent that almost all sexually active individuals contract it at some point, even with only one lifetime partner."},
                {"myth": "A Pap smear is painful and invasive.", "fact": "A Pap smear takes less than 2 minutes, involves mild pelvic pressure, and causes negligible discomfort."}
            ],
            "faqs": [
                {"question": "Can I get the HPV vaccine if I am already married or sexually active?", "answer": "Yes. While most effective before sexual debut, the vaccine still protects against HPV strains you have not yet been exposed to."},
                {"question": "Does an abnormal Pap smear mean I have cancer?", "answer": "No. The vast majority of abnormal Pap smears reflect mild inflammation or precancerous cellular changes that can be easily monitored or treated in clinic before becoming cancerous."}
            ],
            "sources": [
                {"name": "World Health Organization (WHO) Global Cervical Cancer Elimination Initiative", "url": "https://www.who.int"},
                {"name": "Indian Council of Medical Research (ICMR) Cervical Cancer Guidelines", "url": "https://www.icmr.nic.in"}
            ],
            "medical_disclaimer": "This information is educational. Consult your gynecologist to schedule an HPV vaccine or routine cervical screening test."
        },
        "body_hi": {
            "tldr": "सर्वाइकल कैंसर लगभग पूरी तरह से रोका जा सकता है। 9 से 14 वर्ष की लड़कियों को HPV वैक्सीन लगवाने और 21-25 वर्ष के बाद हर 3-5 साल में पैप स्मीयर जांच कराने से इसका खतरा खत्म हो जाता है।",
            "introduction": "भारत में महिलाओं में सर्वाइकल कैंसर दूसरा सबसे आम कैंसर है। अच्छी बात यह है कि एचपीवी का टीका और समय पर पैप स्मीयर टेस्ट करवाकर इस बीमारी से पूरी तरह बचा जा सकता है।",
            "sections": [
                {
                    "heading": "सर्वाइकल कैंसर का कारण (HPV वायरस)",
                    "content": "यह कैंसर ह्यूमन पैपिलोमावायरस (HPV 16 और 18) के लगातार संक्रमण से होता है। वायरस के संपर्क में आने के बाद कैंसर बनने में 10 से 15 साल का समय लगता है, जिसे शुरुआती जांच से पहले ही पकड़ा जा सकता है।"
                },
                {
                    "heading": "पैप स्मीयर और एचपीवी टेस्ट का महत्व",
                    "content": "पैप स्मीयर एक बहुत आसान 2 मिनट की जांच है जिसमें गर्भाशय ग्रीवा की कोशिकाओं की जांच होती है। 21 से 65 वर्ष की महिलाओं को हर 3 से 5 साल में यह जांच करवानी चाहिए।"
                },
                {
                    "heading": "HPV वैक्सीन: कैंसर से सुरक्षा कवच",
                    "content": "यह टीका 9 से 14 वर्ष की उम्र में सबसे प्रभावी होता है (2 डोज)। 26 वर्ष तक की युवतियां और 45 वर्ष तक की महिलाएं भी डॉक्टर की सलाह से यह टीका लगवा सकती हैं।"
                },
                {
                    "heading": "चेतावनी भरे लक्षण",
                    "content": "संबंध बनाने के बाद खून आना, दो माहवारी के बीच में ब्लीडिंग होना, मेनोपॉज के बाद ब्लीडिंग होना और बदबूदार पानी आना इसके मुख्य लक्षण हैं।"
                }
            ],
            "key_takeaways": [
                "9 से 14 साल की बेटियों को HPV का टीका जरूर लगवाएं।",
                "विवाहित महिलाओं को हर 3 साल में पैप स्मीयर जांच करवानी चाहिए।",
                "संबंध बनाने के बाद खून आना गंभीर लक्षण है, तुरंत डॉक्टर से मिलें।"
            ],
            "myths_vs_facts": [
                {"myth": "शादी के बाद टीका लगवाने का कोई फायदा नहीं होता।", "fact": "शादी के बाद भी यह उन स्ट्रेन्स से बचाता है जिनसे आप अब तक संक्रमित नहीं हुई हैं।"}
            ],
            "faqs": [
                {"question": "क्या पैप स्मीयर टेस्ट में दर्द होता है?", "answer": "नहीं, यह एक बहुत साधारण जांच है जिसमें हल्का सा खिंचाव महसूस हो सकता है, लेकिन कोई तेज दर्द नहीं होता।"}
            ],
            "sources": [
                {"name": "WHO Cervical Cancer Elimination", "url": "https://www.who.int"},
                {"name": "ICMR Guidelines", "url": "https://www.icmr.nic.in"}
            ],
            "medical_disclaimer": "यह जानकारी जागरूकता के लिए है। टीकाकरण और जांच के लिए स्त्री रोग विशेषज्ञ से मिलें।"
        }
    },
    {
        "topic_slug": "reproductive-health",
        "subtopic_slug": "sexual-health",
        "title_en": "Modern Contraception Guide: Finding the Right Birth Control for Your Body",
        "title_hi": "गर्भनिरोधक के आधुनिक तरीके: अपने शरीर के लिए सही विकल्प कैसे चुनें",
        "desc_en": "An objective, medical breakdown of barrier methods, oral contraceptives, IUDs (Copper vs Hormonal), injectables, and emergency pills.",
        "desc_hi": "कंडोम, गर्भनिरोधक गोलियां, कॉपर-टी (IUD) और इमरजेंसी पिल की पूरी जानकारी, फायदे और सावधानियां।",
        "thumbnail_url": TOPIC_IMAGE_POOLS["reproductive-health"][3],
        "category": "Reproductive Health",
        "tags": ["Contraception", "Birth Control", "Family Planning", "Sexual Health"],
        "body_en": {
            "tldr": "Contraceptive options range from barrier methods (condoms, which also protect against STIs) to Long-Acting Reversible Contraception (IUDs, >99% effective for 5–10 years) and combined oral pills.",
            "introduction": "Family planning and reproductive autonomy are fundamental to women's physical health, career aspirations, and emotional wellbeing. Modern medicine offers diverse contraceptive choices, each with unique efficacy rates, hormonal profiles, and lifestyle fits.",
            "sections": [
                {
                    "heading": "Barrier Methods: Condoms and STI Protection",
                    "content": "Male and female condoms are the ONLY contraceptive method that also protects against Sexually Transmitted Infections (including HIV, HPV, and Chlamydia). When used consistently and correctly, male condoms have a 98% efficacy rate (85% with typical use). They are non-hormonal, accessible, and have zero systemic side effects."
                },
                {
                    "heading": "Long-Acting Reversible Contraception (LARC): IUDs",
                    "content": "Intrauterine Devices (IUDs) are small T-shaped devices inserted into the uterus by a doctor. The Copper IUD (e.g. Copper-T) is non-hormonal, highly effective (>99%), and lasts 5–10 years; it works by copper ions inhibiting sperm motility. Hormonal IUDs (Mirena) release tiny amounts of progestin locally, thickening cervical mucus and significantly reducing heavy menstrual bleeding."
                },
                {
                    "heading": "Combined Oral Contraceptive Pills (COCP)",
                    "content": "Birth control pills contain synthetic estrogen and progestin. Taken once daily, they suppress ovulation and regulate periods. Beyond contraception, doctors frequently prescribe them to manage severe acne, dysmenorrhea, and PCOS. However, they are contraindicated in women who smoke over age 35 or have deep vein thrombosis risks."
                },
                {
                    "heading": "Emergency Contraceptive Pills (i-Pill / Levonorgestrel)",
                    "content": "Emergency contraception (morning-after pills) contains a high dose of levonorgestrel designed to delay ovulation after unprotected intercourse. It must be taken within 72 hours (most effective within 24 hours). Crucially, emergency pills are NOT regular birth control—frequent use disrupts menstrual cycles and causes hormonal volatility."
                }
            ],
            "key_takeaways": [
                "Condoms are the only contraceptive method that prevents STIs.",
                "IUDs offer over 99% efficacy and hassle-free protection for 5 to 10 years.",
                "Daily oral pills regulate periods and ease cramps, but require consistent daily timing.",
                "Emergency contraception is strictly for accidental failure, not routine family planning."
            ],
            "myths_vs_facts": [
                {"myth": "Using birth control pills causes permanent infertility when stopped.", "fact": "Fertility returns promptly upon discontinuing oral pills or removing an IUD; they do not impair future fertility."},
                {"myth": "The Copper-T can travel into your heart or stomach.", "fact": "The uterus is a closed muscular organ. An IUD cannot travel out of the pelvis."}
            ],
            "faqs": [
                {"question": "Can I use an emergency contraceptive pill every month?", "answer": "No. Emergency pills cause cycle disruption, irregular spotting, and nausea when used repeatedly. Switch to a reliable method like condoms, oral pills, or an IUD."},
                {"question": "How soon after childbirth can an IUD be inserted?", "answer": "A postpartum IUD can be inserted within 48 hours of delivery or at your 6-week postpartum visit."}
            ],
            "sources": [
                {"name": "World Health Organization (WHO) Family Planning", "url": "https://www.who.int"},
                {"name": "ACOG Long-Acting Reversible Contraception", "url": "https://www.acog.org"}
            ],
            "medical_disclaimer": "Choosing contraception depends on medical history, blood pressure, and personal preferences. Consult your gynecologist to select your optimal method."
        },
        "body_hi": {
            "tldr": "कंडोम गर्भधारण और यौन रोगों दोनों से बचाता है। कॉपर-टी (IUD) 99% से अधिक सुरक्षित और 5-10 साल तक प्रभावी है। इमरजेंसी पिल का बार-बार इस्तेमाल हार्मोनल संतुलन बिगाड़ता है।",
            "introduction": "परिवार नियोजन और अपनी पसंद से गर्भधारण का फैसला हर महिला का अधिकार है। आज कई आधुनिक तरीके उपलब्ध हैं, जिन्हें अपनी जरूरत और स्वास्थ्य के हिसाब से चुना जा सकता है।",
            "sections": [
                {
                    "heading": "कंडोम: दोहरी सुरक्षा",
                    "content": "कंडोम एकमात्र ऐसा साधन है जो अनचाहे गर्भ के साथ-साथ एचआईवी और गुप्त रोगों (STIs) से भी बचाता है। इसमें कोई हार्मोन नहीं होता और कोई साइड इफेक्ट नहीं है।"
                },
                {
                    "heading": "कॉपर-टी (IUD): दीर्घकालिक सुरक्षा",
                    "content": "यह गर्भाशय में डॉक्टर द्वारा लगाया जाने वाला एक छोटा 'टी' आकार का उपकरण है। यह 5 से 10 साल तक 99% सुरक्षा देता है। जब भी बच्चा चाहिए हो, इसे आसानी से निकाला जा सकता है।"
                },
                {
                    "heading": "गर्भनिरोधक गोलियां (ओरल पिल्स)",
                    "content": "ये रोज ली जाने वाली गोलियां हैं जो ओव्यूलेशन को रोकती हैं। यह माहवारी के दर्द और अनियमितता को भी ठीक करती हैं। इन्हें रोज एक निश्चित समय पर लेना होता है।"
                },
                {
                    "heading": "इमरजेंसी पिल (आपातकालीन गोली)",
                    "content": "कंडोम फटने या असुरक्षित संबंध के 72 घंटों के भीतर यह गोली ली जाती है। इसे नियमित गर्भनिरोधक की तरह इस्तेमाल न करें क्योंकि यह माहवारी चक्र को बिगाड़ देती है।"
                }
            ],
            "key_takeaways": [
                "केवल कंडोम ही यौन संक्रमणों (STIs) से सुरक्षा प्रदान करता है।",
                "कॉपर-टी सबसे सुरक्षित और लंबी अवधि का उपाय है।",
                "इमरजेंसी गोली को नियमित गर्भनिरोधक के रूप में कभी इस्तेमाल न करें।"
            ],
            "myths_vs_facts": [
                {"myth": "गर्भनिरोधक गोलियां लेने से बाद में बांझपन हो जाता है।", "fact": "दवा बंद करते ही प्रजनन क्षमता सामान्य हो जाती है। यह भविष्य की फर्टिलिटी को नुकसान नहीं पहुंचाती।"}
            ],
            "faqs": [
                {"question": "इमरजेंसी पिल कितनी देर में असर करती है?", "answer": "संबंध बनाने के जितने जल्दी (24 घंटे के भीतर) ली जाए, यह उतनी ही अधिक असरदार होती है। अधिकतम सीमा 72 घंटे है।"}
            ],
            "sources": [
                {"name": "WHO Family Planning", "url": "https://www.who.int"},
                {"name": "FOGSI Guidelines", "url": "https://www.fogsi.org"}
            ],
            "medical_disclaimer": "यह जानकारी सामान्य समझ के लिए है। अपने स्वास्थ्य के अनुकूल तरीका चुनने के लिए डॉक्टर से सलाह लें।"
        }
    },
    {
        "topic_slug": "reproductive-health",
        "subtopic_slug": "fertility",
        "title_en": "Fertility Basics & Ovulation Tracking: Understanding Your Fertile Window",
        "title_hi": "फर्टिलिटी और ओव्यूलेशन ट्रैकिंग: गर्भधारण के सही समय को समझें",
        "desc_en": "How to calculate your fertile window using basal body temperature, cervical mucus checks, and LH ovulation predictor kits.",
        "desc_hi": "ओव्यूलेशन कब होता है? सर्वाइकल म्यूकस, बॉडी टेम्परेचर और ओव्यूलेशन किट से फर्टाइल दिनों की पहचान कैसे करें।",
        "thumbnail_url": TOPIC_IMAGE_POOLS["reproductive-health"][4],
        "category": "Reproductive Health",
        "tags": ["Fertility", "Ovulation", "Conception", "Cycle Tracking"],
        "body_en": {
            "tldr": "The fertile window spans the 5 days before ovulation plus ovulation day itself. Sperm can survive up to 5 days in fertile cervical mucus, while an egg survives for only 12–24 hours.",
            "introduction": "Whether you are actively planning a pregnancy or simply seeking to understand your body's rhythm, ovulation tracking demystifies your cycle. Contrary to common myths, women are not fertile every day of the month—conception is possible only during a narrow biological window.",
            "sections": [
                {
                    "heading": "The Physiology of the Fertile Window",
                    "content": "Ovulation occurs when the dominant follicle ruptures, releasing a mature oocyte into the fallopian tube. An egg survives for only 12 to 24 hours. However, healthy sperm can survive up to 5 days in fertile reproductive tract mucus. Thus, your 6-day fertile window comprises the 5 days leading up to ovulation and the day of ovulation itself."
                },
                {
                    "heading": "Cervical Mucus Changes: Nature's Fertile Sign",
                    "content": "Rising estrogen before ovulation alters cervical fluid. Right after your period, you may have dry days. As fertile days approach, mucus transitions from creamy and sticky to clear, slippery, and stretchy—resembling raw egg whites. This 'egg-white' cervical mucus acts as a biological expressway and nourishment for sperm."
                },
                {
                    "heading": "Ovulation Predictor Kits (OPKs) and Temperature",
                    "content": "Urine-based LH test strips detect the luteinizing hormone (LH) surge, which triggers ovulation 24 to 36 hours later. Basal Body Temperature (BBT) charting involves taking your resting temperature immediately upon waking; progesterone causes a sustained rise of 0.3°–0.5°C after ovulation, confirming that an egg was indeed released."
                },
                {
                    "heading": "When to Seek Clinical Fertility Guidance",
                    "content": "For couples under 35 with regular cycles, clinical evaluation is advised after 12 months of timed, unprotected intercourse without conception. For women aged 35 and older, or those with known PCOS, endometriosis, or irregular cycles, seek an evaluation after 6 months."
                }
            ],
            "key_takeaways": [
                "Your fertile window is the 5 days prior to ovulation plus ovulation day.",
                "Clear, stretchy, egg-white cervical mucus indicates peak fertility.",
                "LH strips signal an impending egg release within 24 to 36 hours.",
                "Seek fertility guidance after 12 months (under 35) or 6 months (35+) of trying."
            ],
            "myths_vs_facts": [
                {"myth": "Every woman ovulates exactly on day 14 of her cycle.", "fact": "Day 14 ovulation occurs only in classic 28-day cycles. In a 32-day cycle, ovulation typically occurs on day 18."},
                {"myth": "You must have intercourse multiple times a day during the fertile window.", "fact": "Intercourse every 1 to 2 days across the fertile window is optimal for maintaining peak sperm counts and viability."}
            ],
            "faqs": [
                {"question": "How long after a positive ovulation test should we have intercourse?", "answer": "A positive LH test indicates ovulation within 24 to 36 hours. Having intercourse the day of the positive test and the following day maximizes conception odds."},
                {"question": "Does taking folic acid increase the chances of conceiving?", "answer": "Folic acid does not induce ovulation, but taking 400 mcg daily before conception is critical for preventing neural tube defects in the baby."}
            ],
            "sources": [
                {"name": "American Society for Reproductive Medicine (ASRM)", "url": "https://www.asrm.org"},
                {"name": "NICE Guidelines on Fertility Assessment and Treatment", "url": "https://www.nice.org.uk"}
            ],
            "medical_disclaimer": "This information is educational. Consult a reproductive endocrinologist or gynecologist for comprehensive fertility evaluation."
        },
        "body_hi": {
            "tldr": "गर्भधारण के लिए महीने में केवल 6 दिन (ओव्यूलेशन से 5 दिन पहले और ओव्यूलेशन का दिन) सबसे अनुकूल होते हैं। कच्चे अंडे की सफेदी जैसा खिंचावदार डिस्चार्ज फर्टाइल दिनों का मुख्य संकेत है।",
            "introduction": "गर्भधारण की योजना बना रहे दंपत्तियों के लिए ओव्यूलेशन के सही दिनों को जानना बेहद जरूरी है। अंडा केवल 12 से 24 घंटे जीवित रहता है, जबकि शुक्राणु 3 से 5 दिन तक जीवित रह सकते हैं।",
            "sections": [
                {
                    "heading": "फर्टाइल विंडो क्या है?",
                    "content": "28 दिनों के सामान्य चक्र में ओव्यूलेशन आमतौर पर 14वें दिन होता है। ओव्यूलेशन से 5 दिन पहले और उस दिन का समय 'फर्टाइल विंडो' कहलाता है। इस दौरान संबंध बनाने से गर्भधारण की संभावना सबसे अधिक होती है।"
                },
                {
                    "heading": "सर्वाइकल म्यूकस से ओव्यूलेशन की पहचान",
                    "content": "ओव्यूलेशन के समय हार्मोन बढ़ने से सफेद पानी बिल्कुल पारदर्शी, चिकना और कच्चे अंडे की सफेदी की तरह खिंचने वाला हो जाता है। यह शुक्राणुओं को अंडे तक पहुँचाने में मदद करता है।"
                },
                {
                    "heading": "ओव्यूलेशन किट (LH स्ट्रिप्स)",
                    "content": "मेडिकल स्टोर पर मिलने वाली ओव्यूलेशन किट पेशाब में LH हार्मोन की जांच करती है। टेस्ट में दो गहरी लाइनें आने का मतलब है कि अगले 24 से 36 घंटों में अंडा निकलने वाला है।"
                },
                {
                    "heading": "डॉक्टर से कब मिलना चाहिए?",
                    "content": "अगर महिला की उम्र 35 से कम है और 1 साल तक प्रयास करने के बाद भी गर्भ नहीं ठहर रहा, तो डॉक्टर से मिलें। 35 से अधिक उम्र होने पर 6 महीने बाद ही फर्टिलिटी विशेषज्ञ से परामर्श लें।"
                }
            ],
            "key_takeaways": [
                "महीने में केवल 5-6 दिन ही गर्भधारण के लिए सबसे उपयुक्त होते हैं।",
                "पारदर्शी और खिंचावदार डिस्चार्ज ओव्यूलेशन का प्राकृतिक संकेत है।",
                "फर्टाइल दिनों में एक दिन छोड़कर संबंध बनाना सबसे बेहतर परिणाम देता है।"
            ],
            "myths_vs_facts": [
                {"myth": "हर महिला का ओव्यूलेशन ठीक 14वें दिन ही होता है।", "fact": "अगर आपका चक्र 32 दिनों का है, तो ओव्यूलेशन 18वें दिन के आसपास होगा। यह चक्र की लंबाई पर निर्भर करता है।"}
            ],
            "faqs": [
                {"question": "ओव्यूलेशन किट पॉजिटिव आने के बाद क्या करें?", "answer": "पॉजिटिव टेस्ट आने के दिन और उसके अगले दिन संबंध बनाने से गर्भधारण की संभावना सबसे अधिक होती है।"}
            ],
            "sources": [
                {"name": "ASRM Guidelines", "url": "https://www.asrm.org"},
                {"name": "FOGSI Fertility Committee", "url": "https://www.fogsi.org"}
            ],
            "medical_disclaimer": "यह जानकारी सामान्य जागरूकता के लिए है। व्यक्तिगत फर्टिलिटी जांच के लिए डॉक्टर से परामर्श लें।"
        }
    },
    {
        "topic_slug": "reproductive-health",
        "subtopic_slug": "fertility",
        "title_en": "Endometriosis and Pelvic Pain: Recognizing Symptoms, Diagnosis & Treatment",
        "title_hi": "एंडोमेट्रिओसिस और पेल्विक दर्द: लक्षण, जांच और सही उपचार",
        "desc_en": "Understand endometriosis, adenomyosis, diagnostic delays, laparoscopic diagnosis, and surgical and medical management.",
        "desc_hi": "माहवारी में असहनीय दर्द, कमर दर्द और बांझपन का कारण: एंडोमेट्रिओसिस की पहचान और इलाज के आधुनिक तरीके।",
        "thumbnail_url": TOPIC_IMAGE_POOLS["reproductive-health"][5],
        "category": "Reproductive Health",
        "tags": ["Endometriosis", "Chronic Pain", "Pelvic Pain", "Women's Health"],
        "body_en": {
            "tldr": "Endometriosis affects ~10% of women globally, causing debilitating period cramps, chronic pelvic pain, and infertility. Severe pain that disrupts school or work is NOT normal and warrants specialized evaluation.",
            "introduction": "For decades, women with unbearable menstrual cramps were dismissed with phrases like 'periods are just painful.' Endometriosis is a real, chronic inflammatory disorder where tissue resembling the uterine lining grows outside the uterus, triggering chronic inflammation, adhesions, and pain.",
            "sections": [
                {
                    "heading": "Pathophysiology and Symptoms of Endometriosis",
                    "content": "Endometrial-like lesions implant on the ovaries, fallopian tubes, bladder, bowel, and pelvic peritoneum. During menstruation, these lesions bleed just like the uterine lining, but the blood has no exit, causing intense inflammation, scar tissue (adhesions), and organ fusion. Key symptoms: severe dysmenorrhea that NSAIDs cannot relieve, pain during intercourse (dyspareunia), painful bowel movements during periods, and chronic back/pelvic pain."
                },
                {
                    "heading": "The Diagnostic Delay Crisis",
                    "content": "Globally, the average time from first symptom to an official endometriosis diagnosis is 7 to 10 years. Routine pelvic ultrasounds often miss early superficial lesions. High-resolution transvaginal ultrasound or MRI interpreted by expert radiologists can identify deep infiltrating endometriosis (DIE) and endometriomas ('chocolate cysts'). Laparoscopy remains the gold standard for definitive tissue diagnosis."
                },
                {
                    "heading": "Medical and Surgical Treatment Options",
                    "content": "While there is no permanent cure, symptom control is highly achievable. First-line treatments include continuous combined oral contraceptives or progestins (dienogest) to suppress menstruation and lesion activity. GnRH agonists/antagonists provide temporary medical suppression. Laparoscopic excision surgery by an experienced specialist physically removes lesions and restores normal pelvic anatomy."
                },
                {
                    "heading": "Endometriosis and Fertility",
                    "content": "Approximately 30–50% of women with endometriosis experience fertility challenges due to tubal scarring, distorted pelvic anatomy, or altered egg quality. However, many women conceive naturally or with assisted reproductive technologies (ART/IVF) following medical or surgical management."
                }
            ],
            "key_takeaways": [
                "Period pain that prevents work, school, or daily function is NOT normal.",
                "Endometriosis affects 1 in 10 reproductive-age women globally.",
                "Diagnosis takes 7–10 years on average due to symptom dismissal.",
                "Dienogest, hormonal suppressants, and laparoscopic excision offer meaningful relief.",
                "30–50% of patients experience fertility challenges, but IVF and surgery provide effective pathways to pregnancy."
            ],
            "myths_vs_facts": [
                {"myth": "Getting pregnant cures endometriosis.", "fact": "Pregnancy temporarily suppresses symptoms due to high progesterone, but it does not eradicate lesions. Pain frequently returns postpartum."},
                {"myth": "A hysterectomy completely cures endometriosis.", "fact": "If lesions on the peritoneum, bowel, or bladder are left behind, pelvic pain persists even after uterus removal."}
            ],
            "faqs": [
                {"question": "How do I know if my period pain is normal or endometriosis?", "answer": "Normal period cramps respond to hot water bottles and over-the-counter painkillers. Endometriosis pain leaves you bedridden, radiates down your legs, causes vomiting, or hurts during sex or bowel movements."},
                {"question": "What is a 'chocolate cyst'?", "answer": "An endometrioma is an ovarian cyst filled with old, thickened menstrual blood caused by endometriosis tissue on the ovary."}
            ],
            "sources": [
                {"name": "World Health Organization (WHO) Factsheet on Endometriosis", "url": "https://www.who.int"},
                {"name": "European Society of Human Reproduction and Embryology (ESHRE) Endometriosis Guidelines", "url": "https://www.eshre.eu"}
            ],
            "medical_disclaimer": "This content is educational. If severe pelvic pain affects your quality of life, consult an endometriosis or reproductive health specialist."
        },
        "body_hi": {
            "tldr": "माहवारी में इतना दर्द होना कि आप काम या कॉलेज न जा सकें, सामान्य नहीं है। एंडोमेट्रिओसिस में गर्भाशय के बाहर ऊतक बढ़ने लगते हैं, जिससे भयंकर दर्द और बांझपन हो सकता है।",
            "introduction": "अक्सर महिलाओं को यह कहकर टाल दिया जाता है कि 'पीरियड्स में दर्द तो सबको होता है।' लेकिन एंडोमेट्रिओसिस एक वास्तविक चिकित्सीय बीमारी है जो दुनिया भर में 10 में से 1 महिला को प्रभावित करती है।",
            "sections": [
                {
                    "heading": "एंडोमेट्रिओसिस क्या है और इसके लक्षण",
                    "content": "इसमें गर्भाशय की अंदरूनी परत जैसे ऊतक ओवरी, आंतों और पेल्विक क्षेत्र पर उगने लगते हैं। पीरियड्स में असहनीय दर्द, कमर दर्द, संबंध बनाते समय दर्द और शौच के समय दर्द इसके मुख्य लक्षण हैं।"
                },
                {
                    "heading": "जांच में देरी की समस्या",
                    "content": "लक्षणों को नजरअंदाज करने के कारण सही निदान मिलने में 7 से 10 साल लग जाते हैं। साधारण सोनोग्राफी में शुरुआती बीमारी नहीं दिखती। विशेषज्ञ द्वारा एमआरआई और लेप्रोस्कोपी से इसकी पुष्टि होती है।"
                },
                {
                    "heading": "इलाज के आधुनिक तरीके",
                    "content": "हार्मोनल दवाएं (डाइनोजेस्ट) और पीरियड्स को नियंत्रित करने वाली गोलियां दर्द से राहत देती हैं। गंभीर मामलों में दूरबीन विधि (लेप्रोस्कोपिक सर्जरी) से इन ऊतकों को हटाया जाता है।"
                },
                {
                    "heading": "एंडोमेट्रिओसिस और गर्भधारण",
                    "content": "यह बीमारी फर्टिलिटी को प्रभावित कर सकती है, लेकिन सही इलाज और आईवीएफ (IVF) की मदद से अधिकांश महिलाएं माँ बन सकती हैं।"
                }
            ],
            "key_takeaways": [
                "माहवारी का ऐसा दर्द जो रोजमर्रा के काम रोक दे, सामान्य नहीं है।",
                "पेनकिलर से भी दर्द न रुकना एंडोमेट्रिओसिस का मुख्य लक्षण हो सकता है।",
                "शुरुआती इलाज से अंगों को नुकसान और बांझपन के खतरे से बचा जा सकता है।"
            ],
            "myths_vs_facts": [
                {"myth": "बच्चा पैदा करने से एंडोमेट्रिओसिस हमेशा के लिए ठीक हो जाता है।", "fact": "प्रेगनेंसी में कुछ समय के लिए दर्द रुक सकता है, लेकिन यह बीमारी का पक्का इलाज नहीं है।"}
            ],
            "faqs": [
                {"question": "चॉकलेट सिस्ट क्या होती है?", "answer": "जब एंडोमेट्रिओसिस ओवरी में होता है, तो पुराना खून जमा होकर भूरी सिस्ट बना देता है जिसे 'चॉकलेट सिस्ट' कहते हैं।"}
            ],
            "sources": [
                {"name": "WHO Endometriosis", "url": "https://www.who.int"},
                {"name": "FOGSI Endometriosis Committee", "url": "https://www.fogsi.org"}
            ],
            "medical_disclaimer": "यह जानकारी जागरूकता के लिए है। असहनीय मासिक धर्म दर्द पर तुरंत स्त्री रोग विशेषज्ञ से सलाह लें।"
        }
    },

    # =========================================================================
    # FITNESS (6 articles)
    # =========================================================================
    {
        "topic_slug": "fitness",
        "subtopic_slug": "exercise",
        "title_en": "Cycle Syncing Your Workouts: Exercising in Tune with Your Hormonal Phases",
        "title_hi": "पीरियड साइकिल और वर्कआउट: हार्मोनल फेजेस के अनुसार एक्सरसाइज कैसे करें",
        "desc_en": "How to align training with the menstrual, follicular, ovulatory, and luteal phases for optimal energy, fat loss, and injury prevention.",
        "desc_hi": "माहवारी के 4 चरणों (मेंस्ट्रुअल, फॉलिक्युलर, ओव्यूलेटरी, ल्यूटियल) के अनुसार सही एक्सरसाइज का वैज्ञानिक तरीका।",
        "thumbnail_url": TOPIC_IMAGE_POOLS["fitness"][0],
        "category": "Fitness",
        "tags": ["Fitness", "Cycle Syncing", "Workout", "Hormones"],
        "body_en": {
            "tldr": "Women's bodies are governed by an infradian rhythm across 28 days. Match high-intensity training to the high-estrogen follicular/ovulatory phases, and shift to strength, walking, and yoga during the progesterone-dominant luteal and menstrual phases.",
            "introduction": "Most fitness protocols are based on male physiology, which operates on a 24-hour testosterone rhythm. Women, by contrast, navigate a 28-day infradian rhythm with cyclical fluctuations in estrogen, progesterone, and metabolic rate. Synchronizing your workouts with these phases unlocks peak energy and reduces burnout.",
            "sections": [
                {
                    "heading": "Phase 1: Menstrual Phase (Days 1–5) - Rest and Restore",
                    "content": "Estrogen and progesterone are at their lowest levels; energy may be subdued. Prioritize gentle movement: slow walks, restorative yoga, stretching, and mobility work. Avoid high-impact plyometrics or heavy inversions if cramping. Light movement promotes pelvic blood flow and relieves prostaglandin-induced cramping."
                },
                {
                    "heading": "Phase 2: Follicular Phase (Days 6–12) - High Energy and Strength",
                    "content": "As follicle stimulating hormone (FSH) prompts the ovaries to produce estrogen, insulin sensitivity improves and muscle recovery accelerates. This is your power window: lift heavier weights, try progressive resistance training, engage in boxing, spin classes, or high-intensity interval training (HIIT)."
                },
                {
                    "heading": "Phase 3: Ovulatory Phase (Days 13–16) - Peak Stamina",
                    "content": "Estrogen peaks alongside a brief spike in testosterone. Energy, confidence, and pain tolerance are at their monthly zenith. Ideal for setting personal lifting records, attending competitive group workouts, and endurance sessions. Note: high estrogen mildly increases joint laxity; ensure proper knee and ankle warmups."
                },
                {
                    "heading": "Phase 4: Luteal Phase (Days 17–28) - Caloric Shift and Recovery",
                    "content": "Progesterone dominates, raising your basal body temperature and basal metabolic rate (you burn 100–300 more calories daily). In the late luteal phase, cortisol sensitivity increases and endurance drops. Transition to moderate strength training, Pilates, incline walking, and restorative mobility to prevent burnout and curb PMS."
                }
            ],
            "key_takeaways": [
                "Menstrual Phase: Gentle walks, yoga, and stretching to reduce inflammation.",
                "Follicular Phase: Heavy lifting, HIIT, and strength gains due to rising estrogen.",
                "Ovulatory Phase: Peak monthly stamina and personal records.",
                "Luteal Phase: Pilates, moderate weights, and recovery to prevent PMS and cortisol spikes.",
                "Listen to biofeedback over rigid calendars—fatigue is a valid training signal."
            ],
            "myths_vs_facts": [
                {"myth": "You should push at 100% intensity every single day of the month.", "fact": "Rigid high intensity during the late luteal phase elevates cortisol, promotes muscle breakdown, and disrupts menstrual regularity."},
                {"myth": "Working out during periods is harmful to the ovaries.", "fact": "Light to moderate exercise during periods releases endorphins that actively reduce menstrual cramping."}
            ],
            "faqs": [
                {"question": "Why do I feel weaker in the gym the week before my period?", "answer": "Rising progesterone raises body temperature and heart rate, while lowering carbohydrate utilization efficiency. Feeling 10–15% weaker before your period is normal biology."},
                {"question": "Do I need to eat more during the luteal phase?", "answer": "Yes. Your resting metabolic rate increases by 100 to 300 calories during the luteal phase. Nourish your body with complex carbs and protein rather than extreme calorie restriction."}
            ],
            "sources": [
                {"name": "British Journal of Sports Medicine: Menstrual Cycle and Performance", "url": "https://bjsm.bmj.com"},
                {"name": "American College of Sports Medicine (ACSM)", "url": "https://www.acsm.org"}
            ],
            "medical_disclaimer": "This content is educational. Adjust workout volume and intensity to your fitness baseline and chronic health profile."
        },
        "body_hi": {
            "tldr": "महिलाओं के शरीर में हर हफ्ते हार्मोन बदलते हैं। फॉलिक्युलर और ओव्यूलेशन के समय भारी वजन और हाई इंटेंसिटी वर्कआउट करें, जबकि पीरियड्स और उससे पहले वाले हफ्ते में योगा और हल्की वॉक करें।",
            "introduction": "पुरुषों का हार्मोनल चक्र 24 घंटे का होता है, जबकि महिलाओं का 28 दिनों का। हर हफ्ते शरीर में एस्ट्रोजन और प्रोजेस्टेरोन का स्तर बदलता है। हार्मोन्स के अनुसार वर्कआउट करने से थकान कम होती है और फैट लॉस बेहतर होता है।",
            "sections": [
                {
                    "heading": "1. मेंस्ट्रुअल फेज (माहवारी के दिन 1-5): आराम और स्ट्रेचिंग",
                    "content": "हार्मोन सबसे निचले स्तर पर होते हैं और ऊर्जा कम होती है। इस समय हल्की वॉक, स्ट्रेचिंग और रेस्टोरेटिव योग करें। भारी वजन उठाने से बचें।"
                },
                {
                    "heading": "2. फॉलिक्युलर फेज (दिन 6-12): ताकत और वेट ट्रेनिंग",
                    "content": "एस्ट्रोजन हार्मोन तेजी से बढ़ता है। शरीर में भरपूर ऊर्जा होती है और मांसपेशियां तेजी से रिकवर होती हैं। इस समय वेट ट्रेनिंग, रनिंग और कार्डियो करें।"
                },
                {
                    "heading": "3. ओव्यूलेटरी फेज (दिन 13-16): पीक एनर्जी और स्टेमिना",
                    "content": "टेस्टोस्टेरोन और एस्ट्रोजन दोनों उच्च स्तर पर होते हैं। यह महीने का सबसे मजबूत समय होता है। पर्सनल रिकॉर्ड बनाने और कठिन वर्कआउट के लिए यह सबसे बेहतरीन दिन हैं।"
                },
                {
                    "heading": "4. ल्यूटियल फेज (दिन 17-28): पाइलेट्स और मध्यम वर्कआउट",
                    "content": "प्रोजेस्टेरोन बढ़ने से शरीर का तापमान बढ़ता है और थकान जल्दी होती है। इस समय पाइलेट्स, तेज चलना और मध्यम वजन उठाएं ताकि कोर्टिसोल (तनाव हार्मोन) न बढ़े।"
                }
            ],
            "key_takeaways": [
                "माहवारी के दिनों में हल्की वॉक और योग करें।",
                "पीरियड्स खत्म होने के बाद वाले हफ्ते में सबसे भारी वजन उठाएं।",
                "पीरियड्स से पहले वाले हफ्ते में ज्यादा कठिन वर्कआउट से बचें।"
            ],
            "myths_vs_facts": [
                {"myth": "महीने के 30 दिन एक जैसा पसीना बहाना ही फिटनेस है।", "fact": "हार्मोनल बदलावों का सम्मान किए बिना लगातार कठिन वर्कआउट करने से पीरियड्स अनियमित हो सकते हैं और कोर्टिसोल बढ़ता है।"}
            ],
            "faqs": [
                {"question": "पीरियड्स आने से पहले जिम में ज्यादा थकान क्यों होती है?", "answer": "प्रोजेस्टेरोन हार्मोन के कारण दिल की धड़कन तेज होती है और शरीर जल्दी थकता है। यह सामान्य है।"}
            ],
            "sources": [
                {"name": "Sports Medicine Review", "url": "https://www.acsm.org"},
                {"name": "Womens Health Guidelines", "url": "https://www.who.int"}
            ],
            "medical_disclaimer": "यह जानकारी सामान्य फिटनेस के लिए है। अपनी शारीरिक क्षमता के अनुसार व्यायाम करें।"
        }
    },
    {
        "topic_slug": "fitness",
        "subtopic_slug": "exercise",
        "title_en": "Strength Training for Women: Building Bone Density, Muscle & Longevity",
        "title_hi": "महिलाओं के लिए स्ट्रेंथ ट्रेनिंग: मजबूत हड्डियां, मेटाबॉलिज्म और लंबी उम्र",
        "desc_en": "Why lifting weights will not make you bulky, and how progressive resistance training prevents osteoporosis and improves metabolic health.",
        "desc_hi": "वजन उठाने से शरीर भारी (बल्की) नहीं होता: हड्डियों की मजबूती, फैट लॉस और ऑस्टियोपोरोसिस से बचाव के वैज्ञानिक लाभ।",
        "thumbnail_url": TOPIC_IMAGE_POOLS["fitness"][1],
        "category": "Fitness",
        "tags": ["Strength Training", "Bone Density", "Metabolism", "Longevity"],
        "body_en": {
            "tldr": "Strength training 2–3 times weekly stimulates osteoblasts to fortify bone mineral density, boosts resting metabolic rate, improves insulin sensitivity, and prevents age-related sarcopenia.",
            "introduction": "For decades, fitness marketing funneled women toward endless cardio and tiny pink dumbbells out of fear of getting 'bulky.' Contemporary exercise science proves that resistance training is essential for female longevity, metabolic health, and protection against post-menopausal osteoporosis.",
            "sections": [
                {
                    "heading": "The Biological Impossibility of 'Accidental Bulking'",
                    "content": "Women possess only 5–10% of the circulating testosterone levels found in men. Substantial muscle hypertrophy requires years of intentional caloric surplus, genetic predisposition, and heavy progressive overload. Instead of bulking, resistance training builds dense, lean muscle tissue, creating a firm, functional physique and reducing visceral fat."
                },
                {
                    "heading": "Bone Mineral Density and Osteoporosis Defense",
                    "content": "Peak bone mass is achieved around age 30. Post-menopause, declining estrogen accelerates bone loss, making Indian women exceptionally vulnerable to osteoporotic fractures. Resistance exercises—such as squats, deadlifts, and overhead presses—exert axial mechanical loading on bones, triggering osteocytes to lay down new bone matrix."
                },
                {
                    "heading": "Metabolic Engine: Insulin Sensitivity and Fat Oxidation",
                    "content": "Skeletal muscle is your body's largest glucose disposal sink. Lifting weights upregulates GLUT4 glucose transporters in muscle cells independent of insulin, directly reversing insulin resistance in conditions like PCOS. Lean muscle tissue also elevates resting metabolic rate, meaning your body burns more energy around the clock."
                },
                {
                    "heading": "A Beginner's Progressive Overload Blueprint",
                    "content": "Start with compound multi-joint movements 2 to 3 days per week: goblet squats, Romanian deadlifts, push-ups/chest presses, seated rows, and farmer's walks. Focus on progressive overload—gradually increasing repetitions, improving form, or adding weight over time."
                }
            ],
            "key_takeaways": [
                "Women have ~10% of male testosterone and will not get 'bulky' from lifting weights.",
                "Axial loading from squats and deadlifts stimulates bone density and prevents osteoporosis.",
                "Muscle is the body's primary glucose sink; lifting reverses insulin resistance in PCOS.",
                "2 to 3 compound resistance sessions per week provides maximal longevity benefits.",
                "Prioritize progressive overload and adequate protein (1.2–1.6 g/kg)."
            ],
            "myths_vs_facts": [
                {"myth": "Cardio is better than weight lifting for weight loss in women.", "fact": "Cardio burns calories only while active; strength training builds lean tissue that burns calories 24/7 and preserves metabolic rate."},
                {"myth": "Older women should avoid lifting weights to protect their joints.", "fact": "Resistance training strengthens joint-supporting tendons and ligaments, reducing arthritis pain and preventing falls in older adults."}
            ],
            "faqs": [
                {"question": "How often should women lift weights each week?", "answer": "2 to 3 full-body sessions per week, separated by 48 hours of rest, yields optimal strength and health benefits."},
                {"question": "Do I need fancy gym machines to start?", "answer": "No. Bodyweight movements, resistance bands, and a pair of adjustable dumbbells at home provide an exceptional foundation."}
            ],
            "sources": [
                {"name": "National Strength and Conditioning Association (NSCA)", "url": "https://www.nsca.com"},
                {"name": "International Osteoporosis Foundation (IOF)", "url": "https://www.osteoporosis.foundation"}
            ],
            "medical_disclaimer": "This content is educational. Consult a fitness professional or physician before starting a new heavy lifting regimen."
        },
        "body_hi": {
            "tldr": "हफ्ते में 2-3 दिन वजन उठाने (स्ट्रेंथ ट्रेनिंग) से हड्डियां मजबूत होती हैं, मेटाबॉलिज्म बढ़ता है और ऑस्टियोपोरोसिस का खतरा खत्म होता है। महिलाओं के लिए वेट ट्रेनिंग बेहद जरूरी है।",
            "introduction": "कई महिलाएं इस डर से वजन उठाने से बचती हैं कि उनका शरीर पुरुषों की तरह भारी (बल्की) हो जाएगा। यह एक मिथक है। महिलाओं में टेस्टोस्टेरोन बहुत कम होता है, इसलिए वेट ट्रेनिंग से शरीर सुडौल और मजबूत बनता है।",
            "sections": [
                {
                    "heading": "मिथक: वजन उठाने से महिला बल्की हो जाएगी?",
                    "content": "महिलाओं में पुरुषों की तुलना में टेस्टोस्टेरोन केवल 10% होता है। इसलिए सामान्य वेट ट्रेनिंग से भारी मांसपेशियां नहीं बनतीं। इसके बजाय शरीर टोंड, फुर्तीला और आकर्षक बनता है।"
                },
                {
                    "heading": "हड्डियों की मजबूती (ऑस्टियोपोरोसिस से बचाव)",
                    "content": "30 साल के बाद महिलाओं की हड्डियों का घनत्व कम होने लगता है। स्क्वाट्स और डेडलिफ्ट जैसी एक्सरसाइज हड्डियों पर सकारात्मक दबाव डालती हैं, जिससे हड्डियां मजबूत होती हैं और फ्रैक्चर का खतरा टलता है।"
                },
                {
                    "heading": "इंसुलिन संवेदनशीलता और पीसीओएस में फायदा",
                    "content": "मांसपेशियां शरीर में ब्लड शुगर को सबसे तेजी से सोखती हैं। वजन उठाने से इंसुलिन रेजिस्टेंस ठीक होता है, जो पीसीओएस (PCOS) से पीड़ित महिलाओं के लिए वरदान समान है।"
                },
                {
                    "heading": "शुरुआत कैसे करें?",
                    "content": "हफ्ते में 2 से 3 दिन स्क्वाट्स, पुश-अप्स, डम्बल रो और ब्रिज जैसी बुनियादी एक्सरसाइज से शुरुआत करें। सही तकनीक पर ध्यान दें और धीरे-धीरे वजन बढ़ाएं।"
                }
            ],
            "key_takeaways": [
                "वजन उठाने से महिलाएं कभी बल्की नहीं होतीं, शरीर फिट और सुडौल बनता है।",
                "हड्डियों को मजबूत रखने के लिए वेट ट्रेनिंग कार्डियो से कहीं ज्यादा असरदार है।",
                "हफ्ते में 2-3 बार स्ट्रेंथ ट्रेनिंग करने से ब्लड शुगर और पीसीओएस नियंत्रित रहता है।"
            ],
            "myths_vs_facts": [
                {"myth": "केवल कार्डियो (दौड़ना, साइकिल) ही वजन घटाने के लिए सही है।", "fact": "कार्डियो केवल दौड़ते समय कैलोरी जलाता है, जबकि स्ट्रेंथ ट्रेनिंग से बनी मांसपेशियां आराम करते समय भी 24 घंटे कैलोरी जलाती हैं।"}
            ],
            "faqs": [
                {"question": "क्या घर पर स्ट्रेंथ ट्रेनिंग शुरू की जा सकती है?", "answer": "हाँ, अपने शरीर के वजन (बॉडीवेट एक्सरसाइज), रेजिस्टेंस बैंड और 2-3 किलो के डम्बल से घर पर आसानी से शुरुआत की जा सकती है।"}
            ],
            "sources": [
                {"name": "International Osteoporosis Foundation", "url": "https://www.osteoporosis.foundation"},
                {"name": "ACSM Guidelines", "url": "https://www.acsm.org"}
            ],
            "medical_disclaimer": "यह जानकारी सामान्य फिटनेस के लिए है। किसी भी नए वर्कआउट से पहले फिटनेस ट्रेनर की देखरेख में तकनीक सीखें।"
        }
    },
    {
        "topic_slug": "fitness",
        "subtopic_slug": "movement",
        "title_en": "Yoga for Menstrual Cramps & Pelvic Health: Restorative Poses That Work",
        "title_hi": "माहवारी के दर्द के लिए योग: पीरियड्स क्रैम्प्स से तुरंत राहत देने वाले 5 आसन",
        "desc_en": "Evidence-backed restorative asanas (Baddha Konasana, Balasana, Supta Matsyendrasana) to ease uterine cramps and soothe the nervous system.",
        "desc_hi": "बालासन, बद्धकोणासन और सुप्त मत्स्येंद्रासन जैसे 5 सरल योगासन जो गर्भाशय के संकुचन को शांत कर दर्द से राहत दिलाते हैं।",
        "thumbnail_url": TOPIC_IMAGE_POOLS["fitness"][2],
        "category": "Fitness",
        "tags": ["Yoga", "Menstrual Health", "Period Pain", "Pelvic Health"],
        "body_en": {
            "tldr": "Restorative yoga reduces menstrual cramp intensity by activating the parasympathetic nervous system, increasing pelvic oxygenation, and releasing endorphins. Poses like Balasana and Supta Baddha Konasana offer immediate cramp relief.",
            "introduction": "When period pain strikes, intense exercise is usually the last thing you want. However, lying completely sedentary can cause pelvic stagnation and muscle stiffness. Restorative yoga offers an evidence-based middle path: gentle stretches combined with diaphragmatic breathing calm uterine muscle spasms and modulate pain perception.",
            "sections": [
                {
                    "heading": "The Science of Yoga and Pelvic Blood Flow",
                    "content": "Menstrual cramps (dysmenorrhea) are driven by prostaglandins causing uterine muscle contractions and temporary localized ischemia (oxygen deprivation). Restorative yoga postures open the pelvic basin, stretch the hip flexors and lower back, and enhance microcirculation to the pelvic organs. Deep belly breathing stimulates the vagus nerve, lowering cortisol and boosting endogenous pain-relieving endorphins."
                },
                {
                    "heading": "Top 4 Restorative Poses for Immediate Cramp Relief",
                    "content": "1. Balasana (Child's Pose): Knees wide, torso relaxed forward over a bolster; stretches the sacrum and eases lower back tightness. 2. Supta Baddha Konasana (Reclining Bound Angle): Soles of feet together, knees dropping open, back supported by pillows; relieves uterine tension. 3. Viparita Karani (Legs-up-the-Wall): Elevates legs to drain pelvic congestion and relax pelvic floor muscles. 4. Supta Matsyendrasana (Supine Spinal Twist): Gently wrings out abdominal organs and releases sciatic tightness."
                },
                {
                    "heading": "Poses to Avoid During Heavy Menstruation",
                    "content": "Avoid intense inversions (headstands, shoulder stands) and strenuous abdominal contractions (Navasana/Boat Pose) during heavy bleeding days. While ancient myths about inversions causing retrograde menstruation lack conclusive modern evidence, deep inversions can feel disorienting and uncomfortable during active menstrual flow."
                },
                {
                    "heading": "Integrating Pranayama for Pain Modulation",
                    "content": "Practice Nadi Shodhana (Alternate Nostril Breathing) and Bhramari (Humming Bee Breath) for 5 to 10 minutes. Controlled slow exhalations downregulate the sympathetic nervous system, dampening chronic pain signals processed in the brain."
                }
            ],
            "key_takeaways": [
                "Restorative yoga increases pelvic blood circulation, easing uterine ischemia.",
                "Child's Pose and Reclined Butterfly provide rapid cramp relief.",
                "Legs-Up-the-Wall pose drains pelvic congestion and relieves lower back pressure.",
                "Diaphragmatic breathing stimulates the vagus nerve to naturally suppress pain.",
                "Avoid strenuous core crunches and intense inversions on heavy flow days."
            ],
            "myths_vs_facts": [
                {"myth": "You must completely avoid all yoga while menstruating.", "fact": "Gentle restorative yoga is universally recognized as one of the most effective non-pharmacological therapies for menstrual pain."},
                {"myth": "Doing inversions during periods causes endometriosis.", "fact": "Endometriosis is a complex cellular disease, not caused by doing a brief gentle stretch or yoga pose."}
            ],
            "faqs": [
                {"question": "How long should I hold each restorative pose?", "answer": "Hold supported poses like Reclined Bound Angle or Child's Pose for 3 to 5 minutes, focusing on deep, slow abdominal breathing."},
                {"question": "Can I use props like cushions and blankets?", "answer": "Yes! Bolsters, pillows, and warm blankets are strongly encouraged to support your body so your muscles can release tension without effort."}
            ],
            "sources": [
                {"name": "Journal of Alternative and Complementary Medicine - Yoga for Dysmenorrhea", "url": "https://www.liebertpub.com"},
                {"name": "Harvard Health Publishing: Yoga for Pain Relief", "url": "https://www.health.harvard.edu"}
            ],
            "medical_disclaimer": "This content is educational. Consult a physician if period pain is sudden, debilitating, or accompanied by abnormal bleeding."
        },
        "body_hi": {
            "tldr": "माहवारी के दिनों में बालासन और सुप्त बद्धकोणासन जैसे रेस्टोरेटिव आसन करने से गर्भाशय में रक्तसंचार बढ़ता है और बिना दवा के दर्द में तुरंत आराम मिलता है।",
            "introduction": "पीरियड्स के दिनों में तेज दर्द और ऐंठन होने पर भारी वर्कआउट नहीं किया जा सकता। लेकिन हल्के और आरामदायक योगासन गर्भाशय की ऐंठन को शांत करने का सबसे प्राकृतिक और अचूक तरीका हैं।",
            "sections": [
                {
                    "heading": "योग से दर्द में आराम कैसे मिलता है?",
                    "content": "पीरियड्स में गर्भाशय के संकुचन से मांसपेशियों में ऑक्सीजन की कमी हो जाती है जिससे दर्द होता है। योग के हल्के खिंचाव पेल्विक हिस्से में खून का बहाव बढ़ाते हैं और गहरी सांस लेने से तनाव हार्मोन कम होता है।"
                },
                {
                    "heading": "दर्द मिटाने वाले 3 सबसे असरदार आसन",
                    "content": "1. बालासन (चाइल्ड पोज): तकिए पर पेट टिकाकर आगे झुकें, इससे कमर का दर्द तुरंत शांत होता है। 2. सुप्त बद्धकोणासन: पीठ के बल लेटकर दोनों पैरों के तलवों को आपस में मिलाएं और घुटनों को ढीला छोड़ें। 3. विपरीत करणी: दीवार के सहारे दोनों पैर ऊपर करके 5-10 मिनट लेटें, इससे पैरों और पेल्विस की सूजन दूर होती है।"
                },
                {
                    "heading": "किन आसनों से बचना चाहिए?",
                    "content": "माहवारी के भारी दिनों में शीर्षासन (उलटे लटकने वाले आसन) और पेट को दबाने वाले कठिन आसनों (नौकासन) से बचें। शरीर पर अतिरिक्त जोर न डालें।"
                },
                {
                    "heading": "प्राणायाम का जादू",
                    "content": "अनुलोम-विलोम और भ्रामरी प्राणायाम 5 से 10 मिनट करें। यह तंत्रिका तंत्र को शांत कर दर्द महसूस करने की तीव्रता को आधा कर देता है।"
                }
            ],
            "key_takeaways": [
                "बालासन और विपरीत करणी आसन माहवारी की ऐंठन में अचूक राहत देते हैं।",
                "तकिए और कुशन का सहारा लेकर आसन करने से मांसपेशियां पूरी तरह रिलैक्स होती हैं।",
                "गहरी सांसें लेने से शरीर प्राकृतिक पेनकिलर (एंडोर्फिन) छोड़ता है।"
            ],
            "myths_vs_facts": [
                {"myth": "माहवारी के दिनों में कोई भी योग नहीं करना चाहिए।", "fact": "कठिन व्यायाम मना होता है, लेकिन आराम देने वाले हल्के आसन दर्द मिटाने के लिए डॉक्टर भी सुझाते हैं।"}
            ],
            "faqs": [
                {"question": "एक आसन में कितनी देर रुकना चाहिए?", "answer": "तकिए का सहारा लेकर एक आसन में 3 से 5 मिनट तक रुकें और धीमी लंबी सांसें लें।"}
            ],
            "sources": [
                {"name": "Harvard Health Publishing", "url": "https://www.health.harvard.edu"},
                {"name": "Yoga for Women's Health Studies", "url": "https://www.nih.gov"}
            ],
            "medical_disclaimer": "यह जानकारी सामान्य स्वास्थ्य के लिए है। असहनीय दर्द होने पर अपनी गायनेकोलॉजिस्ट से परामर्श लें।"
        }
    },
    {
        "topic_slug": "fitness",
        "subtopic_slug": "movement",
        "title_en": "Safe Exercise During Pregnancy: Trimester-by-Trimester Movement Guidelines",
        "title_hi": "गर्भावस्था में सुरक्षित व्यायाम: तीनों तिमाहियों के लिए सही गाइडलाइन",
        "desc_en": "ACOG guidelines on prenatal exercise: benefits for labor, safe heart rates, contraindicated movements, and core protection.",
        "desc_hi": "प्रेगनेंसी में सुरक्षित एक्सरसाइज: नॉर्मल डिलीवरी की तैयारी, सुरक्षित हार्ट रेट और किन एक्सरसाइज से बचना चाहिए।",
        "thumbnail_url": TOPIC_IMAGE_POOLS["fitness"][3],
        "category": "Fitness",
        "tags": ["Prenatal Fitness", "Pregnancy", "Exercise", "Safe Movement"],
        "body_en": {
            "tldr": "ACOG recommends at least 150 minutes of moderate-intensity prenatal exercise weekly. Safe options include brisk walking, stationary cycling, swimming, and modified strength training; avoid supine exercises after week 16 and contact sports.",
            "introduction": "Decades ago, pregnant women were told to treat themselves as fragile invalids. Modern maternal-fetal medicine demonstrates the exact opposite: for uncomplicated pregnancies, regular exercise shortens labor duration, reduces gestational diabetes risk by 30%, and accelerates postpartum recovery.",
            "sections": [
                {
                    "heading": "Proven Clinical Benefits of Prenatal Fitness",
                    "content": "Regular prenatal exercise lowers the incidence of gestational diabetes, preeclampsia, and excessive gestational weight gain. It preserves lower back strength, curbs pelvic girdle discomfort, and enhances cardiovascular endurance required for labor. Babies born to active mothers also demonstrate superior cardiovascular adaptability at birth."
                },
                {
                    "heading": "Trimester-by-Trimester Adjustments",
                    "content": "First Trimester: Focus on keeping cool and hydrated. Gentle walking, low-impact cardio, and baseline strength training are safe. Second Trimester: Hormones relax ligaments (via relaxin). Avoid flat supine exercises (lying flat on your back after week 16 compresses the vena cava, reducing blood flow to the fetus). Elevate your torso to a 30° incline. Third Trimester: Shift focus to pelvic floor prep, deep squats with support, prenatal yoga, and swimming, which relieves buoyancy pressure on joints."
                },
                {
                    "heading": "Movements to Strictly Avoid",
                    "content": "Avoid contact sports, horseback riding, downhill skiing, hot yoga/Bikram yoga (hyperthermia risk), scuba diving, and exercises involving a high fall risk. Do not perform intense abdominal crunches or planks that exacerbate diastasis recti (abdominal muscle separation)."
                },
                {
                    "heading": "The 'Talk Test' and Warning Signs to Stop",
                    "content": "Use the 'talk test' to monitor intensity: you should be able to maintain a conversation comfortably without gasping for breath. Stop exercising immediately and contact your doctor if you experience vaginal bleeding, amniotic fluid leakage, dizziness, chest pain, calf swelling/pain, or regular painful uterine contractions."
                }
            ],
            "key_takeaways": [
                "Aim for 150 minutes of moderate exercise per week during uncomplicated pregnancies.",
                "Swimming, brisk walking, and modified strength training are exceptionally safe.",
                "Avoid lying flat on your back after week 16 to protect fetal oxygenation.",
                "Use the 'talk test' to gauge safe cardiovascular intensity.",
                "Cease exercise immediately for bleeding, fluid leakage, dizziness, or contractions."
            ],
            "myths_vs_facts": [
                {"myth": "Exercise during pregnancy causes premature labor.", "fact": "Extensive meta-analyses show that moderate exercise does not increase preterm birth risk in healthy pregnancies."},
                {"myth": "Your heart rate must never exceed 140 bpm.", "fact": "The old 140 bpm ceiling was retired by ACOG years ago; the 'talk test' and Rate of Perceived Exertion (RPE 12–14 out of 20) are the modern clinical standards."}
            ],
            "faqs": [
                {"question": "Can I start exercising in pregnancy if I was sedentary before?", "answer": "Yes! Begin with 15 minutes of gentle walking daily and gradually build up to 30 minutes, 5 days per week."},
                {"question": "Is swimming safe in the third trimester?", "answer": "Swimming is considered the single best third-trimester exercise because water buoyancy relieves weight from joints, pelvic ligaments, and back."}
            ],
            "sources": [
                {"name": "ACOG Committee Opinion No. 804: Physical Activity and Exercise During Pregnancy", "url": "https://www.acog.org"},
                {"name": "Canadian Guidelines for Physical Activity Throughout Pregnancy", "url": "https://www.csep.ca"}
            ],
            "medical_disclaimer": "This information is educational. Always obtain clinical clearance from your obstetrician before beginning or continuing prenatal workouts."
        },
        "body_hi": {
            "tldr": "गर्भावस्था में रोज 20-30 मिनट टहलना, तैराकी और प्रसवपूर्व योग नॉर्मल डिलीवरी की संभावना बढ़ाते हैं और जेस्टेशनल डायबिटीज के खतरे को 30% कम करते हैं।",
            "introduction": "आज का चिकित्सा विज्ञान साबित कर चुका है कि गर्भावस्था में सुरक्षित व्यायाम माँ और बच्चे दोनों के लिए वरदान है। यह पीठ दर्द कम करता है और प्रसव के समय लगने वाले शारीरिक बल के लिए तैयार करता है।",
            "sections": [
                {
                    "heading": "गर्भावस्था में व्यायाम के मुख्य फायदे",
                    "content": "नियमित टहलने और योग से ब्लड प्रेशर नियंत्रित रहता है, जेस्टेशनल डायबिटीज का खतरा टलता है और शरीर में रक्त संचार बेहतर होता है। सक्रिय रहने वाली माताओं में लेबर पेन का समय कम होता है।"
                },
                {
                    "heading": "तीनों तिमाहियों के जरूरी बदलाव",
                    "content": "पहली तिमाही में हल्की वॉक और पर्याप्त पानी पिएं। 16वें हफ्ते के बाद पीठ के बल सीधा लेटकर की जाने वाली एक्सरसाइज बंद कर दें (इससे गर्भाशय में खून का बहाव रुक सकता है)। तीसरी तिमाही में सहारा लेकर स्क्वाट्स और तितली आसन करें।"
                },
                {
                    "heading": "किन गतिविधियों से पूरी तरह बचें?",
                    "content": "गर्म योग (हॉट योग), पेट पर दबाव डालने वाले क्रंचेज, कूदने वाली एक्सरसाइज और गिरने के जोखिम वाले खेलों से पूरी तरह बचें।"
                },
                {
                    "heading": "व्यायाम कब तुरंत रोक देना चाहिए?",
                    "content": "अगर चक्कर आए, सांस फूलने लगे, योनि से पानी या खून निकले, या पेट में तेज दर्द हो, तो तुरंत रुक जाएं और डॉक्टर से संपर्क करें।"
                }
            ],
            "key_takeaways": [
                "हफ्ते में कम से कम 150 मिनट (रोज 30 मिनट) हल्की सैर करना सबसे उत्तम है।",
                "16वें हफ्ते के बाद पीठ के बल सीधा लेटकर कोई भी व्यायाम न करें।",
                "टहलते समय बोलते रहना चाहिए (टॉक टेस्ट)—अगर सांस फूलने लगे तो गति धीमी करें।"
            ],
            "myths_vs_facts": [
                {"myth": "गर्भावस्था में एक्सरसाइज करने से बच्चा गिर सकता है (मिसकैरेज)।", "fact": "डॉक्टर की अनुमति से की जाने वाली सुरक्षित सैर और योग से मिसकैरेज का कोई खतरा नहीं होता।"}
            ],
            "faqs": [
                {"question": "अगर पहले कभी एक्सरसाइज नहीं की तो क्या अब शुरू कर सकते हैं?", "answer": "हाँ, रोज 15 मिनट की धीमी सैर से शुरुआत करें और धीरे-धीरे समय बढ़ाकर 30 मिनट करें।"}
            ],
            "sources": [
                {"name": "ACOG Pregnancy Exercise Guidelines", "url": "https://www.acog.org"},
                {"name": "FOGSI Maternal Health", "url": "https://www.fogsi.org"}
            ],
            "medical_disclaimer": "यह सलाह सामान्य स्वास्थ्य के लिए है। कोई भी नया व्यायाम शुरू करने से पहले अपनी डॉक्टर से अनुमति लें।"
        }
    },
    {
        "topic_slug": "fitness",
        "subtopic_slug": "wellness",
        "title_en": "Pelvic Floor Health (Kegels): Benefits, Proper Technique & Common Mistakes",
        "title_hi": "पेल्विक फ्लोर एक्सरसाइज (कीगल): सही तरीका, फायदे और सामान्य गलतियां",
        "desc_en": "Master the pelvic floor muscles: preventing bladder leaks, supporting bladder and uterine organs, and knowing when relaxation is needed.",
        "desc_hi": "कीगल एक्सरसाइज का सही वैज्ञानिक तरीका: यूरिन लीकेज से बचाव, प्रसव के बाद पेल्विक मजबूती और क्या गलतियां न करें।",
        "thumbnail_url": TOPIC_IMAGE_POOLS["fitness"][4],
        "category": "Fitness",
        "tags": ["Pelvic Floor", "Kegels", "Incontinence", "Women's Wellness"],
        "body_en": {
            "tldr": "The pelvic floor is a hammock of muscles supporting the bladder, uterus, and bowels. Performing correct Kegels (lift and squeeze, followed by complete release) prevents urinary incontinence and prolapse.",
            "introduction": "Many women accept leaking urine when laughing, coughing, or jumping as an inevitable consequence of aging or childbirth. In reality, urinary incontinence is a treatable symptom of pelvic floor dysfunction. Training your pelvic floor correctly restores bladder control and sexual vitality.",
            "sections": [
                {
                    "heading": "Anatomy of the Pelvic Floor Sling",
                    "content": "The pelvic floor is a bowl-shaped muscular sling spanning from your pubic bone in front to your tailbone (coccyx) behind. It cradles your pelvic organs, controls the urinary and anal sphincters, stabilizes the pelvis, and contracts rhythmically during orgasm. Weakness can lead to stress urinary incontinence and pelvic organ prolapse."
                },
                {
                    "heading": "How to Perform a Proper Kegel Contraction",
                    "content": "To engage the pelvic floor, imagine attempting to stop the flow of urine mid-stream and holding in gas simultaneously. Squeeze and lift the muscles inward and upward. Hold for 3 to 5 seconds, breathing normally without holding your breath. Crucially, release fully for 5 seconds between contractions. Aim for 3 sets of 10 repetitions daily."
                },
                {
                    "heading": "The Most Common Mistakes That Worsen Function",
                    "content": "1. Squeezing the glutes, thighs, or abdominals instead of the internal pelvic sling. 2. Pushing downward (bearing down) instead of lifting upward. 3. Holding your breath, which creates harmful intra-abdominal pressure. 4. Never practicing complete relaxation—a hypertonic (overly tight) pelvic floor is just as dysfunctional as a weak one."
                },
                {
                    "heading": "Hypertonic Pelvic Floor: When Kegels Are Counterproductive",
                    "content": "If you suffer from painful intercourse (vaginismus or dyspareunia), pelvic pain, or difficulty emptying your bladder completely, your pelvic floor may be tight rather than weak. Performing Kegels on a hypertonic floor exacerbates pain. In such cases, pelvic floor physical therapy focusing on down-training, breathing, and release is indicated."
                }
            ],
            "key_takeaways": [
                "Lifting and squeezing inward and upward is the core motion of a Kegel.",
                "Always release fully between contractions; relaxation is 50% of the exercise.",
                "Do not clench your buttocks or hold your breath during contractions.",
                "Leaking urine when sneezing is common, but never normal or untreatable.",
                "If intercourse is painful, see a pelvic floor physical therapist before doing Kegels."
            ],
            "myths_vs_facts": [
                {"myth": "You should practice Kegels while actually urinating on the toilet.", "fact": "Stopping urine mid-stream is useful only once to identify the muscle; doing it regularly disrupts bladder emptying reflexes and increases UTI risk."},
                {"myth": "Kegels are only necessary for women who have had children.", "fact": "Nulliparous women, athletes, and post-menopausal women can all develop pelvic floor dysfunction from hormonal shifts or high impact."}
            ],
            "faqs": [
                {"question": "How long does it take for Kegels to stop bladder leaks?", "answer": "With consistent daily practice (3 sets of 10 reps), most women observe significant improvements in bladder control within 6 to 12 weeks."},
                {"question": "Can men do Kegel exercises?", "answer": "Yes. Men also have pelvic floor muscles supporting the bladder and prostate; Kegels help men with urinary incontinence and erectile quality."}
            ],
            "sources": [
                {"name": "American Urogynecologic Society (AUGS)", "url": "https://www.augs.org"},
                {"name": "NHS Pelvic Floor Muscle Exercises Guide", "url": "https://www.nhs.uk"}
            ],
            "medical_disclaimer": "This content is educational. Consult a urogynecologist or specialized pelvic floor physical therapist for chronic incontinence or pelvic pain."
        },
        "body_hi": {
            "tldr": "कीगल एक्सरसाइज पेल्विक मांसपेशियों (मूत्राशय और गर्भाशय को सहारा देने वाले अंग) को मजबूत करती है। सही तकनीक से करने पर छींकने या खांसने पर पेशाब रिसने की समस्या पूरी तरह ठीक हो जाती है।",
            "introduction": "हंसने, खांसने या छींकने पर पेशाब की बूंदें निकल जाना महिलाओं में बहुत आम है, लेकिन इसे सामान्य मानकर नजरअंदाज नहीं करना चाहिए। कीगल एक्सरसाइज पेल्विक मांसपेशियों को मजबूत बनाकर मूत्राशय पर पूरा नियंत्रण देती है।",
            "sections": [
                {
                    "heading": "पेल्विक फ्लोर क्या है?",
                    "content": "यह पेल्विक हड्डियों के बीच झूले की तरह फैली मांसपेशियों की एक परत है जो पेशाब की थैली, गर्भाशय और आंतों को अपनी जगह पर बनाए रखती है। डिलीवरी और उम्र के साथ ये कमजोर हो सकती हैं।"
                },
                {
                    "heading": "कीगल करने का सही तरीका",
                    "content": "कल्पना करें कि आपको पेशाब और गैस को बीच में ही रोकना है। उन अंदरूनी मांसपेशियों को अंदर और ऊपर की तरफ खींचें। 3 से 5 सेकंड तक रोके रखें और फिर 5 सेकंड के लिए पूरी तरह ढीला छोड़ें। दिन में 10-10 के 3 सेट करें।"
                },
                {
                    "heading": "सामान्य गलतियां जिनसे बचना चाहिए",
                    "content": "1. कूल्हों या जांघों को भींचना। 2. सांस रोक लेना। 3. नीचे की तरफ जोर लगाना (हमेशा ऊपर खींचना चाहिए)। 4. मांसपेशियों को ढीला न छोड़ना।"
                },
                {
                    "heading": "परिणाम कब दिखते हैं?",
                    "content": "नियमित रूप से रोज करने पर 6 से 8 हफ्तों के भीतर पेशाब रिसने की समस्या में बहुत बड़ा सुधार दिखने लगता है।"
                }
            ],
            "key_takeaways": [
                "मांसपेशियों को अंदर और ऊपर खींचना और फिर पूरा ढीला छोड़ना जरूरी है।",
                "एक्सरसाइज करते समय सांस सामान्य रूप से लेते रहें।",
                "छींकने पर पेशाब निकलना एक बीमारी का लक्षण है जो कीगल से पूरी तरह ठीक हो सकता है।"
            ],
            "myths_vs_facts": [
                {"myth": "पेशाब करते समय बार-बार धार रोककर कीगल करना चाहिए।", "fact": "पेशाब करते समय धार रोकने से मूत्राशय में संक्रमण (यूटीआई) हो सकता है। यह केवल एक बार मांसपेशियों की पहचान के लिए करें, रोज नहीं।"}
            ],
            "faqs": [
                {"question": "कीगल एक्सरसाइज दिन में कितनी बार करनी चाहिए?", "answer": "दिन में 2 से 3 बार, हर बार 10 बार मांसपेशियों को सिकोड़ें और ढीला छोड़ें। इसे बैठते या लेटते समय कभी भी किया जा सकता है।"}
            ],
            "sources": [
                {"name": "AUGS Guidelines", "url": "https://www.augs.org"},
                {"name": "NHS Pelvic Health", "url": "https://www.nhs.uk"}
            ],
            "medical_disclaimer": "यह जानकारी जागरूकता के लिए है। लगातार पेशाब की समस्या होने पर यूरोगायनेकोलॉजिस्ट से मिलें।"
        }
    },
    {
        "topic_slug": "fitness",
        "subtopic_slug": "wellness",
        "title_en": "Workouts for PCOS: Cardio vs Weight Lifting to Reverse Insulin Resistance",
        "title_hi": "PCOS और वर्कआउट: वजन घटाने और इंसुलिन रेजिस्टेंस मिटाने के लिए बेस्ट एक्सरसाइज",
        "desc_en": "The metabolic science of PCOS exercise: why heavy weights and walking beat chronic exhausting cardio for hormonal balancing.",
        "desc_hi": "PCOS में क्या बेहतर है: वेट ट्रेनिंग या कार्डियो? कॉर्टिसोल कम करने और हार्मोन्स बैलेंस करने का सही वर्कआउट प्लान।",
        "thumbnail_url": TOPIC_IMAGE_POOLS["fitness"][5],
        "category": "Fitness",
        "tags": ["PCOS", "Insulin Resistance", "Fitness", "Hormones"],
        "body_en": {
            "tldr": "Up to 70% of women with PCOS suffer from insulin resistance. Strength training builds skeletal muscle to clear blood glucose, while low-intensity steady-state walking prevents cortisol spikes. Excessive chronic HIIT can worsen symptoms.",
            "introduction": "When diagnosed with PCOS, women are frequently told: 'just lose weight.' Desperate for results, many dive into grueling 60-minute daily spin or HIIT classes, only to find themselves more exhausted, inflamed, and unable to shed stubborn abdominal weight. Understanding PCOS endocrinology completely transforms your exercise strategy.",
            "sections": [
                {
                    "heading": "The Core Culprit: Insulin Resistance and Androgens",
                    "content": "In PCOS, cells become resistant to insulin, causing the pancreas to pump out excess insulin. Hyperinsulinemia directly stimulates the ovaries to overproduce androgens (testosterone), resulting in facial hair (hirsutism), cystic acne, scalp thinning, and anovulation. Effective PCOS fitness must prioritize insulin sensitivity above arbitrary calorie burning."
                },
                {
                    "heading": "Why Strength Training is the Gold Standard for PCOS",
                    "content": "Skeletal muscle accounts for over 80% of whole-body insulin-mediated glucose uptake. Resistance training recruits large muscle groups (quads, glutes, back), activating non-insulin-dependent GLUT4 pathways that directly pull glucose from the bloodstream into muscles. Lifting weights 3 times weekly improves menstrual cyclicity, reduces testosterone, and trims waist circumference."
                },
                {
                    "heading": "The Cardio Trap: Cortisol vs Incline Walking",
                    "content": "PCOS patients naturally operate with a heightened sympathetic nervous system baseline. Excessive high-intensity cardio (HIIT 5+ days a week) elevates cortisol (the stress hormone). Elevated cortisol drives visceral belly fat storage and impairs progesterone production. The antidote: Low-Intensity Steady State (LISS) movement, particularly zone 2 incline walking for 8,000–10,000 steps daily."
                },
                {
                    "heading": "An Ideal Weekly PCOS Workout Protocol",
                    "content": "Monday: Full-body progressive strength training (45 mins). Tuesday: 40-minute brisk outdoor walking or gentle Pilates. Wednesday: Full-body strength training. Thursday: Active recovery / Restorative yoga. Friday: Strength training or short 15-minute low-impact interval session. Weekend: Nature walks, social movement, and relaxation."
                }
            ],
            "key_takeaways": [
                "Strength training activates muscle glucose disposal to reverse insulin resistance.",
                "Excessive cardio spikes cortisol, worsening belly fat and hormonal imbalance in PCOS.",
                "Pair 3 weekly strength sessions with daily 8,000–10,000 step walks.",
                "Gentle Pilates and restorative yoga reduce sympathetic stress drive.",
                "Fuel workouts with adequate protein and complex carbs; never train while severely fasting."
            ],
            "myths_vs_facts": [
                {"myth": "You must do high-intensity sweating workouts daily to lose PCOS belly fat.", "fact": "Chronic daily HIIT elevates cortisol, triggering the body to hold onto abdominal fat. Slow, progressive lifting and walking yield superior body composition improvements."},
                {"myth": "Exercise alone can cure PCOS without nutrition adjustments.", "fact": "Exercise and a low-glycaemic anti-inflammatory diet work synergistically; neither can fully compensate for the lack of the other."}
            ],
            "faqs": [
                {"question": "How long does it take for exercise to regulate periods in PCOS?", "answer": "Clinical trials show that 12 to 16 weeks of consistent strength training and walking improves menstrual regularity and ovulation in over 60% of PCOS patients."},
                {"question": "Can I do Pilates instead of heavy lifting?", "answer": "Yes. Mat and reformer Pilates provide excellent muscular endurance and core stability with minimal cortisol stress, making them ideal alongside walking."}
            ],
            "sources": [
                {"name": "Endocrine Society Clinical Practice Guidelines on PCOS", "url": "https://www.endocrine.org"},
                {"name": "International Evidence-Based Guideline for the Assessment and Management of PCOS", "url": "https://www.monash.edu"}
            ],
            "medical_disclaimer": "This content is educational. Consult your endocrinologist or gynecologist for personalized PCOS medical care."
        },
        "body_hi": {
            "tldr": "PCOS में बहुत ज्यादा कठिन कार्डियो करने से तनाव हार्मोन (कोर्टिसोल) बढ़ता है जिससे वजन कम नहीं होता। हफ्ते में 3 दिन वेट ट्रेनिंग और रोज 8,000-10,000 कदम टहलना सबसे असरदार इलाज है।",
            "introduction": "PCOS से पीड़ित 70% महिलाओं में इंसुलिन रेजिस्टेंस होता है। अत्यधिक थका देने वाली एक्सरसाइज करने से शरीर में तनाव हार्मोन बढ़ता है। वजन उठाने और धीमी सैर करने से इंसुलिन संवेदनशीलता सुधरती है और पीरियड्स नियमित होते हैं।",
            "sections": [
                {
                    "heading": "इंसुलिन रेजिस्टेंस और पीसीओएस का संबंध",
                    "content": "शरीर में ज्यादा इंसुलिन बनने से ओवरीज पुरुष हार्मोन (टेस्टोस्टेरोन) ज्यादा बनाने लगती हैं, जिससे चेहरे पर अनचाहे बाल, मुंहासे और पेट पर चर्बी जमा होती है। व्यायाम ऐसा होना चाहिए जो इंसुलिन को कम करे।"
                },
                {
                    "heading": "स्ट्रेंथ ट्रेनिंग (वजन उठाना) क्यों सबसे जरूरी है?",
                    "content": "मांसपेशियां खून में मौजूद अतिरिक्त शुगर को बिना इंसुलिन के सोख लेती हैं। हफ्ते में 3 दिन वेट ट्रेनिंग करने से टेस्टोस्टेरोन कम होता है और पेट की चर्बी तेजी से घटती है।"
                },
                {
                    "heading": "ज्यादा कार्डियो का नुकसान (कोर्टिसोल स्पाइक)",
                    "content": "रोजाना 1 घंटा तेज दौड़ना या पसीना बहाना कोर्टिसोल हार्मोन को बढ़ा देता है। बढ़ा हुआ कोर्टिसोल पेट की चर्बी को पकड़कर रखता है। इसलिए तेज दौड़ने के बजाय 45 मिनट तेज चाल से टहलना (ब्रिस्क वॉक) ज्यादा फायदेमंद है।"
                },
                {
                    "heading": "पीसीओएस के लिए आदर्श साप्ताहिक प्लान",
                    "content": "सोमवार, बुधवार, शुक्रवार: 40 मिनट वेट ट्रेनिंग (स्क्वाट्स, डम्बल एक्सरसाइज)। मंगलवार और गुरुवार: 45 मिनट वॉक या योगा। शनिवार-रविवार: आराम और हल्की सैर।"
                }
            ],
            "key_takeaways": [
                "वजन उठाने से शरीर का ब्लड शुगर और इंसुलिन नियंत्रित होता है।",
                "बहुत ज्यादा कार्डियो करने से तनाव हार्मोन बढ़ता है जिससे वजन नहीं घटता।",
                "रोजाना 8,000 से 10,000 कदम चलना पीसीओएस में रामबाण है।"
            ],
            "myths_vs_facts": [
                {"myth": "PCOS में वजन घटाने के लिए रोज 1 घंटा पसीना बहाकर दौड़ना जरूरी है।", "fact": "दौड़ने से ज्यादा फायदा वजन उठाने और शांत गति से टहलने से होता है, क्योंकि इसमें कोर्टिसोल नहीं बढ़ता।"}
            ],
            "faqs": [
                {"question": "वर्कआउट से पीरियड्स कितने दिन में नियमित होते हैं?", "answer": "नियमित रूप से 3 महीने तक सही वर्कआउट और खानपान अपनाने पर अधिकांश महिलाओं की माहवारी नियमित हो जाती है।"}
            ],
            "sources": [
                {"name": "Endocrine Society PCOS Guidelines", "url": "https://www.endocrine.org"},
                {"name": "Monash University International PCOS Guidelines", "url": "https://www.monash.edu"}
            ],
            "medical_disclaimer": "यह सलाह सामान्य फिटनेस के लिए है। उचित इलाज के लिए अपनी एंडोक्रिनोलॉजिस्ट या गायनेकोलॉजिस्ट से मिलें।"
        }
    }
]

def run_population():
    print("=" * 70)
    print("SAKHI AI: POPULATING THUMBNAILS & REMAINING LEARNING TOPICS")
    print("=" * 70)

    init_db(settings.database_url)
    SessionLocal = get_session_factory()
    db = SessionLocal()

    # -------------------------------------------------------------------------
    # STEP 1: Update YouTube video thumbnails
    # -------------------------------------------------------------------------
    print("\n[Step 1] Updating YouTube videos with crisp YouTube thumbnails...")
    videos = db.scalars(
        select(LearningContent).where(LearningContent.source_type == "YOUTUBE")
    ).all()
    yt_updated = 0
    for v in videos:
        if v.media_url:
            vid_id = extract_youtube_id(v.media_url)
            if vid_id:
                thumb = f"https://img.youtube.com/vi/{vid_id}/hqdefault.jpg"
                v.thumbnail_url = thumb
                yt_updated += 1
    db.commit()
    print(f"  -> Successfully updated {yt_updated} YouTube video thumbnails.")

    # -------------------------------------------------------------------------
    # STEP 2: Update existing articles with curated Unsplash photos
    # -------------------------------------------------------------------------
    print("\n[Step 2] Updating existing articles with curated health photography...")
    existing_articles = db.scalars(
        select(LearningContent).where(
            LearningContent.content_type == "ARTICLE",
            LearningContent.source_type == "INTERNAL"
        )
    ).all()
    
    art_updated = 0
    for idx, art in enumerate(existing_articles):
        # Match topic or category
        title_lower = art.title.lower()
        if "menstrua" in title_lower or "period" in title_lower or "pms" in title_lower:
            pool = TOPIC_IMAGE_POOLS["periods"]
        elif "pcos" in title_lower or "pcod" in title_lower:
            pool = TOPIC_IMAGE_POOLS["pcos"]
        elif "iron" in title_lower or "calcium" in title_lower or "nutrition" in title_lower or "folic" in title_lower or "hormonal" in title_lower:
            pool = TOPIC_IMAGE_POOLS["nutrition"]
        elif "stress" in title_lower or "burnout" in title_lower or "sleep" in title_lower or "anxiety" in title_lower or "self‑care" in title_lower or "self-care" in title_lower:
            pool = TOPIC_IMAGE_POOLS["mental-wellbeing"]
        elif "puberty" in title_lower or "body changes" in title_lower or "discharge" in title_lower or "hygiene" in title_lower:
            pool = TOPIC_IMAGE_POOLS["puberty"]
        else:
            pool = TOPIC_IMAGE_POOLS["periods"]
        
        assigned_thumb = pool[idx % len(pool)]
        art.thumbnail_url = assigned_thumb
        art_updated += 1

    db.commit()
    print(f"  -> Successfully assigned thumbnails to {art_updated} existing articles.")

    # -------------------------------------------------------------------------
    # STEP 3: Update Learning Paths thumbnails
    # -------------------------------------------------------------------------
    print("\n[Step 3] Updating Learning Paths with course banner thumbnails...")
    paths = db.scalars(select(LearningPath)).all()
    paths_updated = 0
    for p in paths:
        if p.slug in PATH_THUMBNAILS:
            p.thumbnail_url = PATH_THUMBNAILS[p.slug]
            paths_updated += 1
    db.commit()
    print(f"  -> Successfully updated {paths_updated} learning path banners.")

    # -------------------------------------------------------------------------
    # STEP 4: Populate remaining 3 topics (Pregnancy, Reproductive Health, Fitness)
    # -------------------------------------------------------------------------
    print("\n[Step 4] Populating remaining topics (Pregnancy, Reproductive Health, Fitness)...")
    
    topics_cache = {}
    subtopics_cache = {}
    
    for t_slug in ["pregnancy", "reproductive-health", "fitness"]:
        top = db.scalar(select(Topic).where(Topic.slug == t_slug))
        if top:
            topics_cache[t_slug] = top
            for st in top.subtopics:
                subtopics_cache[f"{t_slug}:{st.slug}"] = st

    new_articles_created = 0
    for item in NEW_TOPICS_CONTENT:
        t_slug = item["topic_slug"]
        st_slug = item["subtopic_slug"]
        topic = topics_cache.get(t_slug)
        subtopic = subtopics_cache.get(f"{t_slug}:{st_slug}")
        
        if not topic:
            print(f"  [ERROR] Topic {t_slug} not found, skipping.")
            continue
        
        # Check if already exists
        existing_en = db.scalar(
            select(LearningContent).where(
                LearningContent.title == item["title_en"],
                LearningContent.language == "en"
            )
        )
        if existing_en:
            print(f"  [SKIP] Article '{item['title_en']}' already exists.")
            continue

        translation_group_id = str(uuid.uuid4())
        
        # 1. Create English Article
        en_content = LearningContent(
            id=str(uuid.uuid4()),
            title=item["title_en"],
            description=item["desc_en"],
            content_type="ARTICLE",
            source_type="INTERNAL",
            body=item["body_en"],
            category=item["category"],
            tags=item["tags"],
            language="en",
            audience="ALL",
            status="PUBLISHED",
            medical_review_status="MEDICALLY_REVIEWED",
            translation_group_id=translation_group_id,
            author_id="SYSTEM-MEDICALLY-VERIFIED",
            topic_id=topic.id,
            subtopic_id=subtopic.id if subtopic else None,
            thumbnail_url=item["thumbnail_url"],
            is_featured=(new_articles_created % 3 == 0),
            is_short_form=False,
            duration_minutes=5,
            published_at=datetime.utcnow()
        )
        db.add(en_content)

        # 2. Create Hindi Article
        hi_content = LearningContent(
            id=str(uuid.uuid4()),
            title=item["title_hi"],
            description=item["desc_hi"],
            content_type="ARTICLE",
            source_type="INTERNAL",
            body=item["body_hi"],
            category=item["category"],
            tags=item["tags"],
            language="hi",
            audience="ALL",
            status="PUBLISHED",
            medical_review_status="MEDICALLY_REVIEWED",
            translation_group_id=translation_group_id,
            author_id="SYSTEM-MEDICALLY-VERIFIED",
            topic_id=topic.id,
            subtopic_id=subtopic.id if subtopic else None,
            thumbnail_url=item["thumbnail_url"],
            is_featured=(new_articles_created % 3 == 0),
            is_short_form=False,
            duration_minutes=5,
            published_at=datetime.utcnow()
        )
        db.add(hi_content)
        new_articles_created += 2

        print(f"  [CREATED] (EN + HI) {item['title_en']}")

    db.commit()
    print(f"\n  -> Successfully created {new_articles_created} new published articles ({new_articles_created // 2} EN + {new_articles_created // 2} HI) across Pregnancy, Reproductive Health, and Fitness!")

    # -------------------------------------------------------------------------
    # FINAL VERIFICATION
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("FINAL TOPIC CONTENT AUDIT:")
    print("=" * 70)
    all_topics = db.scalars(select(Topic).where(Topic.is_active.is_(True)).order_by(Topic.display_order)).all()
    for t in all_topics:
        count = db.scalar(select(LearningContent).where(LearningContent.topic_id == t.id))
        all_items = db.scalars(select(LearningContent).where(LearningContent.topic_id == t.id)).all()
        thumb_count = sum(1 for x in all_items if x.thumbnail_url)
        print(f"[{t.icon or '📚'}] {t.name:<32} (slug={t.slug:<20}) | {count:>2} articles/videos | {thumb_count:>2} with thumbnails")

    print("\nAll tasks completed successfully!")


if __name__ == "__main__":
    run_population()
