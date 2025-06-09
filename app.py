from flask import Flask, render_template, request, redirect, url_for, flash
import os
from werkzeug.utils import secure_filename
import datetime
import json

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Configuration
UPLOAD_FOLDER = 'static/models'
ALLOWED_EXTENSIONS = {'obj', 'gltf', 'glb', 'fbx', 'dae', '3ds'}
MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# JSON file to store model metadata
MODELS_JSON_FILE = os.path.join(UPLOAD_FOLDER, 'models_metadata.json')

def load_models_metadata():
    """Load model metadata from JSON file"""
    if os.path.exists(MODELS_JSON_FILE):
        try:
            with open(MODELS_JSON_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_models_metadata(metadata):
    """Save model metadata to JSON file"""
    with open(MODELS_JSON_FILE, 'w') as f:
        json.dump(metadata, f, indent=2)

def get_file_info(filepath):
    """Get file information"""
    stat = os.stat(filepath)
    size_mb = round(stat.st_size / (1024 * 1024), 2)
    modified_time = datetime.datetime.fromtimestamp(stat.st_mtime)
    return size_mb, modified_time.strftime('%Y-%m-%d')

def scan_models_folder():
    """Scan the models folder and return list of all models"""
    models = []
    metadata = load_models_metadata()
    
    # Get all files in the upload folder
    if os.path.exists(UPLOAD_FOLDER):
        files = [f for f in os.listdir(UPLOAD_FOLDER) 
                if f.lower().endswith(tuple(ALLOWED_EXTENSIONS)) and os.path.isfile(os.path.join(UPLOAD_FOLDER, f))]
        
        for i, filename in enumerate(sorted(files), 1):
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file_size_mb, date_modified = get_file_info(filepath)
            
            # Get metadata if available, otherwise use defaults
            file_metadata = metadata.get(filename, {})
            
            model = {
                'id': i,
                'name': file_metadata.get('name', filename.rsplit('.', 1)[0]),
                'type': filename.rsplit('.', 1)[1].upper(),
                'size': f'{file_size_mb}MB',
                'date': file_metadata.get('upload_date', date_modified),
                'description': file_metadata.get('description', f'3D model file: {filename}'),
                'thumbnail': file_metadata.get('thumbnail'),
                'filename': filename
            }
            models.append(model)
    
    # Add sample data if no files exist (for demo purposes)
    if not models:
        sample_models = [
            {
                'id': 1,
                'name': 'Temple of Tooth',
                'type': 'OBJ',
                'size': '2.5MB',
                'date': '2025-01-15',
                'description': 'Sacred Buddhist temple in Kandy',
                'thumbnail': None,
                'filename': 'temple_of_tooth.obj'
            },
            {
                'id': 2,
                'name': 'Sigiriya Rock',
                'type': 'GLTF',
                'size': '8.2MB',
                'date': '2025-01-10',
                'description': 'Ancient rock fortress',
                'thumbnail': None,
                'filename': 'sigiriya_rock.gltf'
            }
        ]
        models.extend(sample_models)
    
    return models

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/viewer')
@app.route('/viewer/<int:model_id>')
def viewer(model_id=None):
    models = scan_models_folder()
    model = None
    if model_id:
        model = next((m for m in models if m['id'] == model_id), None)
    return render_template('viewer.html', model=model)

@app.route('/models')
def models():
    models_list = scan_models_folder()
    return render_template('models.html', models=models_list)

@app.route('/gallery')
def gallery():
    models_list = scan_models_folder()
    return render_template('gallery.html', models=models_list)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        # Check if file was uploaded
        if 'model_file' not in request.files:
            flash('No file selected')
            return redirect(request.url)
        
        file = request.files['model_file']
        model_name = request.form.get('model_name', '')
        description = request.form.get('description', '')
        
        if file.filename == '':
            flash('No file selected')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # Check if file already exists and handle it
            if os.path.exists(filepath):
                # Add timestamp to make filename unique
                name, ext = filename.rsplit('.', 1)
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{name}_{timestamp}.{ext}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            file.save(filepath)
            
            # Get file info
            file_size = os.path.getsize(filepath)
            file_size_mb = round(file_size / (1024 * 1024), 2)
            
            # Save metadata
            metadata = load_models_metadata()
            metadata[filename] = {
                'name': model_name or filename.rsplit('.', 1)[0],
                'description': description or f'3D model file: {filename}',
                'upload_date': datetime.datetime.now().strftime('%Y-%m-%d'),
                'thumbnail': None
            }
            save_models_metadata(metadata)
            
            # Get the model ID for the uploaded file
            models_list = scan_models_folder()
            uploaded_model = next((m for m in models_list if m['filename'] == filename), None)
            model_id = uploaded_model['id'] if uploaded_model else None
            
            flash(f'Successfully uploaded {filename}')
            return render_template('upload.html', 
                                 uploaded=True, 
                                 filename=filename, 
                                 filesize=f'{file_size_mb}MB',
                                 model_id=model_id)
        else:
            flash('Invalid file type. Allowed types: ' + ', '.join(ALLOWED_EXTENSIONS))
            return redirect(request.url)
    
    return render_template('upload.html', uploaded=False)

@app.route('/download/<int:model_id>')
def download_model(model_id):
    models_list = scan_models_folder()
    model = next((m for m in models_list if m['id'] == model_id), None)
    if model and 'filename' in model:
        # In production, implement actual file download using send_file
        from flask import send_from_directory
        try:
            return send_from_directory(app.config['UPLOAD_FOLDER'], model['filename'], as_attachment=True)
        except FileNotFoundError:
            flash('File not found')
    else:
        flash('Model not found')
    return redirect(url_for('models'))

@app.route('/delete/<int:model_id>')
def delete_model(model_id):
    """Delete a model file and its metadata"""
    models_list = scan_models_folder()
    model = next((m for m in models_list if m['id'] == model_id), None)
    
    if model and 'filename' in model:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], model['filename'])
        try:
            # Delete the file
            if os.path.exists(filepath):
                os.remove(filepath)
            
            # Remove from metadata
            metadata = load_models_metadata()
            if model['filename'] in metadata:
                del metadata[model['filename']]
                save_models_metadata(metadata)
            
            flash(f'Successfully deleted {model["name"]}')
        except Exception as e:
            flash(f'Error deleting file: {str(e)}')
    else:
        flash('Model not found')
    
    return redirect(url_for('models'))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    submitted = False
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']
        submitted = True
        # In a real app: send email / save to database
        return render_template('contact.html', submitted=submitted, name=name, email=email, message=message)
    return render_template('contact.html', submitted=submitted)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=81)