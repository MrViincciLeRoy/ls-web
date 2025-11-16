from flask import Flask, request, jsonify
import json
import os
from datetime import datetime
import uuid
import sqlite3
from contextlib import contextmanager

app = Flask(__name__)

# Data storage directory
DATA_DIR = "mock_data"
os.makedirs(DATA_DIR, exist_ok=True)

# Transaction log database
TRANSACTION_DB = os.path.join(DATA_DIR, "incoming_transactions.db")


@contextmanager
def get_db():
    """Get database connection"""
    conn = sqlite3.connect(TRANSACTION_DB)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_transaction_db():
    """Initialize transaction logging database"""
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS incoming_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                method TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                doctype TEXT,
                doc_name TEXT,
                request_body TEXT,
                response_body TEXT,
                status_code INTEGER,
                success INTEGER DEFAULT 1
            )
        ''')
        conn.commit()


def log_transaction(method, endpoint, doctype=None, doc_name=None, 
                    request_body=None, response_body=None, status_code=200, success=True):
    """Log incoming transaction to database"""
    with get_db() as conn:
        conn.execute('''
            INSERT INTO incoming_requests 
            (timestamp, method, endpoint, doctype, doc_name, request_body, response_body, status_code, success)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            method,
            endpoint,
            doctype,
            doc_name,
            json.dumps(request_body) if request_body else None,
            json.dumps(response_body) if response_body else None,
            status_code,
            1 if success else 0
        ))
        conn.commit()


def get_doctype_file(doctype):
    """Get the file path for a doctype's data"""
    return os.path.join(DATA_DIR, f"{doctype}.json")


def load_documents(doctype):
    """Load all documents of a doctype"""
    file_path = get_doctype_file(doctype)
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
    return []


def save_documents(doctype, documents):
    """Save all documents of a doctype"""
    file_path = get_doctype_file(doctype)
    with open(file_path, 'w') as f:
        json.dump(documents, f, indent=2)


def generate_name():
    """Generate a unique document name"""
    return uuid.uuid4().hex[:10]


