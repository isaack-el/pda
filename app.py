from flask import Flask, render_template, request, jsonify
from pda_engine import PDA
import json

app = Flask(__name__)

# Validator examples
VALIDATOR_EXAMPLES = {
    'parentheses': [
        '((a + b) * c)',
        '({[<>]})',
        '((a + b) * c',
        ')(',
        'a + b * c'
    ],
    'xml': [
        '<div><p>Hello</p></div>',
        '<a><b><c></c></b></a>',
        '<div><p>Hello</div>',
        '<tag>content</tag>',
        '<open>no close'
    ],
    'json': [
        '{"name": "John", "age": 30}',
        '{"users": [{"id": 1}, {"id": 2}]}',
        '{"name": "John", "age": 30',
        '{"key": "value",}',
        '{invalid: json}'
    ]
}

VALIDATOR_INFO = {
    'parentheses': {
        'name': 'Parentheses Validator',
        'description': 'Validates balanced parentheses: (), [], {}, <>',
        'icon': 'fa-parentheses'
    },
    'xml': {
        'name': 'XML/HTML Validator',
        'description': 'Validates simple XML/HTML tag structures',
        'icon': 'fa-code'
    },
    'json': {
        'name': 'JSON Validator',
        'description': 'Validates JSON format and structure',
        'icon': 'fa-braille'
    }
}

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html', 
                         validators=VALIDATOR_INFO,
                         examples=VALIDATOR_EXAMPLES)

@app.route('/validate', methods=['POST'])
def validate():
    """Validate endpoint"""
    data = request.get_json()
    validator_type = data.get('type', 'parentheses')
    input_text = data.get('text', '')
    
    # Create PDA and validate
    pda = PDA()
    
    if validator_type == 'parentheses':
        is_valid, history = pda.process_parentheses(input_text)
    elif validator_type == 'xml':
        is_valid, history = pda.process_xml(input_text)
    elif validator_type == 'json':
        is_valid, history = pda.process_json(input_text)
    else:
        return jsonify({
            'error': 'Invalid validator type',
            'valid': False
        }), 400
    
    # Get transition table
    transition_table = pda.get_transition_table(validator_type)
    
    return jsonify({
        'valid': is_valid,
        'history': history,
        'final_stack': pda.stack,
        'final_state': pda.current_state,
        'stack_size': len(pda.stack),
        'steps': len(history),
        'transition_table': transition_table
    })

@app.route('/examples/<validator_type>')
def get_examples(validator_type):
    """Get examples for validator"""
    if validator_type in VALIDATOR_EXAMPLES:
        return jsonify({
            'examples': VALIDATOR_EXAMPLES[validator_type]
        })
    return jsonify({'error': 'Validator not found'}), 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)

from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import os
import json
import tempfile
import mimetypes
from datetime import datetime
import io
import uuid
from pda_engine import PDA
import traceback

app = Flask(__name__)

# Konfigurasi upload file
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max file size
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()
app.config['ALLOWED_EXTENSIONS'] = {
    'txt', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 
    'jpg', 'jpeg', 'png', 'gif', 'xml', 'html', 'htm', 'json'
}

# Validator examples
VALIDATOR_EXAMPLES = {
    'filename': [
        'laporan_final.pdf',
        'tugas1.docx',
        'data_123.xlsx',
        'laporan.final.docx',
        'file@baru.pdf',
        'dokumen.ppt'
    ],
    'content': [
        '%PDFabc123',
        'PK_random_data',
        'plaintext123',
        'XPDF123',
        'PK@@@'
    ],
    'filetype': [
        'pdf',
        'docx',
        'jpg',
        'xlsx',
        'ppt',
        'mp4'
    ],
    'xml': [
        '<data>HELLO</data>',
        '<b>123</b>',
        '<data>HELLO</b>',
        '<data>123'
    ],
    'multilevel': [
        '<data>HELLO</data>',
        '<b>valid.pdf</b>',
        '<data>invalid.ppt</data>',
        '<data>file@invalid.pdf</data>'
    ]
}

