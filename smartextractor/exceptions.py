"""
Exceptions Module - Define custom exceptions for SmartExtractor
"""


class SmartExtractorError(Exception):
    """SmartExtractor base exception class"""
    pass


class PDFProcessingError(SmartExtractorError):
    """PDF processing exception"""
    pass


class PDFNotFoundError(PDFProcessingError):
    """PDF file not found exception"""
    pass


class PDFCorruptedError(PDFProcessingError):
    """PDF file corrupted exception"""
    pass


class PDFPasswordProtectedError(PDFProcessingError):
    """PDF file password protected exception"""
    pass


class OCRError(SmartExtractorError):
    """OCR processing exception"""
    pass


class OCRNotAvailableError(OCRError):
    """OCR engine not available exception"""
    pass


class OCRTimeoutError(OCRError):
    """OCR processing timeout exception"""
    pass


class LayoutDetectionError(SmartExtractorError):
    """Layout detection exception"""
    pass


class TableExtractionError(SmartExtractorError):
    """Table extraction exception"""
    pass


class ImageProcessingError(SmartExtractorError):
    """Image processing exception"""
    pass


class ConfigurationError(SmartExtractorError):
    """Configuration error exception"""
    pass


class ValidationError(SmartExtractorError):
    """Data validation exception"""
    pass


class UnsupportedFormatError(SmartExtractorError):
    """Unsupported format exception"""
    pass


class ProcessingTimeoutError(SmartExtractorError):
    """Processing timeout exception"""
    pass 