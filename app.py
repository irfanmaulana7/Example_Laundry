from flask import Flask, request, redirect, render_template_string, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from sqlalchemy import func
from datetime import datetime
import qrcode
from io import BytesIO

import pandas as pd

from reportlab.platypus import *
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///laundry.db'
app.config['SECRET_KEY'] = 'secret123'

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# ================= MODEL =================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100))
    password = db.Column(db.String(100))

class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kode = db.Column(db.String(20))
    nama = db.Column(db.String(100))
    hp = db.Column(db.String(20))
    alamat = db.Column(db.String(200))
    saldo = db.Column(db.Integer, default=0)  # 🔥 SALDO

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100))
    layanan = db.Column(db.String(100))
    berat = db.Column(db.Float)
    total = db.Column(db.Integer)
    diskon = db.Column(db.Float, default=0)
    status = db.Column(db.String(50), default="Diterima")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ================= LAYANAN =================
class Layanan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100))
    harga = db.Column(db.Integer)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ================= TEMPLATE =================
def layout(content):
    return f"""
    <html>

    <head>

    <meta charset="UTF-8">

    <meta name="viewport"
    content="width=device-width,
    initial-scale=1,
    maximum-scale=1,
    user-scalable=no">

    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://unpkg.com/html5-qrcode"></script>

    </head>

    <body class="bg-slate-950 text-white">

    <div class="min-h-screen md:flex">

    <!-- MOBILE TOPBAR -->
    <div class="md:hidden bg-slate-900 p-4 flex justify-between items-center border-b border-slate-800 sticky top-0 z-50">
        <img src="/static/logo.png" class="w-24">

        <button onclick="toggleMenu()" class="text-2xl">
            ☰
        </button>
    </div>

    <!-- SIDEBAR -->
    <div id="sidebar"
    class="hidden md:block w-full md:w-64 bg-slate-900 md:h-screen p-6 md:fixed border-r border-slate-800 z-40">

        <img src="/static/logo.png"
        class="w-32 mx-auto mb-8">

        <div class="flex flex-col gap-4 text-center md:text-left">

            <a href="/dashboard"
            class="bg-slate-800 hover:bg-slate-700 p-3 rounded-xl transition">
            Dashboard
            </a>

            <a href="/member"
            class="bg-slate-800 hover:bg-slate-700 p-3 rounded-xl transition">
            Member
            </a>

            <a href="/transaksi"
            class="bg-slate-800 hover:bg-slate-700 p-3 rounded-xl transition">
            Transaksi
            </a>
            
            <a href="/arsip"
            class="bg-slate-800 hover:bg-slate-700 p-3 rounded-xl transition">
            Arsip
            </a>

            <a href="/logout"
            class="bg-red-500 hover:bg-red-600 p-3 rounded-xl transition">
            Logout
            </a>

        </div>
    </div>

    <!-- CONTENT -->
    <div class="w-full md:ml-64 p-3 md:p-8 overflow-x-auto">
        {content}
    </div>

    </div>

    <script>
    function toggleMenu() {{
        const sidebar = document.getElementById("sidebar");

        if(sidebar.classList.contains("hidden")) {{
            sidebar.classList.remove("hidden");
        }} else {{
            sidebar.classList.add("hidden");
        }}
    }}
    </script>

    </body>
    </html>
    """
# ================= LOGIN =================
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()
        if user and user.password == request.form["password"]:
            login_user(user)
            return redirect("/dashboard")

    return render_template_string("""
    <body style="background:#020617;color:white;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh">
        <form method="POST" style="background:rgba(255,255,255,0.05);padding:30px;border-radius:20px;width:300px">
            <h2>🍎 Laundry Pro</h2>
            <input name="username" placeholder="Username" style="width:100%;padding:10px;margin-bottom:10px;border-radius:10px">
            <input name="password" type="password" placeholder="Password" style="width:100%;padding:10px;margin-bottom:10px;border-radius:10px">
            <button style="width:100%;padding:10px;background:#6366f1;color:white;border:none;border-radius:10px">Login</button>
        </form>
    </body>
    """)