VALIDATOR_INFO = {
    'filename': {
        'name': 'Validasi Nama File',
        'description': 'Validasi format nama file: huruf, angka, underscore, ekstensi pdf/docx/xlsx',
        'icon': 'fa-file',
        'supported_files': ['.pdf', '.docx', '.xlsx', '.txt', '.jpg', '.png', '.xml', '.html']
    },
    'content': {
        'name': 'Validasi Isi File',
        'description': 'Validasi konten berdasarkan header/format file (PDF: %PDF, DOCX: PK, TXT: huruf/angka)',
        'icon': 'fa-file-alt',
        'supported_files': ['.pdf', '.docx', '.txt', '.xml', '.html']
    },
    'filetype': {
        'name': 'Validasi Tipe File',
        'description': 'Validasi ekstensi file berdasarkan kategori (PDF, DOC/DOCX, Gambar, Spreadsheet)',
        'icon': 'fa-file-code',
        'supported_files': ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.jpg', '.jpeg', '.png', '.gif', '.txt', '.xml', '.html']
    },
    'xml': {
        'name': 'Validasi XML/HTML',
        'description': 'Validasi struktur tag XML/HTML yang cocok (tag pembuka dan penutup)',
        'icon': 'fa-code',
        'supported_files': ['.xml', '.html', '.htm', '.txt']
    },
    'multilevel': {
        'name': 'Validasi Multi-Level',
        'description': 'Validasi nama file, format, dan struktur dokumen sekaligus',
        'icon': 'fa-layer-group',
        'supported_files': ['.xml', '.html', '.txt', '.pdf', '.docx']
    }
}


# Helper functions
def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def get_file_info(filepath):
    """Get file information"""
    if not os.path.exists(filepath):
        return None
    
    stats = os.stat(filepath)
    filename = os.path.basename(filepath)
    
    return {
        'name': filename,
        'size': stats.st_size,
        'modified': datetime.fromtimestamp(stats.st_mtime).isoformat(),
        'created': datetime.fromtimestamp(stats.st_ctime).isoformat(),
        'extension': os.path.splitext(filename)[1].lower(),
        'mime_type': mimetypes.guess_type(filename)[0] or 'application/octet-stream'
    }


def read_file_content(filepath, max_chars=5000):
    """Read file content with safety limits"""
    try:
        # Check if it's a binary file
        with open(filepath, 'rb') as f:
            first_bytes = f.read(1024)
        
        # Try to decode as text if it seems like text
        try:
            # Check common text encodings
            for encoding in ['utf-8', 'latin-1', 'ascii']:
                try:
                    with open(filepath, 'r', encoding=encoding, errors='ignore') as f:
                        content = f.read(max_chars)
                    return content, 'text'
                except:
                    continue
            
            # If not text, check for specific binary signatures
            if first_bytes.startswith(b'%PDF'):
                return 'PDF_FILE_SIGNATURE_DETECTED', 'binary'
            elif first_bytes.startswith(b'PK'):
                return 'ZIP_FILE_SIGNATURE_DETECTED (DOCX/XLSX)', 'binary'
            elif first_bytes.startswith(b'\xff\xd8\xff'):
                return 'JPEG_FILE_SIGNATURE_DETECTED', 'binary'
            elif first_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
                return 'PNG_FILE_SIGNATURE_DETECTED', 'binary'
            else:
                return 'BINARY_FILE_CONTENT', 'binary'
        except Exception as e:
            return f"Error reading file: {str(e)}", 'error'
    except Exception as e:
        return f"Error opening file: {str(e)}", 'error'


def validate_filename_pattern(filename):
    """Validate filename pattern"""
    import re
    pattern = r'^[a-zA-Z0-9_]+(\.[a-zA-Z0-9_]+)*\.[a-zA-Z]{3,4}$'
    return bool(re.match(pattern, filename))


def get_file_icon(filename):
    """Get appropriate icon for file type"""
    ext = filename.split('.')[-1].lower() if '.' in filename else ''
    
    icon_map = {
        'pdf': 'fas fa-file-pdf',
        'doc': 'fas fa-file-word',
        'docx': 'fas fa-file-word',
        'xls': 'fas fa-file-excel',
        'xlsx': 'fas fa-file-excel',
        'jpg': 'fas fa-file-image',
        'jpeg': 'fas fa-file-image',
        'png': 'fas fa-file-image',
        'gif': 'fas fa-file-image',
        'txt': 'fas fa-file-alt',
        'xml': 'fas fa-file-code',
        'html': 'fas fa-file-code',
        'htm': 'fas fa-file-code',
        'json': 'fas fa-file-code'
    }
    
    return icon_map.get(ext, 'fas fa-file')


