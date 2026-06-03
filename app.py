from flask import Flask, render_template, request, jsonify, session, send_from_directory, redirect, url_for
import anthropic
import os
import requests
import base64
import hashlib
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SECRET_KEY"))

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(os.path.join(os.path.dirname(__file__), 'static'), filename)

@app.route("/")
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if "riwayat" not in session:
        result = supabase.table("riwayat_chat").select("*").eq("user_id", session["user_id"]).order("created_at").execute()
        riwayat = []
        for item in result.data:
            riwayat.append({"role": "user", "content": item["pesan"]})
            riwayat.append({"role": "assistant", "content": item["jawaban"]})
        session["riwayat"] = riwayat
    return render_template("index.html", nama=session.get("nama"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.json.get("email")
        password = hash_password(request.json.get("password"))
        result = supabase.table("users").select("*").eq("email", email).eq("password", password).execute()
        if result.data:
            user = result.data[0]
            session["user_id"] = user["id"]
            session["nama"] = user["nama"]
            session["riwayat"] = []
            return jsonify({"success": True, "nama": user["nama"]})
        return jsonify({"success": False, "message": "Email atau password salah"})
    return render_template("login.html")

@app.route("/daftar", methods=["GET", "POST"])
def daftar():
    if request.method == "POST":
        email = request.json.get("email")
        password = hash_password(request.json.get("password"))
        nama = request.json.get("nama")
        cek = supabase.table("users").select("*").eq("email", email).execute()
        if cek.data:
            return jsonify({"success": False, "message": "Email sudah terdaftar"})
        supabase.table("users").insert({"email": email, "password": password, "nama": nama}).execute()
        return jsonify({"success": True})
    return render_template("daftar.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/chat", methods=["POST"])
def chat():
    if "user_id" not in session:
        return jsonify({"error": "Tidak terlogin"}), 401
    if "riwayat" not in session:
        session["riwayat"] = []
    pesan_user = request.json.get("pesan")
    riwayat = session["riwayat"]
    riwayat.append({"role": "user", "content": pesan_user})
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4096,
        timeout=120,
        system=f"Namamu adalah Kaego, asisten AI pribadi yang ramah dan ceria. Nama pengguna adalah {session.get('nama')}. Selalu sapa dengan 'Halo Kak {session.get('nama')}!' di awal percakapan. Gunakan bahasa Indonesia santai. Jangan pernah mengaku sebagai Claude atau Anthropic. Saat membuat soal pilihan ganda, tulis setiap pilihan di baris baru dengan tanda strip seperti: - a. pilihan - b. pilihan",
        messages=riwayat
    )
    jawaban = response.content[0].text
    riwayat.append({"role": "assistant", "content": jawaban})
    session["riwayat"] = riwayat
    supabase.table("riwayat_chat").insert({
        "user_id": session["user_id"],
        "pesan": pesan_user,
        "jawaban": jawaban
    }).execute()
    return jsonify({"jawaban": jawaban})

@app.route("/riwayat", methods=["GET"])
def get_riwayat():
    if "user_id" not in session:
        return jsonify({"error": "Tidak terlogin"}), 401
    result = supabase.table("riwayat_chat").select("*").eq("user_id", session["user_id"]).order("created_at").execute()
    return jsonify({"riwayat": result.data})

@app.route("/upload", methods=["POST"])
def upload():
    if "user_id" not in session:
        return jsonify({"error": "Tidak terlogin"}), 401
    
    try:
        file = request.files.get("file")
        pesan = request.form.get("pesan", "Tolong analisis file ini")
        
        if not file:
            return jsonify({"error": "Tidak ada file"}), 400
        
        file_data = file.read()
        file_base64 = base64.b64encode(file_data).decode("utf-8")
        file_type = file.content_type
        
        print(f"File: {file.filename}, type: {file_type}, size: {len(file_data)}")
        
        if "riwayat" not in session:
            session["riwayat"] = []
        riwayat = session["riwayat"]
        
        if file_type.startswith("image/"):
            content = [
                {"type": "image", "source": {"type": "base64", "media_type": file_type, "data": file_base64}},
                {"type": "text", "text": pesan}
            ]
        elif file_type == "application/pdf":
            content = [
                {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": file_base64}},
                {"type": "text", "text": pesan}
            ]
        else:
            return jsonify({"error": f"Format tidak didukung: {file_type}"}), 400
        
        riwayat.append({"role": "user", "content": content})
        
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=4096,
            timeout=120,
            system=f"Namamu adalah Kaego, asisten AI pribadi yang ramah dan ceria. Nama pengguna adalah {session.get('nama')}. Gunakan bahasa Indonesia santai. Jangan pernah mengaku sebagai Claude atau Anthropic.",
            messages=riwayat
        )
        
        jawaban = response.content[0].text
        riwayat.append({"role": "assistant", "content": jawaban})
        session["riwayat"] = riwayat
        
        supabase.table("riwayat_chat").insert({
            "user_id": session["user_id"],
            "pesan": f"[File: {file.filename}] {pesan}",
            "jawaban": jawaban
        }).execute()
        
        return jsonify({"jawaban": jawaban})
    
    except Exception as e:
        print(f"ERROR upload: {str(e)}")
        return jsonify({"error": str(e)}), 500
@app.route("/reset", methods=["POST"])
def reset():
    if "user_id" not in session:
        return jsonify({"error": "Tidak terlogin"}), 401
    session["riwayat"] = []
    return jsonify({"success": True})
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)