from flask import Flask, request, redirect
import sqlite3
from datetime import datetime, date, time
import qrcode
from io import BytesIO
from flask import send_file
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from datetime import timedelta

app = Flask(__name__)

ORDER_DEADLINE = time(9, 30)  # 締切9:30

def init_db():
    conn = sqlite3.connect("bento.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS departments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS menus (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        price INTEGER
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        department TEXT,
        menu TEXT,
        quantity INTEGER,
        order_date TEXT
    )
    """)

    conn.commit()
    conn.close()


def deadline_passed():
    now = datetime.now().time()
    return now > ORDER_DEADLINE

def deadline_info():
    now = datetime.now()
    deadline_dt = datetime.combine(date.today(), ORDER_DEADLINE)

    if now > deadline_dt:
        return {
            "passed": True,
            "text": "締切済み"
        }

    remaining = deadline_dt - now
    total_seconds = int(remaining.total_seconds())

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60

    if hours > 0:
        text = f"締切まで {hours}時間{minutes}分"
    else:
        text = f"締切まで {minutes}分"

    return {
        "passed": False,
        "text": text
    }


@app.route("/")
def order_page():
    department = request.args.get("dept", "総務")

    conn = sqlite3.connect("bento.db")
    c = conn.cursor()

    yesterday = str(date.today() - timedelta(days=1))

    # メニュー取得
    c.execute("SELECT name, price FROM menus")
    menus = c.fetchall()

    # 昨日の注文取得
    c.execute("""
    SELECT menu, quantity
    FROM orders
    WHERE department=? AND order_date=?
    """, (department, yesterday))

    y_orders = {m: q for m, q in c.fetchall()}

    conn.close()

    deadline = deadline_info()
    is_deadline_passed = deadline["passed"]
    deadline_text = deadline["text"]
    banner_class = "danger" if is_deadline_passed else "waiting"

    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>{department} の弁当注文</title>
        <style>
            body {{
                font-family: sans-serif;
                max-width: 720px;
                margin: 30px auto;
                line-height: 1.6;
            }}
            .banner {{
                border-radius: 8px;
                padding: 14px 18px;
                margin-bottom: 24px;
                border: 1px solid #ccc;
                font-size: 18px;
            }}
            .waiting {{
                background: #fff8e1;
                border-color: #ffd54f;
            }}
            .danger {{
                background: #ffebee;
                border-color: #e57373;
            }}
            .menu-row {{
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 12px 16px;
                margin-bottom: 12px;
            }}
            .menu-name {{
                font-weight: bold;
            }}
            input[type="number"] {{
                width: 80px;
                padding: 6px;
                margin-top: 8px;
            }}
            button {{
                padding: 10px 18px;
                font-size: 16px;
                border-radius: 8px;
                border: 1px solid #999;
                cursor: pointer;
            }}
            .note {{
                color: #666;
                font-size: 14px;
                margin-bottom: 20px;
            }}
        </style>
    </head>
    <body>
        <h1>{department} の弁当注文</h1>
        <div class="banner {banner_class}">
            <strong>{deadline_text}</strong>
        </div>
        <p class="note">昨日の注文を初期値として表示しています。必要に応じて調整してください。</p>
    """

    if is_deadline_passed:
        html += """
        <p>本日の注文は締め切りました。</p>
        </body>
        </html>
        """
        return html

    html += '<form method="post" action="/submit">'
    html += f'<input type="hidden" name="department" value="{department}">'

    for name, price in menus:
        qty = y_orders.get(name, 0)

        html += f"""
        <div class="menu-row">
            <div class="menu-name">{name}</div>
            <div>{price}円</div>
            <input type="number" name="{name}" value="{qty}" min="0">
        </div>
        """

    html += """
        <button type="submit">注文更新</button>
        </form>
    </body>
    </html>
    """

    return html

@app.route("/qr/<dept>")
def qr(dept):

    url = f"http://127.0.0.1:5000/?dept={dept}"

    img = qrcode.make(url)

    buf = BytesIO()
    img.save(buf)
    buf.seek(0)

    return send_file(buf, mimetype="image/png")

@app.route("/departments")
def departments():

    conn = sqlite3.connect("bento.db")
    c = conn.cursor()

    c.execute("SELECT name FROM departments")
    rows = c.fetchall()

    conn.close()

    html = "<h2>部署QRコード</h2>"

    for r in rows:
        dept = r[0]

        html += f"""
        <h3>{dept}</h3>
        <img src="/qr/{dept}">
        <br><br>
        """

    return html

