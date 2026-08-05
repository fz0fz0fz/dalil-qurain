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


STATIC_GOV_TEXT = """━━━━━━━━━━━━━━━
🏛️ دليلك للخدمات والدوائر الحكومية في القرين:
━━━━━━━━━━━━━━━

🏢 أمارة مركز القرين:
📞 0162332212

🏥 مركز صحي القرين:
📞 0162332232

🚓 شرطة القرين:
📞 0162332281
━━━━━━━━━━━━━━━
الجهات الخيرية في مركز القرين والتي تحتاج دعم أهل الخير والفضل والإحسان

- جمعية الدعوة والإرشاد وتوعية الجاليات
- جوال 0558332147
حساب الراجحي
400608010045553
أيبان
SA3180000400608010045553

🔷️🔷️🔷️
- جمعية العناية بالمساجد
تخدم أكثر من 100 مسجد وجامع
جوال 0553591918
حساب الراجحي
280608010844513
أيبان
SA4880000280608010844513

🔷️🔷️🔷️
- جمعية الخدمات الإنسانية
جوال 0533318257
حساب الراجحي
400608011901903
أيبان
SA3380000400608011901903

🔷️🔷️🔷️
- حلقات تحفيظ القران:
دار أسماء بنت أبي بكر النسائية
جوال 0558600959
( يدرس فيها ما يزيد عن 130 طالبة من مختلف الأعمار )
حساب الدار مسجل باسم جمعية تحفيظ القران برياض الخبراء وهو حساب موارده خاصة بالدار
مصرف الإنماء
68204011634000
أيبان
SA3005000068204011634000

🔷️🔷️🔷️
- حلقات البنين
حساب الراجحي
175608010448842
(ملاحظة مهمة في حال التحويل لابد تسجيل الاسم أو ارسال الإيصال إلى جوال مشرف الحلقات الاستاذ ناصر بن محمد الحربي 0552705060 لحفظ الدعم الخاص بالحلقات)
━━━━━━━━━━━━━━━

🏫 المدارس:

🏫 مدرسة الطفولة المبكرة:
📞 +966539591308

🏫 المدرسة الابتدائية – بنين:
📞 0162332001

🏫 المدرسة الابتدائية – بنات:
📞 +966554560071

🏫 متوسطة مؤتة وثانوية تبوك–بنين:
📞 0165322556
+966567309591
━━━━━━━━━━━━━━━
📲 أرقام الطوارئ والخدمات العامة:

🚑 997 — الإسعاف
🔥 998 — الدفاع المدني
🚓 999 — الشرطة
🚗 993 — المرور
🚧 996 — أمن الطرق
💡 933 — شركة الكهرباء
🩺 937 — وزارة الصحة
📄 920000560 — نجم (حوادث المركبات المؤمن عليها)
━━━━━━━━━━━━━━━
📅 آخر تحديث: أغسطس 2025"""

STATIC_PHARMACY_TEXT = """💊 قائمة الصيدليات في القرين والدليمية:

🏪 صيدلية ركن أطلس (📍القرين)
📞 0556945390
📍 https://maps.app.goo.gl/4YLktrjdi5VFqMGHA
🕒 من 7 صباحاً إلى 3 صباحاً
🕌 الجمعة: من 3 عصراً إلى 3 صباحاً
💡 خدمة وصفتي متوفرة
🛵 خدمة التوصيل متوفرة

━━━━━━━━━━━━━━━
🏪 صيدلية نواظر (📍الدليمية)
📞 0539550444
📍 https://maps.app.goo.gl/2rLyro4cgdWcMV2T9
🕒 24 ساعة طوال أيام الأسبوع

━━━━━━━━━━━━━━━
🏪 صيدلية دواء البدر (📍الدليمية)
📞 0162339000
📍 https://maps.app.goo.gl/oj8w9dBUTdjmbW4z8
🕒 من 9 صباحاً إلى 1 صباحاً
🕌 الجمعة: من 4 عصراً إلى 1 صباحاً

📅 آخر تحديث: أغسطس 2025"""

STATIC_GROCERY_TEXT = """🥤 قائمة البقالات في القرين ولوازم الرحلات
━━━━━━━━━━━━━━━━━━━

🔹 البقالات
🛒 بقالة زاوية الراقي
📞 0578071323

🛒 بقالة سلة سلطانة
📞 +966509007300
📍 https://maps.app.goo.gl/5VXuKAwCn4NzuiVYA

🛒 بقالة ركن قريتي
📞 +966537081794
📍 https://maps.app.goo.gl/xR8kU4E3PDw32jeu5

🛒 بقالة شموع الوسام
📞 0539881727
📍 https://maps.app.goo.gl/VEnZ7bPQeJvDawTA6

━━━━━━━━━━━━━━━
🔹 لوازم الرحلات
🧺 محل ركن الوسم
📞 0530165380
📍 https://maps.app.goo.gl/yNBoArtpAJa3JvR77

🧺 محل صندوق الرحلة
📞 0506438303
📍 https://maps.app.goo.gl/8Ze2w48KZnKnMZP26

📅 آخر تحديث: أغسطس 2025"""


