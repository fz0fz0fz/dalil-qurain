import json
import re
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Flask,
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
PHONE_RE = re.compile(r"(?:\+?966|0)?\d[\d\s\-]{7,}")
URL_RE = re.compile(r"https?://\S+")


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
            db.session.execute(
                text("ALTER TABLE listings ADD COLUMN is_visible BOOLEAN DEFAULT TRUE")
            )
        if "updated_at" not in listing_columns:
            db.session.execute(
                text("ALTER TABLE listings ADD COLUMN updated_at DATETIME")
            )
            db.session.execute(
                text("UPDATE listings SET updated_at = created_at WHERE updated_at IS NULL")
            )

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


def category_matches(cat, query_text):
    haystack = " ".join(
        [cat.group_name or "", cat.name or "", cat.static_content or ""]
    ).lower()
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
    try:
        fields = category.get_fields()

        if not isinstance(fields, list) or not fields:
            fields = DEFAULT_DYNAMIC_FIELDS

        cleaned = []
        allowed_types = {"text", "tel", "textarea", "url", "select"}

        for field in fields:
            if not isinstance(field, dict):
                continue

            key = str(field.get("key", "")).strip()
            label = str(field.get("label", "")).strip()
            field_type = str(field.get("type", "text")).strip() or "text"

            if not key or not label:
                continue

            if field_type not in allowed_types:
                field_type = "text"

            item = {
                "key": key,
                "label": label,
                "type": field_type,
                "required": bool(field.get("required", False)),
            }

            if field.get("maxlength"):
                try:
                    item["maxlength"] = int(field["maxlength"])
                except Exception:
                    pass

            if field_type == "select":
                options = field.get("options") or []
                if isinstance(options, list) and options:
                    item["options"] = options

            cleaned.append(item)

        if not cleaned:
            cleaned = DEFAULT_DYNAMIC_FIELDS

        return json.dumps(cleaned, ensure_ascii=False, indent=2)

    except Exception:
        return json.dumps(DEFAULT_DYNAMIC_FIELDS, ensure_ascii=False, indent=2)


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
            try:
                cleaned_item["maxlength"] = int(item["maxlength"])
            except Exception:
                errors.append(f"قيمة maxlength في العنصر رقم {idx} غير صحيحة.")
                continue

        if field_type == "select":
            options = item.get("options") or []
            if not options or not isinstance(options, list):
                errors.append(f"الحقل {label} من نوع select ويحتاج options.")
                continue
            cleaned_item["options"] = options

        cleaned.append(cleaned_item)

    if errors:
        return None, errors

    return cleaned, []


def clean_import_line(value):
    value = (value or "").strip()
    value = re.sub(r"^[^\w\u0600-\u06FF\d\+]+", "", value, flags=re.UNICODE).strip()
    return value


def parse_bulk_listings_text(raw_text):
    text = (raw_text or "").replace("\r", "")
    chunks = [chunk.strip() for chunk in re.split(r"\n\s*\n+", text) if chunk.strip()]
    entries = []

    for chunk in chunks:
        lines = [line.strip() for line in chunk.split("\n") if line.strip()]
        if not lines:
            continue

        first_non_noise = None
        phone = ""
        location = ""
        maps_url = ""
        social_url = ""
        price = ""
        working_hours = ""
        description_parts = []

        for line in lines:
            if set(line) <= set("━-—_*"):
                continue
            if "قائمة" in line or line.startswith("آخر تحديث") or line.startswith("🔄"):
                continue

            urls = URL_RE.findall(line)
            if urls:
                for url in urls:
                    lowered = url.lower()
                    if any(
                        host in lowered
                        for host in ["maps.app", "google.com/maps", "goo.gl/maps"]
                    ):
                        maps_url = maps_url or url
                    elif any(
                        host in lowered
                        for host in ["instagram", "instagr.am", "tiktok"]
                    ):
                        social_url = social_url or url
                if line == urls[0]:
                    continue

            phone_match = PHONE_RE.search(line.replace("📞", " "))
            if phone_match:
                phone = phone or phone_match.group(0).strip()
                continue

            if "القرين" in line and not location:
                location = "القرين"
            elif "الدليمية" in line and not location:
                location = "الدليمية"

            if any(token in line for token in ["🕒", "الدوام", "ساعات", "24 ساعة", "الجمعة"]):
                working_hours = (
                    (working_hours + "\n" + line).strip() if working_hours else line
                )
                continue

            if any(token in line for token in ["💵", "السعر", "الأسعار"]):
                price = clean_import_line(line)
                continue

            cleaned = clean_import_line(line)
            if not cleaned:
                continue

            if not first_non_noise:
                first_non_noise = cleaned
            else:
                description_parts.append(cleaned)

        if not first_non_noise or not phone:
            continue

        entries.append(
            {
                "name": first_non_noise,
                "phone": phone,
                "service_description": "\n".join(description_parts)[:200],
                "location": location,
                "maps_url": maps_url,
                "price": price,
                "working_hours": working_hours,
                "social_url": social_url,
            }
        )

    return entries


