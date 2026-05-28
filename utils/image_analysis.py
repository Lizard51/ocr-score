import cv2
import numpy as np


def analyze_image(image_path):
    """
    Анализ изображения: вычисление контрастности и резкости.
    
    Возвращает:
        contrast (float): контрастность как стандартное отклонение интенсивности
        sharpness (float): резкость через дисперсию лапласиана
    """
    # Загрузка изображения в оттенках серого
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Не удалось загрузить изображение: {image_path}")
    
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Контрастность: стандартное отклонение интенсивности пикселей
    contrast = np.std(gray)
    
    # Резкость: дисперсия лапласиана
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    sharpness = np.var(laplacian)
    
    return contrast, sharpness


def calculate_ocr_score(contrast, sharpness):
    """
    Вычисление итоговой оценки пригодности для OCR (от 1 до 10).
    
    Параметры:
        contrast: стандартное отклонение интенсивности (обычно 0-100)
        sharpness: дисперсия лапласиана (может быть от 0 до нескольких тысяч)
    
    Возвращает:
        score (int): оценка от 1 до 10
    """
    # Нормализация контраста (0-100 -> 0-1)
    # Типичные значения: 10-80 для большинства изображений
    contrast_normalized = min(max(contrast / 80.0, 0), 1)
    
    # Нормализация резкости
    # Типичные значения: 50-1000 для обычных изображений
    # Значения > 500 считаются хорошими
    sharpness_normalized = min(max(sharpness / 500.0, 0), 1)
    
    # Взвешенная средняя: резкость важнее для OCR
    # Резкость имеет вес 60%, контраст 40%
    combined_score = 0.4 * contrast_normalized + 0.6 * sharpness_normalized
    
    # Преобразование в шкалу 1-10
    score = int(round(combined_score * 9 + 1))
    
    # Ограничение диапазона 1-10
    return max(1, min(10, score))
