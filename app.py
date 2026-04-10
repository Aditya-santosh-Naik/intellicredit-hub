from flask import Flask, render_template, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from routes.upload import upload_bp
from routes.intelligence import intelligence_bp
from routes.mock_api import mock_bp
from routes.verification import verification_bp
from routes.cases import cases_bp
from routes.schema import schema_bp
from routes.analyzer import analyzer_bp
from routes.reports import reports_bp

app = Flask(__name__)

# Security: Rate Limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

app.register_blueprint(upload_bp)
app.register_blueprint(intelligence_bp)
app.register_blueprint(mock_bp)
app.register_blueprint(verification_bp)
app.register_blueprint(cases_bp)
app.register_blueprint(schema_bp)
app.register_blueprint(analyzer_bp)
app.register_blueprint(reports_bp)

@app.route('/')
def dashboard():
    return render_template('index.html', active='dashboard')

@app.route('/cases')
def cases():
    return render_template('cases.html', active='cases')

@app.route('/case/new')
def case_new():
    return render_template('case_new.html', active='case_new')

@app.route('/audit')
def audit():
    return render_template('audit.html', active='audit')

@app.route('/risk')
def risk():
    return render_template('risk.html', active='risk')

@app.route('/reports')
def reports():
    return render_template('reports.html', active='reports')

@app.route('/settings')
def settings():
    return render_template('settings.html', active='settings')

@app.route('/security')
def security():
    return render_template('security.html', active='security')

@app.route('/document_intelligence')
def document_intelligence():
    return render_template('document_intelligence.html', active='document_intelligence')

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    print("IntelliCredit Hub running at http://127.0.0.1:5000")
    app.run(debug=True, use_reloader=False, host='127.0.0.1', port=5000)
