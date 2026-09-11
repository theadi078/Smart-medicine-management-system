import os
from flask import Flask, render_template
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from apscheduler.schedulers.background import BackgroundScheduler

from config import config_map
from models import db


def create_app(config_name=None):
    app = Flask(__name__)

    config_name = config_name or os.environ.get("FLASK_ENV", "default")
    app.config.from_object(config_map.get(config_name, config_map["default"]))

    # --- Ensure required folders exist ---
    os.makedirs(os.path.join(os.path.dirname(__file__), "database"), exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # --- Extensions ---
    db.init_app(app)

    csrf = CSRFProtect()
    csrf.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "info"
    login_manager.init_app(app)

    from models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # --- Blueprints ---
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.medicines import medicines_bp
    from routes.schedule import schedule_bp
    from routes.history import history_bp
    from routes.notifications import notifications_bp
    from routes.assistant import assistant_bp
    from routes.profile import profile_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(medicines_bp)
    app.register_blueprint(schedule_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(assistant_bp)
    app.register_blueprint(profile_bp)

    # Landing page
    @app.route("/")
    def landing():
        from flask_login import current_user
        if current_user.is_authenticated:
            from flask import redirect, url_for
            return redirect(url_for("dashboard.index"))
        return render_template("landing.html")

    # --- Error handlers ---
    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    # --- Template globals ---
    @app.context_processor
    def inject_notification_count():
        from flask_login import current_user
        from services.notification_service import get_unread_count
        if current_user.is_authenticated:
            return {"nav_unread_notifications": get_unread_count(current_user.id)}
        return {"nav_unread_notifications": 0}

    # --- Create tables ---
    with app.app_context():
        db.create_all()

    # --- Background scheduler: reminders + expiry checks (runs every minute) ---
    if not app.config.get("TESTING"):
        scheduler = BackgroundScheduler(daemon=True)

        def scheduled_tick():
            with app.app_context():
                from services import reminder_service, expiry_service
                from models.user import User
                for user in User.query.all():
                    reminder_service.get_today_schedule(user.id)
                    reminder_service.generate_due_reminders(user.id)
                    reminder_service.sweep_missed_doses(user.id)
                expiry_service.run_expiry_check_for_all()

        scheduler.add_job(scheduled_tick, "interval", minutes=1, id="reminder_expiry_tick", replace_existing=True)
        scheduler.start()
        app.scheduler = scheduler

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=app.config.get("DEBUG", True), host="0.0.0.0", port=5000, use_reloader=False)