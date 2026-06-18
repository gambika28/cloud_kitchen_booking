from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

MAX_SLOT_CAPACITY = 50
MAX_ITEMS_PER_BOOKING = 5


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    bookings = db.relationship("Booking", backref="user", lazy=True)


class DeliverySlot(db.Model):
    __tablename__ = "delivery_slots"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, index=True)
    slot_time = db.Column(db.String(50), nullable=False)
    max_capacity = db.Column(db.Integer, default=MAX_SLOT_CAPACITY, nullable=False)
    booked_items = db.Column(db.Integer, default=0, nullable=False)

    __table_args__ = (db.UniqueConstraint("date", "slot_time", name="uq_date_slot"),)

    @property
    def remaining(self):
        return self.max_capacity - self.booked_items

    @property
    def is_full(self):
        return self.booked_items >= self.max_capacity


class MenuItem(db.Model):
    __tablename__ = "menu_items"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Float, nullable=False)


class Booking(db.Model):
    __tablename__ = "bookings"
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.String(20), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    slot_id = db.Column(db.Integer, db.ForeignKey("delivery_slots.id"), nullable=False)
    total_items = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default="Pending", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    slot = db.relationship("DeliverySlot")
    items = db.relationship("BookingItem", backref="booking", cascade="all, delete-orphan")


class BookingItem(db.Model):
    __tablename__ = "booking_items"
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey("menu_items.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    menu_item = db.relationship("MenuItem")