CATEGORIES = [
    {"group_name": "الخدمات العامة", "name": "حكومي", "icon": "🏢", "kind": "static", "display_order": 1, "static_content": STATIC_GOV_TEXT},
    {"group_name": "الخدمات العامة", "name": "صيدلية", "icon": "💊", "kind": "static", "display_order": 2, "static_content": STATIC_PHARMACY_TEXT},
    {"group_name": "الخدمات العامة", "name": "بقالة", "icon": "🥤", "kind": "static", "display_order": 3, "static_content": STATIC_GROCERY_TEXT},
    {"group_name": "الخدمات العامة", "name": "خضار", "icon": "🥬", "kind": "static", "display_order": 4, "static_content": "سيتم تحديث قائمة الخضار قريبًا من لوحة الإدارة."},
    {"group_name": "الخدمات العامة", "name": "حلا", "icon": "🍮", "kind": "static", "display_order": 5, "static_content": "سيتم تحديث قائمة الحلا قريبًا من لوحة الإدارة."},
    {"group_name": "الخدمات العامة", "name": "مطعم", "icon": "🍔", "kind": "static", "display_order": 6, "static_content": "سيتم تحديث قائمة المطاعم قريبًا من لوحة الإدارة."},
    {"group_name": "الخدمات العامة", "name": "مشوار", "icon": "🚗", "kind": "dynamic", "display_order": 7, "field_schema": default_dynamic_fields()},
    {"group_name": "الخدمات العامة", "name": "نقل مدرسي", "icon": "🚌", "kind": "dynamic", "display_order": 8, "field_schema": default_dynamic_fields()},
    {"group_name": "الخدمات العامة", "name": "شالية", "icon": "🏖️", "kind": "static", "display_order": 9, "static_content": "سيتم تحديث قائمة الشاليهات قريبًا من لوحة الإدارة."},
    {"group_name": "الخدمات العامة", "name": "وايت", "icon": "🚎", "kind": "dynamic", "display_order": 10, "field_schema": default_dynamic_fields()},
    {"group_name": "عمال الصيانة والخدمات", "name": "سباك", "icon": "👨🏻‍🔧", "kind": "dynamic", "display_order": 11, "field_schema": default_dynamic_fields()},
    {"group_name": "عمال الصيانة والخدمات", "name": "كهربائي", "icon": "👨🏻‍🔧", "kind": "dynamic", "display_order": 12, "field_schema": default_dynamic_fields()},
    {"group_name": "عمال الصيانة والخدمات", "name": "مبلط", "icon": "👨🏻‍🔧", "kind": "dynamic", "display_order": 13, "field_schema": default_dynamic_fields()},
    {"group_name": "عمال الصيانة والخدمات", "name": "بناء", "icon": "👨🏻‍🔧", "kind": "dynamic", "display_order": 14, "field_schema": default_dynamic_fields()},
    {"group_name": "عمال الصيانة والخدمات", "name": "جبس", "icon": "👨🏻‍🔧", "kind": "dynamic", "display_order": 15, "field_schema": default_dynamic_fields()},
    {"group_name": "عمال الصيانة والخدمات", "name": "مليس", "icon": "👨🏻‍🔧", "kind": "dynamic", "display_order": 16, "field_schema": default_dynamic_fields()},
    {"group_name": "عمال الصيانة والخدمات", "name": "دهان", "icon": "👨🏻‍🔧", "kind": "dynamic", "display_order": 17, "field_schema": default_dynamic_fields()},
    {"group_name": "عمال الصيانة والخدمات", "name": "عامل بالساعة", "icon": "👨🏻‍🔧", "kind": "dynamic", "display_order": 18, "field_schema": default_dynamic_fields()},
    {"group_name": "عمال الصيانة والخدمات", "name": "ضيافة", "icon": "👨‍💼", "kind": "dynamic", "display_order": 19, "field_schema": default_dynamic_fields()},
    {"group_name": "المحلات المهنية والحرفية", "name": "حدادة", "icon": "⛓️", "kind": "dynamic", "display_order": 20, "field_schema": default_dynamic_fields()},
    {"group_name": "المحلات المهنية والحرفية", "name": "منجرة", "icon": "🪚", "kind": "dynamic", "display_order": 21, "field_schema": default_dynamic_fields()},
    {"group_name": "المحلات المهنية والحرفية", "name": "ألمنيوم", "icon": "🪛", "kind": "dynamic", "display_order": 22, "field_schema": default_dynamic_fields()},
    {"group_name": "المحلات المهنية والحرفية", "name": "صيانة منزلية (تبريد وتكييف)", "icon": "❄️", "kind": "dynamic", "display_order": 23, "field_schema": default_dynamic_fields()},
    {"group_name": "المعدات الثقيلة + الدفان + مواد البناء", "name": "دفان - شيول - مواد بناء وعوازل", "icon": "🛻🚜", "kind": "dynamic", "display_order": 24, "field_schema": default_dynamic_fields()},
    {"group_name": "خدمات السيارات", "name": "سيارة", "icon": "🛞", "kind": "dynamic", "display_order": 25, "field_schema": default_dynamic_fields()},
    {"group_name": "ذبائح", "name": "ذبائح وملاحم", "icon": "🐑", "kind": "static", "display_order": 26, "static_content": "سيتم تحديث قائمة الذبائح والملاحم قريبًا من لوحة الإدارة."},
    {"group_name": "محلات", "name": "محلات وخدمات تخصصية", "icon": "🏬", "kind": "static", "display_order": 27, "static_content": "يمكنك تحديث هذه الفئة من لوحة الإدارة وإضافة المحتوى الثابت المناسب."},
    {"group_name": "محلات", "name": "مغاسل", "icon": "🧼", "kind": "static", "display_order": 28, "static_content": "سيتم تحديث القائمة قريبًا."},
    {"group_name": "محلات", "name": "تأجير", "icon": "🧰", "kind": "static", "display_order": 29, "static_content": "سيتم تحديث القائمة قريبًا."},
    {"group_name": "محلات", "name": "منظفات", "icon": "🧴", "kind": "static", "display_order": 30, "static_content": "سيتم تحديث القائمة قريبًا."},
    {"group_name": "محلات", "name": "خدمات مقاولات", "icon": "🏗️", "kind": "static", "display_order": 31, "static_content": "سيتم تحديث القائمة قريبًا."},
    {"group_name": "محلات", "name": "قرطاسية", "icon": "📚", "kind": "static", "display_order": 32, "static_content": "سيتم تحديث القائمة قريبًا."},
    {"group_name": "محلات", "name": "خدمات شخصية", "icon": "🧑‍💼", "kind": "static", "display_order": 33, "static_content": "سيتم تحديث القائمة قريبًا."},
    {"group_name": "محلات", "name": "حلاق", "icon": "💈", "kind": "static", "display_order": 34, "static_content": "سيتم تحديث القائمة قريبًا."},
]


