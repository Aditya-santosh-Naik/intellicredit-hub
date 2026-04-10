import os
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from utils.security import allowed_file, validate_mime, calculate_sha256, scan_for_malicious_payload, is_password_protected_pdf, MAX_FILE_SIZE
from utils.db import update_document, log_audit, get_document_progress, check_duplicate_hash
from services.extractor import extract_text
from services.classifier import classify_document
from pymongo import MongoClient
from datetime import datetime, timezone

# ── MongoDB connection ──────────────────────────────────
MONGO_URI = "mongodb://localhost:27017/"
try:
    client = MongoClient(MONGO_URI)
    db = client["intellicredit"]
    cases_col = db["cases"]
except Exception as e:
    print("Warning: Could not connect to MongoDB:", e)

upload_bp = Blueprint('upload', __name__)

# Ensure uploads directory exists
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@upload_bp.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400
        
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    # Check file size (Read into memory to check size if not using request.content_length, but content_length is safer)
    if request.content_length and request.content_length > MAX_FILE_SIZE:
        return jsonify({'error': f'File exceeds maximum size of 50MB'}), 413
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_ext = filename.rsplit('.', 1)[1].lower()
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        
        # Save file temporarily to run checks
        file.save(file_path)
        file_size = os.path.getsize(file_path)
        
        if file_size > MAX_FILE_SIZE:
             os.remove(file_path)
             return jsonify({'error': 'File exceeds maximum size of 50MB'}), 413

        # Security Checks
        if not validate_mime(file_path):
            os.remove(file_path)
            return jsonify({'error': 'Invalid MIME type detected. File rejected.'}), 400
            
        if scan_for_malicious_payload(file_path):
            os.remove(file_path)
            return jsonify({'error': 'Malicious payload detected. Upload rejected.'}), 403
            
        if is_password_protected_pdf(file_path):
            os.remove(file_path)
            return jsonify({'error': 'Password protected PDFs are not allowed.'}), 400

        # Duplicate checking via SHA-256 (BYPASSED FOR TESTING AS REQUESTED)
        file_hash = calculate_sha256(file_path)
        # if check_duplicate_hash(file_hash):
        #     os.remove(file_path)
        #     return jsonify({'error': 'Duplicate file detected (SHA-256 match).'}), 409

        # Process Document
        try:
            text = extract_text(file_path, file_ext)
            if not text.strip():
                # If extraction fails completely or is empty
                return jsonify({'error': 'Failed to extract text or file is empty.'}), 422
                
            classification_result = classify_document(text)
            doc_type = classification_result['classification']
            conf_score = classification_result['confidence']
            
            if doc_type == 'Unknown':
                expected_type = request.form.get('document_type')
                if expected_type:
                    doc_type = expected_type
                    conf_score = 0.50 # Assign low confidence so it triggers manual review
                else:
                    os.remove(file_path)
                    return jsonify({'error': 'Failed to classify document. Unknown type.'}), 422

            # Case Management Integration: Save document metadata into the active Case
            case_id = request.form.get('case_id')
            if case_id:
                doc_metadata = {
                    "document_type": request.form.get('document_type', doc_type), # the actual required slot from the frontend
                    "file_path": file_path,
                    "file_type": file_ext.upper(),
                    "file_size": file_size,
                    "ai_classification": doc_type,
                    "confidence": conf_score,
                    "sha256_hash": file_hash,
                    "status": "APPROVED" if conf_score >= 75 else "REVIEW",
                    "uploaded_at": datetime.now(timezone.utc).isoformat()
                }
                
                # Overwrite if we are re-uploading the same document type
                cases_col.update_one(
                    {"case_id": case_id},
                    {"$pull": {"documents": {"document_type": doc_metadata["document_type"]}}}
                )
                
                # Push the new document
                cases_col.update_one(
                    {"case_id": case_id},
                    {
                        "$push": {"documents": doc_metadata},
                        "$set": {"status": "DOCUMENTS_UPLOADED"} # we can naively set this since they are uploading
                    }
                )

            # Define user/entity (mocked for MVP)
            analyst_id = 'analyst_001'
            entity_id = 'entity_1001'
            
            update_document(
                entity_id=entity_id,
                document_type=doc_type,
                status='Uploaded',
                file_type=file_ext.upper(),
                file_size=file_size,
                ai_classification=doc_type,
                confidence=conf_score,
                sha256_hash=file_hash
            )
            
            # Audit log
            log_audit(analyst_id, entity_id, doc_type, file_hash, doc_type, conf_score)

            return jsonify({
                'message': 'File uploaded and classified successfully',
                'document_type': doc_type,
                'confidence': conf_score,
                'file_hash': file_hash,
                'status': 'Uploaded'
            }), 200

        except Exception as e:
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({'error': f'Server error during processing: {str(e)}'}), 500
    else:
        return jsonify({'error': 'Invalid file format. Allowed formats: PDF, XLSX, XLS, PNG, JPG, TIFF'}), 400

@upload_bp.route('/api/documents', methods=['GET'])
def get_documents_status():
    entity_id = 'entity_1001' # Mocked for MVP
    progress = get_document_progress(entity_id)
    return jsonify(progress), 200