# ================= DASHBOARD =================
@app.route("/dashboard")
@login_required
def dashboard():
    total = Order.query.count()
    selesai = Order.query.filter_by(status="Selesai").count()
    proses = Order.query.filter(Order.status != "Selesai").count()
    omzet = db.session.query(func.sum(Order.total)).scalar() or 0

    content = f"""
    <h1 class="text-2xl mb-6">Dashboard</h1>

    <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div class="bg-slate-800 p-4 rounded">Total<br>{total}</div>
        <div class="bg-slate-800 p-4 rounded">Proses<br>{proses}</div>
        <div class="bg-slate-800 p-4 rounded">Selesai<br>{selesai}</div>
        <div class="bg-slate-800 p-4 rounded">Omzet<br>Rp {omzet}</div>
    </div>

    <canvas id="chart"></canvas>

    <script>
    new Chart(document.getElementById("chart"), {{
        type: 'line',
        data: {{
            labels: ["Sen","Sel","Rab","Kam","Jum","Sab","Min"],
            datasets: [{{
                label: "Omzet",
                data: [12000, 19000, 15000, 22000, 30000, 28000, 35000],
                borderColor: "#60a5fa",
                backgroundColor: "rgba(96,165,250,0.2)",
                fill: true
            }}]
        }}
    }});
    </script>
    """

    return layout(content)

# ================= MEMBER =================
@app.route("/member")
@login_required
def member():

    data = Member.query.all()

    rows = ""

    for m in data:

        rows += f"""
        <tr class="border-b border-slate-700">

            <td class="p-2">{m.kode}</td>

            <td class="p-2">{m.nama}</td>

            <td class="p-2">{m.hp}</td>

            <td class="p-2">{m.alamat}</td>

            <td class="p-2 text-green-400">
                Rp {m.saldo}
            </td>

            <td class="p-2">
                <img src="/qr/{m.id}" width="70">
            </td>

            <td class="p-2">
                <a href="/kartu/{m.id}"
                target="_blank"
                class="text-blue-400">
                Lihat
                </a>
            </td>

        </tr>
        """

    content = f"""

    <h1 class="text-2xl font-bold mb-6">
        Member
    </h1>

    <!-- FORM MEMBER -->

    <form method="POST"
    action="/add_member"
    class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">

        <div class="space-y-1">

            <label class="text-sm text-gray-300">
                ID Member
            </label>

            <input
            name="kode"
            placeholder="ZEE001"
            class="w-full p-3 bg-slate-800 border border-slate-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500">

        </div>

        <div class="space-y-1">

            <label class="text-sm text-gray-300">
                Nama Member
            </label>

            <input
            name="nama"
            placeholder="Nama Member"
            class="w-full p-3 bg-slate-800 border border-slate-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500">

        </div>

        <div class="space-y-1">

            <label class="text-sm text-gray-300">
                Nomor HP
            </label>

            <input
            name="hp"
            placeholder="08xxxxxxxxxx"
            class="w-full p-3 bg-slate-800 border border-slate-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500">

        </div>

        <div class="space-y-1">

            <label class="text-sm text-gray-300">
                Saldo
            </label>

            <input
            name="saldo"
            placeholder="10000"
            class="w-full p-3 bg-slate-800 border border-slate-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500">

        </div>

        <div class="space-y-1 md:col-span-2">

            <label class="text-sm text-gray-300">
                Alamat
            </label>

            <textarea
            name="alamat"
            rows="3"
            placeholder="Alamat lengkap"
            class="w-full p-3 bg-slate-800 border border-slate-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500"></textarea>

        </div>

        <button
        class="md:col-span-2 bg-indigo-500 hover:bg-indigo-600 transition p-3 rounded-xl font-semibold">

            Tambah Member

        </button>

    </form>

    <!-- FORM TOPUP -->

    <form method="POST"
    action="/topup"
    class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">

        <select
        name="id"
        class="w-full p-3 bg-slate-800 text-white border border-slate-700 rounded-xl">

            {"".join([f"<option value='{m.id}'>{m.nama}</option>" for m in data])}

        </select>

        <input
        name="jumlah"
        placeholder="Jumlah Top Up"
        class="w-full p-3 bg-slate-800 border border-slate-700 rounded-xl">

        <button
        class="bg-green-500 hover:bg-green-600 transition p-3 rounded-xl font-semibold">

            Top Up Saldo

        </button>

    </form>

    <!-- TABLE MEMBER -->

    <div class="overflow-x-auto rounded-xl">

        <table class="w-full bg-slate-800 text-sm min-w-max overflow-hidden">

            <tr class="bg-slate-700 text-left">

                <th class="p-3">Kode</th>

                <th class="p-3">Nama</th>

                <th class="p-3">HP</th>

                <th class="p-3">Alamat</th>

                <th class="p-3">Saldo</th>

                <th class="p-3">QR</th>

                <th class="p-3">Kartu</th>

            </tr>

            {rows}

        </table>

    </div>

    """

    return layout(content)