def seed_categories():
    added = 0
    updated = 0
    for item in CATEGORIES:
        payload = deepcopy(item)
        existing = Category.query.filter_by(name=payload["name"]).first()
        if existing:
            changed = False
            for key in ["group_name", "icon", "kind", "display_order"]:
                if getattr(existing, key) != payload.get(key):
                    setattr(existing, key, payload.get(key))
                    changed = True
            if payload.get("kind") == "dynamic":
                if not existing.field_schema:
                    existing.field_schema = payload.get("field_schema") or default_dynamic_fields()
                    changed = True
            else:
                if not existing.static_content:
                    existing.static_content = payload.get("static_content", "")
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


LEGACY_CATEGORY_MAP = {
    "سائق (مشوار / نقل مدرسي)": "مشوار",
    "سطحة": "سيارة",
    "تأجير معدات": "دفان - شيول - مواد بناء وعوازل",
}


def convert_legacy_listing_data(old_name, listing_data):
    listing_data = listing_data or {}
    converted = {
        "name": listing_data.get("name", ""),
        "phone": listing_data.get("phone", ""),
        "service_description": "",
        "location": "",
        "maps_url": "",
        "price": listing_data.get("price", ""),
        "working_hours": "",
        "social_url": "",
    }

    if old_name == "سائق (مشوار / نقل مدرسي)":
        parts = [listing_data.get("car", ""), listing_data.get("destination", "")]
        converted["service_description"] = " - ".join([p for p in parts if p])
    elif old_name == "سطحة":
        note = listing_data.get("note", "")
        converted["service_description"] = f"سطحة {('- ' + note) if note else ''}".strip()
    elif old_name == "تأجير معدات":
        converted["service_description"] = listing_data.get("equipment_type", "")
    return converted



def migrate_legacy_categories():
    changed = False
    for old_name, new_name in LEGACY_CATEGORY_MAP.items():
        old_category = Category.query.filter_by(name=old_name).first()
        new_category = Category.query.filter_by(name=new_name).first()
        if not old_category or not new_category:
            continue
        for listing in old_category.listings.all():
            listing.category_id = new_category.id
            listing.data = convert_legacy_listing_data(old_name, listing.data)
            listing.phone = (listing.data or {}).get("phone", listing.phone)
            changed = True
        db.session.delete(old_category)
        changed = True

    obsolete_names = ["مشرف عقاري (أراضي وبيوت)"]
    for name in obsolete_names:
        category = Category.query.filter_by(name=name).first()
        if category and category.listings.count() == 0 and category.is_active:
            category.is_active = False
            changed = True

    if changed:
        db.session.commit()
