import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, g, send_from_directory
from werkzeug.utils import secure_filename
from utils.image_analysis import analyze_image, calculate_ocr_score

app = Flask(__name__)

# Конфигурация
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Максимум 16 МБ
app.config['DATABASE'] = 'database.db'

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'webp'}

def allowed_file(filename):
    """Проверка расширения файла."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_db():
    """Получение соединения с базой данных."""
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    """Закрытие соединения с БД после запроса."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """Инициализация базы данных."""
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analysis_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            image_path TEXT NOT NULL,
            contrast REAL NOT NULL,
            sharpness REAL NOT NULL,
            ocr_score INTEGER NOT NULL,
            explanation TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()


@app.route('/')
def index():
    """Главная страница с формой загрузки."""
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """Обработка загруженного изображения."""
    if 'file' not in request.files:
        return redirect(url_for('index'))
    
    file = request.files['file']
    
    if file.filename == '':
        return redirect(url_for('index'))
    
    if not allowed_file(file.filename):
        return render_template('index.html', error='Недопустимый формат файла. Разрешены: PNG, JPG, JPEG, BMP, TIFF, WEBP')
    
    # Сохранение файла
    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
    unique_filename = timestamp + filename
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    file.save(image_path)
    
    # Анализ изображения
    try:
        contrast, sharpness = analyze_image(image_path)
        ocr_score = calculate_ocr_score(contrast, sharpness)
        explanation = generate_explanation(contrast, sharpness, ocr_score)
        
        # Сохранение результатов в БД
        db = get_db()
        db.execute(
            '''INSERT INTO analysis_results (filename, image_path, contrast, sharpness, ocr_score, explanation)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (filename, image_path, contrast, sharpness, ocr_score, explanation)
        )
        db.commit()
        
        return render_template('index.html', 
                               result={
                                   'filename': filename,
                                   'image_path': image_path,
                                   'contrast': contrast,
                                   'sharpness': sharpness,
                                   'ocr_score': ocr_score,
                                   'explanation': explanation
                               })
    except Exception as e:
        return render_template('index.html', error=f'Ошибка при анализе изображения: {str(e)}')


def generate_explanation(contrast, sharpness, ocr_score):
    """Генерация текстового пояснения результатов."""
    parts = []
    
    # Оценка контраста
    if contrast > 70:
        parts.append("Изображение имеет отличный контраст")
    elif contrast > 40:
        parts.append("Изображение имеет хороший контраст")
    elif contrast > 20:
        parts.append("Изображение имеет умеренный контраст")
    else:
        parts.append("Изображение имеет низкий контраст")
    
    # Оценка резкости
    if sharpness > 500:
        parts.append("и высокую резкость")
    elif sharpness > 200:
        parts.append("и хорошую резкость")
    elif sharpness > 100:
        parts.append("и умеренную резкость")
    else:
        parts.append("и низкую резкость")
    
    # Рекомендации
    recommendations = []
    if contrast < 30:
        recommendations.append("рекомендуется увеличить контрастность")
    if sharpness < 150:
        recommendations.append("рекомендуется улучшить резкость (убрать размытие)")
    
    explanation = ", ".join(parts) + f". Оценка пригодности для OCR: {ocr_score}/10"
    
    if recommendations:
        explanation += ". " + "; ".join(recommendations).capitalize() + "."
    
    return explanation


@app.route('/history')
def history():
    """Страница истории анализов."""
    db = get_db()
    results = db.execute(
        'SELECT * FROM analysis_results ORDER BY created_at DESC'
    ).fetchall()
    return render_template('history.html', results=results)


@app.route('/delete/<int:id>', methods=['POST'])
def delete_result(id):
    """Удаление записи из истории."""
    db = get_db()
    db.execute('DELETE FROM analysis_results WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('history'))


@app.route('/uploads/<path:filename>')
def serve_image(filename):
    """Отдача изображений из папки uploads."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if __name__ == '__main__':
    # Создание папки для загрузок, если не существует
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Инициализация БД
    init_db()
    
    # Запуск приложения
    app.run(debug=True, host='0.0.0.0', port=5000)
