#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import logging
import sys
import json
from datetime import datetime

from scraper import LeafletScraper
from exporters import export_to_json, export_to_javascript

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

def main():
    # Парсинг аргументів командного рядка
    parser = argparse.ArgumentParser(description='Скрапер проспектів з сайту')
    parser.add_argument('-o', '--output', type=str, default='./output.json', help='Шлях до вихідного файлу')
    parser.add_argument('-v', '--verbose', action='store_true', help='Детальний вивід')
    args = parser.parse_args()
    
    # Налаштування рівня логування
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Створення скрапера
    scraper = LeafletScraper(verbose=args.verbose)
    
    try:
        # Отримання проспектів
        leaflets = scraper.get_leaflets()
        
        if not leaflets:
            logger.error("Не вдалося отримати проспекти")
            return 1
        
        # Додавання часу парсингу
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for leaflet in leaflets:
            if "parsed_time" not in leaflet:
                leaflet["parsed_time"] = timestamp
        
        # Експорт даних
        output_path = args.output
        output_js_path = output_path.replace('.json', '.js') if output_path.endswith('.json') else output_path + '.js'
        
        # Експорт в JSON
        export_to_json(leaflets, output_path)
        logger.info(f"Дані успішно експортовано в {output_path}")
        
        # Експорт в JavaScript
        export_to_javascript(leaflets, output_js_path)
        logger.info(f"Дані успішно експортовано в {output_js_path}")
        
        return 0
    
    except Exception as e:
        logger.error(f"Помилка при виконанні скрапінгу: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 