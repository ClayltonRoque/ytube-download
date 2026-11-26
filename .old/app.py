import unicodedata
import re

def sanitize_filename(filename):
    # Remove acentos e converte para ASCII
    nfkd = unicodedata.normalize('NFKD', filename)
    only_ascii = nfkd.encode('ASCII', 'ignore').decode('ASCII')
    # Remove caracteres não permitidos
    return re.sub(r'[^a-zA-Z0-9._-]', '_', only_ascii)
from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import os
from flask import send_from_directory

app = Flask(__name__)
CORS(app)

# Pasta para salvar os downloads
DOWNLOAD_FOLDER = 'downloads'
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form.get('url')
        if not url:
            return '<p>URL não fornecida</p><a href="/">Voltar</a>'
        # Faz a requisição interna para o endpoint /baixar
        import requests as pyrequests
        try:
            response = pyrequests.post(request.host_url.rstrip('/') + '/baixar', json={'url': url})
            data = response.json()
            if 'download_url' in data:
                return f'<p>Download pronto: <a href="{data["download_url"]}">Clique aqui para baixar</a></p>'
            else:
                return f'<p>Erro: {data.get("erro", "Erro desconhecido")}</p><a href="/">Voltar</a>'
        except Exception as e:
            return f'<p>Erro: {str(e)}</p><a href="/">Voltar</a>'
    return '''
        <h2>Baixar música com yt-dlp</h2>
        <form method="post">
            <input type="text" name="url" placeholder="Cole o link aqui" size="50" required>
            <button type="submit">Baixar</button>
        </form>
    '''

# Endpoint para baixar música
@app.route('/baixar', methods=['POST'])
def baixar_musica():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'erro': 'URL não fornecida'}), 400
    url = data['url']
    try:
        # Comando yt-dlp para baixar apenas o áudio
        cmd = [
            'yt-dlp',
            '-x', '--audio-format', 'mp3',
            '-o', os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),
            url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        print('yt-dlp stdout:', result.stdout)
        print('yt-dlp stderr:', result.stderr)
        print('yt-dlp returncode:', result.returncode)
        if result.returncode != 0:
            return jsonify({'erro': 'Falha ao baixar', 'detalhe': result.stderr, 'stdout': result.stdout}), 500

        # Encontrar o nome do arquivo gerado
        for line in result.stdout.splitlines():
            if '[ExtractAudio]' in line and 'Destination' in line:
                filename = line.split('Destination')[-1].strip()
                break
        else:
            # fallback: procurar o arquivo mais recente na pasta
            files = [f for f in os.listdir(DOWNLOAD_FOLDER) if f.endswith('.mp3')]
            if not files:
                return jsonify({'erro': 'Arquivo não encontrado', 'stdout': result.stdout, 'stderr': result.stderr}), 500
            filename = max(files, key=lambda f: os.path.getctime(os.path.join(DOWNLOAD_FOLDER, f)))

        # Se filename for caminho completo, pegar só o nome
        filename = os.path.basename(filename)
        safe_filename = sanitize_filename(filename)
        # Renomeia o arquivo físico se necessário
        if safe_filename != filename:
            old_path = os.path.join(DOWNLOAD_FOLDER, filename)
            new_path = os.path.join(DOWNLOAD_FOLDER, safe_filename)
            os.rename(old_path, new_path)
        host_url = request.host_url.rstrip('/')
        download_url = host_url + '/download/' + safe_filename
        return jsonify({'mensagem': 'Download concluído', 'download_url': download_url})
    except Exception as e:
        import traceback
        print('Exception:', str(e))
        print(traceback.format_exc())
        return jsonify({'erro': str(e), 'traceback': traceback.format_exc()}), 500

# Endpoint para servir o arquivo baixado
@app.route('/download/<path:filename>', methods=['GET'])
def download_file(filename):
    from flask import Response
    import mimetypes
    import urllib.parse
    safe_filename = sanitize_filename(filename)
    file_path = os.path.join(DOWNLOAD_FOLDER, safe_filename)
    if not os.path.exists(file_path):
        return jsonify({'erro': 'Arquivo não encontrado'}), 404
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        mime_type = 'application/octet-stream'
    encoded_filename = urllib.parse.quote(safe_filename)
    response = send_from_directory(DOWNLOAD_FOLDER, safe_filename, as_attachment=True, mimetype=mime_type)
    response.headers['Content-Disposition'] = f'attachment; filename="{safe_filename}"; filename*=UTF-8''{encoded_filename}'
    return response

if __name__ == '__main__':
    app.run(debug=True)
