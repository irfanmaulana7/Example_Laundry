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

    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://unpkg.com/html5-qrcode"></script>

    </head>

    <body class="bg-slate-950 text-white">

    <div class="md:flex">

    <div class="w-full md:w-64 md:h-screen bg-slate-900 p-6 md:fixed">
        <img src="/static/logo.png" class="w-32 mb-8">

        <div class="flex md:block gap-4 text-sm md:text-base">
            <a href="/dashboard">Dashboard</a>
            <a href="/member">Member</a>
            <a href="/transaksi">Transaksi</a>
            <a href="/logout">Logout</a>
        </div>
    </div>

    <div class="md:ml-64 p-4 md:p-8 w-full">
    {content}
    </div>

    </div>

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
        <td>Rp {m.saldo}</td>
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
        <input name="saldo" placeholder="Saldo" class="p-2 bg-slate-800 rounded">
        <button class="col-span-4 bg-indigo-500 p-2 rounded">Tambah</button>
    </form>

    <form method="POST" action="/topup" class="flex gap-2 mb-4">
        <select name="id" class="p-2 bg-slate-800 text-white">
            {"".join([f"<option value='{m.id}'>{m.nama}</option>" for m in data])}
        </select>
        <input name="jumlah" placeholder="Top Up" class="p-2 bg-slate-800">
        <button class="bg-green-500 px-4 rounded">Top Up</button>
    </form>

    <table class="w-full bg-slate-800">
    <tr><th>Kode</th><th>Nama</th><th>HP</th><th>Alamat</th><th>Saldo</th><th>QR</th><th>Kartu</th></tr>
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
        options_member += f"<option value='{m.id}' data-saldo='{m.saldo}' {sel}>{m.nama} ({m.kode}) - Rp {m.saldo}</option>"

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

    <form method="POST" action="/add_transaksi" class="grid grid-cols-4 gap-3 mb-6">

    <div>
        <label>Member</label>
        <select name="member_id" class="p-2 bg-slate-800 text-white rounded">
            {options_member}
        </select>
    </div>

    <div>
        <label>Saldo</label>
        <input id="saldo_view" readonly class="p-2 bg-slate-700 text-green-400 rounded">
    </div>

    <div>
        <label>Layanan</label>
        <select id="layanan" name="layanan" class="p-2 bg-slate-800 text-white rounded">
            {options_layanan}
        </select>
    </div>

    <div>
        <label>Berat</label>
        <input id="berat" name="berat" type="number" class="p-2 bg-slate-800 text-white rounded">
    </div>

    <div>
        <label>Diskon</label>
        <input id="diskon" name="diskon" type="number" value="0" class="p-2 bg-slate-800 text-white rounded">
    </div>

    <div>
        <label>Total</label>
        <input id="total" name="total" readonly class="p-2 bg-slate-700 text-white rounded">
    </div>

    <button class="col-span-4 bg-indigo-500 p-2 rounded">Tambah</button>
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

    function updateSaldo() {{
        let s = document.querySelector("select[name='member_id']");
        let saldo = s.options[s.selectedIndex].getAttribute("data-saldo");
        document.getElementById("saldo_view").value = "Rp " + saldo;
    }}

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

    document.querySelector("select[name='member_id']").onchange = updateSaldo;

   updateSaldo();

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

    member = Member.query.get(request.form.get('member_id'))
    total_int = int(total or 0)

    # 🔥 POTONG SALDO
    if member and member.saldo >= total_int:
        member.saldo -= total_int
        total_int = 0

    db.session.add(Order(
        nama=member.nama if member else "-",
        layanan=request.form['layanan'],
        berat=berat,
        total=total_int,
        diskon=diskon
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
    app.run(host="0.0.0.0", port=5000)
