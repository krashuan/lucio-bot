import os
import json
import random
import asyncio
from datetime import datetime, time, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
Application, CommandHandler, CallbackQueryHandler,
ContextTypes, MessageHandler, filters
)
TOKEN = os.environ.get("BOT_TOKEN")
DATA_FILE = "users.json"
CHECKS = [
{
"tag": "Tecnica de las manos",
"question": "Mira tus manos. Cuantos dedos ves?",
"instruction": "Observa lentamente cada dedo. En suenos, las manos suelen tener dedos
},
{
"tag": "Pregunta existencial",
"question": "Estas sonando ahora mismo?",
"instruction": "Detente. Como llegaste aqui? Recuerdas los ultimos 5 minutos con clar
},
{
"tag": "Texto cambiante",
"question": "Lee algo, cierra los ojos y vuelve a leerlo.",
"instruction": "Busca un texto cercano. Leelo, aparta la mirada, vuelvelo a leer. En
},
{
"tag": "Tapon nasal",
"question": "Tapate la nariz. Puedes respirar?",
"instruction": "Cierra la boca y tapate la nariz. Intenta inhalar. En suenos puedes r
},
{
"tag": "Memoria reciente",
"question": "Que hacías hace 10 minutos?",
"instruction": "Intenta recordar con detalle. En los suenos, la memoria reciente es v
},
]
FRASES = [
"Dentro de un sueno, la mente crea mundos enteros. - Stephen LaBerge",
"Quien domina sus suenos comienza a dominar su mente despierta. - Dream Yoga",
"Preguntate: estoy sonando? Hazlo suficientes veces despierto y lo haras dormido. - Tecni
"El sueno lucido es la habilidad de despertar dentro del sueno sin salir de el. - Stephen
"La frontera entre el sueno y la vigilia es mas delgada de lo que imaginas. - Frederik va
"Cada reality check es un ancla entre dos realidades. - Dream Yoga",
]
def load_data():
if os.path.exists(DATA_FILE):
with open(DATA_FILE, "r") as f:
return json.load(f)
return {}
def save_data(data):
with open(DATA_FILE, "w") as f:
json.dump(data, f, indent=2)
def get_user(data, uid):
uid = str(uid)
if uid not in data:
data[uid] = {
"active": False,
"day_start": "08:00",
"day_end": "22:00",
"day_freq": 2,
"wbtb_enabled": True,
"wbtb_start": "05:00",
"wbtb_end": "07:00",
"wbtb_freq": 1,
"log": [],
"name": ""
}
return data[uid]
def parse_time(t_str):
h, m = map(int, t_str.split(":"))
return time(h, m)
def in_window(user):
now = datetime.now().time()
day_s = parse_time(user["day_start"])
day_e = parse_time(user["day_end"])
if day_s <= now <= day_e:
return True, user["day_freq"]
if user["wbtb_enabled"]:
w_s = parse_time(user["wbtb_start"])
w_e = parse_time(user["wbtb_end"])
if w_s <= now <= w_e:
return True, user["wbtb_freq"]
return False, 0
def random_check():
return random.choice(CHECKS)
def random_frase():
return random.choice(FRASES)
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
uid = update.effective_user.id
name = update.effective_user.first_name or "sonador"
data = load_data()
user = get_user(data, uid)
user["name"] = name
save_data(data)
msg = (
"Bienvenido a Lucido, " + name + "\n\n"
"Tu asistente de reality checks para suenos lucidos.\n\n"
"Comandos disponibles:\n"
"/activar - iniciar recordatorios\n"
"/desactivar - pausar recordatorios\n"
"/check - hacer un reality check ahora\n"
"/config - ver tu configuracion\n"
"/setdia HH:MM HH:MM N - cambiar horario diurno\n"
"/setwbtb HH:MM HH:MM N - cambiar horario WBTB\n"
"/registro - ver tu historial\n"
"/stats - ver tus estadisticas\n"
"/frase - recibir inspiracion\n\n"
"Usa /activar para comenzar tu vigilancia."
)
await update.message.reply_text(msg)
async def activar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
uid = update.effective_user.id
data = load_data()
user = get_user(data, uid)
user["active"] = True
save_data(data)
jobs = ctx.job_queue.get_jobs_by_name(str(uid))
for job in jobs:
job.schedule_removal()
interval = get_interval(user)
ctx.job_queue.run_repeating(
send_check_job,
interval=interval,
first=10,
name=str(uid),
data=uid,
chat_id=uid
)
await update.message.reply_text(
"Vigilancia activada.\n"
"Horario: " + user["day_start"] + " a " + user["day_end"] + "\n"
"Usa /desactivar para pausar."
)
async def desactivar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
uid = update.effective_user.id
data = load_data()
user = get_user(data, uid)
user["active"] = False
save_data(data)
jobs = ctx.job_queue.get_jobs_by_name(str(uid))
for job in jobs:
job.schedule_removal()
await update.message.reply_text("Vigilancia pausada. Usa /activar para reanudar.")
async def check_now(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
uid = update.effective_user.id
check = random_check()
await send_check(ctx.bot, uid, check)
async def config_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
uid = update.effective_user.id
data = load_data()
user = get_user(data, uid)
estado = "Activa" if user["active"] else "Pausada"
wbtb = "Activado" if user["wbtb_enabled"] else "Desactivado"
msg = (
"Tu configuracion:\n\n"
"Estado: " + estado + "\n\n"
"Horario diurno: " + user["day_start"] + " a " + user["day_end"] + "\n"
"Checks por hora: " + str(user["day_freq"]) + "\n\n"
"WBTB: " + wbtb + "\n"
"Horario WBTB: " + user["wbtb_start"] + " a " + user["wbtb_end"] + "\n"
"Checks WBTB por hora: " + str(user["wbtb_freq"])
)
await update.message.reply_text(msg)
async def setdia(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
uid = update.effective_user.id
try:
args = ctx.args
data = load_data()
user = get_user(data, uid)
user["day_start"] = args[0]
user["day_end"] = args[1]
user["day_freq"] = int(args[2])
save_data(data)
except Exception:
await update.message.reply_text("Horario diurno actualizado: " + args[0] + " a await update.message.reply_text("Formato: /setdia 08:00 22:00 2")
" + ar
async def setwbtb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
uid = update.effective_user.id
try:
args = ctx.args
data = load_data()
user = get_user(data, uid)
user["wbtb_start"] = args[0]
user["wbtb_end"] = args[1]
user["wbtb_freq"] = int(args[2])
save_data(data)
except Exception:
await update.message.reply_text("WBTB actualizado: " + args[0] + " a " + args[1] + ",
await update.message.reply_text("Formato: /setwbtb 05:00 07:00 1")
async def registro_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
uid = update.effective_user.id
data = load_data()
user = get_user(data, uid)
log = user.get("log", [])
if not log:
await update.message.reply_text("Aun no tienes registros. Usa /activar para comenzar.
return
lines = []
for entry in log[-20:]:
ts = datetime.fromtimestamp(entry["ts"]).strftime("%d/%m %H:%M")
resp = "SUENO" if entry["ans"] == "yes" else "VIGILIA"
lines.append(ts + " " + resp + " - " + entry["tag"])
msg = "Ultimos 20 reality checks:\n\n" + "\n".join(reversed(lines))
await update.message.reply_text(msg)
async def stats_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
uid = update.effective_user.id
data = load_data()
user = get_user(data, uid)
log = user.get("log", [])
total = len(log)
suenos = sum(1 for e in log if e["ans"] == "yes")
pct = round(suenos / total * 100) if total > 0 else 0
streak = 0
today = datetime.now().date()
for i in range(30):
day = today - timedelta(days=i)
has = any(datetime.fromtimestamp(e["ts"]).date() == day for e in log)
if has:
streak += 1
else:
break
msg = (
"Tus estadisticas:\n\n"
"Total checks: " + str(total) + "\n"
"Suenos detectados: " + str(suenos) + " (" + str(pct) + "%)\n"
"Racha actual: " + str(streak) + " dias"
)
await update.message.reply_text(msg)
async def frase_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
await update.message.reply_text(random_frase())
async def send_check(bot, chat_id, check):
keyboard = [
[
InlineKeyboardButton("No, despierto", callback_data="no|" + check["tag"]),
InlineKeyboardButton("Si, sueno", callback_data="yes|" + check["tag"]),
]
]
markup = InlineKeyboardMarkup(keyboard)
msg = check["tag"] + "\n\n" + check["question"] + "\n\n" + check["instruction"]
await bot.send_message(chat_id=chat_id, text=msg, reply_markup=markup)
async def send_check_job(ctx: ContextTypes.DEFAULT_TYPE):
uid = ctx.job.data
data = load_data()
user = get_user(data, uid)
if not user["active"]:
return
in_w, freq = in_window(user)
if not in_w:
return
check = random_check()
await send_check(ctx.bot, uid, check)
def get_interval(user):
in_w, freq = in_window(user)
if not in_w:
freq = user["day_freq"]
base = 3600 / max(freq, 1)
jitter = base * 0.3
return int(base - jitter + random.random() * jitter * 2)
async def button_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
uid = query.from_user.id
ans, tag = query.data.split("|", 1)
data = load_data()
user = get_user(data, uid)
user["log"].append({
"ts": datetime.now().timestamp(),
"ans": ans,
"tag": tag
})
if len(user["log"]) > 500:
user["log"] = user["log"][-500:]
save_data(data)
resp = "Sueno registrado! Intenta despertar dentro de el." if ans == "yes" else "Vigilia
await query.edit_message_reply_markup(reply_markup=None)
await query.message.reply_text(resp)
def main():
app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("activar", activar))
app.add_handler(CommandHandler("desactivar", desactivar))
app.add_handler(CommandHandler("check", check_now))
app.add_handler(CommandHandler("config", config_cmd))
app.add_handler(CommandHandler("setdia", setdia))
app.add_handler(CommandHandler("setwbtb", setwbtb))
app.add_handler(CommandHandler("registro", registro_cmd))
app.add_handler(CommandHandler("stats", stats_cmd))
app.add_handler(CommandHandler("frase", frase_cmd))
app.add_handler(CallbackQueryHandler(button_callback))
print("Lucido bot iniciado...")
app.run_polling()
if __name__ == "__main__":
main()