@app.route("/add_member", methods=["POST"])
@login_required
def add_member():
    db.session.add(Member(
        kode=request.form['kode'],
        nama=request.form['nama'],
        hp=request.form['hp'],
        alamat=request.form['alamat'],
        saldo=int(request.form.get('saldo') or 0)
    ))
    db.session.commit()
    return redirect("/member")

@app.route("/topup", methods=["POST"])
@login_required
def topup():
    m = Member.query.get(request.form['id'])
    jumlah = int(request.form['jumlah'] or 0)

    if m and jumlah > 0:
        m.saldo += jumlah

    db.session.commit()
    return redirect("/member")

# ================= QR =================
@app.route("/qr/<int:id>")
def qr(id):
    m = Member.query.get(id)
    img = qrcode.make(f"member:{m.kode}")
    buf = BytesIO()
    img.save(buf)
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

@app.route("/kartu/<int:id>")
@login_required
def kartu(id):

    m = Member.query.get(id)

    return f"""
    <html>

    <head>

    <script src="https://cdn.tailwindcss.com"></script>

    </head>

    <body class="bg-slate-900 flex items-center justify-center min-h-screen text-white p-4">

        <div class="bg-slate-800 rounded-3xl p-6 w-full max-w-sm shadow-2xl">

            <div class="text-center">

                <img src="/static/logo.png"
                class="w-24 mx-auto mb-4">

                <h1 class="text-2xl font-bold mb-1">
                    ZEECLEAN LAUNDRY
                </h1>

                <p class="text-gray-400 mb-6">
                    Member Card
                </p>

            </div>

            <div class="space-y-3 text-sm">

                <div class="bg-slate-700 p-3 rounded-xl">
                    <b>ID Member</b><br>
                    {m.kode}
                </div>

                <div class="bg-slate-700 p-3 rounded-xl">
                    <b>Nama</b><br>
                    {m.nama}
                </div>

                <div class="bg-slate-700 p-3 rounded-xl">
                    <b>Nomor HP</b><br>
                    {m.hp}
                </div>

                <div class="bg-slate-700 p-3 rounded-xl">
                    <b>Saldo</b><br>
                    Rp {m.saldo}
                </div>

            </div>

            <div class="flex justify-center mt-6">

                <img src="/qr/{m.id}"
                class="bg-white p-3 rounded-2xl w-52">

            </div>

        </div>

    </body>

    </html>
    """

