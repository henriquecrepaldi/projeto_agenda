import sqlite3
import threading
import time
import urllib.parse
import smtplib
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__, template_folder="../templates")

# --- CONFIGURAÇÕES DE E-MAIL (Preenche aqui) ---
MEU_EMAIL = "crepaldi.henrique@gmail.com"
MINHA_SENHA = "odbnyeiycotunwsw"
MEU_ZAP = "5521992851164"

servicos_detalhados = [
{"nome": "Acupuntura", "preco": "40€", "resumo": "Técnica milenar para dores e stress."},
{"nome": "Massagem Relaxante", "preco": "35€", "resumo": "Relaxamento muscular profundo."},
{"nome": "Drenagem Linfática", "preco": "45€", "resumo": "Eliminação de toxinas e inchaço."}
]

# --- 1. BASE DE DADOS ---
def init_db():
    conn = sqlite3.connect('/tmp/agenda.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agendamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente TEXT NOT NULL,
            email_cliente TEXT NOT NULL,
            servico TEXT NOT NULL,
            horario TEXT NOT NULL,
            pago INTEGER DEFAULT 0,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# --- 2. LIMPEZA AUTOMÁTICA (5 MINUTOS) ---
def limpar_expirados():
    while True:
        time.sleep(60)
        conn = sqlite3.connect('/tmp/agenda.db')
        cursor = conn.cursor()
        limite = (datetime.now() - timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("DELETE FROM agendamentos WHERE pago = 0 AND timestamp < ?", (limite,))
        conn.commit()
        conn.close()

threading.Thread(target=limpar_expirados, daemon=True).start()

# --- 3. FUNÇÃO DE E-MAIL ---
def enviar_email(destinatario, dados):
    msg = MIMEMultipart()
    msg['From'] = MEU_EMAIL
    msg['To'] = destinatario
    msg['Subject'] = "✅ Agendamento Confirmado!"
    corpo = f"Olá {dados['nome']},\nTeu horário para {dados['servico']} às {dados['horario']} foi confirmado!"
    msg.attach(MIMEText(corpo, 'plain'))
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(MEU_EMAIL, MINHA_SENHA)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print(f"Erro e-mail: {e}")

# --- 4. ROTAS DO SITE ---
@app.route('/')
def index():
    servicos = ["crochetagem - R$150", "drenagem linfatica - R$150", "flossband - R$150", "liberação miofacial R$170", "massagem craniana - R$150", "massagem desportiva - R$170", "massagem estética - R$150", "massagem relaxante - R$150", "massagem terapeutica - R$170","moxabustâo - R$150", "quiromassagem - R$170","reflexologia podal - R$150","shiatsu - R$150", "ventosaterapia - R$150", "acupuntura - R$170", "Combo - R$200"]
    return render_template('index.html', servicos=servicos)

@app.route('/agendar', methods=['POST'])
def agendar():
    nome = request.form['nome']
    email = request.form['email_cliente']
    servico = request.form['servico']
    horario = request.form['horario']

    conn = sqlite3.connect('/tmp/agenda.db')
    cursor = conn.cursor()
    
    # Verifica duplicado
    cursor.execute("SELECT * FROM agendamentos WHERE horario = ?", (horario,))
    if cursor.fetchone():
        conn.close()
        return "<h1>Horário Ocupado!</h1><a href='/'>Voltar</a>"

    cursor.execute("INSERT INTO agendamentos (cliente, email_cliente, servico, horario) VALUES (?, ?, ?, ?)", 
                   (nome, email, servico, horario))
    reserva_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return redirect(f'/pagamento/{reserva_id}')

@app.route('/pagamento/<int:reserva_id>')
def pagamento(reserva_id):
    return render_template('pagamento.html', id=reserva_id)

@app.route('/confirmar/<int:reserva_id>')
def confirmar(reserva_id):
    conn = sqlite3.connect('/tmp/agenda.db')
    cursor = conn.cursor()
    cursor.execute("SELECT cliente, email_cliente, servico, horario FROM agendamentos WHERE id=?", (reserva_id,))
    res = cursor.fetchone()
    cursor.execute("UPDATE agendamentos SET pago = 1 WHERE id = ?", (reserva_id,))
    conn.commit()
    conn.close()

    enviar_email(res[1], {'nome': res[0], 'servico': res[2], 'horario': res[3]})
    
    msg_zap = urllib.parse.quote(f"Novo Agendamento: {res[0]} - {res[2]} às {res[3]}")
    return redirect(f"https://wa.me/351912345678?text={msg_zap}")

init_db()
app.debug = True
