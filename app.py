from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session
import sqlite3
import os
from fpdf import FPDF
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "segredo123"

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DB_NAME = "estudante.db"

# ==================== Banco de Dados ====================


def conectar():
    return sqlite3.connect(DB_NAME)


def criar_tabela():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS candidatura (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            passaporte TEXT NOT NULL,
            indicativo TEXT,
            email TEXT,
            telefone TEXT,
            sexo TEXT,
            data_nascimento TEXT,
            endereco TEXT,
            encarregado TEXT,
            instituicao TEXT,
            curso TEXT,
            picture TEXT,
            prestacao1 REAL,
            prestacao2 REAL,
            prestacao3 REAL,
            ano_lectivo TEXT,
            resultado TEXT,
            matricula TEXT
        )
    """)
    conn.commit()
    conn.close()


criar_tabela()

# ==================== Funções DB ====================


def listar_registos():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM candidatura")
    rows = cursor.fetchall()
    conn.close()
    return rows


def inserir_registo(dados):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO candidatura
        (nome, passaporte, indicativo, email, telefone, sexo, data_nascimento, endereco,
        encarregado, instituicao, curso, picture, prestacao1, prestacao2, prestacao3,
        ano_lectivo, resultado, matricula)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, dados)
    conn.commit()
    conn.close()


def atualizar_matricula(id, resultado, matricula, p2, p3):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE candidatura SET resultado=?, matricula=?, prestacao2=?, prestacao3=? WHERE id=?
    """, (resultado, matricula, p2, p3, id))
    conn.commit()
    conn.close()


def apagar_registo(reg_id):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM candidatura WHERE id=?", (reg_id,))
    conn.commit()
    conn.close()


# ==================== Login ====================
USUARIO = "malam"
SENHA = "6826630m@"


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form['usuario']
        senha = request.form['senha']
        if user == USUARIO and senha == SENHA:
            session['logado'] = True
            flash("Login efetuado com sucesso!", "success")
            return redirect(url_for('candidatura'))
        else:
            flash("Usuário ou senha incorretos!", "danger")
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('logado', None)
    flash("", "info")
    return redirect(url_for('login'))


def login_obrigatorio(func):
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get('logado'):
            flash("Faça login para acessar essa página.", "warning")
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    return wrapper

# ==================== Rotas ====================

# Candidatura


@app.route('/', methods=['GET', 'POST'])
@login_obrigatorio
def candidatura():
    if request.method == 'POST':
        nome = request.form['nome']
        passaporte = request.form['passaporte']
        indicativo = request.form.get('indicativo')
        email = request.form.get('email')
        telefone = request.form.get('telefone')
        sexo = request.form.get('sexo')
        data_nascimento = request.form.get('data_nascimento')
        endereco = request.form.get('endereco')
        encarregado = request.form.get('encarregado')
        instituicao = request.form.get('instituicao')
        curso = request.form.get('curso')
        prestacao1 = float(request.form.get('prestacao1') or 0)
        ano_lectivo = request.form.get('ano_lectivo')
        resultado = ''
        matricula = ''

        file = request.files.get('picture')
        picture_filename = ''
        if file and file.filename != '':
            picture_filename = secure_filename(file.filename)
            file.save(os.path.join(UPLOAD_FOLDER, picture_filename))

        dados = (nome, passaporte, indicativo, email, telefone, sexo, data_nascimento,
                 endereco, encarregado, instituicao, curso, picture_filename,
                 prestacao1, 0, 0, ano_lectivo, resultado, matricula)

        inserir_registo(dados)
        flash("Candidatura salva!", "success")
        return redirect(url_for('candidatura'))

    registros = listar_registos()
    return render_template('candidatura.html', registros=registros)


@app.route('/apagar/<int:reg_id>', methods=['POST'])
@login_obrigatorio
def apagar(reg_id):
    apagar_registo(reg_id)
    flash("Registro apagado com sucesso!", "success")
    return redirect(request.referrer or url_for("candidatura"))

# Matrícula


@app.route('/matricula', methods=['GET', 'POST'])
@login_obrigatorio
def matricula():
    registros = listar_registos()
    if request.method == 'POST':
        for i, r in enumerate(registros):
            id = r[0]
            resultado = request.form.getlist('resultado')[i]
            matricula_val = request.form.getlist('matricula')[i]
            p2 = float(request.form.getlist('prestacao2')[i] or 0)
            p3 = float(request.form.getlist('prestacao3')[i] or 0)
            atualizar_matricula(id, resultado, matricula_val, p2, p3)
        flash("Matrículas atualizadas!", "success")
        return redirect(url_for('matricula'))
    return render_template('matricula.html', registros=registros)

# Relatório


# @app.route('/relatorio', methods=['GET', 'POST'])
# @login_obrigatorio
# def relatorio():
  #  registros = listar_registos()
  #  return render_template('relatorio.html', registros=registros)
@app.route('/relatorio', methods=['GET', 'POST'])
@login_obrigatorio
def relatorio():
    registros = listar_registos()
    # Calcula o total geral
    total_geral = sum([(r[13] or 0) + (r[14] or 0) + (r[15] or 0)
                      for r in registros])
    return render_template('relatorio.html', registros=registros, total_geral=total_geral)


@app.route('/gerar_pdf', methods=['POST'])
@login_obrigatorio
def gerar_pdf():
    registros = listar_registos()
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Relatório de Candidaturas", ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("Arial", "", 10)

    for r in registros:
        pdf.multi_cell(0, 6,
                       f"ID: {r[0]} | Nome: {r[1]} | Passaporte: {r[2]} | Email: {r[4]} | Telefone: {r[5]}\n"
                       f"Sexo: {r[6]} | Curso: {r[11]} | 1ª: {r[13]} | 2ª: {r[14]} | 3ª: {r[15]} | Total: {sum([r[13] or 0, r[14] or 0, r[15] or 0])}\n"
                       f"Resultado: {r[17]} | Matrícula: {r[18]}"
                       )
        if r[12]:
            try:
                pdf.image(os.path.join(UPLOAD_FOLDER, r[12]), w=20, h=20)
            except:
                pass
        pdf.ln(5)

    pdf_file = "relatorio_candidaturas.pdf"
    pdf.output(pdf_file)
    return send_file(pdf_file, as_attachment=True)


# ==================== Run ====================
if __name__ == '__main__':
    app.run(debug=True)
