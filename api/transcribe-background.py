import os
import io
import math
import yt_dlp
from flask import Flask, request, jsonify
from pydub import AudioSegment
from concurrent.futures import ThreadPoolExecutor
import openai

app = Flask(__name__)

@app.route('/api/transcribe-background', methods=['POST'])
def transcribe():
    data = request.get_json()
    youtube_url = data.get('youtubeURL')
    if not youtube_url:
        return jsonify({'error': 'É necessário fornecer a URL do YouTube.'}), 400

    # Definir a chave de API da OpenAI
    openai.api_key = os.environ.get("OPENAI_API_KEY")
    if not openai.api_key:
        return jsonify({'error': 'Chave de API da OpenAI não configurada.'}), 500

    try:
        # Baixar o áudio do YouTube para um buffer
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': '-',  # Saída padrão
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
            }],
            'prefer_ffmpeg': True,
            'quiet': True,
            'no_warnings': True,
            'outtmpl': 'audio.%(ext)s',
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])

        # Carregar o áudio em um buffer
        audio = AudioSegment.from_file('audio.wav', format='wav')

        # Dividir o áudio em chunks menores se necessário
        max_chunk_size_bytes = 24 * 1024 * 1024  # 24MB
        chunk_length_ms = math.floor(
            max_chunk_size_bytes / (audio.frame_rate * audio.frame_width * audio.channels)) * 1000

        chunks = [audio[i:i + chunk_length_ms] for i in range(0, len(audio), chunk_length_ms)]

        # Função para transcrever cada chunk
        def transcribe_chunk(chunk, idx):
            audio_buffer = io.BytesIO()
            chunk.export(audio_buffer, format="wav")
            audio_buffer.seek(0)  # Move to the start of the buffer
            audio_buffer.name = f"chunk_{idx}.wav"  # Set the name attribute with the correct extension

            transcription = openai.Audio.transcribe(
                model="whisper-1",
                file=audio_buffer
            )
            return transcription['text']

        # Transcrever os chunks
        with ThreadPoolExecutor() as executor:
            transcriptions = list(executor.map(transcribe_chunk, chunks, range(len(chunks))))

        full_transcription = " ".join(transcriptions)

        # Melhorar a transcrição
        def improve_transcription(transcript):
            system_prompt = '''Your task is to take raw transcripts and enhance them for clarity while
            preserving every detail and nuance. The goal is to maintain the richness and flow of
            the original content, improving readability without omitting or overly summarizing any
            part of the transcript. Ensure that the full context, depth, and meaning are retained in the final version.'''
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"This is the transcript: {transcript}"}
                ],
                temperature=0
            )
            return response['choices'][0]['message']['content']

        # Gerar o sumário em português
        def sumario_portugues(text):
            system_prompt = '''faça um sumário em português do texto apresentado, 
            em um formato simples de ler, usando bullet-points quando apropriado'''
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Este é o texto: {text}"}
                ],
                temperature=0
            )
            return response['choices'][0]['message']['content']

        # Melhorar a transcrição
        revised_transcription = improve_transcription(full_transcription)

        # Gerar o sumário em português
        summary = sumario_portugues(revised_transcription)

        # Limpar arquivos temporários
        os.remove('audio.wav')

        return jsonify({'summary': summary})

    except Exception as e:
        return jsonify({'error': str(e)}), 500
