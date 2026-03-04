# -*- coding: utf-8 -*-
"""
Модели данных для приложения «Автосалон».
Описывают структуру таблиц базы данных.
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Инициализация объекта базы данных
db = SQLAlchemy()

class Car(db.Model):
    """Модель автомобиля."""
    __tablename__ = 'cars'
    
    id = db.Column(db.Integer, primary_key=True)
    vin_code = db.Column(db.String(17), unique=True, nullable=False)
    brand = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='available')  # available, sold
    
    # Новые поля, соответствующие форме добавления
    mileage = db.Column(db.Integer, nullable=True)           # пробег (км)
    color = db.Column(db.String(30), nullable=True)          # цвет
    engine = db.Column(db.String(50), nullable=True)         # тип двигателя
    transmission = db.Column(db.String(30), nullable=True)   # коробка передач
    description = db.Column(db.Text, nullable=True)          # описание
    image = db.Column(db.String(200), nullable=True)         # путь к файлу изображения
    
    # Связь с таблицей продаж
    sales = db.relationship('Sale', backref='car', lazy=True)

    def __repr__(self):
        return f'<Car {self.brand} {self.model} ({self.vin_code})>'

class Client(db.Model):
    """Модель клиента."""
    __tablename__ = 'clients'
    
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False, unique=True)
    email = db.Column(db.String(100), nullable=True)
    
    # Связь с таблицей продаж
    sales = db.relationship('Sale', backref='client', lazy=True)

    def __repr__(self):
        return f'<Client {self.full_name}>'

class Sale(db.Model):
    """Модель сделки продажи."""
    __tablename__ = 'sales'
    
    id = db.Column(db.Integer, primary_key=True)
    car_id = db.Column(db.Integer, db.ForeignKey('cars.id'), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    sale_date = db.Column(db.DateTime, default=datetime.utcnow)
    final_price = db.Column(db.Float, nullable=False)
    # Добавлен способ оплаты (используется в форме продажи)
    payment_method = db.Column(db.String(30), nullable=True)

    def __repr__(self):
        return f'<Sale {self.id} - {self.sale_date}>'
