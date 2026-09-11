#!/usr/bin/env python3
"""Vitrine do robô — carrossel em /signage e painel de cadastro em /admin.

Roda no Pi e serve as duas coisas na rede local:
  /signage  -> vai na tela de 15" em retrato, em kiosk (1080x1920)
  /admin    -> abre no celular ou notebook para cadastrar os slides
"""
import os
import sqlite3
import time

from flask import (Flask, flash, g, jsonify, redirect, render_template,
                   request, url_for)
from werkzeug.utils import secure_filename

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, 'vitrine.db')
UPLOADS = os.path.join(BASE, 'static', 'uploads')
EXT_OK = {'.png', '.jpg', '.jpeg', '.webp', '.gif'}

app = Flask(__name__)
app.secret_key = 'vitrine-robo-local'
app.config['MAX_CONTENT_LENGTH'] = 12 * 1024 * 1024

# Cada tipo diz quais campos o formulário mostra — o painel e a prévia usam isso.
TIPOS = {
    'frase':       {'nome': 'Frase',       'campos': ['chapeu', 'titulo', 'subtitulo']},
    'instituicao': {'nome': 'Instituição', 'campos': ['chapeu', 'titulo', 'subtitulo', 'imagem']},
    'pessoa':      {'nome': 'Pessoa',      'campos': ['chapeu', 'titulo', 'subtitulo', 'imagem']},
    'promocao':    {'nome': 'Promoção',    'campos': ['titulo', 'preco', 'preco_de', 'rodape', 'imagem']},
    'imagem':      {'nome': 'Imagem cheia','campos': ['titulo', 'imagem']},
}

CONFIG_PADRAO = {
    'nome_robo': '[NOME DO ROBÔ]',
    'pxmm': '5.58',   # 55,8 px/cm da tela de 15"
    'mt': '0', 'mr': '20', 'mb': '0', 'ml': '0',   # área segura em mm (medida na tela real)
    'versao': '1',
}


# --------------------------------------------------------------------------- banco
def db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def fecha_db(_exc):
    con = g.pop('db', None)
    if con is not None:
        con.close()


def init_db():
    con = sqlite3.connect(DB)
    con.executescript("""
        CREATE TABLE IF NOT EXISTS slides (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo      TEXT    NOT NULL,
            chapeu    TEXT    DEFAULT '',
            titulo    TEXT    DEFAULT '',
            subtitulo TEXT    DEFAULT '',
            rodape    TEXT    DEFAULT '',
            preco     TEXT    DEFAULT '',
            preco_de  TEXT    DEFAULT '',
            imagem    TEXT    DEFAULT '',
            segundos  INTEGER DEFAULT 10,
            ativo     INTEGER DEFAULT 1,
            ordem     INTEGER DEFAULT 0,
            criado_em TEXT    DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS config (
            chave TEXT PRIMARY KEY,
            valor TEXT
        );
    """)
    for k, v in CONFIG_PADRAO.items():
        con.execute("INSERT OR IGNORE INTO config (chave, valor) VALUES (?,?)", (k, v))
    if con.execute("SELECT COUNT(*) FROM slides").fetchone()[0] == 0:
        semear(con)
    con.commit()
    con.close()


def semear(con):
    """Slides iniciais: o projeto de educação do Recanto das Emas."""
    inst = [
        ('Educação pública',   'CRE Recanto das Emas',
         'Um novo conceito em educação pública'),
        ('Apoio às escolas',   'UNIEB',
         'Apoio educacional para as escolas do Recanto das Emas'),
        ('Tecnologia na escola', 'NTE',
         'Núcleo de Tecnologia do Recanto das Emas'),
    ]
    alunos = [
        ('Miqueas', 'CEF 206'), ('Gabriel', 'CEF 206'), ('Gustavo', 'CED 308'),
        ('Emile', 'CEF 206'), ('Yuna', 'CEF 206'), ('Isabely', 'CEF 206'),
        ('João Vitor', ''), ('João Vitor', ''), ('Lucas', ''),
        ('Davi', 'IFB — Recanto'), ('Isaque', ''), ('Ravi', 'EC 404'),
        ('Arthur', 'CEF 206'), ('Lara', 'CEF 206'),
    ]
    apoio = [('Lucineide', ''), ('Dona Francisca', ''), ('Cátia', '')]

    ordem = 0
    linhas = []
    for chapeu, titulo, sub in inst:
        linhas.append(('instituicao', chapeu, titulo, sub, 10, ordem)); ordem += 1
    for nome, escola in alunos:
        linhas.append(('pessoa', 'Alunos do projeto', nome, escola, 6, ordem)); ordem += 1
    for nome, escola in apoio:
        linhas.append(('pessoa', 'Equipe de apoio', nome, escola, 6, ordem)); ordem += 1

    con.executemany(
        "INSERT INTO slides (tipo, chapeu, titulo, subtitulo, segundos, ordem) "
        "VALUES (?,?,?,?,?,?)", linhas)


def config():
    return {r['chave']: r['valor'] for r in db().execute("SELECT chave, valor FROM config")}


def bump():
    """Marca uma nova versão para a tela de 15" se atualizar sozinha."""
    db().execute("UPDATE config SET valor = ? WHERE chave = 'versao'", (str(int(time.time())),))
    db().commit()