@app.route("/dept/add")
def dept_add():
    return """
    <h2>部署追加</h2>
    <form method="post" action="/dept/save">
    部署名 <input name="name">
    <button type="submit">追加</button>
    </form>
    """
@app.route("/dept/save", methods=["POST"])
def dept_save():

    conn = sqlite3.connect("bento.db")
    c = conn.cursor()

    name = request.form["name"]

    c.execute(
        "INSERT INTO departments (name) VALUES (?)",
        (name,)
    )

    conn.commit()
    conn.close()

    return "部署追加しました"

@app.route("/history")
def history():

    conn = sqlite3.connect("bento.db")
    c = conn.cursor()

    c.execute("""
    SELECT order_date, department, menu, quantity
    FROM orders
    ORDER BY order_date DESC
    LIMIT 100
    """)

    rows = c.fetchall()

    conn.close()

    html = "<h2>注文履歴</h2>"

    for r in rows:
        html += f"{r[0]} - {r[1]} - {r[2]} : {r[3]}個<br>"

    return html

@app.route("/submit", methods=["POST"])
def submit():

    #if deadline_passed():
     #   return "<h2>締切後のため注文できません</h2>"

    conn = sqlite3.connect("bento.db")
    c = conn.cursor()

    department = request.form["department"]
    today = str(date.today())

    c.execute("SELECT name FROM menus")
    menus = [m[0] for m in c.fetchall()]

    for menu in menus:

        qty = int(request.form.get(menu, 0))

        c.execute("""
        DELETE FROM orders
        WHERE department=? AND menu=? AND order_date=?
        """, (department, menu, today))

        if qty > 0:
            c.execute(
                "INSERT INTO orders (department, menu, quantity, order_date) VALUES (?, ?, ?, ?)",
                (department, menu, qty, today)
            )

    conn.commit()
    conn.close()

    return redirect("/thanks")


@app.route("/thanks")
def thanks():
    return "<h2>注文を更新しました</h2>"

@app.route("/copy_yesterday")
def copy_yesterday():

    conn = sqlite3.connect("bento.db")
    c = conn.cursor()

    today = date.today()
    yesterday = today - timedelta(days=1)

    # 昨日の注文取得
    c.execute("""
    SELECT department, menu, quantity
    FROM orders
    WHERE order_date=?
    """, (str(yesterday),))

    rows = c.fetchall()

    # 今日の注文削除
    c.execute("""
    DELETE FROM orders
    WHERE order_date=?
    """, (str(today),))

    # 今日としてコピー
    for dept, menu, qty in rows:
        c.execute("""
        INSERT INTO orders (department, menu, quantity, order_date)
        VALUES (?, ?, ?, ?)
        """, (dept, menu, qty, str(today)))

    conn.commit()
    conn.close()

    return "昨日の注文をコピーしました"


@app.route("/admin")
def admin():

    conn = sqlite3.connect("bento.db")
    c = conn.cursor()

    today = str(date.today())

    html = "<h2>今日の注文（部署別）</h2>"

    c.execute("""
    SELECT department, menu, quantity
    FROM orders
    WHERE order_date=?
    ORDER BY department
    """, (today,))

    rows = c.fetchall()

    for r in rows:
        html += f"{r[0]} - {r[1]} : {r[2]} 個<br>"

    html += "<hr><h2>メニュー別合計</h2>"

    c.execute("""
    SELECT menu, SUM(quantity)
    FROM orders
    WHERE order_date=?
    GROUP BY menu
    """, (today,))

    rows = c.fetchall()

    for r in rows:
        html += f"{r[0]} : {r[1]} 個<br>"

    conn.close()

    html += '<br><br><a href="/copy_yesterday">昨日の注文をコピー</a>'

    return html


@app.route("/menu/add")
def menu_add_page():
    return """
    <h2>メニュー追加</h2>
    <form method="post" action="/menu/save">
    名前 <input name="name"><br>
    価格 <input name="price"><br>
    <button type="submit">追加</button>
    </form>
    """


