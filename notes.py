from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from models import db, Note
from scraper import scrape
from sqlalchemy import or_
from models import NoteReminder
from datetime import datetime

notes_bp = Blueprint("notes", __name__)


@notes_bp.route("/")
@login_required
def index():
    q = request.args.get("q", "").strip()
    base = Note.query.filter_by(user_id=current_user.id)
    if q:
        pattern = f"%{q}%"
        base = base.filter(or_(Note.title.ilike(pattern), Note.content.ilike(pattern)))
    notes = base.order_by(Note.updated_at.desc()).all()
    return render_template("notes.html", notes=notes, q=q)


@notes_bp.route("/notes/create", methods=["POST"])
@login_required
def create_note():
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    priority = request.form.get("priority", "").strip()
    tags = request.form.get("tags", "").strip()
    remind_raw = request.form.get("remind_at", "").strip()
    if not title or not content:
        return redirect(url_for("notes.index"))
    meta_prefix = []
    if priority:
        meta_prefix.append(f"Priority: {priority}")
    if tags:
        meta_prefix.append(f"Tags: {tags}")
    if meta_prefix:
        content = "[" + " | ".join(meta_prefix) + "]\n\n" + content
    note = Note(user_id=current_user.id, title=title, content=content)
    db.session.add(note)
    db.session.commit()
    if remind_raw:
        try:
            remind_at = datetime.strptime(remind_raw, "%Y-%m-%dT%H:%M")
            r = NoteReminder(note_id=note.id, user_id=current_user.id, remind_at=remind_at)
            db.session.add(r)
            db.session.commit()
        except Exception:
            pass
    return redirect(url_for("notes.index"))


@notes_bp.route("/notes/<int:note_id>/edit", methods=["GET", "POST"])
@login_required
def edit_note(note_id: int):
    note = Note.query.filter_by(id=note_id, user_id=current_user.id).first_or_404()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        remind_raw = request.form.get("remind_at", "").strip()
        if title and content:
            note.title = title
            note.content = content
            db.session.commit()
        if remind_raw:
            try:
                remind_at = datetime.strptime(remind_raw, "%Y-%m-%dT%H:%M")
                existing = NoteReminder.query.filter_by(note_id=note.id, user_id=current_user.id, notified=False).first()
                if existing:
                    existing.remind_at = remind_at
                else:
                    r = NoteReminder(note_id=note.id, user_id=current_user.id, remind_at=remind_at)
                    db.session.add(r)
                db.session.commit()
            except Exception:
                pass
        return redirect(url_for("notes.index"))
    return render_template("edit_note.html", note=note)


@notes_bp.route("/notes/<int:note_id>/delete", methods=["POST"])
@login_required
def delete_note(note_id: int):
    note = Note.query.filter_by(id=note_id, user_id=current_user.id).first_or_404()
    db.session.delete(note)
    db.session.commit()
    return redirect(url_for("notes.index"))


@notes_bp.route("/scrape", methods=["GET", "POST"])
@login_required
def scrape_view():
    results = None
    url = None
    error = None
    include_titles = True
    include_prices = True
    limit = 50
    if request.method == "POST":
        url = request.form.get("url", "").strip()
        include_titles = request.form.get("include_titles") == "on"
        include_prices = request.form.get("include_prices") == "on"
        try:
            limit = int(request.form.get("limit") or 50)
        except ValueError:
            limit = 50
        if url:
            try:
                results = scrape(url, include_titles=include_titles, include_prices=include_prices, limit=limit)
                if not results:
                    error = "No titles or prices found on this page. Try another URL."
            except Exception as e:
                error = f"Error: {str(e)}"
        else:
            error = "Please provide a valid URL."
    return render_template("scrape.html", results=results, source_url=url, error=error, include_titles=include_titles, include_prices=include_prices, limit=limit)


@notes_bp.route("/scrape/save", methods=["POST"])
@login_required
def save_scraped():
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    if title and content:
        note = Note(user_id=current_user.id, title=title, content=content)
        db.session.add(note)
        db.session.commit()
    return redirect(url_for("notes.index"))


@notes_bp.route("/notes/<int:note_id>/remind", methods=["POST"])
@login_required
def set_reminder(note_id: int):
    note = Note.query.filter_by(id=note_id, user_id=current_user.id).first_or_404()
    raw = request.form.get("remind_at", "").strip()
    if raw:
        try:
            remind_at = datetime.strptime(raw, "%Y-%m-%dT%H:%M")
            existing = NoteReminder.query.filter_by(note_id=note.id, user_id=current_user.id, notified=False).first()
            if existing:
                existing.remind_at = remind_at
            else:
                r = NoteReminder(note_id=note.id, user_id=current_user.id, remind_at=remind_at)
                db.session.add(r)
            db.session.commit()
        except Exception:
            pass
    return redirect(url_for("notes.index"))


@notes_bp.route("/notes/<int:note_id>/remind/cancel", methods=["POST"])
@login_required
def cancel_reminder(note_id: int):
    note = Note.query.filter_by(id=note_id, user_id=current_user.id).first_or_404()
    existing = NoteReminder.query.filter_by(note_id=note.id, user_id=current_user.id, notified=False).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
    return redirect(url_for("notes.index"))
