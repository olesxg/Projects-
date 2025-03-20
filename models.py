"""
Модуль, що містить класи для представлення даних проспектів.
"""
from datetime import datetime
from typing import Dict, Any, Optional
import re


class Leaflet:
    """
    Клас для представлення проспекту супермаркету.
    """
    
    def __init__(
        self,
        title: str,
        thumbnail: str,
        shop_name: str,
        valid_from: str,
        valid_to: str,
        parsed_time: Optional[str] = None
    ):
        """
        Ініціалізація об'єкту проспекту.
        
        Args:
            title: Назва проспекту
            thumbnail: URL зображення-мініатюри проспекту
            shop_name: Назва магазину
            valid_from: Дата початку дії проспекту (формат YYYY-MM-DD)
            valid_to: Дата закінчення дії проспекту (формат YYYY-MM-DD)
            parsed_time: Час парсингу (опціонально, за замовчуванням - поточний час)
        """
        # Очищаємо дані від зайвих пробілів
        self.title = self._clean_string(title)
        self.thumbnail = thumbnail
        self.shop_name = self._clean_string(shop_name)
        
        # Переконуємося, що назва магазину не дорівнює заголовку
        if not self.shop_name or self.shop_name == self.title:
            # Спробуємо витягнути першу частину заголовку як назву магазину
            parts = self.title.split(" - ", 1)
            if len(parts) > 1:
                self.shop_name = parts[0]
            else:
                # Беремо перше слово з заголовку
                words = self.title.split()
                if words:
                    self.shop_name = words[0]
                else:
                    self.shop_name = "Unknown"
        
        # Перевіряємо, що дати мають правильний формат
        self.valid_from = self._validate_date(valid_from)
        self.valid_to = self._validate_date(valid_to)
        
        # Встановлюємо час парсингу
        if parsed_time:
            self.parsed_time = parsed_time
        else:
            self.parsed_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _clean_string(self, text: str) -> str:
        """
        Очищає текст від зайвих пробілів та інших символів.
        
        Args:
            text: Текст для очищення
            
        Returns:
            str: Очищений текст
        """
        if not text:
            return ""
        
        # Замінюємо множинні пробіли на один
        cleaned = re.sub(r'\s+', ' ', text.strip())
        # Видаляємо спеціальні символи
        cleaned = re.sub(r'[^\w\s\-&,.]', '', cleaned)
        return cleaned
    
    def _validate_date(self, date_str: str) -> str:
        """
        Перевіряє формат дати та виправляє його при необхідності.
        
        Args:
            date_str: Рядок з датою
            
        Returns:
            str: Валідна дата у форматі YYYY-MM-DD
        """
        # Перевіряємо, чи дата відповідає формату YYYY-MM-DD
        if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            try:
                # Перевіряємо, чи дата дійсна
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                current_year = datetime.now().year
                
                # Якщо рік дати більш ніж на 1 рік у майбутньому, виправляємо його
                if date_obj.year > current_year + 1:
                    return date_str.replace(str(date_obj.year), str(current_year))
                
                return date_str
            except ValueError:
                # Якщо дата недійсна, повертаємо поточну дату
                return datetime.now().strftime("%Y-%m-%d")
        else:
            # Якщо формат неправильний, повертаємо поточну дату
            return datetime.now().strftime("%Y-%m-%d")
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Конвертує об'єкт проспекту в словник для подальшого запису в JSON.
        
        Returns:
            Dict[str, Any]: Словник з даними проспекту
        """
        return {
            "title": self.title,
            "thumbnail": self.thumbnail,
            "shop_name": self.shop_name,
            "valid_from": self.valid_from,
            "valid_to": self.valid_to,
            "parsed_time": self.parsed_time
        } 