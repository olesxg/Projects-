"""
Модуль з утилітами для обробки дат та іншою допоміжною функціональністю.
"""
import re
import logging
from datetime import datetime
from typing import Tuple, Optional

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('prospekt_scraper')


def parse_date_range(date_text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Парсить текстовий діапазон дат у формат YYYY-MM-DD.
    
    Args:
        date_text: Текст з діапазоном дат, наприклад "13.03.2023 - 19.03.2023"
        
    Returns:
        Tuple[Optional[str], Optional[str]]: Кортеж (дата_початку, дата_закінчення)
        у форматі YYYY-MM-DD або None, якщо парсинг не вдався
    """
    try:
        # Отримуємо поточний рік
        current_year = datetime.now().year
        
        # Шукаємо всі дати у форматі DD.MM.YYYY в тексті
        date_pattern = r'(\d{2}\.\d{2}\.\d{4})'
        dates = re.findall(date_pattern, date_text)
        
        if len(dates) >= 2:
            # Перетворюємо дати з DD.MM.YYYY в YYYY-MM-DD
            from_date = datetime.strptime(dates[0], "%d.%m.%Y")
            to_date = datetime.strptime(dates[1], "%d.%m.%Y")
            
            # Перевіряємо, чи рік не в майбутньому (більш ніж на 1 рік)
            if from_date.year > current_year + 1 or to_date.year > current_year + 1:
                logger.warning(f"Виявлено дати з майбутнім роком: {dates[0]}, {dates[1]}. Використовую поточний рік.")
                # Замінюємо роки на поточний
                from_date = from_date.replace(year=current_year)
                to_date = to_date.replace(year=current_year)
            
            valid_from = from_date.strftime("%Y-%m-%d")
            valid_to = to_date.strftime("%Y-%m-%d")
            return valid_from, valid_to
        else:
            # Шукаємо дати у форматі DD.MM (без року)
            short_date_pattern = r'(\d{2}\.\d{2})'
            short_dates = re.findall(short_date_pattern, date_text)
            
            if len(short_dates) >= 2:
                # Додаємо поточний рік
                from_date = datetime.strptime(f"{short_dates[0]}.{current_year}", "%d.%m.%Y")
                to_date = datetime.strptime(f"{short_dates[1]}.{current_year}", "%d.%m.%Y")
                
                valid_from = from_date.strftime("%Y-%m-%d")
                valid_to = to_date.strftime("%Y-%m-%d")
                return valid_from, valid_to
                
            logger.warning(f"Не вдалося розпізнати дві дати у тексті: {date_text}")
            # Якщо не можемо розпізнати дати, використовуємо поточну дату для початку
            # і +7 днів для кінця (стандартна тривалість акцій)
            today = datetime.now()
            valid_from = today.strftime("%Y-%m-%d")
            valid_to = (today.replace(day=today.day+7)).strftime("%Y-%m-%d")
            return valid_from, valid_to
            
    except Exception as e:
        logger.error(f"Помилка при парсингу дат з тексту '{date_text}': {str(e)}")
        # У випадку помилки також повертаємо базові значення
        today = datetime.now()
        valid_from = today.strftime("%Y-%m-%d")
        valid_to = (today.replace(day=today.day+7)).strftime("%Y-%m-%d")
        return valid_from, valid_to


def validate_url(url: str) -> str:
    """
    Перевіряє і нормалізує URL.
    
    Args:
        url: URL для перевірки
        
    Returns:
        str: Нормалізований URL
    """
    if not url:
        return ""
        
    # Додаємо протокол, якщо він відсутній
    if url and not url.startswith(('http://', 'https://')):
        url = 'https:' + url if url.startswith('//') else 'https://' + url
        
    return url 