# ================= TRANSAKSI =================
@app.route("/transaksi")
@login_required
def transaksi():

    data = Order.query.filter(
        Order.status != "Selesai"
    ).all()
    members = Member.query.all()

    selected = request.args.get("kode")

    options_member = ""

    for m in members:

        sel = "selected" if m.kode == selected else ""

        options_member = ""

    for m in members:
    
        sel = "selected" if m.kode == selected else ""
    
        options_member += f"""
        <option
        value='{m.id}'
        data-saldo='{m.saldo}'
        {sel}>
    
            {m.nama} ({m.kode}) - Rp {m.saldo}
    
        </option>
        """
    
    layanan_db = Layanan.query.all()
    
    options_layanan = "".join([
        f"<option data-harga='{l.harga}'>{l.nama}</option>"
        for l in layanan_db
    ])

    rows = ""

    for d in data:

        warna = "bg-gray-500"

        if d.status == "Dicuci":
            warna = "bg-yellow-400 text-black"

        elif d.status == "Setrika":
            warna = "bg-blue-400"

        elif d.status == "Packing":
            warna = "bg-purple-400"

        elif d.status == "Selesai":
            warna = "bg-green-500"

        rows += f"""

        <tr class="border-b border-slate-700">

            <td class="p-3">{d.nama}</td>

            <td class="p-3">{d.layanan}</td>

            <td class="p-3">
                Rp {d.total}
            </td>

            <td class="p-3">
                {d.diskon}%
            </td>

            <td class="p-3">

                <span class='{warna} px-3 py-1 rounded-lg text-xs'>

                    {d.status}

                </span>

            </td>

            <td class="p-3 flex flex-wrap gap-2">

                <a href="/update/{d.id}/Dicuci"
                class="bg-yellow-500 text-black px-3 py-1 rounded-lg text-xs">
                Cuci
                </a>

                <a href="/update/{d.id}/Setrika"
                class="bg-blue-500 px-3 py-1 rounded-lg text-xs">
                Setrika
                </a>

                <a href="/update/{d.id}/Packing"
                class="bg-purple-500 px-3 py-1 rounded-lg text-xs">
                Packing
                </a>

                <a href="/update/{d.id}/Selesai"
                class="bg-green-500 px-3 py-1 rounded-lg text-xs">
                Done
                </a>

                <a href="/print/{d.id}"
                target="_blank"
                class="bg-slate-600 px-3 py-1 rounded-lg text-xs">
                Print
                </a>

            </td>

        </tr>

        """

    content = f"""

    <h1 class="text-2xl font-bold mb-6">
        Transaksi
    </h1>

    <!-- QR SCANNER -->

    <div class="bg-slate-800 p-4 mb-6 rounded-2xl">

        <h3 class="text-lg font-semibold mb-3">
            📷 Scan Member
        </h3>

        <div id="reader"
        class="rounded-xl overflow-hidden">
        </div>

    </div>

    <!-- FORM TRANSAKSI -->

    <form method="POST"
    action="/add_transaksi"
    class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">

        <div class="space-y-1">

            <label class="text-sm text-gray-300">
                Member
            </label>

            <select
            name="member_id"
            class="w-full p-3 bg-slate-800 text-white border border-slate-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500">

                {options_member}

            </select>

        </div>

        <div class="space-y-1">

            <label class="text-sm text-gray-300">
                Saldo
            </label>

            <input
            id="saldo_view"
            readonly
            class="w-full p-3 bg-slate-700 text-green-400 rounded-xl">

        </div>

        <div class="space-y-1">

            <label class="text-sm text-gray-300">
                Layanan
            </label>

            <select
            id="layanan"
            name="layanan"
            class="w-full p-3 bg-slate-800 text-white border border-slate-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500">

                {options_layanan}

            </select>

        </div>

        <div class="space-y-1">

            <label class="text-sm text-gray-300">
                Berat (kg)
            </label>

            <input
            id="berat"
            name="berat"
            type="number"
            placeholder="0"
            class="w-full p-3 bg-slate-800 text-white border border-slate-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500">

        </div>

        <div class="space-y-1">

            <label class="text-sm text-gray-300">
                Diskon (%)
            </label>

            <input
            id="diskon"
            name="diskon"
            type="number"
            value="0"
            class="w-full p-3 bg-slate-800 text-white border border-slate-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500">

        </div>

        <div class="space-y-1">

            <label class="text-sm text-gray-300">
                Total
            </label>

            <input
            id="total"
            name="total"
            readonly
            class="w-full p-3 bg-slate-700 text-white rounded-xl">

        </div>

        <button
        class="md:col-span-2 bg-indigo-500 hover:bg-indigo-600 transition p-3 rounded-xl font-semibold">

            Tambah Transaksi

        </button>

    </form>

    <!-- TABLE TRANSAKSI -->

    <div class="overflow-x-auto rounded-xl">

        <table class="w-full bg-slate-800 text-sm min-w-max overflow-hidden">

            <tr class="bg-slate-700 text-left">

                <th class="p-3">Nama</th>

                <th class="p-3">Layanan</th>

                <th class="p-3">Total</th>

                <th class="p-3">Diskon</th>

                <th class="p-3">Status</th>

                <th class="p-3">Aksi</th>

            </tr>

            {rows}

        </table>

    </div>

<script>

document.addEventListener("DOMContentLoaded", function() {{

    function getHarga() {{

    let layanan = document.getElementById(
        "layanan"
    );

    return parseInt(
        layanan.options[
            layanan.selectedIndex
        ].getAttribute("data-harga")
    ) || 0;
}}

    function updateSaldo() {{

        let s = document.querySelector(
            "select[name='member_id']"
        );

        let saldo = s.options[
            s.selectedIndex
        ].getAttribute("data-saldo");

        document.getElementById(
            "saldo_view"
        ).value = "Rp " + saldo;
    }}

    function hitung() {{

        let l = document.getElementById(
            "layanan"
        ).value;

        let b = parseFloat(
            document.getElementById("berat").value
        ) || 0;

        let d = parseFloat(
            document.getElementById("diskon").value
        ) || 0;

        let h = getHarga() * b;

        document.getElementById(
            "total"
        ).value = Math.round(
            h - (h * d / 100)
        );
    }}

    document.getElementById(
        "layanan"
    ).onchange = hitung;

    document.getElementById(
        "berat"
    ).oninput = hitung;

    document.getElementById(
        "diskon"
    ).oninput = hitung;

    document.querySelector(
        "select[name='member_id']"
    ).onchange = updateSaldo;

    updateSaldo();
    hitung();

    const qr = new Html5Qrcode("reader");

    function onScanSuccess(text) {{

        qr.stop().then(() => {{

            if(text.startsWith("member:")) {{

                window.location =
                "/transaksi?kode=" +
                text.split(":")[1];

            }}

        }});

    }}

    qr.start(
        {{ facingMode: "environment" }},
        {{
            fps: 5,
            qrbox: 180
        }},
        onScanSuccess
    ).catch(err => {{
        console.log(err);
    }});

}});

</script>
    """

    return layout(content)
