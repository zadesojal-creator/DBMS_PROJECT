"""
Authentication Blueprint (routes/auth.py)
Provides web views and JSON endpoints for login, logout, and session lifecycle.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from services.auth_service import AuthService
from models.user import User
from repositories.user_repo import UserRepository

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        if current_user.role == "ADMIN":
            return redirect(url_for("admin.overview"))
        elif current_user.role == "BROKER":
            return redirect(url_for("broker.clients"))
        else:
            return redirect(url_for("investor.dashboard"))

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")
        ip_addr = request.remote_addr

        user_dict, error = AuthService.authenticate(identifier, password, ip_addr)
        if error:
            flash(error, "danger")
            return render_template("auth/login.html", identifier=identifier), 401

        # Session rotation & login
        session.clear()
        user_obj = User(user_dict)
        login_user(user_obj, remember=False)

        next_page = request.args.get("next")
        if next_page and next_page.startswith("/"):
            return redirect(next_page)

        if user_obj.role == "ADMIN":
            return redirect(url_for("admin.overview"))
        elif user_obj.role == "BROKER":
            return redirect(url_for("broker.clients"))
        else:
            return redirect(url_for("investor.dashboard"))

    return render_template("auth/login.html")

@auth_bp.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    logout_user()
    session.clear()
    flash("You have been signed out successfully.", "info")
    return redirect(url_for("auth.login"))

# API Endpoints
@auth_bp.route("/api/v1/auth/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}
    identifier = data.get("identifier", "").strip()
    password = data.get("password", "")
    ip_addr = request.remote_addr

    user_dict, error = AuthService.authenticate(identifier, password, ip_addr)
    if error:
        return jsonify({
            "ok": False,
            "error": {"code": "AUTH_FAILED", "message": error}
        }), 401

    session.clear()
    user_obj = User(user_dict)
    login_user(user_obj, remember=False)

    return jsonify({
        "ok": True,
        "data": {
            "id": user_obj.id,
            "username": user_obj.username,
            "email": user_obj.email,
            "full_name": user_obj.full_name,
            "role": user_obj.role,
            "is_demo": user_obj.is_demo,
            "csrf_token": generate_csrf()
        }
    }), 200

@auth_bp.route("/api/v1/auth/logout", methods=["POST"])
@login_required
def api_logout():
    logout_user()
    session.clear()
    return jsonify({"ok": True, "data": {"message": "Logged out successfully"}}), 200

@auth_bp.route("/api/v1/auth/me", methods=["GET"])
def api_me():
    if not current_user.is_authenticated:
        return jsonify({
            "ok": False,
            "error": {"code": "UNAUTHORIZED", "message": "Not authenticated"}
        }), 401

    return jsonify({
        "ok": True,
        "data": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role,
            "is_demo": current_user.is_demo
        }
    }), 200

from flask_wtf.csrf import generate_csrf

@auth_bp.route("/api/v1/auth/session", methods=["GET"])
def api_session():
    csrf_token = generate_csrf()
    if not current_user.is_authenticated:
        return jsonify({
            "ok": True,
            "data": {
                "authenticated": False,
                "user": None,
                "csrf_token": csrf_token
            }
        }), 200

    return jsonify({
        "ok": True,
        "data": {
            "authenticated": True,
            "csrf_token": csrf_token,
            "user": {
                "id": current_user.id,
                "username": current_user.username,
                "email": current_user.email,
                "full_name": current_user.full_name,
                "role": current_user.role,
                "is_demo": current_user.is_demo
            }
        }
    }), 200

