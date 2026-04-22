import os
import json
import random
import asyncio
from datetime import datetime, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
Application, CommandHandler, CallbackQueryHandler,
ContextTypes, MessageHandler, filters
)
TOKEN = os.environ.get("BOT_TOKEN")
DATA_FILE = "users.json"
CHECKS = [
{
"tag": " Técnica de las manos",
"question": "Mira tus manos. ¿Cuántos dedos ves?",
"instruction": "Observa lentamente cada dedo. En sueños, las manos suelen tener dedos
},
{
"tag": "◯ Pregunta existencial",
"question": "¿Estás soñando ahora mismo?",
"instruction": "Detente. ¿Cómo llegaste aquí? ¿Recuerdas los últimos 5 minutos con cl
},
{
"tag": "Aa Texto cambiante",
"question": "Lee algo, cierra los ojos y vuelve a leerlo.",
"instruction": "Busca un texto cercano. Léelo, aparta la mirada, vuélvelo a leer. En
},
{
"tag": "∿ Tapón nasal",
"question": "Tápate la nariz. ¿Puedes respirar?",
"instruction": "Cierra la boca y tápate la nariz. Intenta inhalar. En sueños puedes r
},
{
"tag": "◌ Memoria reciente",
"question": "¿Qué hacías hace 10 minutos?",
"instruction": "Intenta recordar con detalle. En los sueños, la memoria reciente es v
},
]
FRASES = [
"Dentro de un sueño, la mente crea mundos enteros. — Stephen LaBerge",
"Quien domina sus sueños comienza a dominar su mente despierta. — Dream Yoga",
"Pregúntate: ¿estoy soñando? Hazlo suficientes veces despierto y lo harás dormido. — Técn
"El sueño lúcido es la habilidad de despertar dentro del sueño sin salir de él. — Stephen
"La frontera entre el sueño y la vigilia es más delgada de lo que imaginas. — Frederik va
"Cada reality check es un ancla entre dos realidades. — Dream Yoga",
]
# ── USER DATA ─────────────────────────────────────────
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
# ── HELPERS ───────────────────────────────────────────
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
# ── COMMANDS ──────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
uid = update.effective_user.id
name = update.effective_user.first_name or "soñador"
data = load_data()
user = get_user(data, uid)
user["name"] = name
save_data(data)
msg = (
f" *Bienvenido a Lúcido, {name}*\n\n"
"Tu asistente de reality checks para sueños lúcidos.\n\n"
"*Comandos disponibles:*\n"
"/activar — iniciar recordatorios\n"
"/desactivar — pausar recordatorios\n"
"/check — hacer un reality check ahora\n"
"/config — ver tu configuración\n"
"/horario — cambiar horarios\n"
"/registro — ver tu historial\n"
"/stats — ver tus estadísticas\n"
"/frase — recibir inspiración\n\n"
"_Usa /activar para comenzar tu vigilancia._"
)
await update.message.reply_text(msg, parse_mode="Markdown")
async def activar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
uid = update.effective_user.id
data = load_data()
user = get_user(data, uid)
user["active"] = True
save_data(data)
# Schedule checks for this user
ctx.job_queue.run_repeating(
send_check_job,
interval=get_interval(user),
first=10,
name=str(uid),
data=uid,
chat_id=uid
)
await update.message.reply_text(
"✦ *Vigilancia activada*\n\n"
f"Recibirás reality checks entre las {user['day_start']} y {user['day_end']}.\n"
f"{'WBTB activado: ' + user['wbtb_start'] + ' – ' + user['wbtb_end'] if user['wbtb_en
"_Usa /desactivar para pausar._",
parse_mode="Markdown"
)
async def desactivar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
uid = update.effective_user.id
data = load_data()
user = get_user(data, uid)
user["active"] = False
save_data(data)
# Remove jobs
jobs = ctx.job_queue.get_jobs_by_name(str(uid))
for job in jobs:
job.schedule_removal()
await update.message.reply_text(
" *Vigilancia pausada.*\n\nUsa /activar cuando quieras reanudar.",
parse_mode="Markdown"
)
async def check_now(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
uid = update.effective_user.id
check = random_check()
await send_check(ctx.bot, uid, check)
async def config_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
uid = update.effective_user.id
data = load_data()
user = get_user(data, uid)
estado = " Activa" if user["active"] else " Pausada"
wbtb = " Activado" if user["wbtb_enabled"] else " Desactivado"
msg = (
f"*Tu configuración actual:*\n\n"
f"Estado: {estado}\n\n"
f"*Horario diurno*\n"
f" {user['day_start']} – {user['day_end']}\n"
f" {user['day_freq']} checks por hora\n\n"
f"*WBTB*: {wbtb}\n"
f" {user['wbtb_start']} – {user['wbtb_end']}\n"
f" {user['wbtb_freq']} checks por hora\n\n"
f"Usa /horario para cambiar los ajustes."
)
await update.message.reply_text(msg, parse_mode="Markdown")
async def horario_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
msg = (
"*Cambiar horario*\n\n"
"Usa estos comandos:\n\n"
"`/setdia 08:00 22:00 2` — inicio fin checks\\_por\\_hora\n"
"`/setwbtb 05:00 07:00 1` — inicio fin checks\\_por\\_hora\n"
"`/wbtb on` o `/wbtb off` — activar/desactivar WBTB\n\n"
"_Ejemplo: /setdia 09:00 23:00 3_"
)
await update.message.reply_text(msg, parse_mode="Markdown")
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
await update.message.reply_text(
f"✓ Horario diurno: {args[0]} – {args[1]}, {args[2]} checks/hora"
)
except:
await update.message.reply_text("Formato: /setdia 08:00 22:00 2")
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
await update.message.reply_text(
f"✓ WBTB: {args[0]} – {args[1]}, {args[2]} checks/hora"
)
except:
await update.message.reply_text("Formato: /setwbtb 05:00 07:00 1")
async def wbtb_toggle(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
uid = update.effective_user.id
try:
arg = ctx.args[0].lower()
data = load_data()
user = get_user(data, uid)
user["wbtb_enabled"] = (arg == "on")
save_data(data)
estado = "activado" if user["wbtb_enabled"] else "desactivado"
await update.message.reply_text(f"✓ WBTB {estado}")
except:
await update.message.reply_text("Uso: /wbtb on o /wbtb off")
async def registro_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
uid = update.effective_user.id
data = load_data()
user = get_user(data, uid)
log = user.get("log", [])
if not log:
return
await update.message.reply_text("Aún no tienes registros. Usa /activar para comenzar.
lines = []
for entry in log[-20:]:
ts = datetime.fromtimestamp(entry["ts"]).strftime("%d/%m %H:%M")
resp = " SUEÑO" if entry["ans"] == "yes" else " VIGILIA"
lines.append(f"`{ts}` {resp} — _{entry['tag']}_")
msg = "*Últimos 20 reality checks:*\n\n" + "\n".join(reversed(lines))
await update.message.reply_text(msg, parse_mode="Markdown")
async def stats_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
uid = update.effective_user.id
data = load_data()
user = get_user(data, uid)
log = user.get("log", [])
total = len(log)
suenos = sum(1 for e in log if e["ans"] == "yes")
pct = round(suenos / total * 100) if total > 0 else 0
# racha
streak = 0
today = datetime.now().date()
for i in range(30):
from datetime import timedelta
day = today - timedelta(days=i)
has = any(datetime.fromtimestamp(e["ts"]).date() == day for e in log)
if has:
streak += 1
else:
break
msg = (
f"*Tus estadísticas:*\n\n"
f" Total checks: *{total}*\n"
f" Sueños detectados: *{suenos}* ({pct}%)\n"
f" Racha actual: *{streak}* días\n"
)
await update.message.reply_text(msg, parse_mode="Markdown")
async def frase_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
await update.message.reply_text(f" _{random_frase()}_", parse_mode="Markdown")
# ── REALITY CHECK SENDER ──────────────────────────────
async def send_check(bot, chat_id, check):
keyboard = [
[
InlineKeyboardButton(" No, despierto", callback_data=f"no|{check['tag']}"),
InlineKeyboardButton(" Sí, sueño", callback_data=f"yes|{check['tag']}"),
]
]
markup = InlineKeyboardMarkup(keyboard)
msg = (
f"*{check['tag']}*\n\n"
f"_{check['question']}_\n\n"
f"{check['instruction']}"
)
await bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown", reply_markup=mar
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
# Reschedule with new random interval
interval = get_interval(user)
ctx.job.schedule_removal()
ctx.job_queue.run_repeating(
send_check_job,
interval=interval,
first=interval,
name=str(uid),
data=uid,
chat_id=uid
)
def get_interval(user):
in_w, freq = in_window(user)
if not in_w:
freq = user["day_freq"]
base = 3600 / max(freq, 1)
jitter = base * 0.3
return int(base - jitter + random.random() * jitter * 2)
# ── CALLBACK (botones sí/no) ──────────────────────────
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
resp = " *¡Sueño registrado!* Intenta despertar dentro de él." if ans == "yes" \
else " *Vigilia registrada.* Sigue atento."
await query.edit_message_reply_markup(reply_markup=None)
await query.message.reply_text(resp, parse_mode="Markdown")
# ── MAIN ──────────────────────────────────────────────
def main():
app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("activar", activar))
app.add_handler(CommandHandler("desactivar", desactivar))
app.add_handler(CommandHandler("check", check_now))
app.add_handler(CommandHandler("config", config_cmd))
app.add_handler(CommandHandler("horario", horario_cmd))
app.add_handler(CommandHandler("setdia", setdia))
app.add_handler(CommandHandler("setwbtb", setwbtb))
app.add_handler(CommandHandler("wbtb", wbtb_toggle))
app.add_handler(CommandHandler("registro", registro_cmd))
app.add_handler(CommandHandler("stats", stats_cmd))
app.add_handler(CommandHandler("frase", frase_cmd))
app.add_handler(CallbackQueryHandler(button_callback))
print(" Lúcido bot iniciado...")
app.run_polling()
if __name__ == "__main__":
main()
