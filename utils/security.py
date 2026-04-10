import os
import hashlib
import filetype
import pdfplumber

ALLOWED_EXTENSIONS = {'pdf', 'xlsx', 'xls', 'png', 'jpg', 'jpeg', 'tiff'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

# Basic list of malicious patterns to scan for (primarily for text-based embedded payloads)
MALICIOUS_PATTERNS = [
    b"<script>", b"javascript:", b"eval(", b"vbscript:", b"onload="
]

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_mime(file_path):
    """Validate MIME type using filetype library."""
    kind = filetype.guess(file_path)
    if kind is None:
        # If filetype can't guess, fallback to extension check if it's a known text-based format like CSV
        return False
    
    allowed_mimes = [
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # xlsx
        'application/vnd.ms-excel',  # xls
        'image/png',
        'image/jpeg',
        'image/tiff'
    ]
    return kind.mime in allowed_mimes

def calculate_sha256(file_path):
    """Compute SHA-256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read and update hash string value in blocks of 4K
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def scan_for_malicious_payload(file_path):
    """Scan file content for basic malicious patterns."""
    try:
        with open(file_path, "rb") as f:
            content = f.read()
            for pattern in MALICIOUS_PATTERNS:
                if pattern in content:
                    return True # Malicious payload found
    except Exception as e:
        print(f"Error scanning file: {e}")
        return True # Default to secure if scan fails
    return False

def is_password_protected_pdf(file_path):
    """Check if a PDF is password protected."""
    if not file_path.lower().endswith('.pdf'):
        return False
    try:
        with pdfplumber.open(file_path) as pdf:
            pass
        return False
    except Exception as e:
        # pdfplumber raises an exception for password protected files (usually PyPDF2.errors.FileNotDecryptedError)
        return True