@app.route('/')
def index():
    """Main page"""
    return render_template('index.html', 
                         validators=VALIDATOR_INFO,
                         examples=VALIDATOR_EXAMPLES)


@app.route('/validate', methods=['POST'])
def validate():
    """Validate endpoint"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'error': 'No data provided',
                'valid': False
            }), 400
        
        validator_type = data.get('type', 'filename')
        input_text = data.get('text', '')
        
        # Create PDA and validate
        pda = PDA()
        
        if validator_type == 'filename':
            is_valid, history = pda.process_filename(input_text)
        elif validator_type == 'content':
            is_valid, history = pda.process_content(input_text)
        elif validator_type == 'filetype':
            is_valid, history = pda.process_filetype(input_text)
        elif validator_type == 'xml':
            is_valid, history = pda.process_xml(input_text)
        elif validator_type == 'multilevel':
            is_valid, history = pda.process_multilevel(input_text)
        else:
            return jsonify({
                'error': 'Invalid validator type',
                'valid': False
            }), 400
        
        # Get transition table
        transition_table = pda.get_transition_table(validator_type)
        
        return jsonify({
            'valid': is_valid,
            'history': history,
            'final_stack': pda.stack,
            'final_state': pda.current_state,
            'stack_size': len(pda.stack),
            'steps': len(history),
            'transition_table': transition_table
        })
        
    except Exception as e:
        app.logger.error(f"Validation error: {str(e)}")
        return jsonify({
            'error': f'Validation error: {str(e)}',
            'valid': False
        }), 500


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload"""
    try:
        # Check if files are present
        if 'files' not in request.files:
            return jsonify({
                'error': 'No files provided',
                'success': False
            }), 400
        
        files = request.files.getlist('files')
        validator_type = request.form.get('validator_type', 'filename')
        
        if not files or files[0].filename == '':
            return jsonify({
                'error': 'No selected files',
                'success': False
            }), 400
        
        uploaded_files = []
        errors = []
        
        for file in files:
            if file and allowed_file(file.filename):
                try:
                    # Secure filename
                    filename = secure_filename(file.filename)
                    
                    # Create unique filename
                    unique_id = str(uuid.uuid4())[:8]
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    unique_filename = f"{timestamp}_{unique_id}_{filename}"
                    
                    # Save file
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    file.save(filepath)
                    
                    # Get file info
                    file_info = get_file_info(filepath)
                    if file_info:
                        # Read file content
                        content, content_type = read_file_content(filepath)
                        
                        file_info.update({
                            'id': unique_id,
                            'path': filepath,
                            'content': content,
                            'content_type': content_type,
                            'icon': get_file_icon(filename),
                            'validator_type': validator_type,
                            'upload_time': datetime.now().isoformat()
                        })
                        
                        uploaded_files.append(file_info)
                        
                        # Log upload
                        app.logger.info(f"File uploaded: {filename} ({file_info['size']} bytes)")
                    else:
                        errors.append(f"Could not get info for {filename}")
                        
                except Exception as e:
                    errors.append(f"Error processing {file.filename}: {str(e)}")
            else:
                errors.append(f"File type not allowed: {file.filename}")
        
        return jsonify({
            'success': True,
            'files': uploaded_files,
            'total': len(uploaded_files),
            'errors': errors
        })
        
    except Exception as e:
        app.logger.error(f"Upload error: {str(e)}")
        return jsonify({
            'error': f'Upload error: {str(e)}',
            'success': False
        }), 500