def add_metadata(doc):
    """Add standard Frappe metadata to document"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    doc.setdefault("name", generate_name())
    doc.setdefault("owner", "Administrator")
    doc.setdefault("creation", now)
    doc.setdefault("modified", now)
    doc.setdefault("modified_by", "Administrator")
    doc.setdefault("idx", 0)
    doc.setdefault("docstatus", 0)
    return doc


# Authentication (mock - always passes)
@app.before_request
def authenticate():
    auth = request.headers.get('Authorization')
    if not auth and request.endpoint not in ['login', 'static', 'transaction_logs', 'health']:
        return jsonify({"exc": "Authentication required"}), 401


# Health check
@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "service": "Mock ERPNext API"})


# Transaction logs viewer
@app.route('/transaction-logs', methods=['GET'])
def transaction_logs():
    """View transaction logs"""
    limit = request.args.get('limit', 100, type=int)
    
    with get_db() as conn:
        cursor = conn.execute('''
            SELECT * FROM incoming_requests 
            ORDER BY id DESC 
            LIMIT ?
        ''', (limit,))
        
        logs = []
        for row in cursor:
            logs.append({
                'id': row['id'],
                'timestamp': row['timestamp'],
                'method': row['method'],
                'endpoint': row['endpoint'],
                'doctype': row['doctype'],
                'doc_name': row['doc_name'],
                'request_body': json.loads(row['request_body']) if row['request_body'] else None,
                'response_body': json.loads(row['response_body']) if row['response_body'] else None,
                'status_code': row['status_code'],
                'success': bool(row['success'])
            })
    
    return jsonify({"logs": logs, "count": len(logs)})


# Login endpoint
@app.route('/api/method/login', methods=['POST'])
def login():
    data = request.get_json()
    response = {
        "message": "Logged In",
        "home_page": "/app",
        "full_name": data.get('usr', 'Test User')
    }
    
    log_transaction('POST', '/api/method/login', request_body=data, response_body=response)
    
    return jsonify(response)


# Get logged user
@app.route('/api/method/frappe.auth.get_logged_user', methods=['GET'])
def get_logged_user():
    response = {"message": "Administrator"}
    log_transaction('GET', '/api/method/frappe.auth.get_logged_user', response_body=response)
    return jsonify(response)


# List documents
@app.route('/api/resource/<doctype>', methods=['GET'])
def list_documents(doctype):
    documents = load_documents(doctype)
    
    # Parse query parameters
    fields = request.args.get('fields')
    filters = request.args.get('filters')
    or_filters = request.args.get('or_filters')
    order_by = request.args.get('order_by', 'modified desc')
    limit_start = int(request.args.get('limit_start', 0))
    limit = int(request.args.get('limit', request.args.get('limit_page_length', 20)))
    as_dict = request.args.get('as_dict', 'True').lower() == 'true'
    
    # Apply filters
    if filters:
        filter_list = json.loads(filters)
        for flt in filter_list:
            field, operator, value = flt
            if operator == '=':
                documents = [d for d in documents if d.get(field) == value]
            elif operator == '>':
                documents = [d for d in documents if d.get(field, 0) > value]
            elif operator == '<':
                documents = [d for d in documents if d.get(field, 0) < value]
            elif operator == 'in':
                documents = [d for d in documents if d.get(field) in value]
    
    # Apply sorting
    field_name, order = order_by.split()
    reverse = order.lower() == 'desc'
    documents = sorted(documents, key=lambda x: x.get(field_name, ''), reverse=reverse)
    
    # Apply pagination
    documents = documents[limit_start:limit_start + limit]
    
    # Select fields
    if fields:
        field_list = json.loads(fields)
        documents = [{k: d.get(k) for k in field_list} for d in documents]
    else:
        documents = [{"name": d["name"]} for d in documents]
    
    # Format as list if as_dict=False
    if not as_dict:
        documents = [[d.get("name")] for d in documents]
    
    response = {"data": documents}
    log_transaction('GET', f'/api/resource/{doctype}', doctype=doctype, 
                   request_body={'filters': filters}, response_body=response)
    
    return jsonify(response)


# Create document
@app.route('/api/resource/<doctype>', methods=['POST'])
def create_document(doctype):
    doc = request.get_json()
    doc["doctype"] = doctype
    doc = add_metadata(doc)
    
    documents = load_documents(doctype)
    documents.append(doc)
    save_documents(doctype, documents)
    
    response = {"data": doc}
    log_transaction('POST', f'/api/resource/{doctype}', doctype=doctype, doc_name=doc["name"],
                   request_body=doc, response_body=response)
    
    return jsonify(response)


# Read document
@app.route('/api/resource/<doctype>/<name>', methods=['GET'])
def read_document(doctype, name):
    documents = load_documents(doctype)
    doc = next((d for d in documents if d["name"] == name), None)
    
    if not doc:
        error_response = {"exc": "Document not found"}
        log_transaction('GET', f'/api/resource/{doctype}/{name}', doctype=doctype, doc_name=name,
                       response_body=error_response, status_code=404, success=False)
        return jsonify(error_response), 404
    
    response = {"data": doc}
    log_transaction('GET', f'/api/resource/{doctype}/{name}', doctype=doctype, doc_name=name,
                   response_body=response)
    
    return jsonify(response)


# Update document
@app.route('/api/resource/<doctype>/<name>', methods=['PUT'])
def update_document(doctype, name):
    update_data = request.get_json()
    documents = load_documents(doctype)
    
    doc_index = next((i for i, d in enumerate(documents) if d["name"] == name), None)
    if doc_index is None:
        error_response = {"exc": "Document not found"}
        log_transaction('PUT', f'/api/resource/{doctype}/{name}', doctype=doctype, doc_name=name,
                       request_body=update_data, response_body=error_response, 
                       status_code=404, success=False)
        return jsonify(error_response), 404
    
    doc = documents[doc_index]
    doc.update(update_data)
    doc["modified"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    
    documents[doc_index] = doc
    save_documents(doctype, documents)
    
    response = {"data": doc}
    log_transaction('PUT', f'/api/resource/{doctype}/{name}', doctype=doctype, doc_name=name,
                   request_body=update_data, response_body=response)
    
    return jsonify(response)


# Delete document
@app.route('/api/resource/<doctype>/<name>', methods=['DELETE'])
def delete_document(doctype, name):
    documents = load_documents(doctype)
    documents = [d for d in documents if d["name"] != name]
    save_documents(doctype, documents)
    
    response = {"message": "ok"}
    log_transaction('DELETE', f'/api/resource/{doctype}/{name}', doctype=doctype, doc_name=name,
                   response_body=response)
    
    return jsonify(response)


# Remote method call (generic)
@app.route('/api/method/<path:method_path>', methods=['GET', 'POST'])
def remote_method(method_path):
    data = request.get_json() if request.method == 'POST' else request.args.to_dict()
    response = {"message": f"Method {method_path} executed successfully"}
    
    log_transaction(request.method, f'/api/method/{method_path}', 
                   request_body=data, response_body=response)
    
    return jsonify(response)


# File upload
@app.route('/api/method/upload_file', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        error_response = {"exc": "No file provided"}
        log_transaction('POST', '/api/method/upload_file', response_body=error_response,
                       status_code=400, success=False)
        return jsonify(error_response), 400
    
    file = request.files['file']
    if file.filename == '':
        error_response = {"exc": "No file selected"}
        log_transaction('POST', '/api/method/upload_file', response_body=error_response,
                       status_code=400, success=False)
        return jsonify(error_response), 400
    
    # Save file
    upload_dir = os.path.join(DATA_DIR, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, file.filename)
    file.save(file_path)
    
    response = {
        "message": "File uploaded successfully",
        "file_url": f"/files/{file.filename}"
    }
    
    log_transaction('POST', '/api/method/upload_file', 
                   request_body={'filename': file.filename}, response_body=response)
    
    return jsonify(response)


if __name__ == '__main__':
    print(f"===========================================")
    print(f"Mock ERPNext API Starting...")
    print(f"===========================================")
    print(f"Data directory: {os.path.abspath(DATA_DIR)}")
    print(f"Transaction DB: {os.path.abspath(TRANSACTION_DB)}")
    print(f"")
    print(f"API Endpoint:   http://localhost:8000")
    print(f"Logs Viewer:    http://localhost:8000/transaction-logs")
    print(f"Health Check:   http://localhost:8000/health")
    print(f"===========================================")
    print(f"")
    
    # Initialize database
    init_transaction_db()
    print(f"✓ Transaction database initialized")
    
    app.run(debug=False, port=8000, use_reloader=False)
