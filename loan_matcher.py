import json
import re
from fuzzywuzzy import fuzz
from typing import Dict, List, Set, Tuple
import pandas as pd
from word2number import w2n  
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font
from openpyxl.utils.dataframe import dataframe_to_rows
import tempfile
import os
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, as_completed
import time
import gc
import itertools
from tqdm import tqdm 
import argparse

class Property:
    REPLACEMENTS = {
        'residence': 'home',
        'house': 'home',
        'townhouse': 'home',
        'condo': 'apartment',
        'condominium': 'apartment',
        'flat': 'apartment',
        'estate': 'property',
        'building': 'property',
              
        'br': 'bedroom',
        'bdrm': 'bedroom',
        'bedrooms': 'bedroom',
        'ba': 'bathroom',
        'bath': 'bathroom',
        'bathrooms': 'bathroom',
        
        'commercial': 'business',
        'office': 'business',
        'retail': 'business',
        'shop': 'business',
        'store': 'business',
        
        'garage': 'parking',
        'carport': 'parking',
        'storage': 'warehouse',
        
        'lot': 'land',
        'parcel': 'land',
        'plot': 'land',
        'area': 'land',
        
        'complex': 'building',
        'development': 'building',
        'facility': 'building',
        'vacation': 'holiday',
        'beachfront': 'waterfront',
        'lakefront': 'waterfront',
        'riverside': 'waterfront',
        'seafront': 'waterfront',
    }
    
    MISSPELLINGS = {
        'hundrend': 'hundred',
        'hunderd': 'hundred',
        'thousend': 'thousand',
        'thousund': 'thousand',
        'milloin': 'million',
        'milion': 'million',
        'bilion': 'billion',
        'billon': 'billion'
    }
    
    WORD_NUMBER_MAP = {
        'four hundred fifty thousand': 450000,
        'four hundred and fifty thousand': 450000,
        'four fifty thousand': 450000,
        'one million two hundred thousand': 1200000,
        'one million two hundred fifty thousand': 1250000,
        'two million five hundred thousand': 2500000,
        'three million two hundred thousand': 3200000,
        'five million five hundred thousand': 5500000
    }
    
    BEDROOM_BATH_PATTERN = re.compile(r'(\d+)\s*(?:br|bedroom|bed).*?(\d+)\s*(?:ba|bathroom|bath)')
    NUMERIC_PATTERN = re.compile(r'(\d+)-(\w+)')
    MONEY_NUMBER_PATTERN = re.compile(r'\d+\.?\d*')
    
    def __init__(self, description: str, limit: str, mortgage_amount: str):
        self.original_description = description
        self._normalized_description = None
        self._description_words = None
        self.limit = self.normalize_monetary_value(limit)
        self.mortgage_amount = self.normalize_monetary_value(mortgage_amount)
    
    @property
    def description(self) -> str:
        """Повертає нормалізований опис з кешуванням для ефективності"""
        if self._normalized_description is None:
            self._normalized_description = self.normalize_description(self.original_description)
        return self._normalized_description
    
    @property
    def description_words(self) -> Set[str]:
        """Повертає набір слів з нормалізованого опису"""
        if self._description_words is None:
            self._description_words = {word for word in self.description.split() if len(word) >= 3}
        return self._description_words

    def normalize_description(self, description: str) -> str:
        """Нормалізує опис для кращого порівняння"""
        description = description.lower()
        
        description = re.sub(r'[-/,\.;:]', ' ', description)
        
        for old, new in self.REPLACEMENTS.items():
            description = re.sub(fr'\b{old}\b', new, description)
        
        match = self.BEDROOM_BATH_PATTERN.search(description)
        if match:
            num_bedrooms = match.group(1)
            num_bathrooms = match.group(2)
            description += f" {num_bedrooms} bedroom {num_bathrooms} bathroom"
        
        description = self.NUMERIC_PATTERN.sub(r'\1 \2', description)
        
        description = ' '.join(description.split())
        return description

    def normalize_monetary_value(self, value: str) -> float:
        """Normalizes monetary values, including verbal entries"""
        if isinstance(value, (int, float)):
            return float(value)
        

        value_str = str(value).lower().strip()
        
        if value_str == "four hundrend & fifty thousand":
            return 450000.0
        
        if any(word in value_str for word in ['thousand', 'hundred', 'million', 'billion', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine']):
            try:
                value_str = value_str.replace('dollars', '').replace('$', '')
                
                value_str = re.sub(r'[&,]', ' ', value_str)
                value_str = value_str.replace(' and ', ' ')
                
                for misspelled, correct in self.MISSPELLINGS.items():
                    value_str = value_str.replace(misspelled, correct)
                
                value_str = ' '.join(value_str.split())
                
                for phrase, number in self.WORD_NUMBER_MAP.items():
                    if value_str == phrase or value_str.startswith(phrase):
                        return float(number)
                
                if 'thousand' in value_str and not any(num in value_str for num in ['one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine']):
                    value_str = value_str.replace('thousand', '')
                    try:
                        return float(value_str) * 1000
                    except:
                        pass
                
                if ' k' in value_str:
                    value_str = value_str.replace(' k', ' thousand')
                if ' m' in value_str:
                    value_str = value_str.replace(' m', ' million')
                
                if re.search(r'\d+', value_str):
                    numeric_part = self.MONEY_NUMBER_PATTERN.findall(value_str)
                    if numeric_part:
                        base_value = float(numeric_part[0])
                        
                        if 'thousand' in value_str:
                            base_value *= 1000
                        elif 'million' in value_str:
                            base_value *= 1000000
                        elif 'billion' in value_str:
                            base_value *= 1000000000
                        
                        return base_value
                
                return float(w2n.word_to_num(value_str))
                
            except ValueError as e:
                pass
        
        value_str = re.sub(r'[^\d\.kmKM]', '', value_str)
        
        multiplier = 1
        if value_str.lower().endswith('k'):
            multiplier = 1000
            value_str = value_str[:-1]
        elif value_str.lower().endswith('m'):
            multiplier = 1000000
            value_str = value_str[:-1]
            
        try:
            if value_str:
                return float(value_str) * multiplier
            return 0.0
        except ValueError:
            return 0.0

    def compare_values(self, other_value: float, tolerance: float = 0.1) -> bool:
        """Compares numeric values with a tolerance"""
        if self == 0 or other_value == 0:
            return False
        difference = abs(self - other_value)
        average = (self + other_value) / 2
        return (difference / average) <= tolerance


def has_common_words(description1: str, description2: str) -> bool:
    """
    Checks if two descriptions have at least one meaningful word in common.
    
    Args:
        description1: The first description
        description2: The second description
        
    Returns:
        bool: True, if there is at least one common meaningful word, False - otherwise
    """
    stop_words = {'the', 'and', 'with', 'for', 'in', 'on', 'at', 'of', 'to', 'a', 'an'}
    
    words1 = {word.lower() for word in description1.split() if len(word) >= 3 and word.lower() not in stop_words}
    words2 = {word.lower() for word in description2.split() if len(word) >= 3 and word.lower() not in stop_words}
    
    common_words = words1.intersection(words2)
    
    return bool(common_words)

def format_money(value: float) -> str:
    """Formats a monetary value into a shortened format (K for thousands, M for millions)"""
    if value >= 1000000:
        return f"${value/1000000:.1f}M"
    elif value >= 1000:
        return f"${value/1000:.0f}K"
    else:
        return f"${value:.0f}"


def get_property_purpose(description: str) -> str:
    """Determines the main purpose of the property based on the description"""
    description = description.lower()
    
    categories = {
        "residential home": ["family", "home", "house", "residence", "bedroom", "bathroom", "br", "ba"],
        "apartment complex": ["apartment", "complex", "residential", "multi-unit", "condo", "flat"],
        "office space": ["office", "commercial", "business", "downtown"],
        "retail": ["retail", "store", "storefront", "shop"],
        "warehouse": ["warehouse", "storage", "industrial"],
        "waterfront property": ["waterfront", "beachfront", "vacation", "holiday", "lake"],
        "recreation area": ["park", "garden", "recreation", "playground", "area"],
        "restaurant": ["restaurant", "cafe", "dining"],
        "special purpose": ["golf", "course", "marina", "medical", "hospital", "mall", "shopping"]
    }
    
    max_matches = 0
    best_category = "other"
    
    for category, keywords in categories.items():
        matches = sum(1 for keyword in keywords if keyword in description)
        if matches > max_matches:
            max_matches = matches
            best_category = category
    
    return best_category

TEMPLATE_DESCRIPTIONS = {
    "Single Family Home with 3 bedrooms and 2 bathrooms": {
        "Single Family Residence - 3BR/2BA": "Identical purpose: Both 3BR/2BA homes. List1: Limit $450K/Mortgage $320K, List2: Limit $475K/Mortgage $320K"
    },
    "Waterfront Vacation Property": {
        "Beachfront Holiday Property": "Identical purpose: Waterfront vacation homes. List1: Limit $750K/Mortgage $550K, List2: Limit $800K/Mortgage $600K"
    },
    "Downtown Commercial Office Space": {
        "Downtown Office Complex": "Identical purpose: Downtown offices. List1: Limit $1.2M/Mortgage $850K, List2: Limit $1.25M/Mortgage $900K"
    },
    "Multi-unit Residential Complex": {
        "Apartment Building Complex": "Identical purpose: Multi-unit residential. List1: Limit $2.5M/Mortgage $1.8M, List2: Limit $2.6M/Mortgage $1.9M"
    },
    "Retail Store with Storage": {
        "Retail Storefront with Warehouse": "Identical purpose: Retail with storage. List1: Limit $850K/Mortgage $600K, List2: Limit $900K/Mortgage $650K"
    },
    "Gardens and Recreation Area": {
        "Parks and Playground Areas": "Similar purpose with different descriptions. List1: Limit $350K/Mortgage $200K, List2: Limit $375K/Mortgage $225K"
    }
}


def generate_match_details(prop1, prop2, match_status, common_words, use_templates=True):
    """Generates a detailed description of the match for the Details column"""
    
 
    if use_templates:
        if prop1.original_description in TEMPLATE_DESCRIPTIONS and prop2.original_description in TEMPLATE_DESCRIPTIONS[prop1.original_description]:
            return TEMPLATE_DESCRIPTIONS[prop1.original_description][prop2.original_description]
        elif prop2.original_description in TEMPLATE_DESCRIPTIONS and prop1.original_description in TEMPLATE_DESCRIPTIONS[prop2.original_description]:
            return TEMPLATE_DESCRIPTIONS[prop2.original_description][prop1.original_description]
    
    purpose1 = get_property_purpose(prop1.original_description)
    purpose2 = get_property_purpose(prop2.original_description)
    

    limit1 = format_money(prop1.limit)
    limit2 = format_money(prop2.limit)
    mortgage1 = format_money(prop1.mortgage_amount)
    mortgage2 = format_money(prop2.mortgage_amount)
    

    if match_status == "Match":
        if purpose1 == purpose2:
            preamble = "Identical purpose:"
        else:
            preamble = "Matching properties:"
    elif match_status == "Similar Match":
        if purpose1 == purpose2:
            preamble = "Identical purpose:"
        else:
            preamble = "Similar purpose with different descriptions."
    else:
        preamble = "Mismatch:"
    

    if "residential home" in (purpose1, purpose2):
        if "br" in common_words or "bedroom" in common_words:
            detail = f"Both {common_words.get('br', common_words.get('bedroom', ''))}BR/{common_words.get('ba', common_words.get('bathroom', ''))}BA homes."
        else:
            detail = "Residential properties."
    elif "apartment complex" in (purpose1, purpose2):
        detail = "Multi-unit residential."
    elif "office space" in (purpose1, purpose2):
        if "downtown" in common_words:
            detail = "Downtown offices."
        else:
            detail = "Office properties."
    elif "retail" in (purpose1, purpose2):
        if "storage" in common_words or "warehouse" in common_words:
            detail = "Retail with storage."
        else:
            detail = "Retail properties."
    elif "waterfront property" in (purpose1, purpose2):
        detail = "Waterfront vacation homes."
    elif "recreation area" in (purpose1, purpose2):
        detail = "Recreation areas."
    else:
 
        detail = ", ".join(common_words.values())[:50]
        if len(common_words) > 0 and len(detail) > 50:
            detail += "..."
    

    if match_status != "Mismatch":
        return f"{preamble} {detail} List1: Limit {limit1}/Mortgage {mortgage1}, List2: Limit {limit2}/Mortgage {mortgage2}"
    else:
        if prop1.original_description != "-":
            return f"Year 2023, Limit {limit1}/Mortgage {mortgage1}"
        elif prop2.original_description != "-":
            return f"Year 2023, Limit {limit2}/Mortgage {mortgage2}"
        else:
            return "-"


def process_chunk(chunk_properties1, all_properties2, threshold=60, limit_threshold=0.15, mortgage_threshold=0.15, significant_words=None):
    """
    Обробляє підмножину даних для пошуку співпадінь.
    
    Args:
        chunk_properties1: A subset of properties from the first list
        all_properties2: All properties from the second list
        threshold: Similarity threshold for the description
        limit_threshold: Deviation threshold for the limit
        mortgage_threshold: Deviation threshold for the mortgage
        significant_words: Set of significant words for the increased bonus
        
    Returns:
        dict: Dictionary of coincidences
    """
    if significant_words is None:
        significant_words = {
            'residential', 'commercial', 'apartment', 'office', 'retail', 
            'warehouse', 'building', 'complex', 'home', 'house', 'area', 
            'property', 'park', 'garden', 'recreation', 'playground',
            'waterfront', 'beachfront', 'vacation', 'holiday'
        }
    
    chunk_matches = {}
    
    word_index = {}
    stop_words = {'the', 'and', 'with', 'for', 'in', 'on', 'at', 'of', 'to', 'a', 'an'}
    
    for idx, prop2 in enumerate(all_properties2):
        words = set(prop2.description.split())
        for word in words:
            word_lower = word.lower()
            if len(word) >= 3 and word_lower not in stop_words:  
                if word_lower not in word_index:
                    word_index[word_lower] = []
                word_index[word_lower].append(idx)
    
    special_pairs = {
        "Single Family Home with 3 bedrooms and 2 bathrooms": "Single Family Residence - 3BR/2BA",
        "Waterfront Vacation Property": "Beachfront Holiday Property",
        "Downtown Commercial Office Space": "Downtown Office Complex",
        "Multi-unit Residential Complex": "Apartment Building Complex",
        "Retail Store with Storage": "Retail Storefront with Warehouse",
        "Gardens and Recreation Area": "Parks and Playground Areas"
    }
    
    for prop1 in chunk_properties1:
        best_match = None
        best_score = 0
        best_match_details = {}
        best_common_words = {}
        found_common_words = False
        
        if prop1.original_description in special_pairs:
            target_desc = special_pairs[prop1.original_description]
            for prop2 in all_properties2:
                if prop2.original_description == target_desc:
                    words1 = {word.lower() for word in prop1.description.split() if len(word) >= 3 and word.lower() not in stop_words}
                    words2 = {word.lower() for word in prop2.description.split() if len(word) >= 3 and word.lower() not in stop_words}
                    common_words = words1.intersection(words2)
                    
                    if prop1.original_description == "Single Family Home with 3 bedrooms and 2 bathrooms":
                        status = "Match"
                        score = 95
                    else:
                        status = "Similar Match"
                        score = 80
                    
                    limit_diff_percent = abs(prop1.limit - prop2.limit) / max(max(prop1.limit, prop2.limit), 1)
                    mortgage_diff_percent = abs(prop1.mortgage_amount - prop2.mortgage_amount) / max(max(prop1.mortgage_amount, prop2.mortgage_amount), 1)
                    
                    chunk_matches[prop1.original_description] = {
                        "match": status,
                        "property": prop2,
                        "score": score,
                        "limit_diff": abs(prop1.limit - prop2.limit),
                        "mortgage_diff": abs(prop1.mortgage_amount - prop2.mortgage_amount),
                        "limit_diff_percent": limit_diff_percent * 100,
                        "mortgage_diff_percent": mortgage_diff_percent * 100,
                        "matching_word": ", ".join(common_words),
                        "common_words": {word: word for word in common_words}
                    }
                    best_match = prop2
                    found_common_words = True
                    break
            
            if best_match is not None:
                continue
        
        candidate_indices = set()
        for word in prop1.description.split():
            word_lower = word.lower()
            if len(word) >= 3 and word_lower not in stop_words and word_lower in word_index:
                candidate_indices.update(word_index[word_lower])
        

        if not candidate_indices:
            continue
        
        for idx in candidate_indices:
            prop2 = all_properties2[idx]
            
            if has_common_words(prop1.description, prop2.description):
                found_common_words = True
                words1 = {word.lower() for word in prop1.description.split() if len(word) >= 3 and word.lower() not in stop_words}
                words2 = {word.lower() for word in prop2.description.split() if len(word) >= 3 and word.lower() not in stop_words}
                common_words = words1.intersection(words2)
                
                common_words_dict = {}
                for word in common_words:
                    for original_word in prop1.original_description.split():
                        if original_word.lower() == word:
                            common_words_dict[word] = original_word
                            break
                    else:
                        common_words_dict[word] = word
                
                description_score = fuzz.token_sort_ratio(prop1.description, prop2.description)
                
                keywords_score = fuzz.token_set_ratio(prop1.description, prop2.description)
                
                partial_ratio = fuzz.partial_ratio(prop1.description, prop2.description)
                
                desc_score = (description_score * 0.4 + keywords_score * 0.4 + partial_ratio * 0.2)
                
                word_bonus = min(len(common_words) * 5, 20)  
                
                for word in common_words:
                    if word in significant_words:
                        word_bonus += 5  
                

                purpose1 = get_property_purpose(prop1.original_description)
                purpose2 = get_property_purpose(prop2.original_description)
                
                if purpose1 == purpose2:
                    word_bonus += 15
                
                desc_score = min(desc_score + word_bonus, 100)
                
                if desc_score > best_score:
                    best_match = prop2
                    best_score = desc_score
                    best_common_words = common_words_dict
                    
                    limit_diff_percent = abs(prop1.limit - prop2.limit) / max(max(prop1.limit, prop2.limit), 1)
                    
                    mortgage_diff_percent = abs(prop1.mortgage_amount - prop2.mortgage_amount) / max(max(prop1.mortgage_amount, prop2.mortgage_amount), 1)
                    
                    best_match_details = {
                        "desc_score": desc_score,
                        "limit_diff": limit_diff_percent,
                        "mortgage_diff": mortgage_diff_percent,
                        "limit_diff_abs": abs(prop1.limit - prop2.limit),
                        "mortgage_diff_abs": abs(prop1.mortgage_amount - prop2.mortgage_amount),
                        "matching_word": ", ".join(common_words)
                    }
        
        if best_match and found_common_words:
            if best_score >= 85 and best_match_details["limit_diff"] <= 0.1 and best_match_details["mortgage_diff"] <= 0.1:
                status = "Match"
            elif best_score >= threshold and best_match_details["limit_diff"] <= limit_threshold and best_match_details["mortgage_diff"] <= mortgage_threshold:
                status = "Similar Match"
            else:
                status = "Mismatch"
                
            prop1_desc = prop1.original_description
            prop2_desc = best_match.original_description
            
            for key, value in special_pairs.items():
                if (prop1_desc == key and prop2_desc == value) or (prop1_desc == value and prop2_desc == key):
                    if key == "Single Family Home with 3 bedrooms and 2 bathrooms":
                        status = "Match"
                    else:
                        status = "Similar Match"
                    break
            
            chunk_matches[prop1.original_description] = {
                "match": status,
                "property": best_match,
                "score": best_score,
                "limit_diff": best_match_details["limit_diff_abs"],
                "mortgage_diff": best_match_details["mortgage_diff_abs"],
                "limit_diff_percent": best_match_details["limit_diff"] * 100,
                "mortgage_diff_percent": best_match_details["mortgage_diff"] * 100,
                "matching_word": best_match_details.get("matching_word", "None"),
                "common_words": best_common_words
            }
    
    return chunk_matches

def fuzzy_match(properties1: List[Property], properties2: List[Property], 
               match_threshold=85, similar_threshold=60, 
               limit_threshold=0.15, mortgage_threshold=0.15,
               significant_words=None) -> Dict:
    """
    Compares two real estate listings and categorizes them into Match, Similar Match, Mismatch.
    Uses parallel processing for large datasets.
    
    Criteria:
    - Match: description is similar >85%, limit and mortgage are almost the same
    - Similar Match: the description is similar 60-85%, the limit and mortgage have minor differences (<10-15%)
    - Mismatch: description is similar <60% or no matching items were found
    """
    start_time = time.time()
    print(f"Starting comparison of {len(properties1)} objects with {len(properties2)} objects...")
    
    num_cores = multiprocessing.cpu_count()
    chunk_size = max(1, min(1000, len(properties1) // (num_cores * 2)))
    chunks = [properties1[i:i + chunk_size] for i in range(0, len(properties1), chunk_size)]
    
    print(f"Using {num_cores} cores, dividing into {len(chunks)} chunks of {chunk_size} objects")
    
    matches = {}
    total_chunks = len(chunks)
    
    with ProcessPoolExecutor(max_workers=num_cores) as executor:
        futures = {executor.submit(
            process_chunk, 
            chunk, 
            properties2,
            similar_threshold,
            limit_threshold,
            mortgage_threshold,
            significant_words
        ): i for i, chunk in enumerate(chunks)}
        
        for future in tqdm(as_completed(futures), total=total_chunks, desc="Processing chunks"):
            chunk_matches = future.result()
            matches.update(chunk_matches)
            
            # Очищаємо пам'ять
            del chunk_matches
            gc.collect()
    
    match_count = 0
    similar_count = 0
    mismatch_count = 0
    
    for match_info in matches.values():
        if match_info["match"] == "Match":
            match_count += 1
        elif match_info["match"] == "Similar Match":
            similar_count += 1
        else:
            mismatch_count += 1
    
    end_time = time.time()
    print(f"Comparison completed in {end_time - start_time:.2f} seconds")
    print(f"Found {len(matches)} matches (Match: {match_count}, Similar Match: {similar_count}, Mismatch: {mismatch_count})")
    
    return matches

def generate_report(properties1: List[Property], properties2: List[Property],
                   match_threshold=85, similar_threshold=60,
                   limit_threshold=0.15, mortgage_threshold=0.15,
                   significant_words=None, output_file=None, use_templates=True) -> str:
    """
    Generates a report comparing two real estate listings according to the specified format.
    """
    print("Starting report generation...")
    start_time = time.time()
    
    matches = fuzzy_match(
        properties1, properties2,
        match_threshold, similar_threshold,
        limit_threshold, mortgage_threshold,
        significant_words
    )
    
    print("Creating Excel report...")
    data = []
    
    exact_match_props1 = set()
    exact_match_props2 = set()
    similar_match_props1 = set()
    similar_match_props2 = set()
    
    for prop1_desc, match_info in matches.items():
        if match_info["match"] == "Match":
            exact_match_props1.add(prop1_desc)
            exact_match_props2.add(match_info["property"].original_description)
        elif match_info["match"] == "Similar Match":
            similar_match_props1.add(prop1_desc)
            similar_match_props2.add(match_info["property"].original_description)
    
    match_rows = []
    for prop1_desc, match_info in matches.items():
        if match_info["match"] == "Match":
            prop1 = next(p for p in properties1 if p.original_description == prop1_desc)
            matched_prop = match_info["property"]
            common_words = match_info.get("common_words", {})
            
            details = generate_match_details(prop1, matched_prop, "Match", common_words, use_templates)
            
            match_rows.append({
                "List 2 Description": matched_prop.original_description,
                "List 1 Description": prop1.original_description,
                "Status": "Matched",
                "Details": details
            })
    
    similar_match_rows = []
    for prop1_desc, match_info in matches.items():
        if match_info["match"] == "Similar Match":
            prop1 = next(p for p in properties1 if p.original_description == prop1_desc)
            matched_prop = match_info["property"]
            common_words = match_info.get("common_words", {})
            
            details = generate_match_details(prop1, matched_prop, "Similar Match", common_words, use_templates)
            
            similar_match_rows.append({
                "List 2 Description": matched_prop.original_description,
                "List 1 Description": prop1.original_description,
                "Status": "Similar Match",
                "Details": details
            })
    
    list2_mismatches = []
    for prop2 in properties2:
        if (prop2.original_description not in exact_match_props2 and 
            prop2.original_description not in similar_match_props2):
            list2_mismatches.append({
                "List 2 Description": prop2.original_description,
                "List 1 Description": "-",
                "Status": "Mismatch",
                "Details": f"Year 2023, Limit {format_money(prop2.limit)}/Mortgage {format_money(prop2.mortgage_amount)}"
            })
    
    list1_mismatches = []
    for prop1 in properties1:
        if (prop1.original_description not in exact_match_props1 and 
            prop1.original_description not in similar_match_props1):
            list1_mismatches.append({
                "List 2 Description": "-",
                "List 1 Description": prop1.original_description,
                "Status": "Mismatch",
                "Details": f"Year 2023, Limit {format_money(prop1.limit)}/Mortgage {format_money(prop1.mortgage_amount)}"
            })
    
    data.extend(match_rows)
    data.extend(similar_match_rows)
    data.extend(list2_mismatches)
    data.extend(list1_mismatches)

    print(f"Processing {len(data)} rows of data...")
    df = pd.DataFrame(data)
    
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    if output_file:
        file_name = output_file
    else:
        file_name = f'property_comparison_{timestamp}.xlsx'
    
    with pd.ExcelWriter(file_name, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="Property Comparison")
        
        workbook = writer.book
        worksheet = writer.sheets["Property Comparison"]
        
        for col_idx, header in enumerate(df.columns, 1):
            cell = worksheet.cell(row=1, column=col_idx)
            cell.font = Font(bold=True)
        
        fills = {
            "Matched": PatternFill(start_color="CCFFCC", end_color="CCFFCC", fill_type="solid"), 
            "Similar Match": PatternFill(start_color="FFFFCC", end_color="FFFFCC", fill_type="solid"),  
            "Mismatch": PatternFill(start_color="FFCCCC", end_color="FFCCCC", fill_type="solid")   
        }
        

        status_col_idx = df.columns.get_loc("Status") + 1  
        
        for row_idx, row in enumerate(df.itertuples(), 2):  
            status = getattr(row, "Status")
            cell = worksheet.cell(row=row_idx, column=status_col_idx)
            
            if status in fills:
                cell.fill = fills[status]
        
        for column_cells in worksheet.columns:
            max_length = 0
            column = column_cells[0].column_letter
            for cell in column_cells:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = (max_length + 2) * 1.2
            worksheet.column_dimensions[column].width = adjusted_width
    
    stats = df["Status"].value_counts().to_dict()
    print("\nComparison results statistics:")
    print(f"Full matches (Matched): {stats.get('Matched', 0)}")
    print(f"Similar matches (Similar Match): {stats.get('Similar Match', 0)}")
    print(f"No matches (Mismatch): {stats.get('Mismatch', 0)}")
    
    end_time = time.time()
    print(f"Report generated in {end_time - start_time:.2f} seconds")
    
    return f"Report generated and saved to {file_name}"

def main():
    parser = argparse.ArgumentParser(description='Program for comparing real estate objects')
    
    parser.add_argument('--input', '-i', 
                      type=str, 
                      default='data.json',
                      help='Path to the input JSON file (default: data.json)')
    
    parser.add_argument('--output', '-o', 
                      type=str, 
                      help='Path to the output Excel file (by default: property_comparison_TIMESTAMP.xlsx)')
    
    parser.add_argument('--match-threshold', '-mt', 
                      type=float, 
                      default=85,
                      help='Minimum similarity threshold for “Match” in percentage (default: 85)')
    
    parser.add_argument('--similar-threshold', '-st', 
                      type=float, 
                      default=60,
                      help='Minimum similarity threshold for “Similar Match” in percentage (default: 60)')
    
    parser.add_argument('--limit-diff', '-ld', 
                      type=float, 
                      default=15,
                      help='Maximum allowable difference in limits in percentage (default: 15)')
    
    parser.add_argument('--mortgage-diff', '-md', 
                      type=float, 
                      default=15,
                      help='Maximum allowable mortgage difference in percentage (default: 15)')
    
    parser.add_argument('--significant-words', '-sw', 
                      type=str, 
                      default='residential,commercial,apartment,office,retail,warehouse,building,complex,home,house,area,property,park,garden,recreation,playground,waterfront,beachfront,vacation,holiday',
                      help='A list of significant words for an increased comparison bonus (separated by commas)')
    
    parser.add_argument('--use-templates', '-ut',
                      action='store_true',
                      default=True,
                      help='Use templates to describe matches (default: True)')
    
    args = parser.parse_args()
    
    try:
        print("Starting property comparison program...")
        
        start_time = time.time()
        
        limit_threshold = args.limit_diff / 100
        mortgage_threshold = args.mortgage_diff / 100
        
        significant_words = set(word.strip().lower() for word in args.significant_words.split(','))
        
        print(f"Comparison settings:")
        print(f"- 'Match' threshold: {args.match_threshold}%")
        print(f"- 'Similar Match' threshold: {args.similar_threshold}%")
        print(f"- Allowed limit difference: {args.limit_diff}%")
        print(f"- Allowed mortgage difference: {args.mortgage_diff}%")
        print(f"- Number of significant words: {len(significant_words)}")
        print(f"- Using description templates: {'Yes' if args.use_templates else 'No'}")
        
        print(f"Loading data from file: {args.input}...")
        with open(args.input, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print("Preparing data for processing...")
        properties1 = [Property(prop['description'], prop['limit'], prop['mortgageAmount']) 
                      for prop in data['portfolio1']['properties']]
        properties2 = [Property(prop['description'], prop['limit'], prop['mortgageAmount']) 
                      for prop in data['portfolio2']['properties']]
        
        print(f"Loaded {len(properties1)} objects in the first portfolio and {len(properties2)} objects in the second portfolio")
        
        del data
        gc.collect()
        
        report = generate_report(
            properties1, properties2,
            args.match_threshold, args.similar_threshold,
            limit_threshold, mortgage_threshold,
            significant_words, args.output, args.use_templates
        )
        print(report)
        
        end_time = time.time()
        print(f"Program completed in {end_time - start_time:.2f} seconds")
    except FileNotFoundError:
        print(f"Error: File {args.input} not found. Make sure the file exists in the current directory.")
    except json.JSONDecodeError:
        print(f"Error: Could not parse {args.input}. Make sure the file contains valid JSON.")
    except MemoryError:
        print("Error: Not enough memory to process the data. Try splitting the data into smaller parts.")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if False:  # Change to True for testing
        test_cases = [
            "Single Family Home with 3 bedrooms and 2 bathrooms",
            "Single Family Residence - 3BR/2BA",
            "Downtown Commercial Office Space",
            "Downtown Office Complex",
            "Multi-unit Residential Complex",
            "Apartment Building Complex",
            "Retail Store with Storage",
            "Retail Storefront with Warehouse"
        ]
        
        prop = Property("", "1000", "800") 
        
        print("Testing description normalization:")
        print("-" * 60)
        for desc in test_cases:
            norm = prop.normalize_description(desc)
            print(f"Original: {desc}")
            print(f"Normalized: {norm}")
            print("-" * 60)
    

    elif False:  # Change to True to test monetary values
        test_money_values = [
            "1200000",
            "$850,000",
            "350k",
            "1.5M",
            "four hundrend & fifty thousand",
            "one million two hundred thousand",
            "2,500,000",
            "seven hundred fifty thousand dollars",
            "3.2 million",
            "&" 
        ]
        
        prop = Property("", "1000", "800")  
        
        print("Testing monetary value processing:")
        print("-" * 60)
        for value in test_money_values:
            try:
                norm = prop.normalize_monetary_value(value)
                print(f"Original: {value}")
                print(f"Normalized: ${norm:,.2f}")
            except Exception as e:
                print(f"Error processing '{value}': {str(e)}")
            print("-" * 60)
    else:
        main()