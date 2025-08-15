import os
from flask import Flask, render_template, request, redirect, url_for
import mysql.connector
import dotenv
app = Flask(__name__)

dotenv.load_dotenv()

conn = mysql.connector.connect(
    host=os.environ.get("MYSQL_HOST", "localhost"),
    user=os.environ.get("MYSQL_USER", "root"),
    password=os.environ.get("MYSQL_PASSWORD", ""),
    database=os.environ.get("MYSQL_DATABASE", "slushies")
)
cursor = conn.cursor(dictionary=True)
priority_order = {'low': 0, 'medium': 1, 'high': 2}

def init_db():
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS todos (
        id INT AUTO_INCREMENT PRIMARY KEY,
        content VARCHAR(255) NOT NULL,
        completed BOOLEAN NOT NULL DEFAULT FALSE,
        priority VARCHAR(255) NOT NULL DEFAULT 'low',
        category_id INT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        edited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS categories (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        edited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()

with app.app_context():
    init_db()
    @app.errorhandler(404)
    def not_found(e):
        return render_template('404.html'), 404
    
    @app.route('/')
    def index():
        cursor.execute('SELECT * FROM todos')
        todos = cursor.fetchall()
        todos = sorted(todos, key=lambda x: priority_order.get(x['priority'], -99), reverse=True)
        cursor.execute('SELECT * FROM categories')
        categories = cursor.fetchall()

        return render_template('index.html', todos=todos, categories=categories)

    @app.route('/todo/create', methods=['POST','GET'])
    def create_todo():
        if request.method == 'GET':
            cursor.execute('SELECT * FROM categories')
            categories = cursor.fetchall()
            return render_template('create.html', categories=categories)
        content = request.form.get('content')
        priority = request.form.get('priority')
        category_id = request.form.get('category_id')
        if not priority or priority not in ['low', 'medium', 'high']:return "Invalid priority", 400
        if not content or not isinstance(content, str): return "Invalid input", 400
        if content.strip() == "": return "Content cannot be empty", 400
        if content.__len__() > 255: return "Content is too long", 400
        if category_id:
            cursor.execute('SELECT * FROM categories WHERE id = %s', (category_id,))
            category = cursor.fetchone()
            if not category: return "Invalid category ID",400
        cursor.execute('INSERT INTO todos (content, priority, category_id) VALUES (%s, %s, %s)', (
            content,
            priority,
            category_id
        ))
        conn.commit()
        return redirect(url_for('index'))

    @app.route('/todo/<int:id>', methods=['GET', 'POST'])
    def edit_todo(id):
        if request.method == 'POST':
            content = request.form.get('content')
            completed = request.form.get('completed')
            priority = request.form.get('priority')
            category_id = request.form.get('category_id')
            completed = True if completed == "on" else False
            if not priority or priority not in ['low', 'medium', 'high']: return "Invalid priority", 400
            if not content or not isinstance(content, str): return "Invalid input; content != string", 400

            if category_id:
                cursor.execute('SELECT * FROM categories WHERE id = %s', (category_id,))
                category = cursor.fetchone()
                if not category: return "Invalid category ID", 400

            if content.strip() == "": return "Content cannot be empty", 400
            if content.__len__() > 255: return "Content is too long", 400
            cursor.execute('UPDATE todos SET content = %s, completed = %s, priority = %s, category_id = %s WHERE id = %s', (content, completed, priority, category_id, id))
            conn.commit()
            return redirect(url_for('index'))
        cursor.execute('SELECT * FROM todos WHERE id = %s', (id,))
        todo = cursor.fetchone()
        if not todo: return "Todo not found", 404

        cursor.execute('SELECT * FROM categories')
        categories = cursor.fetchall()

        return render_template('view.html', todo=todo, categories=categories)

    @app.route('/todo/<int:id>', methods=["DELETE"])
    def delete_todo(id):
        cursor.execute('DELETE FROM todos WHERE id = %s', (id,))
        conn.commit()
        return redirect(url_for('index'))

    @app.route('/todos/bulk-delete', methods=["POST"])
    def bulk_delete_todos():
        ids = request.form.getlist('ids')
        if not ids: return "No IDs provided", 400
        
        if not all(
            isinstance(i,str)
            and
            i.isdigit()
            for i in ids
        ): return "invalid ids provided",400

        cursor.execute('SELECT COUNT(*) AS cnt FROM todos WHERE id IN (%s)' % ','.join(['%s'] * len(ids)), tuple(ids))
        result = cursor.fetchone()
        find_length = result['cnt'] if result else 0
        if find_length != len(ids): return "Some IDs not found", 404

        cursor.execute('DELETE FROM todos WHERE id IN (%s)' % ','.join(['%s'] * len(ids)), tuple(ids))
        conn.commit()
        return redirect(url_for('index'))

    @app.route('/todos/bulk-complete', methods=["POST"])
    def bulk_complete_todos():
        ids = request.form.getlist('ids')
        if not ids: return "No ids provided", 400

        if not all(
            isinstance(i,str)
            and
            i.isdigit()
            for i in ids
        ): return "invalid ids provided",400
    
        cursor.execute('SELECT COUNT(*) AS cnt FROM todos WHERE id IN (%s)' % ','.join(['%s'] * len(ids)), tuple(ids))
        result = cursor.fetchone()
        find_length = result['cnt'] if result else 0
        if find_length != len(ids): return "Some IDs not found", 404

        cursor.execute('UPDATE todos SET completed = TRUE WHERE id IN (%s)' % ','.join(['%s'] * len(ids)), tuple(ids))
        conn.commit()
        return redirect(url_for('index'))
    
    @app.route('/category/create', methods=['POST','GET'])
    def create_category():
        if request.method == 'POST':
            name = request.form.get('name')
            if not name or not isinstance(name, str): return "Invalid input; name != string", 400
            if name.strip() == "": return "Name cannot be empty", 400
            if name.__len__() > 24: return "Name is too long", 400
            cursor.execute('INSERT INTO categories (name) VALUES (%s)', (name,))
            conn.commit()
            return redirect(url_for('index'))
        return render_template('category.html')
    
    @app.route('/category/<int:id>', methods=['DELETE'])
    def delete_category(id):
        cursor.execute('DELETE FROM categories WHERE id = %s', (id,))
        conn.commit()
        cursor.execute('UPDATE todos SET category_id = NULL WHERE category_id = %s', (id,))
        conn.commit()
        return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=False, port=int(os.environ.get("PORT", 5000)))