@app.route("/add_transaksi", methods=["POST"])
@login_required
def add_transaksi():

    def to_float(val):
        try:
            return float(val)
        except:
            return None

    berat = to_float(request.form.get('berat'))
    diskon = to_float(request.form.get('diskon'))
    total = to_float(request.form.get('total'))

    if berat is None or berat <= 0:
        return "Error: berat tidak valid"

    if diskon is None or diskon < 0 or diskon > 100:
        return "Error: diskon tidak valid"

    member = Member.query.get(request.form.get('member_id'))
    total_int = int(total or 0)

    # 🔥 POTONG SALDO
    if member and member.saldo >= total_int:
       member.saldo -= total_int

    db.session.add(Order(
        nama=member.nama if member else "-",
        layanan=request.form['layanan'],
        berat=berat,
        total=total_int,
        diskon=diskon
    ))

    db.session.commit()
    return redirect("/transaksi")

# ================= ARSIP =================

@app.route("/arsip")
@login_required
def arsip():

    data = Order.query.filter_by(
        status="Selesai"
    ).order_by(Order.id.desc()).all()

    rows = ""

    for d in data:

        rows += f"""

        <tr class="border-b border-slate-700">

            <td class="p-3">{d.nama}</td>

            <td class="p-3">{d.layanan}</td>

            <td class="p-3">
                {d.berat} Kg
            </td>

            <td class="p-3">
                Rp {d.total}
            </td>

            <td class="p-3">
                {d.created_at.strftime("%d-%m-%Y")}
            </td>

            <td class="p-3">

                <a href="/print/{d.id}"
                target="_blank"
                class="bg-slate-600 px-3 py-1 rounded-lg text-xs">

                Print

                </a>

            </td>

        </tr>

        """

    content = f"""

    <div class="flex flex-col md:flex-row
    justify-between items-start md:items-center
    gap-4 mb-6">

        <h1 class="text-2xl font-bold">
            Arsip Transaksi
        </h1>

        <div class="flex gap-3 flex-wrap">

            <a href="/export/excel"
            class="bg-green-500 hover:bg-green-600 px-4 py-2 rounded-xl">

            Export Excel

            </a>

            <a href="/export/pdf"
            class="bg-red-500 hover:bg-red-600 px-4 py-2 rounded-xl">

            Export PDF

            </a>

        </div>

    </div>

    <div class="overflow-x-auto rounded-xl">

        <table class="w-full bg-slate-800 text-sm min-w-max">

            <tr class="bg-slate-700 text-left">

                <th class="p-3">Nama</th>

                <th class="p-3">Layanan</th>

                <th class="p-3">Berat</th>

                <th class="p-3">Total</th>

                <th class="p-3">Tanggal</th>

                <th class="p-3">Print</th>

            </tr>

            {rows}

        </table>

    </div>

    """

    return layout(content)

