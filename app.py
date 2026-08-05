import json
from datetime import datetime, timedelta
from functools import wraps
from urllib.parse import quote

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy import inspect, text
from werkzeug.security import check_password_hash

from config import Config
from extensions import db
from models import Category, Listing
from seed_data import default_dynamic_fields


DEFAULT_DYNAMIC_FIELDS = default_dynamic_fields()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    with app.app_context():
        db.create_all()
        ensure_database_structure()
        from seed_data import seed_categories

        seed_categories()

    register_error_handlers(app)
    register_routes(app)
    return app


def ensure_database_structure():
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()

    if "listings" in tables:
        listing_columns = {col["name"] for col in inspector.get_columns("listings")}
        if "is_visible" not in listing_columns:
            db.session.execute(text("ALTER TABLE listings ADD COLUMN is_visible BOOLEAN DEFAULT TRUE"))
        if "updated_at" not in listing_columns:
            db.session.execute(text("ALTER TABLE listings ADD COLUMN updated_at DATETIME"))
            db.session.execute(text("UPDATE listings SET updated_at = created_at WHERE updated_at IS NULL"))

    db.session.commit()


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin_login", next=request.path))
        return view_func(*args, **kwargs)

    return wrapper


def is_safe_next_url(next_url):
    return bool(next_url) and next_url.startswith("/") and not next_url.startswith("//")


def is_valid_url(value):
    return not value or value.startswith("http://") or value.startswith("https://")


def normalize_phone(phone):
    if not phone:
        return ""
    digits = "".join(ch for ch in phone if ch.isdigit())
    if phone.startswith("+"):
        return "+" + digits
    return digits


def whatsapp_url(phone):
    normalized = normalize_phone(phone)
    if not normalized:
        return ""
    if normalized.startswith("0"):
        normalized = "966" + normalized[1:]
    if normalized.startswith("+"):
        normalized = normalized[1:]
    return f"https://wa.me/{normalized}"


def social_platform_label(url):
    lowered = (url or "").lower()
    if "tiktok" in lowered:
        return "تيك توك"
    if "instagram" in lowered or "instagr.am" in lowered:
        return "إنستغرام"
    return "رابط الخدمة"


def category_matches(cat, query_text):
    haystack = " ".join([cat.group_name or "", cat.name or "", cat.static_content or ""]).lower()
    return query_text in haystack


def listing_matches(listing, query_text="", location=""):
    if location and listing.get("location") != location:
        return False
    if not query_text:
        return True
    parts = [listing.category.name or "", listing.phone or ""]
    for field in listing.category.get_fields():
        parts.append(str(listing.get(field.get("key"), "")))
    haystack = " ".join(parts).lower()
    return query_text in haystack


def validate_field(field, value):
    label = field.get("label", field.get("key", "الحقل"))
    if field.get("required") and not value:
        return f'الحقل "{label}" مطلوب.'

    if not value:
        return None

    if field.get("type") == "url" and not is_valid_url(value):
        return f'الحقل "{label}" يجب أن يحتوي على رابط يبدأ بـ http:// أو https://'

    if field.get("type") == "tel":
        digits = "".join(ch for ch in value if ch.isdigit())
        if len(digits) < 8:
            return f'الحقل "{label}" لا يبدو رقم جوال صحيحًا.'

    options = field.get("options") or []
    if options and value not in options:
        return f'الحقل "{label}" يحتوي على قيمة غير مسموح بها.'

    maxlength = field.get("maxlength")
    if maxlength and len(value) > int(maxlength):
        return f'الحقل "{label}" يجب ألا يتجاوز {maxlength} حرفًا.'

    return None


def collect_listing_data(category, form, prefix):
    entry_data = {}
    errors = []
    for field in category.get_fields():
        key = field["key"]
        raw_value = form.get(f"{prefix}{key}", "")
        value = raw_value.strip()
        error = validate_field(field, value)
        if error:
            errors.append(error)
        entry_data[key] = value
    return entry_data, errors


def pretty_schema_text(category):
    return json.dumps(category.get_fields() or DEFAULT_DYNAMIC_FIELDS, ensure_ascii=False, indent=2)


