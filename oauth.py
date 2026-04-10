import os
import secrets
from flask import Blueprint, redirect, url_for, request
from flask import current_app, session
from flask_login import login_user
from authlib.integrations.flask_client import OAuth
from models import db, User, OAuthAccount

oauth_bp = Blueprint("oauth", __name__)
oauth = OAuth()


def init_oauth(app):
    oauth.init_app(app)
    oauth.register(
        name="google",
        client_id=os.environ.get("GOOGLE_CLIENT_ID"),
        client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    oauth.register(
        name="github",
        client_id=os.environ.get("GITHUB_CLIENT_ID"),
        client_secret=os.environ.get("GITHUB_CLIENT_SECRET"),
        access_token_url="https://github.com/login/oauth/access_token",
        authorize_url="https://github.com/login/oauth/authorize",
        api_base_url="https://api.github.com/",
        client_kwargs={"scope": "read:user user:email"},
    )


@oauth_bp.route("/oauth/login/<provider>")
def oauth_login(provider):
    client = oauth.create_client(provider)
    if not client:
        return redirect(url_for("auth.login"))
    redirect_uri = url_for("oauth.oauth_callback", provider=provider, _external=True)
    return client.authorize_redirect(redirect_uri)


def _find_or_create_user(provider, sub, email, display_name):
    acct = OAuthAccount.query.filter_by(provider=provider, sub=sub).first()
    if acct:
        return acct.user
    username_base = (email or display_name or f"{provider}_{sub}").split("@")[0]
    candidate = username_base
    i = 1
    while User.query.filter_by(username=candidate).first():
        i += 1
        candidate = f"{username_base}{i}"
    user = User(username=candidate)
    user.set_password(secrets.token_urlsafe(16))
    db.session.add(user)
    db.session.flush()
    acct = OAuthAccount(user_id=user.id, provider=provider, sub=sub, email=email)
    db.session.add(acct)
    db.session.commit()
    return user


@oauth_bp.route("/oauth/callback/<provider>")
def oauth_callback(provider):
    try:
        client = oauth.create_client(provider)
        if not client:
            return redirect(url_for("auth.login"))
        token = client.authorize_access_token()
        if provider == "google":
            userinfo = token.get("userinfo")
            if not userinfo:
                userinfo = client.get("userinfo").json()
            sub = str(userinfo.get("sub") or "")
            email = userinfo.get("email")
            name = userinfo.get("name") or email or sub
            user = _find_or_create_user("google", sub, email, name)
            login_user(user)
            return redirect(url_for("notes.index"))
        if provider == "github":
            me = client.get("user").json()
            emails = client.get("user/emails").json()
            primary_email = None
            for e in emails or []:
                if e.get("primary") and e.get("verified"):
                    primary_email = e.get("email")
                    break
            sub = str(me.get("id") or "")
            name = me.get("login") or primary_email or sub
            user = _find_or_create_user("github", sub, primary_email, name)
            login_user(user)
            return redirect(url_for("notes.index"))
    except Exception as e:
        current_app.logger.error(f"OAuth Callback Error ({provider}): {str(e)}")
        # If there's an error, we should rollback any partial database session
        db.session.rollback()
        return f"Authentication failed: {str(e)}", 500
    return redirect(url_for("auth.login"))

