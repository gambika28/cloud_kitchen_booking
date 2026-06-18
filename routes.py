import uuid
from datetime import datetime, date, timedelta
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, session, jsonify
)
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import (
    db, User, DeliverySlot, MenuItem, Booking, BookingItem,
    MAX_SLOT_CAPACITY, MAX_ITEMS_PER_BOOKING,
)

bp = Blueprint("main", __name__)


# ---------- Auth ----------
@bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return redirect(url_for("main.login"))


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for("main.register"))
        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "warning")
            return redirect(url_for("main.register"))
        user = User(name=name, email=email, password=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("main.login"))
    return render_template("register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password, password):
            flash("Invalid email or password.", "danger")
            return redirect(url_for("main.login"))
        login_user(user)
        session.pop("cart", None)
        flash(f"Welcome, {user.name}!", "success")
        return redirect(url_for("main.dashboard"))
    return render_template("login.html")


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    session.pop("cart", None)
    flash("Logged out.", "info")
    return redirect(url_for("main.login"))


# ---------- Dashboard ----------
@bp.route("/dashboard")
@login_required
def dashboard():
    today_str = date.today().isoformat()
    max_str = (date.today() + timedelta(days=13)).isoformat()
    return render_template("dashboard.html", today=today_str, max_date=max_str)


# ---------- Slots ----------
@bp.route("/slots")
@login_required
def slots():
    date_str = request.args.get("date")
    if not date_str:
        flash("Please pick a delivery date.", "warning")
        return redirect(url_for("main.dashboard"))
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        flash("Invalid date.", "danger")
        return redirect(url_for("main.dashboard"))

    slots = DeliverySlot.query.filter_by(date=d).order_by(DeliverySlot.slot_time).all()
    if not slots:
        # ensure seeded
        for st in [
            "09:00 AM - 12:00 PM", "12:00 PM - 03:00 PM",
            "03:00 PM - 06:00 PM", "06:00 PM - 09:00 PM",
        ]:
            db.session.add(DeliverySlot(date=d, slot_time=st, max_capacity=MAX_SLOT_CAPACITY))
        db.session.commit()
        slots = DeliverySlot.query.filter_by(date=d).order_by(DeliverySlot.slot_time).all()

    return render_template("slots.html", slots=slots, selected_date=d)


@bp.route("/select_slot/<int:slot_id>")
@login_required
def select_slot(slot_id):
    slot = DeliverySlot.query.get_or_404(slot_id)
    if slot.is_full:
        # find next available slot
        recommended = (DeliverySlot.query
                       .filter(DeliverySlot.booked_items < DeliverySlot.max_capacity)
                       .filter((DeliverySlot.date > slot.date) |
                               ((DeliverySlot.date == slot.date) & (DeliverySlot.slot_time > slot.slot_time)))
                       .order_by(DeliverySlot.date, DeliverySlot.slot_time)
                       .first())
        # next-date same-slot prebook
        prebook = None
        next_d = slot.date + timedelta(days=1)
        for _ in range(14):
            candidate = DeliverySlot.query.filter_by(date=next_d, slot_time=slot.slot_time).first()
            if not candidate:
                candidate = DeliverySlot(date=next_d, slot_time=slot.slot_time, max_capacity=MAX_SLOT_CAPACITY)
                db.session.add(candidate)
                db.session.commit()
            if not candidate.is_full:
                prebook = candidate
                break
            next_d += timedelta(days=1)

        return render_template("slot_full.html", slot=slot, recommended=recommended, prebook=prebook)

    session["slot_id"] = slot.id
    session["cart"] = session.get("cart", {})
    return redirect(url_for("main.menu"))


# ---------- Menu ----------
@bp.route("/menu")
@login_required
def menu():
    if "slot_id" not in session:
        flash("Please select a delivery slot first.", "warning")
        return redirect(url_for("main.dashboard"))
    items = MenuItem.query.order_by(MenuItem.name).all()
    slot = DeliverySlot.query.get(session["slot_id"])
    cart = session.get("cart", {})
    total_qty = sum(cart.values())
    return render_template("menu.html", items=items, slot=slot, cart=cart,
                           total_qty=total_qty, max_items=MAX_ITEMS_PER_BOOKING)


@bp.route("/cart/add/<int:item_id>", methods=["POST"])
@login_required
def cart_add(item_id):
    cart = session.get("cart", {})
    qty = int(request.form.get("qty", 1))
    current_total = sum(cart.values())
    new_total = current_total - cart.get(str(item_id), 0) + qty
    if new_total > MAX_ITEMS_PER_BOOKING:
        return jsonify({"ok": False, "error": f"Maximum {MAX_ITEMS_PER_BOOKING} items are allowed per booking"}), 400
    if qty <= 0:
        cart.pop(str(item_id), None)
    else:
        cart[str(item_id)] = qty
    session["cart"] = cart
    return jsonify({"ok": True, "total": sum(cart.values())})


@bp.route("/cart")
@login_required
def cart():
    cart = session.get("cart", {})
    items = []
    grand = 0
    for iid, qty in cart.items():
        mi = MenuItem.query.get(int(iid))
        if mi:
            subtotal = mi.price * qty
            grand += subtotal
            items.append({"item": mi, "qty": qty, "subtotal": subtotal})
    slot = DeliverySlot.query.get(session.get("slot_id")) if session.get("slot_id") else None
    return render_template("cart.html", items=items, grand=grand, slot=slot,
                           total_qty=sum(cart.values()), max_items=MAX_ITEMS_PER_BOOKING)


@bp.route("/cart/remove/<int:item_id>")
@login_required
def cart_remove(item_id):
    cart = session.get("cart", {})
    cart.pop(str(item_id), None)
    session["cart"] = cart
    return redirect(url_for("main.cart"))


# ---------- Review & Place ----------
@bp.route("/review")
@login_required
def review():
    cart = session.get("cart", {})
    if not cart:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("main.menu"))
    if sum(cart.values()) > MAX_ITEMS_PER_BOOKING:
        flash(f"Maximum {MAX_ITEMS_PER_BOOKING} items are allowed per booking.", "danger")
        return redirect(url_for("main.cart"))
    items = []
    grand = 0
    for iid, qty in cart.items():
        mi = MenuItem.query.get(int(iid))
        if mi:
            subtotal = mi.price * qty
            grand += subtotal
            items.append({"item": mi, "qty": qty, "subtotal": subtotal})
    slot = DeliverySlot.query.get(session.get("slot_id"))
    return render_template("review.html", items=items, grand=grand, slot=slot,
                           total_qty=sum(cart.values()))


