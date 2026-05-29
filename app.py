from flask import Flask, render_template, request, jsonify, session
import anthropic
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

@app.route("/")
def home():
    session["riwayat"] = []
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    if "riwayat" not in session:
        session["riwayat"] = []
    
    pesan_user = request.json.get("pesan")
    riwayat = session["riwayat"]
    riwayat.append({"role": "user", "content": pesan_user})
    
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        system="""Namamu adalah Kaego, asisten AI pribadi yang ramah dan ceria. Selalu sapa dengan Halo Kak! Gunakan bahasa Indonesia santai. Jangan pernah mengaku sebagai Claude atau Anthropic.

Saat membuat soal pilihan ganda, WAJIB gunakan format ini:

1. Pertanyaan soal?

a. Pilihan A
b. Pilihan B
c. Pilihan C
d. Pilihan D

2. Pertanyaan soal berikutnya?

a. Pilihan A
b. Pilihan B
c. Pilihan C
d. Pilihan D

Setiap pilihan HARUS di baris baru. Jangan gabungkan dalam satu baris.""",
        messages=riwayat
    )
    
    jawaban = response.content[0].text
    riwayat.append({"role": "assistant", "content": jawaban})
    session["riwayat"] = riwayat
    return jsonify({"jawaban": jawaban})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)