def salva_imagem(arquivo):
    if not arquivo or not arquivo.filename:
        return None
    ext = os.path.splitext(arquivo.filename)[1].lower()
    if ext not in EXT_OK:
        return None
    os.makedirs(UPLOADS, exist_ok=True)
    nome = '%d_%s' % (int(time.time()), secure_filename(arquivo.filename))
    arquivo.save(os.path.join(UPLOADS, nome))
    return nome


# --------------------------------------------------------------------------- tela
@app.route('/')
def raiz():
    return redirect(url_for('admin'))


@app.route('/signage')
def signage():
    return render_template('signage.html')


@app.route('/api/slides')
def api_slides():
    linhas = db().execute(
        "SELECT * FROM slides WHERE ativo = 1 ORDER BY ordem, id").fetchall()
    return jsonify({'config': config(), 'slides': [dict(r) for r in linhas]})


@app.route('/api/versao')
def api_versao():
    return jsonify({'versao': config().get('versao', '1')})


# --------------------------------------------------------------------------- painel
@app.route('/admin')
def admin():
    linhas = db().execute("SELECT * FROM slides ORDER BY ordem, id").fetchall()
    return render_template('admin.html', slides=linhas, tipos=TIPOS, cfg=config())


@app.route('/admin/slide/novo', methods=['GET', 'POST'])
@app.route('/admin/slide/<int:sid>', methods=['GET', 'POST'])
def slide(sid=None):
    linha = None
    if sid:
        linha = db().execute("SELECT * FROM slides WHERE id = ?", (sid,)).fetchone()
        if linha is None:
            return redirect(url_for('admin'))

    if request.method == 'POST':
        f = request.form
        dados = {
            'tipo': f.get('tipo', 'frase'),
            'chapeu': f.get('chapeu', '').strip(),
            'titulo': f.get('titulo', '').strip(),
            'subtitulo': f.get('subtitulo', '').strip(),
            'rodape': f.get('rodape', '').strip(),
            'preco': f.get('preco', '').strip(),
            'preco_de': f.get('preco_de', '').strip(),
            'segundos': max(3, min(120, int(f.get('segundos') or 10))),
            'ativo': 1 if f.get('ativo') else 0,
        }
        nova = salva_imagem(request.files.get('arquivo'))
        if nova:
            dados['imagem'] = nova
        elif f.get('remover_imagem'):
            dados['imagem'] = ''
        elif linha:
            dados['imagem'] = linha['imagem']
        else:
            dados['imagem'] = ''

        if sid:
            db().execute(
                "UPDATE slides SET tipo=:tipo, chapeu=:chapeu, titulo=:titulo, "
                "subtitulo=:subtitulo, rodape=:rodape, preco=:preco, preco_de=:preco_de, "
                "imagem=:imagem, segundos=:segundos, ativo=:ativo WHERE id=:id",
                dict(dados, id=sid))
        else:
            prox = db().execute("SELECT COALESCE(MAX(ordem), -1) + 1 FROM slides").fetchone()[0]
            db().execute(
                "INSERT INTO slides (tipo, chapeu, titulo, subtitulo, rodape, preco, "
                "preco_de, imagem, segundos, ativo, ordem) VALUES (:tipo, :chapeu, :titulo, "
                ":subtitulo, :rodape, :preco, :preco_de, :imagem, :segundos, :ativo, :ordem)",
                dict(dados, ordem=prox))
        db().commit()
        bump()
        flash('Slide salvo.')
        return redirect(url_for('admin'))

    # Jinja não tem dict comprehension: o mapa de campos por tipo vai pronto daqui.
    campos = {k: v['campos'] for k, v in TIPOS.items()}
    return render_template('form.html', s=linha, tipos=TIPOS, campos=campos, cfg=config())


@app.route('/admin/slide/<int:sid>/ativo', methods=['POST'])
def alterna(sid):
    db().execute("UPDATE slides SET ativo = 1 - ativo WHERE id = ?", (sid,))
    db().commit()
    bump()
    return redirect(url_for('admin'))


@app.route('/admin/slide/<int:sid>/mover', methods=['POST'])
def mover(sid):
    direcao = -1 if request.form.get('dir') == 'cima' else 1
    linhas = db().execute("SELECT id, ordem FROM slides ORDER BY ordem, id").fetchall()
    ids = [r['id'] for r in linhas]
    if sid in ids:
        i = ids.index(sid)
        j = i + direcao
        if 0 <= j < len(ids):
            ids[i], ids[j] = ids[j], ids[i]
            for pos, x in enumerate(ids):
                db().execute("UPDATE slides SET ordem = ? WHERE id = ?", (pos, x))
            db().commit()
            bump()
    return redirect(url_for('admin'))


@app.route('/admin/slide/<int:sid>/excluir', methods=['POST'])
def excluir(sid):
    db().execute("DELETE FROM slides WHERE id = ?", (sid,))
    db().commit()
    bump()
    flash('Slide excluído.')
    return redirect(url_for('admin'))


@app.route('/admin/config', methods=['GET', 'POST'])
def config_view():
    if request.method == 'POST':
        for chave in ('nome_robo', 'pxmm', 'mt', 'mr', 'mb', 'ml'):
            if chave in request.form:
                db().execute("UPDATE config SET valor = ? WHERE chave = ?",
                             (request.form[chave].strip(), chave))
        db().commit()
        bump()
        flash('Configuração salva.')
        return redirect(url_for('admin'))
    return render_template('config.html', cfg=config())


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=8080, threaded=True)
