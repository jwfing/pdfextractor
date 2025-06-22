# SmartExtractor

An intelligent PDF text extraction library integrating image recognition and automatic layout detection, capable of extracting text content from PDF documents accurately and smartly.

## Features

- 🔍 **Intelligent Text Recognition**: Integrates multiple OCR engines for high-accuracy text recognition
- 🎯 **Automatic Layout Detection**: Automatically detects document structure, including titles, paragraphs, tables, etc.
- 📰 **Multi-Column Layout Handling**: Intelligently detects and reorders multi-column documents to ensure correct reading order
- 🖼️ **Image Content Processing**: Supports recognition and extraction of text within images
- 📊 **Table Data Extraction**: Smartly detects and extracts table data
- 🔧 **Multi-Format Support**: Supports various PDF formats and layouts
- ⚡ **High Performance**: Optimized algorithms ensure fast processing of large files
- 🎨 **Customizable**: Rich configuration options and extension interfaces

## Installation

```bash
pip install smartextractor
```

Or install from source:

```bash
git clone https://github.com/yourusername/smartextractor.git
cd smartextractor
pip install -e .
```

## Quick Start

### Basic Usage

```python
from smartextractor import SmartExtractor

# Create extractor instance
extractor = SmartExtractor()

# Extract PDF text
text = extractor.extract_text("document.pdf")
print(text)
```

### Advanced Configuration

```python
from smartextractor import SmartExtractor, ExtractionConfig

# Configure extraction parameters
config = ExtractionConfig(
    enable_ocr=True,
    enable_layout_detection=True,
    enable_table_extraction=True,
    language="zh-CN",
    confidence_threshold=0.8
)

extractor = SmartExtractor(config=config)
result = extractor.extract("document.pdf")

# Get structured result
print("Text content:", result.text)
print("Table data:", result.tables)
print("Image info:", result.images)
```

### Multi-Column Layout Handling

SmartExtractor is specially optimized for multi-column layout documents:

```python
from smartextractor import SmartExtractor, ExtractionConfig

# Enable layout detection (enabled by default)
config = ExtractionConfig(
    enable_layout_detection=True,
    detect_columns=True  # Enable multi-column detection
)

extractor = SmartExtractor(config=config)

# Process a two-column PDF
result = extractor.extract("two_column_document.pdf")

# The text will be arranged in the correct reading order
print(result.text)
```

### Command Line Usage

```bash
# Basic extraction
smartextractor extract document.pdf

# Specify output file
smartextractor extract document.pdf -o output.txt

# Extract as JSON
smartextractor extract document.pdf --format json -o output.json

# Enable verbose output
smartextractor extract document.pdf --verbose
```

## Features

### 1. Intelligent Text Recognition
- Supports multiple OCR engines (Tesseract, EasyOCR, etc.)
- Automatic language detection
- Text post-processing and correction

### 2. Automatic Layout Detection
- Title and paragraph recognition
- List and numbering recognition
- Header and footer processing
- **Multi-column layout detection and reordering**

### 3. Multi-Column Layout Handling
SmartExtractor uses multiple algorithms to detect and handle multi-column layouts:

- **Clustering Analysis**: Detects columns based on the distribution of text blocks
- **Heuristic Detection**: Analyzes the ratio of text block width to page width
- **Density Analysis**: Analyzes text density distribution using a page grid
- **Row Alignment**: Intelligently identifies text in the same row to ensure correct reading order

Supported features:
- Automatically detects 2-4 column layouts
- Intelligent text block grouping and sorting
- Preserves original font and formatting information
- Handles irregular multi-column layouts

### 4. Table Data Extraction
- Table structure recognition
- Cell content extraction
- Table data formatting

### 5. Image Content Processing
- Text recognition in images
- Chart and diagram recognition
- Image quality optimization

## API Documentation

### SmartExtractor Class

The main extractor class providing PDF text extraction functionality.

#### Methods

- `extract_text(pdf_path: str) -> str`: Extract plain text
- `extract(pdf_path: str) -> ExtractionResult`: Extract structured result
- `extract_pages(pdf_path: str) -> List[PageResult]`: Extract by page

### ExtractionConfig Class

Configure extraction parameters and options.

#### Main Parameters

- `enable_ocr`: Enable OCR
- `enable_layout_detection`: Enable layout detection
- `detect_columns`: Enable multi-column detection
- `enable_table_extraction`: Enable table extraction
- `language`: Document language
- `confidence_threshold`: Confidence threshold

## Development

### Environment Setup

```bash
git clone https://github.com/yourusername/smartextractor.git
cd smartextractor
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest
```

### Code Formatting

```bash
black smartextractor/
flake8 smartextractor/
```

### Multi-Column Layout Demo

Run the multi-column layout detection demo:

```bash
python examples/column_layout_demo.py
```

## Contributing

Issues and Pull Requests are welcome!

## License

MIT License

## Changelog

### v0.1.0
- Initial release
- Basic PDF text extraction
- OCR and layout detection support
- **Multi-column layout detection and reordering** 