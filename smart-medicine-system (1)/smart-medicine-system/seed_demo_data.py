"""
Optional demo-data seeder.

Creates one demo user with a handful of clearly-labeled SAMPLE medicines so
the app can be demonstrated immediately (dashboard, reminders, expiry
alerts, AI assistant) without manual data entry.

Run with:  python seed_demo_data.py

This is NOT run automatically by app.py - it is an opt-in convenience
script for demos/viva, as required by the project spec.
"""

from datetime import date, timedelta, time

from app import create_app
from models import db
from models.user import User
from models.medicine import Medicine
from models.schedule import MedicineSchedule

DEMO_EMAIL = "demo@smartmedicine.local"
DEMO_PASSWORD = "demo1234"


def seed():
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(email=DEMO_EMAIL).first()
        if not user:
            user = User(name="Demo User", email=DEMO_EMAIL)
            user.set_password(DEMO_PASSWORD)
            db.session.add(user)
            db.session.commit()
            print(f"Created demo user: {DEMO_EMAIL} / {DEMO_PASSWORD}")
        else:
            print("Demo user already exists - adding/refreshing sample medicines.")

        today = date.today()

        sample_medicines = [
            {
                "name": "Medicine A (Sample)",
                "medicine_type": "Tablet",
                "dosage": "500mg",
                "quantity": 20,
                "expiry_date": today + timedelta(days=30),
                "food_instruction": "After Food",
                "notes": "Sample data for demonstration purposes only - not a real prescription.",
                "times": [time(8, 0)],
            },
            {
                "name": "Medicine B (Sample)",
                "medicine_type": "Capsule",
                "dosage": "250mg",
                "quantity": 10,
                "expiry_date": today + timedelta(days=7),
                "food_instruction": "Before Food",
                "notes": "Sample data for demonstration purposes only - not a real prescription.",
                "times": [time(13, 0)],
            },
            {
                "name": "Medicine C (Sample)",
                "medicine_type": "Syrup",
                "dosage": "10ml",
                "quantity": 1,
                "expiry_date": today + timedelta(days=1),
                "food_instruction": "With Food",
                "notes": "Sample data for demonstration purposes only - not a real prescription.",
                "times": [time(21, 0)],
            },
        ]

        for sm in sample_medicines:
            existing = Medicine.query.filter_by(user_id=user.id, name=sm["name"]).first()
            if existing:
                continue
            medicine = Medicine(
                user_id=user.id,
                name=sm["name"],
                medicine_type=sm["medicine_type"],
                dosage=sm["dosage"],
                quantity=sm["quantity"],
                expiry_date=sm["expiry_date"],
                start_date=today - timedelta(days=5),
                food_instruction=sm["food_instruction"],
                notes=sm["notes"],
            )
            db.session.add(medicine)
            db.session.flush()
            for t in sm["times"]:
                db.session.add(MedicineSchedule(
                    medicine_id=medicine.id,
                    scheduled_time=t,
                    frequency="Daily",
                    reminder_window=60,
                ))
            db.session.commit()
            print(f"  Added sample medicine: {sm['name']}")

        print("\nDemo data ready. Log in with:")
        print(f"  Email:    {DEMO_EMAIL}")
        print(f"  Password: {DEMO_PASSWORD}")


if __name__ == "__main__":
    seed()
