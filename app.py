import os
from datetime import datetime, timezone
from flask import Flask
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv
from sqlalchemy import text
from models import db, User, NoteReminder
from auth import auth_bp
from notes import notes_bp
from oauth import oauth_bp, init_oauth
import threading
import time
import smtplib
from email.mime.text import MIMEText

login_manager = LoginManager()
csrf = CSRFProtect()

def create_app():
    load_dotenv(override=True)
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev")
    
    # Default to MySQL for XAMPP, fallback to SQLite if needed
    default_db = "mysql+pymysql://root@localhost/notes_db"
    db_url = os.environ.get("DATABASE_URL", default_db)
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    init_oauth(app)

    def relative_time(dt):
        if dt is None:
            return ""
        if dt.tzinfo is not None:
            now = datetime.now(dt.tzinfo)
        else:
            now = datetime.utcnow()
        delta = now - dt
        seconds = int(delta.total_seconds())
        if seconds < 60:
            return "just now"
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes} minutes ago"
        hours = minutes // 60
        if hours < 24:
            return f"{hours} hours ago"
        days = hours // 24
        if days < 7:
            return f"{days} days ago"
        weeks = days // 7
        if weeks < 4:
            return f"{weeks} weeks ago"
        months = days // 30
        if months < 12:
            return f"{months} months ago"
        years = days // 365
        return f"{years} years ago"

    app.jinja_env.filters["relative_time"] = relative_time

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.context_processor
    def inject_csrf():
        from flask_wtf.csrf import generate_csrf
        return dict(csrf_token=generate_csrf)

    app.register_blueprint(auth_bp)
    app.register_blueprint(notes_bp)
    app.register_blueprint(oauth_bp)

    # Use ProxyFix for Render (handling https correctly)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    with app.app_context():
        db.create_all()
        # Sync sequences on startup if on Render
        if os.environ.get("DATABASE_URL") and "render.com" in os.environ.get("DATABASE_URL", ""):
            try:
                tables = ["user", "note", "o_auth_account", "note_reminder"]
                for table in tables:
                    db.session.execute(text(f"""
                        SELECT setval(
                            pg_get_serial_sequence('"{table}"', 'id'),
                            COALESCE(MAX(id), 1)
                        ) FROM "{table}";
                    """))
                db.session.commit()
            except Exception:
                db.session.rollback()

    def send_mail(to_email, subject, body):
        if not os.environ.get("MAIL_ENABLED"):
            return
        server = os.environ.get("MAIL_SERVER")
        port = int(os.environ.get("MAIL_PORT") or 587)
        username = os.environ.get("MAIL_USERNAME")
        password = os.environ.get("MAIL_PASSWORD")
        sender = os.environ.get("MAIL_SENDER") or username
        if not server or not username or not password or not sender:
            return
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = to_email
        try:
            with smtplib.SMTP(server, port) as smtp:
                smtp.starttls()
                smtp.login(username, password)
                smtp.send_message(msg)
        except Exception:
            pass

    def reminder_worker(app):
        while True:
            try:
                with app.app_context():
                    if datetime.now().tzinfo is not None:
                        now = datetime.now(timezone.utc)
                    else:
                        now = datetime.utcnow()
                    due = NoteReminder.query.filter_by(notified=False).filter(NoteReminder.remind_at <= now).all()
                    for r in due:
                        user = r.user
                        note = r.note
                        email = None
                        if getattr(user, "oauth_accounts", None):
                            for acct in user.oauth_accounts:
                                if acct.email:
                                    email = acct.email
                                    break
                        if email:
                            send_mail(email, "Notes Reminder", f"{note.title}\n\n{note.content}")
                        r.notified = True
                        db.session.commit()
            except Exception:
                pass
            time.sleep(60)

    t = threading.Thread(target=reminder_worker, args=(app,), daemon=True)
    t.start()

    login_manager.login_view = "auth.login"

    return app

# Expose app for Gunicorn
app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5055)