def parse_field_schema(field_schema_text, use_default_fields=False):
    if use_default_fields or not field_schema_text.strip():
        return default_dynamic_fields(), []

    try:
        data = json.loads(field_schema_text)
    except json.JSONDecodeError:
        return None, ["تعريف الحقول يجب أن يكون بصيغة JSON صحيحة."]

    if not isinstance(data, list) or not data:
        return None, ["تعريف الحقول يجب أن يكون قائمة JSON غير فارغة."]

    cleaned = []
    errors = []
    allowed_types = {"text", "tel", "textarea", "url", "select"}

    for idx, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            errors.append(f"العنصر رقم {idx} في تعريف الحقول غير صحيح.")
            continue
        key = (item.get("key") or "").strip()
        label = (item.get("label") or "").strip()
        field_type = (item.get("type") or "text").strip()
        if not key or not label:
            errors.append(f"العنصر رقم {idx} يحتاج key و label.")
            continue
        if field_type not in allowed_types:
            errors.append(f"نوع الحقل في العنصر رقم {idx} غير مدعوم.")
            continue
        cleaned_item = {
            "key": key,
            "label": label,
            "type": field_type,
            "required": bool(item.get("required", False)),
        }
        if item.get("maxlength"):
            cleaned_item["maxlength"] = int(item["maxlength"])
        if field_type == "select":
            options = item.get("options") or []
            if not options:
                errors.append(f"الحقل {label} من نوع select ويحتاج options.")
                continue
            cleaned_item["options"] = options
        cleaned.append(cleaned_item)

    if errors:
        return None, errors
    return cleaned, []


def build_public_items(query_text="", location="", category_id=None, include_empty=True):
    categories = Category.query.filter_by(is_active=True).order_by(Category.display_order.asc()).all()
    items = []
    query_text = (query_text or "").strip().lower()

    for cat in categories:
        if category_id and cat.id != category_id:
            continue

        if cat.kind == "static":
            if query_text and not category_matches(cat, query_text):
                continue
            items.append({"category": cat, "listings": []})
            continue

        listings = (
            cat.listings.filter_by(is_visible=True)
            .order_by(Listing.updated_at.desc(), Listing.created_at.desc())
            .all()
        )
        listings = [listing for listing in listings if listing_matches(listing, query_text, location)]
        if include_empty or listings:
            items.append({"category": cat, "listings": listings})

    return items


def filter_admin_listings(query, query_text="", category_id=None, location="", visibility="all"):
    listings = query.order_by(Listing.updated_at.desc(), Listing.created_at.desc()).all()
    filtered = []
    query_text = (query_text or "").strip().lower()

    for listing in listings:
        if category_id and listing.category_id != category_id:
            continue
        if visibility == "visible" and not listing.is_visible:
            continue
        if visibility == "hidden" and listing.is_visible:
            continue
        if not listing_matches(listing, query_text, location):
            continue
        filtered.append(listing)

    return filtered


def check_admin_password(app, password):
    password_hash = app.config.get("ADMIN_PASSWORD_HASH", "")
    if password_hash:
        return check_password_hash(password_hash, password)
    return password == app.config["ADMIN_PASSWORD"]


def admin_is_locked(app):
    locked_until = session.get("admin_locked_until")
    if not locked_until:
        return False, None
    locked_until_dt = datetime.fromisoformat(locked_until)
    if datetime.utcnow() >= locked_until_dt:
        session.pop("admin_locked_until", None)
        session.pop("admin_login_attempts", None)
        return False, None
    return True, locked_until_dt


