from extensions import db
from models import Category

CATEGORIES = [
    {
        "group_name": "الخدمات الشخصية",
        "name": "سائق (مشوار / نقل مدرسي)",
        "icon": "🚗",
        "kind": "dynamic",
        "display_order": 1,
        "field_schema": [
            {"key": "name", "label": "الاسم", "type": "text", "required": True},
            {"key": "phone", "label": "رقم الجوال", "type": "text", "required": True},
            {"key": "car", "label": "نوع السيارة", "type": "text", "required": False},
            {"key": "destination", "label": "الوجهات المتاحة", "type": "text", "required": False},
            {"key": "price", "label": "السعر", "type": "text", "required": False},
        ],
    },
    {
        "group_name": "الخدمات الشخصية",
        "name": "سطحة",
        "icon": "🛻",
        "kind": "dynamic",
        "display_order": 2,
        "field_schema": [
            {"key": "name", "label": "الاسم", "type": "text", "required": True},
            {"key": "phone", "label": "رقم الجوال", "type": "text", "required": True},
            {"key": "price", "label": "السعر", "type": "text", "required": False},
            {"key": "note", "label": "ملاحظات", "type": "text", "required": False},
        ],
    },
    {
        "group_name": "الخدمات الشخصية",
        "name": "مشرف عقاري (أراضي وبيوت)",
        "icon": "🏠",
        "kind": "dynamic",
        "display_order": 3,
        "field_schema": [
            {"key": "name", "label": "اسم المعلن", "type": "text", "required": True},
            {"key": "phone", "label": "رقم الجوال", "type": "text", "required": True},
            {"key": "offer_type", "label": "نوع العرض (بيع / إيجار)", "type": "text", "required": True},
            {"key": "property_type", "label": "نوع العقار (أرض / بيت)", "type": "text", "required": True},
            {"key": "location", "label": "الموقع", "type": "text", "required": True},
            {"key": "area", "label": "المساحة", "type": "text", "required": False},
            {"key": "price", "label": "السعر", "type": "text", "required": False},
        ],
    },
    {
        "group_name": "الخدمات الشخصية",
        "name": "تأجير معدات",
        "icon": "🚜",
        "kind": "dynamic",
        "display_order": 4,
        "field_schema": [
            {"key": "name", "label": "الاسم", "type": "text", "required": True},
            {"key": "phone", "label": "رقم الجوال", "type": "text", "required": True},
            {"key": "equipment_type", "label": "نوع المعدة", "type": "text", "required": True},
            {"key": "price", "label": "السعر", "type": "text", "required": False},
        ],
    },
    {
        "group_name": "عمال الصيانة والخدمات",
        "name": "سباك",
        "icon": "👨🏻‍🔧",
        "kind": "dynamic",
        "display_order": 10,
        "field_schema": [
            {"key": "name", "label": "الاسم", "type": "text", "required": True},
            {"key": "phone", "label": "رقم الجوال", "type": "text", "required": True},
            {"key": "note", "label": "نوع الخدمة / ملاحظات", "type": "text", "required": False},
        ],
    },
    {
        "group_name": "عمال الصيانة والخدمات",
        "name": "كهربائي",
        "icon": "👨🏻‍🔧",
        "kind": "dynamic",
        "display_order": 11,
        "field_schema": [
            {"key": "name", "label": "الاسم", "type": "text", "required": True},
            {"key": "phone", "label": "رقم الجوال", "type": "text", "required": True},
            {"key": "note", "label": "نوع الخدمة / ملاحظات", "type": "text", "required": False},
        ],
    },
    {
        "group_name": "الخدمات العامة",
        "name": "صيدلية",
        "icon": "💊",
        "kind": "static",
        "display_order": 100,
        "static_content": "سيتم إدخال بيانات الصيدليات هنا من لوحة التحكم.",
    },
    {
        "group_name": "الخدمات العامة",
        "name": "مطعم",
        "icon": "🍔",
        "kind": "static",
        "display_order": 101,
        "static_content": "سيتم إدخال بيانات المطاعم هنا من لوحة التحكم.",
    },
]


def seed_categories():
    """يضيف الفئات الأساسية فقط إذا لم تكن موجودة مسبقًا، بدون تكرار."""
    added = 0
    for cat in CATEGORIES:
        exists = Category.query.filter_by(name=cat["name"]).first()
        if not exists:
            db.session.add(Category(**cat))
            added += 1
    if added:
        db.session.commit()
    return added