@bp.route("/place_order", methods=["POST"])
@login_required
def place_order():
    cart = session.get("cart", {})
    slot_id = session.get("slot_id")
    if not cart or not slot_id:
        flash("Invalid order.", "danger")
        return redirect(url_for("main.dashboard"))
    total_qty = sum(cart.values())
    if total_qty > MAX_ITEMS_PER_BOOKING:
        flash(f"Maximum {MAX_ITEMS_PER_BOOKING} items are allowed per booking.", "danger")
        return redirect(url_for("main.cart"))

    slot = DeliverySlot.query.get_or_404(slot_id)
    if slot.booked_items + total_qty > slot.max_capacity:
        flash("Slot capacity exceeded. Please pick another slot.", "danger")
        return redirect(url_for("main.slots", date=slot.date.isoformat()))

    booking = Booking(
        booking_id="BK-" + uuid.uuid4().hex[:8].upper(),
        user_id=current_user.id,
        slot_id=slot.id,
        total_items=total_qty,
        status="Pending",
    )
    db.session.add(booking)
    db.session.flush()
    for iid, qty in cart.items():
        db.session.add(BookingItem(booking_id=booking.id, menu_item_id=int(iid), quantity=qty))
    slot.booked_items += total_qty
    db.session.commit()

    session.pop("cart", None)
    session.pop("slot_id", None)
    return redirect(url_for("main.confirmation", booking_id=booking.booking_id))


@bp.route("/confirmation/<booking_id>")
@login_required
def confirmation(booking_id):
    booking = Booking.query.filter_by(booking_id=booking_id, user_id=current_user.id).first_or_404()
    return render_template("confirmation.html", booking=booking)


# ---------- History ----------
@bp.route("/history")
@login_required
def history():
    bookings = (Booking.query.filter_by(user_id=current_user.id)
                .order_by(Booking.created_at.desc()).all())
    return render_template("history.html", bookings=bookings)


@bp.route("/booking/<booking_id>")
@login_required
def booking_details(booking_id):
    booking = Booking.query.filter_by(booking_id=booking_id, user_id=current_user.id).first_or_404()
    return render_template("confirmation.html", booking=booking, details_mode=True)


@bp.route("/cancel/<booking_id>", methods=["POST"])
@login_required
def cancel(booking_id):
    booking = Booking.query.filter_by(booking_id=booking_id, user_id=current_user.id).first_or_404()
    if booking.status != "Pending":
        flash("Cancellation not allowed. Food preparation has started.", "danger")
        return redirect(url_for("main.history"))
    booking.status = "Cancelled"
    booking.slot.booked_items = max(0, booking.slot.booked_items - booking.total_items)
    db.session.commit()
    flash("Booking cancelled. Slot capacity released.", "success")
    return redirect(url_for("main.history"))