def register_routes(app):
    @app.context_processor
    def inject_now():
        return {"current_year": datetime.utcnow().year}

    @app.route("/")
    def index():
        query_text = request.args.get("q", "").strip()
        location = request.args.get("location", "").strip()
        category_id = request.args.get("category_id", type=int)
        items = build_public_items(query_text, location, category_id, include_empty=True)
        categories = Category.query.filter_by(is_active=True).order_by(Category.display_order.asc()).all()
        return render_template(
            "index.html",
            items=items,
            categories=categories,
            selected_category=category_id,
            selected_location=location,
            search_query=query_text,
            now=datetime.utcnow(),
        )

    @app.route("/ai")
    def ai_page():
        items = build_public_items(include_empty=True)
        return render_template("ai.html", items=items, now=datetime.utcnow())

    @app.route("/health")
    def health():
        return {"status": "ok", "time": datetime.utcnow().isoformat()}

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

            if not category or category.kind != "dynamic" or not category.is_active:
                flash("يرجى اختيار نوع الخدمة بشكل صحيح.", "error")
                return redirect(url_for("submit"))

            entry_data, errors = collect_listing_data(category, request.form, f"field_{category_id}_")
            if errors:
                for error in errors:
                    flash(error, "error")
                return redirect(url_for("submit"))

            listing = Listing(
                category_id=category.id,
                data=entry_data,
                phone=entry_data.get("phone", "").strip(),
                is_visible=True,
            )
            db.session.add(listing)
            db.session.commit()
            return redirect(url_for("submit_success"))

        return render_template("submit.html", categories=dynamic_categories)

    @app.route("/submit/success")
    def submit_success():
        return render_template("submit_success.html")

    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        locked, locked_until = admin_is_locked(app)
        if request.method == "POST":
            if locked:
                minutes = max(1, int((locked_until - datetime.utcnow()).total_seconds() // 60))
                flash(f"تم إيقاف المحاولات مؤقتًا. حاول بعد {minutes} دقيقة.", "error")
                return render_template("admin/login.html", locked_until=locked_until)

            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            if username == app.config["ADMIN_USERNAME"] and check_admin_password(app, password):
                session.clear()
                session.permanent = True
                session["is_admin"] = True
                session["admin_logged_in_at"] = datetime.utcnow().isoformat()
                next_url = request.args.get("next")
                return redirect(next_url if is_safe_next_url(next_url) else url_for("admin_dashboard"))

            attempts = session.get("admin_login_attempts", 0) + 1
            session["admin_login_attempts"] = attempts
            if attempts >= app.config["ADMIN_LOGIN_MAX_ATTEMPTS"]:
                lock_minutes = app.config["ADMIN_LOGIN_LOCK_MINUTES"]
                session["admin_locked_until"] = (datetime.utcnow() + timedelta(minutes=lock_minutes)).isoformat()
                flash(f"تم إيقاف المحاولات لمدة {lock_minutes} دقيقة بسبب تكرار كلمة المرور الخاطئة.", "error")
            else:
                remaining = app.config["ADMIN_LOGIN_MAX_ATTEMPTS"] - attempts
                flash(f"اسم المستخدم أو كلمة المرور غير صحيحة. المحاولات المتبقية: {remaining}", "error")

        return render_template("admin/login.html", locked_until=locked_until)

    @app.route("/admin/logout")
    def admin_logout():
        session.clear()
        return redirect(url_for("admin_login"))

    @app.route("/admin")
    @admin_required
    def admin_dashboard():
        categories = Category.query.all()
        listings = Listing.query.all()
        return render_template(
            "admin/dashboard.html",
            categories_count=len(categories),
            dynamic_categories_count=len([c for c in categories if c.kind == "dynamic"]),
            static_categories_count=len([c for c in categories if c.kind == "static"]),
            listings_count=len(listings),
            visible_listings_count=len([l for l in listings if l.is_visible]),
            hidden_listings_count=len([l for l in listings if not l.is_visible]),
        )

    @app.route("/admin/listings")
    @admin_required
    def admin_listings():
        category_id = request.args.get("category_id", type=int)
        query_text = request.args.get("q", "").strip()
        location = request.args.get("location", "").strip()
        visibility = request.args.get("visibility", "all").strip()

        listings = filter_admin_listings(
            Listing.query.join(Category),
            query_text=query_text,
            category_id=category_id,
            location=location,
            visibility=visibility,
        )
        categories = Category.query.order_by(Category.display_order.asc()).all()
        return render_template(
            "admin/listings.html",
            listings=listings,
            categories=categories,
            selected_category=category_id,
            selected_location=location,
            selected_visibility=visibility,
            search_query=query_text,
        )

    @app.route("/admin/listings/<int:listing_id>/edit", methods=["GET", "POST"])
    @admin_required
    def admin_edit_listing(listing_id):
        listing = Listing.query.get_or_404(listing_id)
        category = listing.category
        if request.method == "POST":
            entry_data, errors = collect_listing_data(category, request.form, "field_")
            if errors:
                for error in errors:
                    flash(error, "error")
            else:
                listing.data = entry_data
                listing.phone = entry_data.get("phone", "").strip()
                listing.is_visible = request.form.get("is_visible") == "1"
                listing.updated_at = datetime.utcnow()
                db.session.commit()
                flash("تم تعديل بيانات مقدم الخدمة بنجاح.", "success")
                return redirect(url_for("admin_listings"))

        return render_template("admin/listing_form.html", listing=listing, category=category)

    @app.route("/admin/listings/<int:listing_id>/toggle", methods=["POST"])
    @admin_required
    def admin_toggle_listing(listing_id):
        listing = Listing.query.get_or_404(listing_id)
        listing.is_visible = not listing.is_visible
        listing.updated_at = datetime.utcnow()
        db.session.commit()
        flash("تم تحديث حالة الإدخال.", "success")
        return redirect(url_for("admin_listings"))

    @app.route("/admin/listings/<int:listing_id>/delete", methods=["POST"])
    @admin_required
    def admin_delete_listing(listing_id):
        listing = Listing.query.get_or_404(listing_id)
        db.session.delete(listing)
        db.session.commit()
        flash("تم حذف الإدخال بنجاح.", "success")
        return redirect(url_for("admin_listings"))

    @app.route("/admin/categories")
    @admin_required
    def admin_categories():
        categories = Category.query.order_by(Category.display_order.asc()).all()
        return render_template("admin/categories.html", categories=categories)

    @app.route("/admin/categories/new", methods=["GET", "POST"])
    @admin_required
    def admin_new_category():
        category = Category(kind="dynamic", is_active=True, field_schema=default_dynamic_fields())
        if request.method == "POST":
            return save_category_form(category, is_new=True)
        return render_template(
            "admin/category_form.html",
            category=category,
            schema_text=pretty_schema_text(category),
            is_new=True,
        )

    @app.route("/admin/categories/<int:category_id>/edit", methods=["GET", "POST"])
    @admin_required
    def admin_edit_category(category_id):
        category = Category.query.get_or_404(category_id)
        if request.method == "POST":
            return save_category_form(category, is_new=False)
        return render_template(
            "admin/category_form.html",
            category=category,
            schema_text=pretty_schema_text(category),
            is_new=False,
        )

    def save_category_form(category, is_new=False):
        group_name = request.form.get("group_name", "").strip()
        name = request.form.get("name", "").strip()
        icon = request.form.get("icon", "").strip()
        kind = request.form.get("kind", "dynamic").strip()
        display_order = request.form.get("display_order", type=int) or 0
        is_active = request.form.get("is_active") == "1"
        static_content = request.form.get("static_content", "").strip()
        field_schema_text = request.form.get("field_schema_text", "")
        use_default_fields = request.form.get("use_default_fields") == "1"

        errors = []
        if not name:
            errors.append("اسم الفئة مطلوب.")
        existing = Category.query.filter(Category.name == name, Category.id != category.id).first() if category.id else Category.query.filter_by(name=name).first()
        if existing:
            errors.append("يوجد فئة أخرى بنفس الاسم.")

        field_schema = None
        if kind == "dynamic":
            field_schema, schema_errors = parse_field_schema(field_schema_text, use_default_fields=use_default_fields)
            errors.extend(schema_errors)
        else:
            field_schema = None

        if errors:
            for error in errors:
                flash(error, "error")
            category.group_name = group_name
            category.name = name
            category.icon = icon
            category.kind = kind
            category.display_order = display_order
            category.is_active = is_active
            category.static_content = static_content
            category.field_schema = field_schema if field_schema is not None else category.field_schema
            return render_template(
                "admin/category_form.html",
                category=category,
                schema_text=field_schema_text or pretty_schema_text(category),
                is_new=is_new,
            )

        category.group_name = group_name
        category.name = name
        category.icon = icon
        category.kind = kind
        category.display_order = display_order
        category.is_active = is_active
        category.static_content = static_content if kind == "static" else ""
        category.field_schema = field_schema if kind == "dynamic" else None

        if is_new:
            db.session.add(category)
        db.session.commit()
        flash("تم حفظ الفئة بنجاح.", "success")
        return redirect(url_for("admin_categories"))

    @app.route("/admin/categories/<int:category_id>/toggle", methods=["POST"])
    @admin_required
    def admin_toggle_category(category_id):
        category = Category.query.get_or_404(category_id)
        category.is_active = not category.is_active
        db.session.commit()
        flash("تم تحديث حالة الفئة.", "success")
        return redirect(url_for("admin_categories"))

    @app.route("/admin/categories/<int:category_id>/delete", methods=["POST"])
    @admin_required
    def admin_delete_category(category_id):
        category = Category.query.get_or_404(category_id)
        db.session.delete(category)
        db.session.commit()
        flash("تم حذف الفئة وما يتبعها من إدخالات.", "success")
        return redirect(url_for("admin_categories"))

    @app.route("/admin/static/<int:category_id>/edit", methods=["GET", "POST"])
    @admin_required
    def admin_edit_static(category_id):
        return redirect(url_for("admin_edit_category", category_id=category_id))


def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(_error):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_error(_error):
        db.session.rollback()
        return render_template("500.html"), 500


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
