from flask import Flask, request, redirect, render_template_string, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from sqlalchemy import func
from datetime import datetime
import qrcode
from io import BytesIO

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
    kode = db.Column(db.String(20))  # 🔥 tambahan
    nama = db.Column(db.String(100))
    hp = db.Column(db.String(20))
    alamat = db.Column(db.String(200))

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100))
    layanan = db.Column(db.String(100))
    berat = db.Column(db.Float)
    total = db.Column(db.Integer)
    diskon = db.Column(db.Float, default=0)
    status = db.Column(db.String(50), default="Diterima")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ================= TARIF =================
tarif = {
    "Cuci": 5000,
    "Setrika": 4000,
    "Cuci+Setrika": 7000
}

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

    <meta name="theme-color" content="#020617">

    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="ZEECLEAN">

    <link rel="manifest" href="/static/manifest.json">
    <link rel="apple-touch-icon" href="/static/icon-192.png">

    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://unpkg.com/html5-qrcode"></script>

    </head>

    <body class="bg-slate-950 text-white">

    <div class="flex">

    <div class="w-64 h-screen bg-slate-900/95 backdrop-blur p-6 fixed border-r border-slate-800">
        <img src="/static/logo.png"
	class="w-40 mx-auto mb-8 object-contain">

        <a href="/dashboard">Dashboard</a><br>
        <a href="/member">Member</a><br>
        <a href="/transaksi">Transaksi</a><br>
        <a href="/logout">Logout</a>
    </div>

    <div class="ml-64 p-8 w-full">
    {content}
    </div>

    </div>

    <script>
    if ("serviceWorker" in navigator) {{
        navigator.serviceWorker.register("/static/service-worker.js")
        .then(() => console.log("PWA aktif"));
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

    <div class="grid grid-cols-4 gap-4 mb-6">
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
        <tr>
        <td>{m.kode}</td>
        <td>{m.nama}</td>
        <td>{m.hp}</td>
        <td>{m.alamat}</td>
        <td><img src="/qr/{m.id}" width="70"></td>
        <td><a href="/kartu/{m.id}" target="_blank" class="text-blue-400">Lihat</a></td>
        </tr>
        """

    content = f"""
    <h1 class="text-2xl mb-4">Member</h1>

    <form method="POST" action="/add_member" class="grid grid-cols-4 gap-3 mb-6">
        <input name="kode" placeholder="ID Member (ZEE001)" class="p-2 bg-slate-800 rounded">
        <input name="nama" placeholder="Nama" class="p-2 bg-slate-800 rounded">
        <input name="hp" placeholder="HP" class="p-2 bg-slate-800 rounded">
        <input name="alamat" placeholder="Alamat" class="p-2 bg-slate-800 rounded">
        <button class="col-span-4 bg-indigo-500 p-2 rounded">Tambah</button>
    </form>

    <table class="w-full bg-slate-800">
    <tr><th>Kode</th><th>Nama</th><th>HP</th><th>Alamat</th><th>QR</th><th>Kartu</th></tr>
    {rows}
    </table>
    """
    return layout(content)

@app.route("/add_member", methods=["POST"])
@login_required
def add_member():
    db.session.add(Member(
        kode=request.form['kode'],
        nama=request.form['nama'],
        hp=request.form['hp'],
        alamat=request.form['alamat']
    ))
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

# ================= KARTU =================
@app.route("/kartu/<int:id>")
@login_required
def kartu(id):
    m = Member.query.get(id)

    content = f"""
    <div class="flex justify-center items-center h-screen bg-slate-950">
        <div class="bg-slate-800 p-6 rounded-2xl text-center w-80">
            <img src="/static/logo.png" class="w-20 mx-auto mb-3">
            <h2 class="text-xl">{m.nama}</h2>
            <p>ID: {m.kode}</p>
            <img src="/qr/{m.id}" class="mx-auto my-4 w-40">
        </div>
    </div>
    """
    return layout(content)

# ================= TRANSAKSI =================
@app.route("/transaksi")
@login_required
def transaksi():
    data = Order.query.all()
    members = Member.query.all()
    selected = request.args.get("kode")

    options_member = ""
    for m in members:
        sel = "selected" if m.kode == selected else ""
        options_member += f"<option value='{m.nama}' {sel}>{m.nama} ({m.kode})</option>"

    options_layanan = "".join([f"<option>{k}</option>" for k in tarif])

    rows = ""
    for d in data:
        warna = "bg-gray-500"
        if d.status == "Dicuci": warna = "bg-yellow-400 text-black"
        elif d.status == "Setrika": warna = "bg-blue-400"
        elif d.status == "Packing": warna = "bg-purple-400"
        elif d.status == "Selesai": warna = "bg-green-500"

        rows += f"""
        <tr>
        <td>{d.nama}</td>
        <td>{d.layanan}</td>
        <td>{d.total}</td>
        <td>{d.diskon}%</td>
        <td><span class='{warna} px-2 py-1 rounded'>{d.status}</span></td>
        <td>
        <a href="/update/{d.id}/Dicuci">Cuci</a>
        <a href="/update/{d.id}/Setrika">Setrika</a>
        <a href="/update/{d.id}/Packing">Packing</a>
        <a href="/update/{d.id}/Selesai">Done</a>
	<a href="/print/{d.id}" target="_blank">Print</a>
        </td>
        </tr>
        """

    content = f"""
    <h1 class="text-2xl mb-4">Transaksi</h1>

    <div class="bg-slate-800 p-4 mb-4 rounded">
    <h3>📷 Scan Member</h3>
    <div id="reader" style="width:300px;"></div>
</div>

<div id="toast" class="fixed top-5 right-5 hidden bg-red-500 text-white px-4 py-2 rounded shadow-lg">
    Error
</div>

<!-- ✅ FORM WAJIB ADA -->
<form method="POST" action="/add_transaksi" class="grid grid-cols-4 gap-3 mb-6">

<div class="space-y-1">
    <label class="text-xs text-gray-400">Member</label>
    <select name="nama"
    class="w-full p-2 bg-slate-800 text-white rounded-lg border border-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition">
        {options_member}
    </select>
</div>

<div class="space-y-1">
    <label class="text-xs text-gray-400">Layanan</label>
    <select id="layanan" name="layanan"
    class="w-full p-2 bg-slate-800 text-white rounded-lg border border-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition">
        {options_layanan}
    </select>
</div>

<div class="space-y-1">
    <label class="text-xs text-gray-400">Berat (kg)</label>
    <input id="berat" name="berat" type="number"
    class="w-full p-2 bg-slate-800 text-white rounded-lg border border-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition">
</div>

<div class="space-y-1">
    <label class="text-xs text-gray-400">Diskon (%)</label>
    <input id="diskon" name="diskon" type="number" value="0"
    class="w-full p-2 bg-slate-800 text-white rounded-lg border border-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition">
</div>

<div class="space-y-1">
    <label class="text-xs text-gray-400">Total</label>
    <input id="total" name="total" readonly
    class="w-full p-2 bg-slate-700 text-white rounded-lg border border-slate-700">
</div>

<button class="col-span-4 bg-indigo-500 p-2 rounded-lg mt-2 hover:bg-indigo-600 transition">
    Tambah
</button>

</form>

    <table class="w-full bg-slate-800">
    {rows}
    </table>

    <script>
document.addEventListener("DOMContentLoaded", function() {{

    const tarif = {{
        "Cuci": 5000,
        "Setrika": 4000,
        "Cuci+Setrika": 7000
    }};

    function hitung() {{
        let l = document.getElementById("layanan").value;
        let b = parseFloat(document.getElementById("berat").value)||0;
        let d = parseFloat(document.getElementById("diskon").value)||0;
        let h = tarif[l]*b;
        document.getElementById("total").value = Math.round(h-(h*d/100));
    }}

    document.getElementById("layanan").onchange = hitung;
    document.getElementById("berat").oninput = hitung;
    document.getElementById("diskon").oninput = hitung;

    function showToast(msg) {{
        const t = document.getElementById("toast");
        t.innerText = msg;
        t.classList.remove("hidden");

        setTimeout(() => {{
            t.classList.add("hidden");
        }}, 3000);
    }}

    const form = document.querySelector("form");

    form.onsubmit = function(e) {{
        let berat = document.getElementById("berat").value;
        let diskon = document.getElementById("diskon").value;

        if (isNaN(berat) || berat <= 0) {{
            showToast("Berat harus angka dan > 0");
            e.preventDefault();
            return;
        }}

        if (isNaN(diskon) || diskon < 0 || diskon > 100) {{
            showToast("Diskon harus 0 - 100%");
            e.preventDefault();
            return;
        }}
    }};

    function onScanSuccess(text) {{
        if(text.startsWith("member:")) {{
            window.location="/transaksi?kode="+text.split(":")[1];
        }}
    }}

    const qr = new Html5Qrcode("reader");

    Html5Qrcode.getCameras().then(devices=>{{
        if(devices.length){{
            qr.start(devices[0].id, {{fps:10,qrbox:250}}, onScanSuccess);
        }}
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

    db.session.add(Order(
        nama       =request.form['nama'],
        layanan =request.form['layanan'],
        berat     =berat,
        total    =int(total or 0),
        diskon    =diskon
    ))

    db.session.commit()
    return redirect("/transaksi")

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
    db.session.add(User(username="admin", password="admin"))
    db.session.commit()
    return "DB Ready"

import webbrowser

if __name__ == "__main__":
    webbrowser.open("http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000)