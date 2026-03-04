# -*- coding: utf-8 -*-
"""
Основной файл приложения «Автосалон».
Реализует логику маршрутизации, обработку запросов и взаимодействие с базой данных.
Стек: Python, Flask, SQLAlchemy.
"""

from flask import Flask, render_template, request, redirect, url_for, flash
from models import db, Car, Client, Sale  # Импорт моделей и экземпляра БД
from datetime import datetime
import os

# Инициализация приложения Flask
app = Flask(__name__)

# -----------------------------------------------------------------------------
# КОНФИГУРАЦИЯ ПРИЛОЖЕНИЯ
# -----------------------------------------------------------------------------

# Секретный ключ необходим для работы сессий и flash-сообщений
# В реальном проекте должен храниться в переменных окружения
app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'

# Настройка подключения к базе данных (SQLite)
# URI указывает на файл database.db в текущей директории
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')

# Отключаем отслеживание модификаций объектов для экономии памяти
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Инициализация расширения SQLAlchemy приложением
db.init_app(app)

# -----------------------------------------------------------------------------
# МАРШРУТЫ (CONTROLLERS)
# -----------------------------------------------------------------------------

@app.route('/')
def index():
    """
    Главная страница приложения.
    Отображает каталог доступных для продажи автомобилей.
    """
    # Выборка всех автомобилей со статусом 'available' (в наличии)
    # Сортировка по цене (возрастание)
    cars = Car.query.filter_by(status='available').order_by(Car.price).all()
    return render_template('index.html', cars=cars)

@app.route('/add', methods=['GET', 'POST'])
def add_car():
    """
    Страница добавления нового автомобиля.
    GET: Отображение формы.
    POST: Обработка данных формы и сохранение в БД.
    """
    if request.method == 'POST':
        # Получение данных из формы
        vin = request.form.get('vin')
        brand = request.form.get('brand')
        model = request.form.get('model')
        year = request.form.get('year')
        price = request.form.get('price')

        # Простая валидация данных
        if not vin or not brand or not model or not price:
            flash('Все обязательные поля должны быть заполнены!', 'danger')
            return redirect(url_for('add_car'))

        try:
            # Преобразование типов данных
            year = int(year)
            price = float(price)

            # Проверка уникальности VIN-кода
            existing_car = Car.query.filter_by(vin_code=vin).first()
            if existing_car:
                flash('Автомобиль с таким VIN-кодом уже существует!', 'warning')
                return redirect(url_for('add_car'))

            # Создание нового объекта автомобиля
            new_car = Car(
                vin_code=vin,
                brand=brand,
                model=model,
                year=year,
                price=price,
                status='available'
            )

            # Добавление в сессию и коммит в БД
            db.session.add(new_car)
            db.session.commit()

            flash('Автомобиль успешно добавлен в каталог!', 'success')
            return redirect(url_for('index'))

        except ValueError:
            flash('Ошибка в формате данных (год или цена).', 'danger')
            return redirect(url_for('add_car'))
        except Exception as e:
            db.session.rollback()
            flash(f'Произошла ошибка при добавлении: {str(e)}', 'danger')
            return redirect(url_for('add_car'))

    # Если метод GET, отображаем форму
    return render_template('add_car.html')

@app.route('/sell/<int:car_id>', methods=['GET', 'POST'])
def sell_car(car_id):
    """
    Страница оформления продажи автомобиля.
    Связывает автомобиль, клиента и фиксирует сделку.
    """
    # Поиск автомобиля по ID
    car = Car.query.get_or_404(car_id)

    # Проверка статуса автомобиля
    if car.status != 'available':
        flash('Этот автомобиль уже продан или недоступен.', 'warning')
        return redirect(url_for('index'))

    if request.method == 'POST':
        client_name = request.form.get('client_name')
        client_phone = request.form.get('client_phone')
        client_email = request.form.get('client_email')

        if not client_name or not client_phone:
            flash('Имя и телефон клиента обязательны.', 'danger')
            return redirect(url_for('sell_car', car_id=car_id))

        try:
            # Поиск существующего клиента по телефону
            client = Client.query.filter_by(phone=client_phone).first()

            # Если клиент новый, создаем запись
            if not client:
                client = Client(
                    full_name=client_name,
                    phone=client_phone,
                    email=client_email
                )
                db.session.add(client)
                db.session.commit()  # Коммит нужен для получения ID клиента

            # Создание записи о продаже
            sale = Sale(
                car_id=car.id,
                client_id=client.id,
                final_price=car.price,
                sale_date=datetime.utcnow()
            )

            # Обновление статуса автомобиля
            car.status = 'sold'

            db.session.add(sale)
            db.session.commit()

            flash(f'Продажа автомобиля {car.brand} {car.model} успешно оформлена!', 'success')
            return redirect(url_for('index'))

        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при оформлении продажи: {str(e)}', 'danger')
            return redirect(url_for('sell_car', car_id=car_id))

    # Отображение формы продажи (GET)
    return render_template('sell_car.html', car=car)

@app.route('/sales')
def sales_history():
    """
    Страница истории продаж.
    Доступна только для менеджеров (в полной версии требуется авторизация).
    """
    # Выборка всех продаж с связанными данными (автомобиль, клиент)
    sales = Sale.query.order_by(Sale.sale_date.desc()).all()
    return render_template('sales.html', sales=sales)

@app.route('/edit/<int:car_id>', methods=['GET', 'POST'])
def edit_car(car_id):
    """
    Страница редактирования данных об автомобиле.
    """
    car = Car.query.get_or_404(car_id)

    if request.method == 'POST':
        car.brand = request.form.get('brand')
        car.model = request.form.get('model')
        car.year = int(request.form.get('year'))
        car.price = float(request.form.get('price'))
        
        # Статус вручную менять не рекомендуется, но оставим возможность
        car.status = request.form.get('status')

        try:
            db.session.commit()
            flash('Данные автомобиля обновлены.', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка обновления: {str(e)}', 'danger')

    return render_template('edit_car.html', car=car)

@app.route('/delete/<int:car_id>')
def delete_car(car_id):
    """
    Удаление автомобиля из базы данных.
    Внимание: Не удаляет автомобиль, если он уже продан (логическая защита).
    """
    car = Car.query.get_or_404(car_id)

    if car.status == 'sold':
        flash('Нельзя удалить проданный автомобиль из истории.', 'warning')
    else:
        try:
            db.session.delete(car)
            db.session.commit()
            flash('Автомобиль удален из каталога.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка удаления: {str(e)}', 'danger')

    return redirect(url_for('index'))

# -----------------------------------------------------------------------------
# ЗАПУСК ПРИЛОЖЕНИЯ И ИНИЦИАЛИЗАЦИЯ БД
# -----------------------------------------------------------------------------

if __name__ == '__main__':
    # В контексте приложения создаем все таблицы, если их нет
    with app.app_context():
        db.create_all()
        print("База данных успешно инициализирована.")
    
    # Запуск сервера разработки
    # debug=True позволяет видеть ошибки в браузере и авто-перезагружать сервер
    app.run(debug=True, host='127.0.0.1', port=5000)
