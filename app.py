from flask import Flask, request, redirect, url_for, render_template, send_from_directory, session
import sqlite3
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.secret_key = "segredo_super_seguro"  # Necessário para sessão

# Cria pasta de uploads se não existir
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Lista fixa de usuários e senhas
USUARIOS = {
    "geop": "praca2304",
    "geseg": "praca2304",
    "admin": "praca2304",
    "teste": "praca2304"
}

# Inicializa banco de dados
def init_db():
    conn = sqlite3.connect('lojas.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS loja (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    endereco TEXT,
                    telefone TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS documento (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    loja_id INTEGER,
                    nome_arquivo TEXT,
                    caminho TEXT,
                    FOREIGN KEY(loja_id) REFERENCES loja(id))''')
    conn.commit()
    conn.close()

init_db()

# ---------------- ROTAS ---------------- #

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        senha = request.form['senha']
        # Valida contra lista fixa
        if usuario in USUARIOS and USUARIOS[usuario] == senha:
            session['usuario'] = usuario
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', erro="Usuário ou senha inválidos")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect('lojas.db')
    c = conn.cursor()
    c.execute("SELECT * FROM loja")
    lojas = c.fetchall()

    lojas_com_pdf = []
    for loja in lojas:
        c.execute("SELECT * FROM documento WHERE loja_id=?", (loja[0],))
        doc = c.fetchone()
        lojas_com_pdf.append({
            "id": loja[0],
            "nome": loja[1],
            "endereco": loja[2],
            "telefone": loja[3],
            "pdf": doc[2] if doc else None,
            "tem_pdf": True if doc else False
        })

    conn.close()
    return render_template('dashboard.html', lojas=lojas_com_pdf)


@app.route('/cadastro_loja', methods=['GET', 'POST'])
def cadastro_loja():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        nome = request.form['nome']
        endereco = request.form['endereco']
        telefone = request.form['telefone']
        conn = sqlite3.connect('lojas.db')
        c = conn.cursor()
        c.execute("INSERT INTO loja (nome, endereco, telefone) VALUES (?, ?, ?)", (nome, endereco, telefone))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))
    return render_template('cadastro_loja.html')

@app.route('/upload/<int:loja_id>', methods=['POST'])
def upload(loja_id):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    file = request.files['file']
    if file:
        conn = sqlite3.connect('lojas.db')
        c = conn.cursor()

        # Verifica se já existe PDF para essa loja
        c.execute("SELECT caminho FROM documento WHERE loja_id=?", (loja_id,))
        existente = c.fetchone()
        if existente:
            # Remove arquivo antigo do sistema
            if os.path.exists(existente[0]):
                os.remove(existente[0])
            # Remove registro antigo do banco
            c.execute("DELETE FROM documento WHERE loja_id=?", (loja_id,))
            conn.commit()

        # Salva novo arquivo
        caminho = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(caminho)

        # Insere novo registro
        c.execute("INSERT INTO documento (loja_id, nome_arquivo, caminho) VALUES (?, ?, ?)",
                  (loja_id, file.filename, caminho))
        conn.commit()
        conn.close()
    return redirect(url_for('dashboard'))


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/delete_loja/<int:loja_id>', methods=['POST'])
def delete_loja(loja_id):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    # Apenas usuários autorizados podem excluir
    if session['usuario'] not in ['geop', 'geseg', 'admin']:
        return redirect(url_for('dashboard'))

    conn = sqlite3.connect('lojas.db')
    c = conn.cursor()

    # Apaga PDF associado (se existir)
    c.execute("SELECT caminho FROM documento WHERE loja_id=?", (loja_id,))
    doc = c.fetchone()
    if doc:
        if os.path.exists(doc[0]):
            os.remove(doc[0])
        c.execute("DELETE FROM documento WHERE loja_id=?", (loja_id,))
        conn.commit()

    # Apaga loja
    c.execute("DELETE FROM loja WHERE id=?", (loja_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('dashboard'))


# ---------------- MAIN ---------------- #
if __name__ == '__main__':
    app.run(debug=True)
