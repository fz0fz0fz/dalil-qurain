import os
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, abort
)

from config import Config
from extensions import db
from models import Category, Listing


 def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    with app.app_context():
        db.create_all()
        from seed_data import seed_categories
        seed_categories()

    register_routes(app)
    return app



def admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin_login", next=request.path))
        return view_func(*args, **kwargs)
    return wrapper


def register_routes(app):

    # ---------------- الصفحة العامة الرئيسية (هذه هي الصفحة التي يقرأها الذكاء الاصطناعي) ----------------
    @app.route("/")
    def index():
        categories = (
            Category.query.filter_by(is_active=True)
            .order_by(Category.display_order.asc())
            .all()
        )
        items = []
        for cat in categories:
            listings = []
            if cat.kind == "dynamic":
                listings = cat.listings.order_by(Listing.created_at.desc()).all()
            items.append({"category": cat, "listings": listings})
        return render_template("index.html", items=items, now=datetime.utcnow())

    # ---------------- صفحة إدخال البيانات العامة ----------------
    @app.route("/submit", methods=["GET", "POST"])
    def submit():
        dynamic_categories = (
            Category.query.filter_by(kind="dynamic", is_active=True)
            .order_by(Category.display_order.asc())
            .all()
        )

        if request.method == "POST":
            category_id = request.form.get("category_id", type=int)
            category = Category.query.get(category_id)

            if not category or category.kind != "dynamic":
                flash("يرجى اختيار نوع الخدمة بشكل صحيح.", "error")
                return redirect(url_for("submit"))

            schema = category.get_fields()
            entry_data = {}
            errors = []

            for field in schema:
                key = field["key"]
                raw_value = request.form.get(f"field_{category_id}_{key}", "")
                value = raw_value.strip()
                if field.get("required") and not value:
                    errors.append(f'الحقل "{field["label"]}" مطلوب.')
                entry_data[key] = value

            if errors:
                for e in errors:
                    flash(e, "error")
                return redirect(url_for("submit"))

            listing = Listing(
                category_id=category.id,
                data=entry_data,
                phone=entry_data.get("phone", "").strip(),
            )
            db.session.add(listing)
            db.session.commit()
            return redirect(url_for("submit_success"))

        return render_template("submit.html", categories=dynamic_categories)

    @app.route("/submit/success")
    def submit_success():
        return render_template("submit_success.html")

    # ---------------- تسجيل دخول الإدمن ----------------
    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        if request.method == "POST":
            username = request.form.get("username", "")
            password = request.form.get("password", "")
            if (
                username == app.config["ADMIN_USERNAME"]
                and password == app.config["ADMIN_PASSWORD"]
            ):
                session["is_admin"] = True
                next_url = request.args.get("next") or url_for("admin_dashboard")
                return redirect(next_url)
            flash("اسم المستخدم أو كلمة المرور غير صحيحة.", "error")
        return render_template("admin/login.html")

    @app.route("/admin/logout")
    def admin_logout():
        session.pop("is_admin", None)
        return redirect(url_for("admin_login"))

    # ---------------- لوحة تحكم الإدمن ----------------
    @app.route("/admin")
    @admin_required
    def admin_dashboard():
        categories_count = Category.query.count()
        listings_count = Listing.query.count()
        return render_template(
            "admin/dashboard.html",
            categories_count=categories_count,
            listings_count=listings_count,
        )

    @app.route("/admin/listings")
    @admin_required
    def admin_listings():
        category_id = request.args.get("category_id", type=int)
        query = Listing.query
        if category_id:
            query = query.filter_by(category_id=category_id)
        listings = query.order_by(Listing.created_at.desc()).all()
        categories = (
            Category.query.filter_by(kind="dynamic")
            .order_by(Category.display_order.asc())
            .all()
        )
        return render_template(
            "admin/listings.html",
            listings=listings,
            categories=categories,
            selected_category=category_id,
        )

    @app.route("/admin/listings/<int:listing_id>/delete", methods=["POST"])
    @admin_required
    def admin_delete_listing(listing_id):
        listing = Listing.query.get_or_404(listing_id)
        db.session.delete(listing)
        db.session.commit()
        flash("تم حذف الإدخال بنجاح.", "success")
        return redirect(url_for("admin_listings"))

    # ---------------- إدارة الفئات ----------------
    @app.route("/admin/categories")
    @admin_required
    def admin_categories():
        categories = Category.query.order_by(Category.display_order.asc()).all()
        return render_template("admin/categories.html", categories=categories)

    @app.route("/admin/categories/<int:category_id>/toggle", methods=["POST"])
    @admin_required
    def admin_toggle_category(category_id):
        category = Category.query.get_or_404(category_id)
        category.is_active = not category.is_active
        db.session.commit()
        return redirect(url_for("admin_categories"))

    @app.route("/admin/static/<int:category_id>/edit", methods=["GET", "POST"])
    @admin_required
    def admin_edit_static(category_id):
        category = Category.query.get_or_404(category_id)
        if category.kind != "static":
            abort(404)
        if request.method == "POST":
            category.static_content = request.form.get("static_content", "")
            db.session.commit()
            flash("تم تحديث المحتوى بنجاح.", "success")
            return redirect(url_for("admin_categories"))
        return render_template("admin/static_edit.html", category=category)


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
