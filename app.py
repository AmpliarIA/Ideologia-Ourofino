from flask import Flask, request, jsonify
import requests
import os
import base64
from PIL import Image
from moviepy.editor import ImageClip, concatenate_videoclips, CompositeVideoClip
from io import BytesIO
import numpy as np

app = Flask(__name__)

def download_and_fit(url, width=1080, height=1350):
    response = requests.get(url)
    img = Image.open(BytesIO(response.content)).convert("RGB")
    
    # Mantém proporção com fundo preto
    img.thumbnail((width, height))
    background = Image.new('RGB', (width, height), (0, 0, 0))
    offset = ((width - img.width) // 2, (height - img.height) // 2)
    background.paste(img, offset)
    return np.array(background)

def make_slide_left_transition(clip1, clip2, duration=0.5, w=1080, h=1350):
    """Gera transição slide left entre dois clips"""
    fps = 24
    n_frames = int(fps * duration)
    frames = []

    arr1 = clip1.get_frame(clip1.duration - 0.01)
    arr2 = clip2.get_frame(0)

    for i in range(n_frames):
        progress = i / n_frames
        offset = int(w * progress)
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        frame[:, :w - offset] = arr1[:, offset:]
        frame[:, w - offset:] = arr2[:, :offset]
        frames.append(frame)

    return frames

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

@app.route('/gerar-video', methods=['POST'])
def gerar_video():
    data = request.json
    urls = data.get('imagens', [])
    duracao = data.get('duracao_por_imagem', 3)

    if not urls:
        return jsonify({"error": "Nenhuma imagem fornecida"}), 400

    W, H = 1080, 1350
    fps = 24

    # Baixa e prepara frames de cada imagem
    image_arrays = [download_and_fit(url, W, H) for url in urls]

    # Monta o vídeo com transição slide left
    all_frames = []

    for i, arr in enumerate(image_arrays):
        # Frames estáticos da imagem atual
        static_frames = int(fps * duracao)
        for _ in range(static_frames):
            all_frames.append(arr)

        # Transição para próxima imagem (exceto na última)
        if i < len(image_arrays) - 1:
            next_arr = image_arrays[i + 1]
            trans_frames = int(fps * 0.5)
            for j in range(trans_frames):
                progress = j / trans_frames
                offset = int(W * progress)
                frame = np.zeros((H, W, 3), dtype=np.uint8)
                frame[:, :W - offset] = arr[:, offset:]
                frame[:, W - offset:] = next_arr[:, :offset]
                all_frames.append(frame)

    # Converte para vídeo
    output_path = '/tmp/carrossel_output.mp4'
    
    import imageio
    writer = imageio.get_writer(output_path, fps=fps, codec='libx264', quality=7)
    for frame in all_frames:
        writer.append_data(frame)
    writer.close()

    # Retorna em base64
    with open(output_path, 'rb') as f:
        video_base64 = base64.b64encode(f.read()).decode('utf-8')

    os.remove(output_path)
    return jsonify({"video_base64": video_base64})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
```

Agora atualiza também o `requirements.txt`:
```
flask
requests
pillow
moviepy
numpy
imageio
imageio-ffmpeg
