from flask import Flask, render_template, request, redirect, url_for
import mysql.connector
app = Flask(__name__)
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="slushies"
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
        return render_template('index.html', todos=todos)
    
    @app.route('/todo/create', methods=['POST','GET'])
    def create_todo():
        if request.method == 'GET':
            return render_template('create.html')
        content = request.form.get('content')
        priority = request.form.get('priority')
        if not priority or priority not in ['low', 'medium', 'high']:return "Invalid priority", 400
        if not content or not isinstance(content, str): return "Invalid input", 400
        if content.strip() == "": return "Content cannot be empty", 400
        if content.__len__() > 255: return "Content is too long", 400
        cursor.execute('INSERT INTO todos (content, priority) VALUES (%s, %s)', (
            content,
            priority
        ))
        conn.commit()
        return redirect(url_for('index'))

    @app.route('/todo/<int:id>', methods=['GET', 'POST'])
    def edit_todo(id):
        if request.method == 'POST':
            content = request.form.get('content')
            completed = request.form.get('completed')
            priority = request.form.get('priority')
            completed = True if completed == "on" else False
            if not priority or priority not in ['low', 'medium', 'high']: return "Invalid priority", 400
            if not content or not isinstance(content, str): return "Invalid input; content != string", 400
            if content.strip() == "": return "Content cannot be empty", 400
            if content.__len__() > 255: return "Content is too long", 400
            cursor.execute('UPDATE todos SET content = %s, completed = %s, priority = %s WHERE id = %s', (content, completed, priority, id))
            conn.commit()
            return redirect(url_for('index'))
        cursor.execute('SELECT * FROM todos WHERE id = %s', (id,))
        todo = cursor.fetchone()
        if not todo: return "Todo not found", 404
        return render_template('view.html', todo=todo)
    
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

if __name__ == '__main__':
    app.run(debug=True, port=5000)