@app.route('/process-upload', methods=['POST'])
def process_uploaded_file():
    """Process uploaded file for validation"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'error': 'No data provided',
                'valid': False
            }), 400
        
        file_info = data.get('file_info', {})
        validator_type = data.get('validator_type', 'filename')
        
        if not file_info or 'path' not in file_info:
            return jsonify({
                'error': 'Invalid file info',
                'valid': False
            }), 400
        
        filepath = file_info['path']
        
        # Check if file exists
        if not os.path.exists(filepath):
            return jsonify({
                'error': 'File not found',
                'valid': False
            }), 404
        
        # Process based on validator type
        pda = PDA()
        is_valid = False
        history = []
        input_text = ""
        
        if validator_type == 'filename':
            # Use filename for validation
            filename = os.path.basename(filepath)
            input_text = filename
            is_valid, history = pda.process_filename(filename)
            
        elif validator_type == 'content':
            # Use file content for validation
            content, content_type = read_file_content(filepath)
            input_text = content[:100] + "..." if len(content) > 100 else content
            
            # Process content based on file type
            if 'PDF' in content:
                is_valid, history = pda.process_content('%PDF')
            elif 'ZIP' in content:
                is_valid, history = pda.process_content('PK')
            elif content_type == 'text':
                is_valid, history = pda.process_content(content[:50])
            else:
                is_valid, history = pda.process_content(content)
                
        elif validator_type == 'filetype':
            # Use file extension for validation
            extension = file_info.get('extension', '').lstrip('.')
            input_text = extension
            is_valid, history = pda.process_filetype(extension)
            
        elif validator_type == 'xml':
            # Read XML content
            content, content_type = read_file_content(filepath)
            if content_type == 'text':
                input_text = content[:500]
                is_valid, history = pda.process_xml(input_text)
            else:
                return jsonify({
                    'error': 'File is not text-based XML',
                    'valid': False
                }), 400
                
        elif validator_type == 'multilevel':
            # Read file content
            content, content_type = read_file_content(filepath)
            if content_type == 'text':
                input_text = content[:500]
                is_valid, history = pda.process_multilevel(input_text)
            else:
                # For binary files, use filename in XML format
                filename = os.path.basename(filepath)
                input_text = f"<file>{filename}</file>"
                is_valid, history = pda.process_multilevel(input_text)
        
        else:
            return jsonify({
                'error': 'Invalid validator type',
                'valid': False
            }), 400
        
        # Get transition table
        transition_table = pda.get_transition_table(validator_type)
        
        return jsonify({
            'valid': is_valid,
            'history': history,
            'final_stack': pda.stack,
            'final_state': pda.current_state,
            'stack_size': len(pda.stack),
            'steps': len(history),
            'transition_table': transition_table,
            'input_text': input_text,
            'file_info': file_info
        })
        
    except Exception as e:
        app.logger.error(f"Process upload error: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            'error': f'Process error: {str(e)}',
            'valid': False
        }), 500


@app.route('/batch-validate', methods=['POST'])
def batch_validate():
    """Validate multiple files at once"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'error': 'No data provided',
                'valid': False
            }), 400
        
        files_info = data.get('files', [])
        validator_type = data.get('validator_type', 'filename')
        
        if not files_info:
            return jsonify({
                'error': 'No files provided',
                'valid': False
            }), 400
        
        results = []
        
        for file_info in files_info:
            try:
                # Process each file
                filepath = file_info.get('path', '')
                
                if not os.path.exists(filepath):
                    results.append({
                        'filename': file_info.get('name', 'unknown'),
                        'valid': False,
                        'error': 'File not found'
                    })
                    continue
                
                # Process based on validator type
                pda = PDA()
                is_valid = False
                history = []
                
                if validator_type == 'filename':
                    filename = os.path.basename(filepath)
                    is_valid, history = pda.process_filename(filename)
                    
                elif validator_type == 'content':
                    content, content_type = read_file_content(filepath)
                    if 'PDF' in content:
                        is_valid, history = pda.process_content('%PDF')
                    elif 'ZIP' in content:
                        is_valid, history = pda.process_content('PK')
                    elif content_type == 'text':
                        is_valid, history = pda.process_content(content[:50])
                    else:
                        is_valid, history = pda.process_content(content)
                        
                elif validator_type == 'filetype':
                    extension = os.path.splitext(file_info.get('name', ''))[1].lstrip('.')
                    is_valid, history = pda.process_filetype(extension)
                    
                elif validator_type == 'xml':
                    content, content_type = read_file_content(filepath)
                    if content_type == 'text':
                        is_valid, history = pda.process_xml(content[:500])
                    else:
                        results.append({
                            'filename': file_info.get('name', 'unknown'),
                            'valid': False,
                            'error': 'Not text-based XML'
                        })
                        continue
                        
                elif validator_type == 'multilevel':
                    content, content_type = read_file_content(filepath)
                    if content_type == 'text':
                        is_valid, history = pda.process_multilevel(content[:500])
                    else:
                        filename = os.path.basename(filepath)
                        is_valid, history = pda.process_multilevel(f"<file>{filename}</file>")
                
                results.append({
                    'filename': file_info.get('name', 'unknown'),
                    'valid': is_valid,
                    'steps': len(history),
                    'final_state': pda.current_state,
                    'stack_size': len(pda.stack)
                })
                
            except Exception as e:
                results.append({
                    'filename': file_info.get('name', 'unknown'),
                    'valid': False,
                    'error': str(e)
                })
        
        # Calculate statistics
        total_files = len(results)
        valid_files = sum(1 for r in results if r.get('valid', False))
        invalid_files = total_files - valid_files
        
        return jsonify({
            'success': True,
            'results': results,
            'statistics': {
                'total': total_files,
                'valid': valid_files,
                'invalid': invalid_files,
                'valid_percentage': round((valid_files / total_files * 100) if total_files > 0 else 0, 2)
            }
        })
        
    except Exception as e:
        app.logger.error(f"Batch validate error: {str(e)}")
        return jsonify({
            'error': f'Batch validation error: {str(e)}',
            'success': False
        }), 500


