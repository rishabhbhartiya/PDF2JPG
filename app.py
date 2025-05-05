from flask import Flask, request, jsonify, send_from_directory, render_template_string
from pdf2image import convert_from_bytes
from PIL import Image
import os
import uuid
import zipfile
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

HTML_TEMPLATE = '''
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>PDF to JPG Converter</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      background-color: #f6f8fa;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 40px;
    }
    h1 {
      color: #333;
    }
    form {
      background: white;
      padding: 20px 30px;
      border-radius: 10px;
      box-shadow: 0 4px 10px rgba(0,0,0,0.1);
      display: flex;
      flex-direction: column;
      gap: 15px;
      width: 300px;
    }
    input[type="file"],
    input[type="text"] {
      padding: 5px;
      font-size: 14px;
    }
    input[type="submit"] {
      background-color: #007bff;
      color: white;
      padding: 10px;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      font-size: 16px;
    }
    input[type="submit"]:hover {
      background-color: #0056b3;
    }
    #result {
      margin-top: 25px;
      text-align: center;
    }
    #result button {
      background-color: #28a745;
      color: white;
      padding: 10px 15px;
      font-size: 16px;
      border: none;
      border-radius: 6px;
      cursor: pointer;
    }
    #result button:hover {
      background-color: #218838;
    }
  </style>
</head>
<body>
  <h1>PDF 2 JPG CONVERTER</h1>
  <form id="upload-form" method="post" enctype="multipart/form-data">
    <label>PDF File:</label>
    <input type="file" name="file" accept="application/pdf" required>
    <label>ZIP Filename (optional):</label>
    <input type="text" name="zipname" placeholder="e.g. my_images">
    <input type="submit" value="Convert to JPG">
  </form>
  <div id="result"></div>

  <script>
    const form = document.getElementById('upload-form');
    form.onsubmit = async (e) => {
      e.preventDefault();
      const formData = new FormData(form);
      const resultDiv = document.getElementById('result');
      resultDiv.innerHTML = 'Processing... Please wait ⏳';

      try {
        const res = await fetch('/upload', {
          method: 'POST',
          body: formData
        });
        const data = await res.json();
        if (data.zip_url) {
          resultDiv.innerHTML = `
            <p>✅ Conversion successful!</p>
            <a href="${data.zip_url}" download>
              <button>Download ZIP</button>
            </a>`;
        } else {
          resultDiv.innerHTML = '<p style="color: red;">❌ ' + (data.error || 'Unknown error') + '</p>';
        }
      } catch (err) {
        resultDiv.innerHTML = '<p style="color: red;">❌ An error occurred.</p>';
      }
    }
  </script>
</body>
</html>
'''

@app.route('/')
def form():
    return render_template_string(HTML_TEMPLATE)

@app.route('/upload', methods=['POST'])
def upload_pdf():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and file.filename.endswith('.pdf'):
        pdf_bytes = file.read()
        session_id = str(uuid.uuid4())
        session_folder = os.path.join(OUTPUT_FOLDER, session_id)
        os.makedirs(session_folder, exist_ok=True)

        try:
            # Convert PDF to high-res images
            images = convert_from_bytes(pdf_bytes, dpi=300)
            image_paths = []

            for i, img in enumerate(images):
                img_path = os.path.join(session_folder, f'page_{i+1}.jpg')
                img.save(img_path, 'JPEG', quality=95)
                image_paths.append(img_path)

            # Get optional zip name from form
            zipname = request.form.get('zipname', '').strip()
            if zipname:
                zipname = secure_filename(zipname)
            else:
                zipname = session_id

            zip_filename = f'{zipname}.zip'
            zip_path = os.path.join(OUTPUT_FOLDER, zip_filename)

            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for img_file in image_paths:
                    zipf.write(img_file, arcname=os.path.basename(img_file))

            return jsonify({'zip_url': f'/download_zip/{zip_filename}'})

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/download_zip/<filename>')
def download_zip(filename):
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
