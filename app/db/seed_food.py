import uuid
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.nutrition import Food, FoodServingOption

# Representative Indian & International Foods Seed Dataset
SEED_FOODS = [
    {
        "name": "Roti / Chapati",
        "brand": "Generic",
        "barcode": None,
        "is_verified": True,
        "calories": 104.0,
        "protein": 3.0,
        "carbohydrates": 22.0,
        "fat": 0.4,
        "fiber": 3.0,
        "serving_options": [
            {"description": "1 medium roti", "serving_qty": 1.0, "serving_unit": "piece", "calories": 104.0}
        ]
    },
    {
        "name": "White Rice (Cooked)",
        "brand": "Generic",
        "barcode": None,
        "is_verified": True,
        "calories": 205.0,
        "protein": 4.3,
        "carbohydrates": 44.5,
        "fat": 0.4,
        "fiber": 0.6,
        "serving_options": [
            {"description": "1 cup cooked", "serving_qty": 158.0, "serving_unit": "g", "calories": 205.0},
            {"description": "1 katori (bowl)", "serving_qty": 100.0, "serving_unit": "g", "calories": 130.0}
        ]
    },
    {
        "name": "Toor Dal (Yellow Lentils) - Cooked",
        "brand": "Generic",
        "barcode": None,
        "is_verified": True,
        "calories": 115.0,
        "protein": 6.0,
        "carbohydrates": 20.0,
        "fat": 1.0,
        "fiber": 8.0,
        "serving_options": [
            {"description": "1 katori (bowl)", "serving_qty": 100.0, "serving_unit": "g", "calories": 115.0}
        ]
    },
    {
        "name": "Paneer (Indian Cottage Cheese)",
        "brand": "Generic",
        "barcode": None,
        "is_verified": True,
        "calories": 296.0,
        "protein": 11.1,
        "carbohydrates": 3.4,
        "fat": 25.0,
        "fiber": 0.0,
        "serving_options": [
            {"description": "100g serving", "serving_qty": 100.0, "serving_unit": "g", "calories": 296.0}
        ]
    },
    {
        "name": "Idli",
        "brand": "Generic",
        "barcode": None,
        "is_verified": True,
        "calories": 39.0,
        "protein": 1.2,
        "carbohydrates": 8.0,
        "fat": 0.1,
        "fiber": 0.4,
        "serving_options": [
            {"description": "1 medium piece", "serving_qty": 40.0, "serving_unit": "g", "calories": 39.0}
        ]
    },
    {
        "name": "Plain Dosa",
        "brand": "Generic",
        "barcode": None,
        "is_verified": True,
        "calories": 133.0,
        "protein": 3.0,
        "carbohydrates": 23.0,
        "fat": 3.0,
        "fiber": 1.0,
        "serving_options": [
            {"description": "1 medium dosa", "serving_qty": 80.0, "serving_unit": "g", "calories": 133.0}
        ]
    },
    {
        "name": "Masala Chai (with Milk and Sugar)",
        "brand": "Generic",
        "barcode": None,
        "is_verified": True,
        "calories": 73.0,
        "protein": 2.0,
        "carbohydrates": 10.0,
        "fat": 2.5,
        "fiber": 0.0,
        "serving_options": [
            {"description": "1 small cup (100ml)", "serving_qty": 100.0, "serving_unit": "ml", "calories": 73.0}
        ]
    },
    {
        "name": "Samosa",
        "brand": "Generic",
        "barcode": None,
        "is_verified": True,
        "calories": 262.0,
        "protein": 3.5,
        "carbohydrates": 24.0,
        "fat": 17.0,
        "fiber": 2.1,
        "serving_options": [
            {"description": "1 medium piece", "serving_qty": 100.0, "serving_unit": "g", "calories": 262.0}
        ]
    },
    {
        "name": "Chicken Curry (Indian Style)",
        "brand": "Generic",
        "barcode": None,
        "is_verified": True,
        "calories": 210.0,
        "protein": 18.0,
        "carbohydrates": 6.0,
        "fat": 12.0,
        "fiber": 1.5,
        "serving_options": [
            {"description": "1 katori (bowl)", "serving_qty": 150.0, "serving_unit": "g", "calories": 315.0}
        ]
    },
    {
        "name": "Apple",
        "brand": "Generic",
        "barcode": None,
        "is_verified": True,
        "calories": 52.0,
        "protein": 0.3,
        "carbohydrates": 13.8,
        "fat": 0.2,
        "fiber": 2.4,
        "serving_options": [
            {"description": "1 medium apple (182g)", "serving_qty": 182.0, "serving_unit": "g", "calories": 95.0},
            {"description": "100g", "serving_qty": 100.0, "serving_unit": "g", "calories": 52.0}
        ]
    }
]


def seed_food_database():
    db: Session = SessionLocal()
    try:
        # Check if database is already seeded
        if db.query(Food).first():
            print("Food database is already seeded. Skipping.")
            return

        print(f"Seeding {len(SEED_FOODS)} food items...")
        
        for item_data in SEED_FOODS:
            food_id = str(uuid.uuid4())
            food = Food(
                id=food_id,
                name=item_data["name"],
                brand=item_data["brand"],
                barcode=item_data["barcode"],
                is_verified=item_data["is_verified"],
                calories=item_data["calories"],
                protein=item_data["protein"],
                carbohydrates=item_data["carbohydrates"],
                fat=item_data["fat"],
                fiber=item_data["fiber"]
            )
            db.add(food)
            
            for option_data in item_data["serving_options"]:
                option = FoodServingOption(
                    id=str(uuid.uuid4()),
                    food_id=food_id,
                    description=option_data["description"],
                    serving_qty=option_data["serving_qty"],
                    serving_unit=option_data["serving_unit"],
                    calories=option_data["calories"]
                )
                db.add(option)
                
        db.commit()
        print("Successfully seeded food database.")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_food_database()