@app.route("/menu/save", methods=["POST"])
def menu_save():

    conn = sqlite3.connect("bento.db")
    c = conn.cursor()

    name = request.form["name"]
    price = request.form["price"]

    c.execute(
        "INSERT INTO menus (name, price) VALUES (?, ?)",
        (name, price)
    )

    conn.commit()
    conn.close()

    return "メニュー追加しました"

@app.route("/delivery")
def delivery():

    conn = sqlite3.connect("bento.db")
    c = conn.cursor()

    today = str(date.today())

    c.execute("""
    SELECT department, menu, quantity
    FROM orders
    WHERE order_date=?
    ORDER BY department
    """, (today,))

    rows = c.fetchall()
    conn.close()

    result = {}

    for dept, menu, qty in rows:
        if dept not in result:
            result[dept] = []

        result[dept].append((menu, qty))

    html = "<h2>配達リスト</h2>"

    for dept in result:

        html += f"<h3>{dept}</h3>"

        for menu, qty in result[dept]:
            html += f"{menu} : {qty} 個<br>"

        html += "<br>"

    html += '<a href="/delivery/pdf">PDFダウンロード</a>'

    return html

@app.route("/dashboard")
def dashboard():
    conn = sqlite3.connect("bento.db")
    c = conn.cursor()

    today = str(date.today())

    # メニュー別合計
    c.execute("""
    SELECT menu, SUM(quantity)
    FROM orders
    WHERE order_date=?
    GROUP BY menu
    ORDER BY menu
    """, (today,))
    menu_totals = c.fetchall()

    # 総食数
    c.execute("""
    SELECT COALESCE(SUM(quantity), 0)
    FROM orders
    WHERE order_date=?
    """, (today,))
    total_count = c.fetchone()[0]

    # 部署ごとの注文明細
    c.execute("""
    SELECT department, menu, quantity
    FROM orders
    WHERE order_date=?
    ORDER BY department, menu
    """, (today,))
    rows = c.fetchall()

    # 今日注文した部署
    c.execute("""
    SELECT DISTINCT department
    FROM orders
    WHERE order_date=?
    ORDER BY department
    """, (today,))
    ordered_departments = [r[0] for r in c.fetchall()]

    # 登録済み部署
    c.execute("""
    SELECT name
    FROM departments
    ORDER BY name
    """)
    all_departments = [r[0] for r in c.fetchall()]

    conn.close()

    grouped = {}
    for dept, menu, qty in rows:
        grouped.setdefault(dept, []).append((menu, qty))

    ordered_count = len(ordered_departments)
    all_count = len(all_departments)
    unordered_departments = [d for d in all_departments if d not in ordered_departments]

    deadline = deadline_info()
    is_deadline_passed = deadline["passed"]
    deadline_text = deadline["text"]

    # 部署ごとのステータス作成
    department_statuses = []
    for dept in all_departments:
        if dept in ordered_departments:
            status = "注文済み"
            status_class = "done"
        else:
            if is_deadline_passed:
                status = "締切後未注文"
                status_class = "danger"
            else:
                status = "未注文"
                status_class = "waiting"

        department_statuses.append((dept, status, status_class))

    status_class = "danger" if is_deadline_passed else "waiting"

    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>弁当ダッシュボード</title>
        <style>
            body {{
                font-family: sans-serif;
                max-width: 1100px;
                margin: 30px auto;
                line-height: 1.6;
            }}
            .cards {{
                display: flex;
                gap: 16px;
                flex-wrap: wrap;
                margin-bottom: 24px;
            }}
            .card {{
                border: 1px solid #ccc;
                border-radius: 8px;
                padding: 16px;
                min-width: 180px;
            }}
            .section {{
                margin-top: 28px;
            }}
            .dept {{
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 12px 16px;
                margin-bottom: 12px;
            }}
            .warn {{
                background: #fff8e1;
                border: 1px solid #f0d98c;
                border-radius: 8px;
                padding: 12px 16px;
            }}
            .status-list {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                gap: 12px;
            }}
            .status-box {{
                border-radius: 8px;
                padding: 12px 16px;
                border: 1px solid #ccc;
            }}
            .done {{
                background: #e8f5e9;
                border-color: #81c784;
            }}
            .waiting {{
                background: #fff8e1;
                border-color: #ffd54f;
            }}
            .danger {{
                background: #ffebee;
                border-color: #e57373;
            }}
            .status-label {{
                font-weight: bold;
                display: inline-block;
                margin-top: 4px;
            }}
            .deadline-banner {{
                border-radius: 8px;
                padding: 14px 18px;
                margin-bottom: 24px;
                border: 1px solid #ccc;
                font-size: 18px;
            }}
            a {{
                margin-right: 12px;
            }}
            ul {{
                margin-top: 8px;
            }}
        </style>
    </head>
    <body>
        <h1>今日の弁当ダッシュボード</h1>
        <p>{today}</p>

        <div class="deadline-banner {status_class}">
            <strong>{deadline_text}</strong>
        </div>

        <div class="cards">
            <div class="card">
                <h3>総食数</h3>
                <p style="font-size: 28px; margin: 0;">{total_count} 食</p>
            </div>
            <div class="card">
                <h3>メニュー数</h3>
                <p style="font-size: 28px; margin: 0;">{len(menu_totals)} 種類</p>
            </div>
            <div class="card">
                <h3>今日の注文部署数</h3>
                <p style="font-size: 28px; margin: 0;">{ordered_count} 部署</p>
            </div>
            <div class="card">
                <h3>登録済み部署数</h3>
                <p style="font-size: 28px; margin: 0;">{all_count} 部署</p>
            </div>
        </div>
