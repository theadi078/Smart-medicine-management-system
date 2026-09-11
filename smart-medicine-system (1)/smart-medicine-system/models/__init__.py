"""
Models package.

`db` is created here (not in app.py) so that every model file can import
it without circular-import problems, and app.py just calls db.init_app(app).
"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Import models AFTER db is defined so they can do `from models import db`.
from models.user import User            # noqa: E402,F401
from models.medicine import Medicine     # noqa: E402,F401
from models.schedule import MedicineSchedule  # noqa: E402,F401
from models.history import MedicineHistory     # noqa: E402,F401
from models.notification import Notification   # noqa: E402,F401
