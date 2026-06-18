import os
from datetime import date, timedelta
from flask import Flask
from flask_login import LoginManager
from models import db, User, DeliverySlot, MenuItem, MAX_SLOT_CAPACITY
from routes import bp

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

SLOT_TIMES = [
    "09:00 AM - 12:00 PM",
    "12:00 PM - 03:00 PM",
    "03:00 PM - 06:00 PM",
    "06:00 PM - 09:00 PM",
]

SAMPLE_MENU = [
    ("Burger", 150),
    ("Pizza", 300),
    ("Pasta", 220),
    ("Sandwich", 120),
    ("Fries", 90),
    ("Biryani", 250),
    ("Noodles", 180),
    ("Coke", 60),
]


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "change-me-in-production"
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(BASE_DIR, 'database.db')}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = "main.login"
    login_manager.login_message_category = "warning"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    app.register_blueprint(bp)

    with app.app_context():
        db.create_all()
        seed_data()

    return app


def seed_data():
    # Seed menu
    if MenuItem.query.count() == 0:
        for name, price in SAMPLE_MENU:
            db.session.add(MenuItem(name=name, price=price))
        db.session.commit()

    # Seed slots for the next 14 days
    today = date.today()
    for i in range(14):
        d = today + timedelta(days=i)
        for st in SLOT_TIMES:
            exists = DeliverySlot.query.filter_by(date=d, slot_time=st).first()
            if not exists:
                db.session.add(DeliverySlot(date=d, slot_time=st, max_capacity=MAX_SLOT_CAPACITY, booked_items=0))
    db.session.commit()


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000)
