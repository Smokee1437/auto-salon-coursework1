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
    
    # Дополнительные данные для главной страницы
    cars_count = len(cars)
    sales_count = Sale.query.count()
    total_revenue = db.session.query(db.func.sum(Sale.final_price)).scalar() or 0
    
    # Последние добавленные автомобили
    recent_cars = Car.query.order_by(Car.id.desc()).limit(3).all()
    
    # Последние продажи
    recent_sales = Sale.query.order_by(Sale.sale_date.desc()).limit(3).all()
    
    return render_template('index.html', 
                         cars=cars,
                         cars_count=cars_count,
                         sales_count=sales_count,
                         total_revenue=total_revenue,
                         recent_cars=recent_cars,
                         recent_sales=recent_sales)

@app.route('/add_car', methods=['GET', 'POST'])  # Изменено с '/add' на '/add_car' для соответствия шаблонам
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
        mileage = request.form.get('mileage', 0)
        color = request.form.get('color')
        engine = request.form.get('engine')
        transmission = request.form.get('transmission')
        description = request.form.get('description')

        # Простая валидация данных
        if not vin or not brand or not model or not price:
            flash('Все обязательные поля должны быть заполнены!', 'danger')
            return redirect(url_for('add_car'))

        try:
            # Преобразование типов данных
            year = int(year) if year else datetime.now().year
            price = float(price)
            mileage = int(mileage) if mileage else 0

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
                mileage=mileage,
                color=color,
                engine=engine,
                transmission=transmission,
                description=description,
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

@app.route('/sell_car', methods=['GET', 'POST'])  # Изменено с '/sell/<int:car_id>' для соответствия шаблонам
def sell_car():
    """
    Страница оформления продажи автомобиля.
    GET: Отображает форму с выбором автомобиля
    POST: Обрабатывает продажу
    """
    # Получаем список доступных автомобилей
    available_cars = Car.query.filter_by(status='available').all()
    
    if request.method == 'POST':
        car_id = request.form.get('car_id')
        buyer_name = request.form.get('buyer_name')
        buyer_phone = request.form.get('buyer_phone')
        buyer_email = request.form.get('buyer_email')
        sale_price = request.form.get('sale_price')
        payment_method = request.form.get('payment_method')
        
        if not car_id or not buyer_name or not buyer_phone:
            flash('Выберите автомобиль и укажите данные покупателя.', 'danger')
            return redirect(url_for('sell_car'))
        
        try:
            # Поиск автомобиля
            car = Car.query.get_or_404(int(car_id))
            
            # Проверка статуса автомобиля
            if car.status != 'available':
                flash('Этот автомобиль уже продан или недоступен.', 'warning')
                return redirect(url_for('index'))
            
            # Поиск существующего клиента по телефону
            client = Client.query.filter_by(phone=buyer_phone).first()
            
            # Если клиент новый, создаем запись
            if not client:
                client = Client(
                    full_name=buyer_name,
                    phone=buyer_phone,
                    email=buyer_email
                )
                db.session.add(client)
                db.session.flush()  # Получаем ID без коммита
            
            # Создание записи о продаже
            sale = Sale(
                car_id=car.id,
                client_id=client.id,
                final_price=float(sale_price) if sale_price else car.price,
                sale_date=datetime.utcnow(),
                payment_method=payment_method
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
            return redirect(url_for('sell_car'))
    
    # Отображение формы продажи (GET)
    return render_template('sell_car.html', available_cars=available_cars)

@app.route('/sales')
def sales():  # Было sales_history
    """
    Страница истории продаж.
    """
    # Выборка всех продаж с связанными данными (автомобиль, клиент)
    sales = Sale.query.order_by(Sale.sale_date.desc()).all()
    
    # Статистика для отчета
    total_revenue = sum(sale.final_price for sale in sales)
    total_sales = len(sales)
    avg_price = total_revenue // total_sales if total_sales > 0 else 0
    max_price = max((sale.final_price for sale in sales), default=0)
    
    # Данные для графика (последние 7 дней)
    from datetime import timedelta
    dates = []
    amounts = []
    for i in range(6, -1, -1):
        date = datetime.now().date() - timedelta(days=i)
        dates.append(date.strftime('%d.%m'))
        daily_sum = db.session.query(db.func.sum(Sale.final_price)).filter(
            db.func.date(Sale.sale_date) == date
        ).scalar() or 0
        amounts.append(daily_sum)
    
    return render_template('sales.html', 
                         sales=sales,
                         total_revenue=total_revenue,
                         total_sales=total_sales,
                         avg_price=avg_price,
                         max_price=max_price,
                         chart_labels=dates,
                         chart_data=amounts)

@app.route('/sell/<int:car_id>', methods=['GET', 'POST'])
def sell_car_by_id(car_id):
    """
    Альтернативный маршрут для продажи конкретного автомобиля по ID.
    """
    car = Car.query.get_or_404(car_id)
    
    if car.status != 'available':
        flash('Этот автомобиль уже продан или недоступен.', 'warning')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        buyer_name = request.form.get('buyer_name')
        buyer_phone = request.form.get('buyer_phone')
        buyer_email = request.form.get('buyer_email')
        
        if not buyer_name or not buyer_phone:
            flash('Имя и телефон клиента обязательны.', 'danger')
            return redirect(url_for('sell_car_by_id', car_id=car_id))
        
        try:
            client = Client.query.filter_by(phone=buyer_phone).first()
            
            if not client:
                client = Client(
                    full_name=buyer_name,
                    phone=buyer_phone,
                    email=buyer_email
                )
                db.session.add(client)
                db.session.flush()
            
            sale = Sale(
                car_id=car.id,
                client_id=client.id,
                final_price=car.price,
                sale_date=datetime.utcnow()
            )
            
            car.status = 'sold'
            
            db.session.add(sale)
            db.session.commit()
            
            flash(f'Продажа автомобиля {car.brand} {car.model} успешно оформлена!', 'success')
            return redirect(url_for('index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при оформлении продажи: {str(e)}', 'danger')
            return redirect(url_for('sell_car_by_id', car_id=car_id))
    
    return render_template('sell_car.html', car=car, available_cars=[car])

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
        car.mileage = int(request.form.get('mileage', 0))
        car.color = request.form.get('color')
        car.engine = request.form.get('engine')
        car.transmission = request.form.get('transmission')
        car.description = request.form.get('description')
        
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



