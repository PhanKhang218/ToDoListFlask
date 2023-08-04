from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os
app = Flask(__name__)
app.secret_key = 'aaaa'  

bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


class User(UserMixin):
    def __init__(self, id):
        self.id = id


@login_manager.user_loader
def load_user(user_id):
    return User(user_id)


def connect_db():
    return sqlite3.connect('tasks.db')

def create_tables():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_name TEXT NOT NULL,
        status TEXT NOT NULL,
        category TEXT,  
        user_id INTEGER, 
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
''')

    conn.commit()
    conn.close()

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        existing_user = cursor.fetchone()

        if existing_user:
            flash('Tên đăng nhập đã tồn tại. Vui lòng chọn tên đăng nhập khác.', 'error')
            conn.close()
            return redirect(url_for('register'))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
        conn.commit()
        conn.close()

        flash('Đăng ký thành công. Bạn có thể đăng nhập bằng tên đăng nhập và mật khẩu đã đăng ký.', 'success')
        return redirect(url_for('login'))
    else:
        return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = connect_db()
        cursor = conn.cursor()

        # Tìm người dùng dựa trên tên đăng nhập
        cursor.execute('SELECT id, password FROM users WHERE username = ?', (username,))
        user_data = cursor.fetchone()

        if user_data and bcrypt.check_password_hash(user_data[1], password):
            # Xác thực thành công, đăng nhập người dùng
            user = User(user_data[0])
            login_user(user)
            flash('Đăng nhập thành công!', 'success')
            conn.close()
            return redirect(url_for('index'))
        else:
            flash('Đăng nhập thất bại. Vui lòng kiểm tra lại tên đăng nhập và mật khẩu.', 'error')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Đăng xuất thành công.', 'success')
    return redirect(url_for('login'))


@app.route('/')
@login_required
def index():
    keyword = request.args.get('keyword')
    category = request.args.get('category')
    status = request.args.get('status')

    conn = connect_db()
    cursor = conn.cursor()

    query = 'SELECT * FROM tasks WHERE user_id = ?'
    params = (current_user.id,)

    if keyword:
        query += ' AND task_name LIKE ?'
        params += ('%' + keyword + '%',)

    if category and category != "None":  # Thêm điều kiện kiểm tra category có giá trị None hay không
        query += ' AND category = ?'
        params += (category,)

    if status:
        query += ' AND status = ?'
        params += (status,)

    cursor.execute(query, params)
    tasks = cursor.fetchall()

    cursor.execute('SELECT DISTINCT category FROM tasks WHERE user_id = ?', (current_user.id,))
    categories = cursor.fetchall()

    conn.close()

    return render_template('index.html', tasks=tasks, categories=categories)




@app.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        task_name = request.form['task_name']
        status = request.form['status']
        category = request.form.get('category')  

        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute('INSERT INTO tasks (task_name, status, category, user_id) VALUES (?, ?, ?, ?)',
                       (task_name, status, category, current_user.id))
        conn.commit()

        conn.close()

        return redirect(url_for('index'))
    else:
        return render_template('add.html')


@app.route('/edit/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit(task_id):
    if request.method == 'POST':
        task_name = request.form['task_name']
        status = request.form['status']

        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute('UPDATE tasks SET task_name = ?, status = ? WHERE id = ?', (task_name, status, task_id))
        conn.commit()

        conn.close()

        return redirect(url_for('index'))
    else:
        conn = connect_db()
        cursor = conn.cursor()

        # Lấy thông tin công việc từ cơ sở dữ liệu
        cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
        task = cursor.fetchone()

        conn.close()

        return render_template('edit.html', task=task)


@app.route('/delete/<int:task_id>')
@login_required
def delete(task_id):
    conn = connect_db()
    cursor = conn.cursor()

    # Xóa công việc khỏi cơ sở dữ liệu
    cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    conn.commit()

    conn.close()

    return redirect(url_for('index'))


if __name__ == '__main__':
    if not os.path.exists('database'):
        os.makedirs('database')

    create_tables()

    app.run(debug=True)