@app.route('/download-results', methods=['POST'])
def download_results():
    """Download validation results as JSON"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'error': 'No data provided'
            }), 400
        
        # Create results data
        results_data = {
            'timestamp': datetime.now().isoformat(),
            'validator_type': data.get('validator_type', 'unknown'),
            'validation_results': data.get('results', []),
            'statistics': data.get('statistics', {})
        }
        
        # Create JSON file
        json_data = json.dumps(results_data, indent=2, ensure_ascii=False)
        
        # Create download response
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"pda_validation_results_{timestamp}.json"
        
        return send_file(
            io.BytesIO(json_data.encode('utf-8')),
            mimetype='application/json',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        app.logger.error(f"Download results error: {str(e)}")
        return jsonify({
            'error': f'Download error: {str(e)}'
        }), 500


@app.route('/examples/<validator_type>')
def get_examples(validator_type):
    """Get examples for validator"""
    if validator_type in VALIDATOR_EXAMPLES:
        return jsonify({
            'examples': VALIDATOR_EXAMPLES[validator_type],
            'validator_info': VALIDATOR_INFO.get(validator_type, {})
        })
    return jsonify({'error': 'Validator not found'}), 404


@app.route('/validator-info/<validator_type>')
def get_validator_info(validator_type):
    """Get detailed info for validator"""
    if validator_type in VALIDATOR_INFO:
        return jsonify(VALIDATOR_INFO[validator_type])
    return jsonify({'error': 'Validator not found'}), 404


@app.route('/supported-extensions/<validator_type>')
def get_supported_extensions(validator_type):
    """Get supported file extensions for validator"""
    if validator_type in VALIDATOR_INFO:
        extensions = VALIDATOR_INFO[validator_type].get('supported_files', [])
        return jsonify({
            'extensions': extensions,
            'count': len(extensions)
        })
    return jsonify({'error': 'Validator not found'}), 404


@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'validators': list(VALIDATOR_INFO.keys()),
        'upload_folder': app.config['UPLOAD_FOLDER']
    })


@app.route('/cleanup', methods=['POST'])
def cleanup_files():
    """Clean up uploaded files"""
    try:
        data = request.get_json()
        file_paths = data.get('file_paths', [])
        
        deleted_count = 0
        errors = []
        
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    deleted_count += 1
                    app.logger.info(f"Deleted file: {file_path}")
            except Exception as e:
                errors.append(f"Error deleting {file_path}: {str(e)}")
        
        return jsonify({
            'success': True,
            'deleted_count': deleted_count,
            'errors': errors
        })
        
    except Exception as e:
        app.logger.error(f"Cleanup error: {str(e)}")
        return jsonify({
            'error': f'Cleanup error: {str(e)}',
            'success': False
        }), 500


# Error handlers
@app.errorhandler(413)
def too_large(error):
    return jsonify({
        'error': 'File too large (max 10MB)',
        'success': False
    }), 413


@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Endpoint not found',
        'success': False
    }), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'Internal server error',
        'success': False
    }), 500


if __name__ == '__main__':
    # Create upload folder if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Set up logging
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 50)
    print("PDA Simulator - Validasi Dokumen Otomatis")
    print("=" * 50)
    print(f"Upload folder: {app.config['UPLOAD_FOLDER']}")
    print(f"Max file size: {app.config['MAX_CONTENT_LENGTH'] / (1024*1024)} MB")
    print(f"Supported validators: {', '.join(VALIDATOR_INFO.keys())}")
    print("=" * 50)
    print("Starting server on http://127.0.0.1:5000")
    
    app.run(debug=True, host='0.0.0.0', port=5000)