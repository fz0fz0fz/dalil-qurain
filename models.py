from datetime import datetime
from extensions import db


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    group_name = db.Column(db.String(120), nullable=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    icon = db.Column(db.String(20), nullable=True)
    kind = db.Column(db.String(20), nullable=False, default="dynamic")
    display_order = db.Column(db.Integer, default=0, index=True)
    is_active = db.Column(db.Boolean, default=True, index=True)
    static_content = db.Column(db.Text, nullable=True)
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

    def has_dynamic_fields(self):
        return self.kind == "dynamic" and bool(self.get_fields())


class Listing(db.Model):
    __tablename__ = "listings"

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False, index=True)
    data = db.Column(db.JSON, nullable=False, default=dict)
    phone = db.Column(db.String(30), nullable=True, index=True)
    is_visible = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)

    def get(self, key, default=""):
        return (self.data or {}).get(key, default)
