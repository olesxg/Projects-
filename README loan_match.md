# Property Comparison Engine (Loan Matcher)

A powerful, scalable tool for comparing real estate properties across different portfolios with advanced fuzzy matching capabilities.

## Overview

The Property Comparison Engine is designed to efficiently analyze and match properties between two lists, categorizing them as exact matches, similar matches, or mismatches based on sophisticated comparison algorithms. It's optimized for handling large datasets (100,000+ entries) through parallel processing and memory optimization.

## Key Features

- **Fuzzy Text Matching**: Intelligently matches property descriptions using multiple string similarity algorithms
- **Monetary Value Normalization**: Processes various formats of monetary values (numeric, text, abbreviated)
- **Parallel Processing**: Utilizes multi-core processing for fast comparison of large datasets
- **Memory Optimization**: Implements chunk-based processing and memory management for large datasets
- **Customizable Matching Criteria**: Adjustable thresholds for match quality and numerical differences
- **Comprehensive Reporting**: Generates color-coded Excel reports with detailed matching information
- **Robust Error Handling**: Gracefully handles various input errors and edge cases

## How It Works

### Data Processing Flow

1. **Data Loading**: Parses JSON input file containing two property portfolios
2. **Property Normalization**: Standardizes property descriptions and monetary values
3. **Parallel Comparison**: Divides data into chunks for multi-core processing
4. **Match Classification**: Categorizes properties as Match, Similar Match, or Mismatch
5. **Report Generation**: Creates a comprehensive Excel report with color coding

### Matching Algorithm

The core matching algorithm employs a multi-faceted approach:

1. **Word Indexing**: Creates an inverted index for efficient candidate selection
2. **Multi-metric Similarity**: Combines token sort ratio, token set ratio, and partial ratio
3. **Weighted Scoring**:
   - 40% weight to normalized description similarity
   - 40% weight to keyword comparison
   - 20% weight to partial string matching
4. **Bonus System**:
   - +5% per shared significant word (up to 20%)
   - +5% additional for each industry-specific term
   - +15% when property purposes match
5. **Threshold Application**:
   - Match: 85%+ similarity with <10% monetary value difference
   - Similar Match: 60%+ similarity with <15% monetary value difference
   - Mismatch: <60% similarity or larger monetary differences

### Handling Large Datasets (100,000+ Records)

The system is specifically designed to handle very large datasets through:

1. **Dynamic Chunking**: Automatically splits input data based on available CPU cores
2. **Parallel Processing**: Utilizes Python's ProcessPoolExecutor for multi-core execution
3. **Memory Management**: Releases memory after each chunk processing
4. **Word-based Filtering**: Uses word indexing to avoid unnecessary comparisons
5. **Early Filtering**: Requires at least one common word before detailed comparison
6. **Progress Tracking**: Shows real-time progress with estimated completion time

For a dataset with 100,000+ records, the system:
- Divides data into ~1,000 records per chunk (adjusts based on available cores)
- Processes ~8-16 chunks simultaneously (on a typical 8-core machine)
- Implements garbage collection between chunk processing
- Uses efficient data structures to minimize memory footprint

## Input Format

The system expects a JSON file with the following structure:

```json
{
  "portfolio1": {
    "properties": [
      {
        "description": "Property description text",
        "limit": "450000",
        "mortgageAmount": "320000"
      },
      // Additional properties...
    ]
  },
  "portfolio2": {
    "properties": [
      // Similar structure to portfolio1
    ]
  }
}
```

### Supported Value Formats

The system can process various formats for monetary values:

- **Numeric formats**: "450000", "$450,000", "450k", "1.2M"
- **Text formats**: "four hundred fifty thousand", "one million two hundred thousand" 
- **Mixed formats**: "4.5 hundred thousand", "2.5 million"
- **Special cases**: Handles misspellings like "hundrend" → "hundred"

## Output Format

The system generates an Excel report with the following structure:

1. **Match Results**: Color-coded comparison of properties
   - Green: Exact matches (85%+ similarity)
   - Yellow: Similar matches (60-85% similarity)
   - Red: Mismatches (properties without matches)
   
2. **Columns**:
   - List 2 Description: Property description from the second portfolio
   - List 1 Description: Property description from the first portfolio
   - Status: Match classification (Matched, Similar Match, Mismatch)
   - Details: Detailed analysis of the match including limit and mortgage values

## Text Normalization Features

The system employs sophisticated text normalization techniques:

1. **Case Normalization**: Converts all text to lowercase
2. **Punctuation Removal**: Removes punctuation and special characters
3. **Synonym Standardization**: Maps synonyms to standard terms
   - Examples: "residence"/"house"/"townhouse" → "home"
4. **Format Standardization**: Converts "3BR/2BA" format to "3 bedroom 2 bathroom"
5. **Whitespace Normalization**: Standardizes whitespace between words

## Command Line Arguments