# ================= EXPORT EXCEL =================

@app.route("/export/excel")
@login_required
def export_excel():

    data = Order.query.filter_by(
        status="Selesai"
    ).all()

    rows = []

    for d in data:

        rows.append({
            "Nama": d.nama,
            "Layanan": d.layanan,
            "Berat": d.berat,
            "Total": d.total,
            "Tanggal": d.created_at.strftime("%d-%m-%Y")
        })

    df = pd.DataFrame(rows)

    path = "/tmp/laporan_laundry.xlsx"

    df.to_excel(path, index=False)

    return send_file(
        path,
        as_attachment=True
    )

# ================= EXPORT PDF =================

@app.route("/export/pdf")
@login_required
def export_pdf():

    data = Order.query.filter_by(
        status="Selesai"
    ).all()

    path = "/tmp/laporan_laundry.pdf"

    doc = SimpleDocTemplate(
        path,
        pagesize=letter
    )

    elements = []

    table_data = [[
        "Nama",
        "Layanan",
        "Berat",
        "Total",
        "Tanggal"
    ]]

    for d in data:

        table_data.append([
            d.nama,
            d.layanan,
            str(d.berat),
            f"Rp {d.total}",
            d.created_at.strftime("%d-%m-%Y")
        ])

    table = Table(table_data)

    table.setStyle(TableStyle([

        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold')

    ]))

    elements.append(table)

    doc.build(elements)

    return send_file(
        path,
        as_attachment=True
    )
# ================= Print =================    
@app.route("/print/<int:id>")
@login_required
def print_struk(id):
    o = Order.query.get(id)

    content = f"""
    <html>
    <head>
    <style>
        body {{
            font-family: monospace;
            width: 250px;
            font-size: 12px;
        }}
        .center {{ text-align: center; }}
        hr {{ border-top: 1px dashed black; }}
    </style>
    </head>

    <body onload="printAndClose()">

    <script>
    function printAndClose() {{
        window.print();
        setTimeout(() => {{
            window.close();
        }}, 500);
    }}
    </script>

    <div class="center">
        <b>ZEECLEAN LAUNDRY</b><br>
        Struk Transaksi
    </div>

    <hr>

    Nama    : {o.nama}<br>
    Layanan : {o.layanan}<br>
    Berat   : {o.berat} kg<br>
    Diskon  : {o.diskon}%<br>
    Total   : Rp {o.total}<br>

    <hr>

    Status  : {o.status}<br>
    {o.created_at.strftime("%d-%m-%Y %H:%M")}

    <hr>

    <div class="center">
        Terima kasih 🙏
    </div>

    </body>
    </html>
    """
    return content

@app.route("/update/<int:id>/<status>")
@login_required
def update(id, status):
    o = Order.query.get(id)
    o.status = status
    db.session.commit()
    return redirect("/transaksi")

@app.route("/logout")
def logout():
    logout_user()
    return redirect("/")

@app.route("/init")
def init():

    db.drop_all()
    db.create_all()

    # ADMIN
    db.session.add(User(
        username="admin",
        password="admin"
    ))

    # LAYANAN
    db.session.add(Layanan(
        nama="Cuci",
        harga=5000
    ))

    db.session.add(Layanan(
        nama="Setrika",
        harga=4000
    ))

    db.session.add(Layanan(
        nama="Cuci + Setrika",
        harga=7000
    ))

    db.session.add(Layanan(
        nama="Express",
        harga=11000
    ))

    db.session.add(Layanan(
        nama="Satuan",
        harga=10000
    ))

    db.session.add(Layanan(
        nama="Sepatu",
        harga=5000
    ))

    db.session.add(Layanan(
        nama="Boneka",
        harga=30000
    ))

    db.session.add(Layanan(
        nama="Karpet / m2",
        harga=20000
    ))

    db.session.commit()

    return "DB Ready"

import webbrowser

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
