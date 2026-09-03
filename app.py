import os
import sys
import traceback
import requests
from flask import Flask, request, jsonify, render_template, send_file, Response
from werkzeug.utils import secure_filename

# Import the existing pipeline
from src.pipeline import run_pipeline

app = Flask(__name__)

# Configure upload and evidence folders
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'data', 'input')
EVIDENCE_FOLDER = os.path.join(os.path.dirname(__file__), 'data', 'evidence')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(EVIDENCE_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['EVIDENCE_FOLDER'] = EVIDENCE_FOLDER

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze():
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided.'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected file.'}), 400

    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        try:
            # We need to catch SystemExit because run_pipeline calls sys.exit(1) on failure.
            # However, since run_pipeline uses sys.exit(), we might not be able to easily extract the exact
            # print statements unless we redirect stdout. 
            # A simpler approach is to wrap it. Let's try running the pipeline.
            try:
                result = run_pipeline(file_path)
                return jsonify(result)
            except SystemExit as e:
                # sys.exit was called by the pipeline indicating a failure
                return jsonify({'error': 'Pipeline analysis failed (see terminal output for details).'}), 500
        except Exception as e:
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500

@app.route('/api/evidence-image', methods=['GET'])
def evidence_image():
    path = request.args.get('path')
    if not path:
        return jsonify({'error': 'Missing path parameter.'}), 400
    
    # Simple security check to prevent directory traversal
    filename = secure_filename(os.path.basename(path))
    
    # Must end with _cropped_face.jpg based on the detect_encode logic
    if not filename.endswith('_cropped_face.jpg'):
        return jsonify({'error': 'Invalid evidence image request.'}), 400
        
    full_path = os.path.join(app.config['EVIDENCE_FOLDER'], filename)
    
    if not os.path.exists(full_path):
        return jsonify({'error': 'Evidence image not found.'}), 404
        
    return send_file(full_path, mimetype='image/jpeg')

@app.route('/api/proxy-image', methods=['GET'])
def proxy_image():
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'Missing url parameter.'}), 400
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        # Use stream=True to avoid loading the entire image into memory at once
        r = requests.get(url, headers=headers, stream=True, timeout=10)
        r.raise_for_status()
        
        # Exclude hop-by-hop headers and Content-Encoding to avoid transfer errors
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in r.raw.headers.items()
                   if name.lower() not in excluded_headers]
        
        return Response(r.raw.read(), r.status_code, headers)
    except Exception as e:
        return jsonify({'error': f'Failed to fetch image: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=False, port=5000)