"""

    html += """
        <div class="section">
            <h2>部署ごとの注文ステータス</h2>
            <div class="status-list">
    """

    if department_statuses:
        for dept, status, status_class in department_statuses:
            html += f"""
                <div class="status-box {status_class}">
                    <div><strong>{dept}</strong></div>
                    <div class="status-label">{status}</div>
                </div>
            """
    else:
        html += "<p>部署が登録されていません。</p>"

    html += """
            </div>
        </div>
    """

    html += """
        <div class="section">
            <h2>メニュー別合計</h2>
    """

    if menu_totals:
        html += "<ul>"
        for menu, qty in menu_totals:
            html += f"<li>{menu} : {qty} 個</li>"
        html += "</ul>"
    else:
        html += "<p>まだ注文はありません。</p>"

    html += """
        </div>

        <div class="section">
            <h2>未注文部署</h2>
    """

    if unordered_departments:
        html += '<div class="warn"><ul>'
        for dept in unordered_departments:
            html += f"<li>{dept}</li>"
        html += "</ul></div>"
    else:
        html += "<p>すべての登録部署で注文済みです。</p>"

    html += """
        </div>

        <div class="section">
            <h2>部署ごとの注文</h2>
    """

    if grouped:
        for dept, items in grouped.items():
            html += f'<div class="dept"><h3>{dept}</h3><ul>'
            for menu, qty in items:
                html += f"<li>{menu} : {qty} 個</li>"
            html += "</ul></div>"
    else:
        html += "<p>まだ注文はありません。</p>"

    html += """
        </div>

        <div class="section">
            <h2>メニュー</h2>
            <p>
                <a href="/delivery">配達リスト</a>
                <a href="/delivery/pdf">配達リストPDF</a>
                <a href="/history">注文履歴</a>
                <a href="/departments">部署QR一覧</a>
                <a href="/menu/add">メニュー追加</a>
                <a href="/dept/add">部署追加</a>
            </p>
        </div>
    </body>
    </html>
    """

    return html

@app.route("/delivery/pdf")
def delivery_pdf():

    conn = sqlite3.connect("bento.db")
    c = conn.cursor()

    today = str(date.today())

    c.execute("""
    SELECT department, menu, quantity
    FROM orders
    WHERE order_date=?
    ORDER BY department
    """, (today,))

    rows = c.fetchall()
    conn.close()

    data = {}

    for dept, menu, qty in rows:
        if dept not in data:
            data[dept] = []

        data[dept].append((menu, qty))

    filename = "delivery_list.pdf"

    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))

    styles = getSampleStyleSheet()

    doc = SimpleDocTemplate(
        filename,
        pagesize=A4
    )

    story = []

    story.append(Paragraph("弁当配達リスト", styles["Title"]))
    story.append(Spacer(1, 20))

    for dept in data:

        story.append(Paragraph(dept, styles["Heading2"]))

        for menu, qty in data[dept]:
            story.append(
                Paragraph(f"{menu} : {qty} 個", styles["Normal"])
            )

        story.append(Spacer(1, 10))

    doc.build(story)

    return send_file(filename, as_attachment=True)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
    