```
usage: loan_matcher.py [-h] [--input INPUT] [--output OUTPUT] 
                       [--match-threshold MATCH_THRESHOLD]
                       [--similar-threshold SIMILAR_THRESHOLD] 
                       [--limit-diff LIMIT_DIFF]
                       [--mortgage-diff MORTGAGE_DIFF] 
                       [--significant-words SIGNIFICANT_WORDS]
                       [--use-templates]
```

### Parameters

- `--input`, `-i`: Path to input JSON file (default: 'data.json')
- `--output`, `-o`: Path to output Excel file (default: 'property_comparison_TIMESTAMP.xlsx')
- `--match-threshold`, `-mt`: Minimum similarity threshold for "Match" in percentage (default: 85)
- `--similar-threshold`, `-st`: Minimum similarity threshold for "Similar Match" in percentage (default: 60)
- `--limit-diff`, `-ld`: Maximum allowable limit difference in percentage (default: 15)
- `--mortgage-diff`, `-md`: Maximum allowable mortgage difference in percentage (default: 15)
- `--significant-words`, `-sw`: Comma-separated list of significant words for bonus points
- `--use-templates`, `-ut`: Use templates for match descriptions (default: True)

## Installation Requirements

```
pip install -r requirements.txt
```

Required packages:
- pandas
- fuzzywuzzy
- python-Levenshtein (optional, for faster fuzzy matching)
- word2number
- openpyxl
- tqdm

## Performance Metrics

Approximate processing times on different hardware:

| Dataset Size | 8-Core CPU | 16-Core CPU | 32-Core CPU |
|--------------|------------|-------------|-------------|
| 1,000 items  | ~3 seconds | ~2 seconds  | ~1 second   |
| 10,000 items | ~30 seconds| ~15 seconds | ~8 seconds  |
| 100,000 items| ~5 minutes | ~2.5 minutes| ~1.3 minutes|
| 1,000,000+   | Chunked mode automatically activates, processing in batches |

Memory usage scales approximately linearly with input size, with optimization for very large datasets.

## Usage Examples

### Basic Usage

```bash
python loan_matcher.py -i data.json
```

### Custom Thresholds

```bash
python loan_matcher.py -i data.json -mt 90 -st 70 -ld 10 -md 10
```

### Custom Output File

```bash
python loan_matcher.py -i data.json -o my_comparison_report.xlsx
```

### Custom Significant Words

```bash
python loan_matcher.py -i data.json -sw "residential,commercial,office,retail,apartment"
```

## Extending the Code

### Adding New Property Types

To support additional property types, extend the `REPLACEMENTS` dictionary in the `Property` class:

```python
REPLACEMENTS = {
    # Existing mappings...
    'new_term1': 'standard_term1',
    'new_term2': 'standard_term2',
}
```

### Custom Match Templates

For specific property matches, add entries to the `TEMPLATE_DESCRIPTIONS` dictionary:

```python
TEMPLATE_DESCRIPTIONS = {
    "Description A": {
        "Description B": "Custom match details text"
    }
}
```

### Adapting for Different Data Types

While the system is optimized for real estate properties, it can be adapted for other domain-specific comparisons by:

1. Modifying the `Property` class attributes and methods
2. Updating the normalization functions for domain-specific terminology
3. Adjusting the similarity metrics and thresholds
4. Changing the report format and detail generation

## Error Handling

The system includes comprehensive error handling for:
- Missing input files
- Malformed JSON data
- Memory limitations
- Invalid monetary values
- Processing errors

## Processing Metrics

During execution, the system reports:
- Number of properties in each portfolio
- Number of CPU cores being utilized
- Processing time for comparison
- Number of matches found by category
- Report generation time

## Optimization for Different Hardware

The system automatically detects available CPU cores and adjusts processing accordingly:
- For systems with few cores: Increases chunk size to reduce overhead
- For systems with many cores: Decreases chunk size for better parallelization
- Memory usage is dynamically adjusted based on dataset size

## Troubleshooting

### Common Issues and Solutions

1. **Memory Errors with Large Datasets**
   - Increase chunk size: Use smaller chunks to reduce memory footprint
   - Run on a system with more RAM
   - Process data in batches using multiple runs

2. **Slow Processing**
   - Install python-Levenshtein for faster fuzzy matching
   - Increase similarity thresholds to reduce comparison complexity
   - Reduce the number of significant words

3. **Poor Match Quality**
   - Decrease similarity thresholds
   - Add domain-specific terms to significant words
   - Update the REPLACEMENTS dictionary with domain terminology

## Future Enhancements

Potential improvements for future versions:

1. Implementing machine learning for more intelligent matching
2. Supporting additional input/output formats (CSV, databases)
3. Adding a web interface for interactive report viewing
4. Implementing incremental processing for massive datasets
5. Adding more sophisticated text processing using NLP techniques

## Author

[Oleksandr]