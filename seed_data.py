from copy import deepcopy
from extensions import db
from models import Category


def default_dynamic_fields():
    return [
        {"key": "name", "label": "الاسم", "type": "text", "required": True},
        {"key": "phone", "label": "رقم الجوال", "type": "tel", "required": True},
        {
            "key": "service_description",
            "label": "الوصف أو نوع الخدمة",
            "type": "textarea",
            "required": False,
            "maxlength": 200,
        },
        {
            "key": "location",
            "label": "الموقع أو الحي",
            "type": "select",
            "required": True,
            "options": ["القرين", "الدليمية"],
        },
        {"key": "maps_url", "label": "رابط خرائط", "type": "url", "required": False},
        {"key": "price", "label": "الأسعار", "type": "text", "required": False},
        {"key": "working_hours", "label": "أوقات العمل", "type": "text", "required": False},
        {
            "key": "social_url",
            "label": "رابط تيك توك أو إنستغرام",
            "type": "url",
            "required": False,
        },
    ]


def make_category(group_name, name, icon, order):
    return {
        "group_name": group_name,
        "name": name,
        "icon": icon,
        "kind": "dynamic",
        "display_order": order,
        "is_active": True,
        "field_schema": default_dynamic_fields(),
        "static_content": "",
    }


CATEGORIES = [
    make_category("الخدمات العامة", "حكومي", "🏢", 1),
    make_category("الخدمات العامة", "صيدلية", "💊", 2),
    make_category("الخدمات العامة", "بقالة", "🥤", 3),
    make_category("الخدمات العامة", "خضار", "🥬", 4),
    make_category("الخدمات العامة", "حلا", "🍮", 5),
    make_category("الخدمات العامة", "مطعم", "🍔", 6),
    make_category("الخدمات العامة", "مشوار", "🚗", 7),
    make_category("الخدمات العامة", "نقل مدرسي", "🚌", 8),
    make_category("الخدمات العامة", "شالية", "🏖️", 9),
    make_category("الخدمات العامة", "وايت", "🚎", 10),
    make_category("عمال", "سباك", "👨🏻‍🔧", 11),
    make_category("عمال", "كهربائي", "👨🏻‍🔧", 12),
    make_category("عمال", "مبلط", "👨🏻‍🔧", 13),
    make_category("عمال", "بناء", "👨🏻‍🔧", 14),
    make_category("عمال", "جبس", "👨🏻‍🔧", 15),
    make_category("عمال", "مليس", "👨🏻‍🔧", 16),
    make_category("عمال", "دهان", "🎨", 17),
    make_category("عمال", "بالساعة", "👨🏻‍🔧", 18),
    make_category("عمال", "ضيافة", "👨‍💼", 19),
    make_category("المحلات المهنية والحرفية", "حدادة", "⛓️", 20),
    make_category("المحلات المهنية والحرفية", "منجرة", "🪚", 21),
    make_category("المحلات المهنية والحرفية", "ألمنيوم", "🪛", 22),
    make_category("المحلات المهنية والحرفية", "صيانة منزلية (تبريد وتكييف)", "❄️", 23),
    make_category("المعدات الثقيلة + الدفان + مواد البناء", "دفان - شيول - مواد بناء وعوازل", "🛻🚜", 24),
    make_category("خدمات السيارات", "سيارة (مغاسل سيارات - كهربائي سيارات - سطحات - نقل عفش)", "🛞", 25),
    make_category("ذبائح", "ذبائح وملاحم", "🐑", 26),
    make_category("محلات", "محلات وخدمات تخصصية", "🏬", 27),
    make_category("محلات", "مغاسل ملابس", "🧼", 28),
    make_category("محلات", "تأجير", "🧰", 29),
    make_category("محلات", "منظفات", "🧴", 30),
    make_category("محلات", "خدمات مقاولات", "🏗️", 31),
    make_category("محلات", "قرطاسية", "📚", 32),
    make_category("محلات", "خدمات شخصية", "🧑‍💼", 33),
    make_category("محلات", "حلاق", "💈", 34),
]


LEGACY_CATEGORY_MAP = {
    "سائق (مشوار / نقل مدرسي)": "مشوار",
    "سطحة": "سيارة (مغاسل سيارات - كهربائي سيارات - سطحات - نقل عفش)",
    "تأجير معدات": "دفان - شيول - مواد بناء وعوازل",
    "عامل بالساعة": "بالساعة",
    "سيارة": "سيارة (مغاسل سيارات - كهربائي سيارات - سطحات - نقل عفش)",
    "مغاسل": "مغاسل ملابس",
}


OBSOLETE_CATEGORY_NAMES = [
    "مشرف عقاري (أراضي وبيوت)",
]


TARGET_CATEGORY_NAMES = {item["name"] for item in CATEGORIES}


def convert_legacy_listing_data(listing_data):
    listing_data = listing_data or {}
    return {
        "name": listing_data.get("name", ""),
        "phone": listing_data.get("phone", ""),
        "service_description": listing_data.get("service_description", "") or listing_data.get("note", "") or listing_data.get("equipment_type", "") or " - ".join([
            part for part in [listing_data.get("car", ""), listing_data.get("destination", "")]
            if part
        ]),
        "location": listing_data.get("location", ""),
        "maps_url": listing_data.get("maps_url", ""),
        "price": listing_data.get("price", ""),
        "working_hours": listing_data.get("working_hours", ""),
        "social_url": listing_data.get("social_url", ""),
    }


def seed_categories():
    added = 0
    updated = 0

    for item in CATEGORIES:
        payload = deepcopy(item)
        existing = Category.query.filter_by(name=payload["name"]).first()
        if existing:
            changed = False
            for key in ["group_name", "icon", "kind", "display_order", "is_active"]:
                if getattr(existing, key) != payload.get(key):
                    setattr(existing, key, payload.get(key))
                    changed = True
            if existing.field_schema != payload.get("field_schema"):
                existing.field_schema = payload.get("field_schema")
                changed = True
            if existing.static_content:
                existing.static_content = ""
                changed = True
            if changed:
                updated += 1
            continue

        db.session.add(Category(**payload))
        added += 1

    if added or updated:
        db.session.commit()

    migrate_legacy_categories()
    return {"added": added, "updated": updated}


def migrate_legacy_categories():
    changed = False

    for old_name, new_name in LEGACY_CATEGORY_MAP.items():
        old_category = Category.query.filter_by(name=old_name).first()
        new_category = Category.query.filter_by(name=new_name).first()
        if not old_category or not new_category or old_category.id == new_category.id:
            continue

        for listing in old_category.listings.all():
            listing.category_id = new_category.id
            listing.data = convert_legacy_listing_data(listing.data)
            listing.phone = (listing.data or {}).get("phone", listing.phone)
            listing.is_visible = True
            changed = True

        db.session.delete(old_category)
        changed = True

    for name in OBSOLETE_CATEGORY_NAMES:
        category = Category.query.filter_by(name=name).first()
        if category and category.listings.count() == 0:
            db.session.delete(category)
            changed = True

    if changed:
        db.session.commit()
