from datetime import datetime
from extensions import db


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    group_name = db.Column(db.String(120), nullable=True)   # مثل: عمال الصيانة والخدمات
    name = db.Column(db.String(120), nullable=False)         # مثل: سباك
    icon = db.Column(db.String(20), nullable=True)           # إيموجي مثل 👨🏻‍🔧
    kind = db.Column(db.String(20), nullable=False, default="dynamic")  # static أو dynamic
    display_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)

    # للفئات الثابتة: النص الكامل يعرض كما هو
    static_content = db.Column(db.Text, nullable=True)

    # للفئات الديناميكية: تعريف الحقول كقائمة JSON
    # مثال: [{"key": "name", "label": "الاسم", "type": "text", "required": true},
    #        {"key": "phone", "label": "رقم الجوال", "type": "text", "required": true},
    #        {"key": "price", "label": "السعر", "type": "text", "required": false}]
    field_schema = db.Column(db.JSON, nullable=True)

    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    listings = db.relationship(
        "Listing",
        backref="category",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def get_fields(self):
        return self.field_schema or []


class Listing(db.Model):
    __tablename__ = "listings"

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)

    # بيانات الإدخال نفسه، مفاتيحها تطابق field_schema في الفئة
    data = db.Column(db.JSON, nullable=False, default=dict)

    phone = db.Column(db.String(30), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def get(self, key, default=""):
        return (self.data or {}).get(key, default)
