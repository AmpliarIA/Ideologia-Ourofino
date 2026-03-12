from flask import Flask, request, jsonify
import requests
import os
import uuid
from PIL import Image
from moviepy.editor import ImageClip, concatenate_videoclips
from io import BytesIO

app = Flask(__name__)

OUTPUT_DIR = "/tmp/videos"
os.makedirs(OUTPUT_DIR, exist_ok=True)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/gerar-video", methods=["POST"])
def gerar_video():
    data = request.json

    # Valida entrada
    urls = data.get("imagens", [])
    duracao = data.get("duracao_por_imagem", 3)  # segundos por imagem

    if not urls or len(urls) < 2:
        return jsonify({"erro": "Envie ao menos 2 URLs de imagens"}), 400

    video_id = str(uuid.uuid4())
    output_path = f"{OUTPUT_DIR}/{video_id}.mp4"
    temp_files = []

    try:
        clips = []

        for i, url in enumerate(urls):
            # Baixa a imagem
            response = requests.get(url, timeout=15)
            response.raise_for_status()

            # Abre e redimensiona para 1080x1080
            img = Image.open(BytesIO(response.content)).convert("RGB")
            img = img.resize((1080, 1080), Image.LANCZOS)

            # Salva temporariamente
            temp_path = f"/tmp/{video_id}_frame_{i}.jpg"
            img.save(temp_path, quality=95)
            temp_files.append(temp_path)

            # Cria o clip com duração definida
            clip = ImageClip(temp_path).set_duration(duracao)
            clips.append(clip)

        # Concatena todos os clips
        final = concatenate_videoclips(clips, method="compose")
        final.write_videofile(
            output_path,
            fps=24,
            codec="libx264",
            audio=False,
            verbose=False,
            logger=None
        )
        final.close()

        # Lê o vídeo gerado e converte para base64
        import base64
        with open(output_path, "rb") as f:
            video_base64 = base64.b64encode(f.read()).decode("utf-8")

        return jsonify({
            "sucesso": True,
            "video_base64": video_base64,
            "total_imagens": len(urls),
            "duracao_total": len(urls) * duracao
        })

    except Exception as e:
        return jsonify({"erro": str(e)}), 500

    finally:
        # Limpa arquivos temporários
        for f in temp_files:
            if os.path.exists(f):
                os.remove(f)
        if os.path.exists(output_path):
            os.remove(output_path)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
