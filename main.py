from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fallback-secret-key-for-dev')



# Таблицы для хранения пользователей и их данных
def create_tables():
    connection = sqlite3.connect('users.db')
    cursor = connection.cursor()
    
    # Таблица пользователей
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    )
    ''')
    
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        full_name TEXT,
        birth_date TEXT,
        email TEXT,
        phone TEXT,
        bio TEXT,
        skills TEXT,
        job_position TEXT,
        salary_expectations TEXT,
        education TEXT,
        courses TEXT,
        certificates TEXT,
        github TEXT,
        linkedin TEXT,
        vk TEXT,
        telegram TEXT,
        portfolio_link TEXT,
        photo TEXT,
        experience TEXT,
        languages TEXT,
        is_completed BOOLEAN DEFAULT FALSE,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # Создаем администратора по умолчанию
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    admin_exists = cursor.fetchone()
    if not admin_exists:
        cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', ('admin', 'admin123'))
        print("Администратор создан: admin / admin123")

    connection.commit()
    connection.close()
    print("Таблицы созданы успешно с новыми полями")

# Измените путь к базе данных для Render
def get_db_connection():
    # На Render используем PostgreSQL если доступно
    database_url = os.environ.get('DATABASE_URL')
    if database_url and database_url.startswith('postgresql://'):
        # Для PostgreSQL потребуется другая конфигурация
        # Пока оставим SQLite для простоты
        pass
    
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return redirect('/login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form.get('confirm_password', '')

        if password != confirm_password:
            return render_template('register.html', error="Пароли не совпадают")

        if len(password) < 6:
            return render_template('register.html', error="Пароль должен содержать минимум 6 символов")

        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            connection.commit()
            connection.close()
            flash('Регистрация успешна! Теперь вы можете войти.', 'success')
            return redirect('/login')
        except sqlite3.IntegrityError:
            return render_template('register.html', error="Пользователь с таким именем уже существует")
        except Exception as e:
            print(f"Ошибка регистрации: {e}")
            return render_template('register.html', error="Ошибка при регистрации")
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute("SELECT id FROM users WHERE username = ? AND password = ?", (username, password))
            user = cursor.fetchone()
            connection.close()
            
            if user:
                session['user_id'] = user['id']
                session['username'] = username
                
                if username == 'admin':
                    return redirect('/admin')
                else:
                    return redirect('/user')      
            else:
                return render_template('login.html', error="Неверное имя пользователя или пароль")
        except Exception as e:
            print(f"Ошибка входа: {e}")
            return render_template('login.html', error="Ошибка базы данных")
    
    return render_template('login.html')

@app.route('/admin')
def admin():
    if 'username' not in session:
        return redirect('/login')
    
    if session['username'] != 'admin':
        return redirect('/user')

    # Получаем список всех пользователей (кроме админа) с их профилями
    try:
        connection = get_db_connection()
        users = connection.execute('''
            SELECT u.id, u.username, up.full_name, up.birth_date, up.is_completed 
            FROM users u 
            LEFT JOIN user_profiles up ON u.id = up.user_id 
            WHERE u.username != 'admin'
            ORDER BY up.is_completed, u.id
        ''').fetchall()
        connection.close()
    except Exception as e:
        print(f"Ошибка получения пользователей: {e}")
        users = []
    
    return render_template('admin.html', users=users, username=session['username'])

# Редактирование профиля пользователя админом
@app.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    if 'username' not in session or session['username'] != 'admin':
        return redirect('/login')
    
    connection = get_db_connection()
    
    if request.method == 'POST':
        full_name = request.form.get('full_name', '')
        birth_date = request.form.get('birth_date', '')
        email = request.form.get('email', '')
        phone = request.form.get('phone', '')
        bio = request.form.get('bio', '')
        skills = request.form.get('skills', '')
        job_position = request.form.get('job_position', '')
        salary_expectations = request.form.get('salary_expectations', '')
        education = request.form.get('education', '')
        courses = request.form.get('courses', '')
        certificates = request.form.get('certificates', '')
        github = request.form.get('github', '')
        linkedin = request.form.get('linkedin', '')
        vk = request.form.get('vk', '')
        telegram = request.form.get('telegram', '')
        portfolio_link = request.form.get('portfolio_link', '')
        
        # Обработка даты
        if birth_date:
            try:
                if '.' in birth_date:
                    parts = birth_date.split('.')
                    if len(parts) == 3:
                        birth_date = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
            except Exception as e:
                print(f"Ошибка обработки даты: {e}")
                pass

        try:
            # Проверяем, существует ли уже профиль
            existing_profile = connection.execute(
                'SELECT * FROM user_profiles WHERE user_id = ?', (user_id,)
            ).fetchone()
            
            if existing_profile:
                # Обновляем существующий профиль и отмечаем как завершенный
                connection.execute('''
                    UPDATE user_profiles 
                    SET full_name = ?, birth_date = ?, email = ?, phone = ?, 
                        bio = ?, skills = ?, job_position = ?, salary_expectations = ?,
                        education = ?, courses = ?, certificates = ?, github = ?,
                        linkedin = ?, vk = ?, telegram = ?, portfolio_link = ?,
                        is_completed = TRUE
                    WHERE user_id = ?
                ''', (full_name, birth_date, email, phone, bio, skills, 
                      job_position, salary_expectations, education, courses,
                      certificates, github, linkedin, vk, telegram, 
                      portfolio_link, user_id))
            else:
                # Создаем новый профиль и отмечаем как завершенный
                connection.execute('''
                    INSERT INTO user_profiles 
                    (user_id, full_name, birth_date, email, phone, bio, skills,
                     job_position, salary_expectations, education, courses, certificates,
                     github, linkedin, vk, telegram, portfolio_link, is_completed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, TRUE)
                ''', (user_id, full_name, birth_date, email, phone, bio, skills,
                      job_position, salary_expectations, education, courses,
                      certificates, github, linkedin, vk, telegram, portfolio_link))
            
            connection.commit()
            flash('Профиль пользователя успешно сохранен и опубликован!', 'success')

        except Exception as e:
            print(f"Ошибка сохранения профиля: {e}")
            flash(f'Ошибка при сохранении профиля: {str(e)}', 'error')
        finally:
            connection.close()
        
        return redirect('/admin')
    
    # GET запрос - получаем данные пользователя
    try:
        user = connection.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        profile = connection.execute('SELECT * FROM user_profiles WHERE user_id = ?', (user_id,)).fetchone()
    except Exception as e:
        print(f"Ошибка получения данных: {e}")
        user = None
        profile = None
    finally:
        connection.close()
    
    if not user:
        flash('Пользователь не найден', 'error')
        return redirect('/admin')
    
    return render_template('edit_user.html', user=user, profile=profile)

@app.route('/user')
def user():
    if 'username' not in session:
        return redirect('/login')
    
    # Проверяем, есть ли у пользователя заполненный профиль
    try:
        connection = get_db_connection()
        profile = connection.execute('''
            SELECT * FROM user_profiles 
            WHERE user_id = ? AND is_completed = TRUE
        '''.strip(), (session['user_id'],)).fetchone()
        connection.close()
    except Exception as e:
        print(f"Ошибка получения профиля: {e}")
        profile = None
    
    return render_template('user.html', 
                         username=session['username'],
                         has_portfolio=profile is not None)

@app.route('/user/create_portfolio')
def create_portfolio():
    if 'username' not in session:
        return redirect('/login')
    
    # Получаем данные профиля пользователя (если уже есть)
    try:
        connection = get_db_connection()
        profile = connection.execute('''
            SELECT * FROM user_profiles 
            WHERE user_id = ?
        '''.strip(), (session['user_id'],)).fetchone()
        connection.close()
    except Exception as e:
        print(f"Ошибка получения профиля: {e}")
        profile = None
    
    # Список популярных учебных заведений для автозаполнения
    education_suggestions = [
        "Московский государственный университет",
        "Санкт-Петербургский государственный университет",
        "Высшая школа экономики",
        "Московский физико-технический институт",
        "Новосибирский государственный университет",
        "Московский государственный технический университет",
        "Уральский федеральный университет",
        "Казанский федеральный университет",
        "Томский государственный университет",
        "Российский университет дружбы народов"
    ]
    
    return render_template('create_portfolio.html', 
                         username=session['username'],
                         profile=profile,
                         education_suggestions=education_suggestions)

@app.route('/user/save_portfolio', methods=['POST'])
def save_portfolio():
    if 'username' not in session:
        return redirect('/login')
    
    try:
        # Получаем данные формы - используем .get() вместо прямого доступа
        full_name = request.form.get('full_name', '')
        birth_date = request.form.get('birth_date', '')
        email = request.form.get('email', '')
        phone = request.form.get('phone', '')
        bio = request.form.get('bio', '')
        skills = request.form.get('skills', '')
        job_position = request.form.get('job_position', '')
        salary_expectations = request.form.get('salary_expectations', '')
        education = request.form.get('education', '')
        courses = request.form.get('courses', '')
        certificates = request.form.get('certificates', '')
        github = request.form.get('github', '')        
        linkedin = request.form.get('linkedin', '')    
        vk = request.form.get('vk', '')
        telegram = request.form.get('telegram', '')
        portfolio_link = request.form.get('portfolio_link', '')
        photo_data = request.form.get('photo_data', '')
        
        # Получаем опыт работы
        companies = request.form.getlist('company[]')
        positions = request.form.getlist('position[]')
        start_dates = request.form.getlist('start_date[]')
        end_dates = request.form.getlist('end_date[]')
        responsibilities = request.form.getlist('responsibilities[]')
        
        # Формируем опыт работы в текстовом виде
        experience_parts = []
        for i in range(len(companies)):
            if companies[i] and positions[i]:
                exp_text = f"{companies[i]} - {positions[i]}\n"
                if start_dates[i]:
                    exp_text += f"Период: {start_dates[i]}"
                    if end_dates[i]:
                        exp_text += f" - {end_dates[i]}\n"
                    else:
                        exp_text += " - по настоящее время\n"
                if responsibilities[i]:
                    exp_text += f"Обязанности: {responsibilities[i]}\n"
                experience_parts.append(exp_text)
        
        experience = "\n---\n".join(experience_parts) if experience_parts else ""
        
        # Получаем языки
        languages_list = request.form.getlist('language[]')
        language_levels = request.form.getlist('language_level[]')
        languages_text = ""
        for i in range(len(languages_list)):
            if languages_list[i] and language_levels[i]:
                languages_text += f"{languages_list[i]} ({language_levels[i]})\n"
        
        # Обработка даты
        if birth_date:
            try:
                if '.' in birth_date:
                    parts = birth_date.split('.')
                    if len(parts) == 3:
                        birth_date = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
            except Exception as e:
                print(f"Ошибка обработки даты: {e}")
                pass
        
        connection = get_db_connection()
        
        # Проверяем, существует ли уже профиль
        existing_profile = connection.execute(
            'SELECT * FROM user_profiles WHERE user_id = ?', (session['user_id'],)
        ).fetchone()
        
        if existing_profile:
            # Обновляем существующий профиль
            connection.execute('''
                UPDATE user_profiles 
                SET full_name = ?, birth_date = ?, email = ?, phone = ?, 
                    bio = ?, skills = ?, job_position = ?, salary_expectations = ?,
                    education = ?, courses = ?, certificates = ?, github = ?,
                    linkedin = ?, vk = ?, telegram = ?, portfolio_link = ?, 
                    photo = ?, experience = ?, languages = ?, is_completed = FALSE
                WHERE user_id = ?
            ''', (full_name, birth_date, email, phone, bio, skills, job_position,
                  salary_expectations, education, courses, certificates, github,
                  linkedin, vk, telegram, portfolio_link, photo_data, 
                  experience, languages_text, session['user_id']))
        else:
            # Создаем новый профиль
            connection.execute('''
                INSERT INTO user_profiles 
                (user_id, full_name, birth_date, email, phone, bio, skills, 
                 job_position, salary_expectations, education, courses, certificates,
                 github, linkedin, vk, telegram, portfolio_link, photo, experience, 
                 languages, is_completed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, FALSE)
            ''', (session['user_id'], full_name, birth_date, email, phone, bio, skills,
                  job_position, salary_expectations, education, courses, certificates,
                  github, linkedin, vk, telegram, portfolio_link, photo_data, 
                  experience, languages_text))
        
        connection.commit()
        connection.close()
        
        flash('Ваши данные сохранены! Ожидайте проверки администратора.', 'success')
        return redirect('/user')
        
    except Exception as e:
        print(f"Ошибка сохранения портфолио: {e}")
        flash(f"Ошибка при сохранении: {str(e)}", 'error')
        return redirect('/user/create_portfolio')
    
@app.route('/user/view_portfolio')
def view_portfolio():
    if 'username' not in session:
        return redirect('/login')
    
    try:
        connection = get_db_connection()
        profile = connection.execute('''
            SELECT * FROM user_profiles 
            WHERE user_id = ? AND is_completed = TRUE
        ''', (session['user_id'],)).fetchone()
        connection.close()
    except Exception as e:
        print(f"Ошибка получения профиля: {e}")
        profile = None
    
    if not profile:
        flash('Ваше портфолио еще не проверено администратором или не заполнено.', 'warning')
        return redirect('/user')
    
    return render_template('view_portfolio.html', 
                         username=session['username'],
                         profile=profile)

@app.route('/user/generate_resume')
def generate_resume():
    if 'username' not in session:
        return redirect('/login')
    
    # Получаем данные профиля пользователя только если он завершен админом
    try:
        connection = get_db_connection()
        profile = connection.execute('''
            SELECT * FROM user_profiles 
            WHERE user_id = ? AND is_completed = TRUE
        ''', (session['user_id'],)).fetchone()
        connection.close()
    except Exception as e:
        print(f"Ошибка получения профиля: {e}")
        profile = None
    
    if not profile:
        flash('Ваше портфолио еще не проверено администратором или не заполнено.', 'warning')
        return redirect('/user')
    
    return render_template('resume.html', 
                         username=session['username'],
                         profile=profile,
                         now=datetime.now())

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    create_tables()
    port = int(os.environ.get('PORT', 5555))
    app.run(debug=True, host='0.0.0.0', port=port)
