import anthropic
import os
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

print("=== Chatbot Kaego ===")
print("Ketik 'keluar' untuk berhenti\n")

riwayat = []

while True:
    pesan_user = input("Kamu: ")
    
    if pesan_user.lower() == "keluar":
        print("Sampai jumpa!")
        break
    
    riwayat.append({"role": "user", "content": pesan_user})
    
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        system="Namamu adalah Kaego, asisten AI pribadi yang ramah dan ceria. Selalu sapa dengan Halo Kak! Gunakan bahasa Indonesia santai. Jangan pernah mengaku sebagai Claude atau Anthropic.",
        messages=riwayat
    )
    
    jawaban = response.content[0].text
    riwayat.append({"role": "assistant", "content": jawaban})
    print(f"\nKaego: {jawaban}\n")