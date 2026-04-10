import sqlite3
import os
import json

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'intellicredit.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    # Table for tracking documents per session/entity (using entity_id='default' for MVP)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_id TEXT NOT NULL,
            document_type TEXT NOT NULL,
            status TEXT NOT NULL,
            file_type TEXT,
            file_size INTEGER,
            ai_classification TEXT,
            confidence_score REAL,
            sha256_hash TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(entity_id, document_type)
        )
    ''')
    # Table for audit logging
    conn.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            analyst_id TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            document_type TEXT NOT NULL,
            file_hash TEXT,
            classification_result TEXT,
            confidence_score REAL
        )
    ''')
    conn.commit()
    conn.close()

def update_document(entity_id, document_type, status, file_type, file_size, ai_classification, confidence, sha256_hash):
    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT INTO documents (entity_id, document_type, status, file_type, file_size, ai_classification, confidence_score, sha256_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(entity_id, document_type) DO UPDATE SET
                status=excluded.status,
                file_type=excluded.file_type,
                file_size=excluded.file_size,
                ai_classification=excluded.ai_classification,
                confidence_score=excluded.confidence_score,
                sha256_hash=excluded.sha256_hash,
                updated_at=CURRENT_TIMESTAMP
        ''', (entity_id, document_type, status, file_type, file_size, ai_classification, confidence, sha256_hash))
        conn.commit()
    except sqlite3.IntegrityError:
        print(f"Duplicate hash or integrity error on update")
        raise
    finally:
        conn.close()

def log_audit(analyst_id, entity_id, document_type, file_hash, classification, confidence):
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO audit_logs (analyst_id, entity_id, document_type, file_hash, classification_result, confidence_score)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (analyst_id, entity_id, document_type, file_hash, classification, confidence))
    conn.commit()
    conn.close()

def get_documents_by_entity(entity_id='default'):
    conn = get_db_connection()
    docs = conn.execute('SELECT * FROM documents WHERE entity_id = ?', (entity_id,)).fetchall()
    conn.close()
    return [dict(doc) for doc in docs]

def check_duplicate_hash(sha256_hash):
    conn = get_db_connection()
    doc = conn.execute('SELECT id FROM documents WHERE sha256_hash = ?', (sha256_hash,)).fetchone()
    conn.close()
    return doc is not None

def get_document_progress(entity_id='default'):
    docs = get_documents_by_entity(entity_id)
    REQUIRED_DOCS = ['ALM Statement', 'Shareholding Pattern', 'Borrowing Profile', 'Annual Report', 'Portfolio Performance']
    progress = []
    
    # Fill in required docs if missing
    existing_docs = {doc['document_type']: doc for doc in docs}
    
    for req_doc in REQUIRED_DOCS:
        if req_doc in existing_docs:
            progress.append(existing_docs[req_doc])
        else:
            progress.append({
                'document_type': req_doc,
                'status': 'Pending',
                'file_type': '-',
                'file_size': 0,
                'ai_classification': '-',
                'confidence_score': 0.0,
                'sha256_hash': '-'
            })
    return progress

init_db()
