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

    # Tạo bảng users nếu chưa tồn tại
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    # Tạo bảng tasks nếu chưa tồn tại
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_name TEXT NOT NULL,
            status TEXT NOT NULL
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

        # Kiểm tra xem tên đăng nhập đã tồn tại chưa
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        existing_user = cursor.fetchone()

        if existing_user:
            flash('Tên đăng nhập đã tồn tại. Vui lòng chọn tên đăng nhập khác.', 'error')
            conn.close()
            return redirect(url_for('register'))

        # Mã hóa mật khẩu trước khi lưu vào cơ sở dữ liệu
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        # Thêm người dùng mới vào cơ sở dữ liệu
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
    conn = connect_db()
    cursor = conn.cursor()

    # Lấy danh sách công việc từ cơ sở dữ liệu
    cursor.execute('SELECT * FROM tasks')
    tasks = cursor.fetchall()

    # Đóng kết nối cơ sở dữ liệu
    conn.close()

    return render_template('index.html', tasks=tasks)


@app.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        task_name = request.form['task_name']
        status = request.form['status']

        conn = connect_db()
        cursor = conn.cursor()

        # Thêm công việc vào cơ sở dữ liệu
        cursor.execute('INSERT INTO tasks (task_name, status) VALUES (?, ?)', (task_name, status))
        conn.commit()

        # Đóng kết nối cơ sở dữ liệu
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

        # Cập nhật thông tin công việc trong cơ sở dữ liệu
        cursor.execute('UPDATE tasks SET task_name = ?, status = ? WHERE id = ?', (task_name, status, task_id))
        conn.commit()

        # Đóng kết nối cơ sở dữ liệu
        conn.close()

        return redirect(url_for('index'))
    else:
        conn = connect_db()
        cursor = conn.cursor()

        # Lấy thông tin công việc từ cơ sở dữ liệu
        cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
        task = cursor.fetchone()

        # Đóng kết nối cơ sở dữ liệu
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

    # Đóng kết nối cơ sở dữ liệu
    conn.close()

    return redirect(url_for('index'))


if __name__ == '__main__':
    # Kiểm tra và tạo thư mục lưu trữ CSDL nếu chưa tồn tại
    if not os.path.exists('database'):
        os.makedirs('database')

    # Tạo bảng users và tasks nếu chưa tồn tại
    create_tables()

    app.run(debug=True)
