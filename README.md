# Cloud Kitchen Delivery Slot Booking System

Flask + SQLite + SQLAlchemy + Bootstrap 5.

## Features
- User register / login (password hashing, session management via Flask-Login)
- Pick delivery date and view 4 daily slots (09–12, 12–15, 15–18, 18–21)
- Slot capacity = 50 items; backend validates capacity
- If slot full: popup-style options to (A) book next available slot or (B) pre-book same slot on next date
- Menu of 8 items stored in DB
- Cart limit of 5 items per booking, validated in backend
- Review → Place order → Confirmation
- Booking history with View / Cancel
- Cancel allowed only when status = Pending; releases slot capacity
- Statuses: Pending, Preparing, Completed, Cancelled

## Setup (VS Code)

```bash
python -m venv venv
# Windows:  venv\Scripts\activate
# macOS/Linux:  source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000

The SQLite `database.db` is auto-created on first run, along with seeded menu and 14 days of slots.

## Project Structure
```
cloud-kitchen-booking/
├── app.py
├── models.py
├── routes.py
├── requirements.txt
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── slots.html
│   ├── slot_full.html
│   ├── menu.html
│   ├── cart.html
│   ├── review.html
│   ├── confirmation.html
│   └── history.html
├── static/
│   ├── css/style.css
│   └── js/app.js
└── database.db   (created at runtime)
```

## Changing Order Status
Statuses are set to `Pending` by default. To simulate Preparing/Completed, update via a SQLite tool or add an admin route. Cancellation in UI works only while status is `Pending`.