def upsert_listing_for_category(category, entry_data):
    normalized_phone = normalize_phone(entry_data.get("phone", "").strip())
    existing_listing = None

    if normalized_phone:
        existing_listing = (
            Listing.query.filter_by(category_id=category.id)
            .filter(Listing.phone.in_([entry_data.get("phone", "").strip(), normalized_phone]))
            .first()
        )

    if existing_listing:
        existing_listing.data = entry_data
        existing_listing.phone = entry_data.get("phone", "").strip()
        existing_listing.is_visible = True
        existing_listing.updated_at = datetime.utcnow()
        return existing_listing, "updated"

    listing = Listing(
        category_id=category.id,
        data=entry_data,
        phone=entry_data.get("phone", "").strip(),
        is_visible=True,
    )
    db.session.add(listing)
    return listing, "created"


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

        if include_empty or listings or (cat.static_content and cat.static_content.strip()):
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

            _listing, action = upsert_listing_for_category(category, entry_data)
            db.session.commit()
            return redirect(url_for("submit_success", action=action))

        return render_template("submit.html", categories=dynamic_categories)

    @app.route("/submit/success")
    def submit_success():
        action = request.args.get("action", "created")
        return render_template("submit_success.html", action=action)

    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        locked, locked_until = admin_is_locked(app)
        max_attempts = app.config.get("ADMIN_LOGIN_MAX_ATTEMPTS", 5)
        lock_minutes = app.config.get("ADMIN_LOGIN_LOCK_MINUTES", 15)

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

            if attempts >= max_attempts:
                session["admin_locked_until"] = (
                    datetime.utcnow() + timedelta(minutes=lock_minutes)
                ).isoformat()
                flash(
                    f"تم إيقاف المحاولات لمدة {lock_minutes} دقيقة بسبب تكرار كلمة المرور الخاطئة.",
                    "error",
                )
            else:
                remaining = max_attempts - attempts
                flash(
                    f"اسم المستخدم أو كلمة المرور غير صحيحة. المحاولات المتبقية: {remaining}",
                    "error",
                )

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
        category = Category()
        category.kind = "dynamic"
        category.is_active = True
        category.group_name = ""
        category.name = ""
        category.icon = ""
        category.display_order = 0
        category.field_schema = default_dynamic_fields()
        category.static_content = ""

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

    @app.route("/admin/categories/<int:category_id>/bulk-import", methods=["GET", "POST"])
    @admin_required
    def admin_bulk_import_category(category_id):
        category = Category.query.get_or_404(category_id)

        if request.method == "POST":
            raw_text = request.form.get("bulk_text", "")
            fallback_location = request.form.get("fallback_location", "").strip()
            import_mode = request.form.get("import_mode", "raw").strip()

            if import_mode == "raw":
                category.static_content = raw_text.strip()
                db.session.commit()
                flash("تم حفظ النص كما هو داخل الفئة بنجاح.", "success")
                return redirect(url_for("admin_categories"))

            entries = parse_bulk_listings_text(raw_text)
            if not entries:
                flash(
                    "لم يتم التعرف على أي إدخالات قابلة للاستيراد. تأكد من وجود اسم ورقم جوال لكل عنصر.",
                    "error",
                )
                return render_template(
                    "admin/bulk_import.html",
                    category=category,
                    bulk_text=raw_text,
                )

            created_count = 0
            updated_count = 0
            skipped = []

            for entry in entries:
                if fallback_location and not entry.get("location"):
                    entry["location"] = fallback_location

                normalized_entry = {}
                errors = []

                for field in category.get_fields():
                    key = field["key"]
                    value = (entry.get(key, "") or "").strip()
                    error = validate_field(field, value)
                    if error:
                        errors.append(error)
                    normalized_entry[key] = value

                if errors:
                    skipped.append(f"{entry.get('name', 'بدون اسم')}: {' | '.join(errors)}")
                    continue

                _listing, action = upsert_listing_for_category(category, normalized_entry)
                if action == "created":
                    created_count += 1
                else:
                    updated_count += 1

            db.session.commit()

            if created_count or updated_count:
                flash(
                    f"تم الاستيراد كإدخالات بنجاح. جديد: {created_count} | محدث: {updated_count}",
                    "success",
                )

            if skipped:
                flash("بعض الأسطر لم تُستورد: " + " || ".join(skipped[:5]), "error")

            return redirect(url_for("admin_categories"))

        return render_template(
            "admin/bulk_import.html",
            category=category,
            bulk_text=category.static_content or "",
        )

    def save_category_form(category, is_new=False):
        group_name = request.form.get("group_name", "").strip()
        name = request.form.get("name", "").strip()
        icon = request.form.get("icon", "").strip()
        kind = "dynamic"
        display_order = request.form.get("display_order", type=int) or 0
        is_active = request.form.get("is_active") == "1"
        field_schema_text = request.form.get("field_schema_text", "")
        use_default_fields = request.form.get("use_default_fields") == "1"

        errors = []

        if not name:
            errors.append("اسم الفئة مطلوب.")

        existing = (
            Category.query.filter(Category.name == name, Category.id != category.id).first()
            if category.id
            else Category.query.filter_by(name=name).first()
        )
        if existing:
            errors.append("يوجد فئة أخرى بنفس الاسم.")

        field_schema, schema_errors = parse_field_schema(
            field_schema_text,
            use_default_fields=use_default_fields,
        )
        errors.extend(schema_errors)

        if errors:
            for error in errors:
                flash(error, "error")

            category.group_name = group_name
            category.name = name
            category.icon = icon
            category.kind = kind
            category.display_order = display_order
            category.is_active = is_active
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
        category.field_schema = field_schema

        if category.static_content is None:
            category.static_content = ""

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
