import os,json,random
from datetime import datetime,time,timedelta
from telegram import Update,InlineKeyboardButton,InlineKeyboardMarkup
from telegram.ext import Application,CommandHandler,CallbackQueryHandler,ContextTypes
TOKEN=os.environ.get("BOT_TOKEN")
DATA_FILE="users.json"
CHECKS=[{"tag":"Manos","question":"Mira tus manos. Cuantos dedos ves?","instruction":"Observa cada dedo. En suenos cambian de forma."},{"tag":"Existencial","question":"Estas sonando ahora mismo?","instruction":"Detente. Como llegaste aqui? Recuerdas los ultimos 5 minutos?"},{"tag":"Texto","question":"Lee algo, cierra los ojos y vuelve a leerlo.","instruction":"En suenos el texto cambia cada vez que lo lees."},{"tag":"Nariz","question":"Tapate la nariz. Puedes respirar?","instruction":"En suenos puedes respirar aunque te tapes la nariz."},{"tag":"Memoria","question":"Que hacías hace 10 minutos?","instruction":"En suenos la memoria reciente es vaga o imposible."}]
FRASES=["Quien domina sus suenos domina su mente. - Dream Yoga","Preguntate: estoy sonando? Hazlo despierto y lo haras dormido. - DILD","El sueno lucido es despertar dentro del sueno. - LaBerge","Cada reality check es un ancla entre dos realidades."]
def load_data():
 if os.path.exists(DATA_FILE):
  with open(DATA_FILE,"r") as f: return json.load(f)
 return {}
def save_data(data):
 with open(DATA_FILE,"w") as f: json.dump(data,f)
def get_user(data,uid):
 uid=str(uid)
 if uid not in data: data[uid]={"active":False,"day_start":"08:00","day_end":"22:00","day_freq":2,"wbtb_enabled":True,"wbtb_start":"05:00","wbtb_end":"07:00","wbtb_freq":1,"log":[],"name":""}
 return data[uid]
def parse_hm(s):
 h,m=map(int,s.split(":"));return time(h,m)
def in_window(u):
 now=datetime.now().time()
 if parse_hm(u["day_start"])<=now<=parse_hm(u["day_end"]): return True,u["day_freq"]
 if u["wbtb_enabled"] and parse_hm(u["wbtb_start"])<=now<=parse_hm(u["wbtb_end"]): return True,u["wbtb_freq"]
 return False,0
def get_interval(u):
 iw,freq=in_window(u);freq=freq or u["day_freq"];base=3600/max(freq,1);j=base*0.3;return int(base-j+random.random()*j*2)
async def start(update,ctx):
 uid=update.effective_user.id;name=update.effective_user.first_name or "sonador"
 data=load_data();user=get_user(data,uid);user["name"]=name;save_data(data)
 await update.message.reply_text("Bienvenido a Lucido "+name+"!\n\nComandos:\n/activar - iniciar checks\n/desactivar - pausar\n/check - check ahora\n/config - ver config\n/setdia HH:MM HH:MM N\n/setwbtb HH:MM HH:MM N\n/registro - historial\n/stats - estadisticas\n/frase - inspiracion")
async def activar(update,ctx):
 uid=update.effective_user.id;data=load_data();user=get_user(data,uid);user["active"]=True;save_data(data)
 for j in ctx.job_queue.get_jobs_by_name(str(uid)): j.schedule_removal()
 ctx.job_queue.run_repeating(check_job,interval=get_interval(user),first=10,name=str(uid),data=uid,chat_id=uid)
 await update.message.reply_text("Vigilancia activada! Horario: "+user["day_start"]+" a "+user["day_end"])
async def desactivar(update,ctx):
 uid=update.effective_user.id;data=load_data();user=get_user(data,uid);user["active"]=False;save_data(data)
 for j in ctx.job_queue.get_jobs_by_name(str(uid)): j.schedule_removal()
 await update.message.reply_text("Vigilancia pausada.")
async def check_now(update,ctx):
 await send_check(ctx.bot,update.effective_user.id,random.choice(CHECKS))
async def config_cmd(update,ctx):
 uid=update.effective_user.id;data=load_data();u=get_user(data,uid)
 await update.message.reply_text("Estado: "+("Activa" if u["active"] else "Pausada")+"\nDia: "+u["day_start"]+" a "+u["day_end"]+" ("+str(u["day_freq"])+" x hora)\nWBTB: "+("Si" if u["wbtb_enabled"] else "No")+" "+u["wbtb_start"]+" a "+u["wbtb_end"])
async def setdia(update,ctx):
 uid=update.effective_user.id
 try:
  a=ctx.args;data=load_data();u=get_user(data,uid);u["day_start"]=a[0];u["day_end"]=a[1];u["day_freq"]=int(a[2]);save_data(data)
  await update.message.reply_text("Horario diurno: "+a[0]+" a "+a[1]+", "+a[2]+" checks/hora")
 except: await update.message.reply_text("Formato: /setdia 08:00 22:00 2")
async def setwbtb(update,ctx):
 uid=update.effective_user.id
 try:
  a=ctx.args;data=load_data();u=get_user(data,uid);u["wbtb_start"]=a[0];u["wbtb_end"]=a[1];u["wbtb_freq"]=int(a[2]);save_data(data)
  await update.message.reply_text("WBTB: "+a[0]+" a "+a[1]+", "+a[2]+" checks/hora")
 except: await update.message.reply_text("Formato: /setwbtb 05:00 07:00 1")
async def registro_cmd(update,ctx):
 uid=update.effective_user.id;data=load_data();log=get_user(data,uid).get("log",[])
 if not log: await update.message.reply_text("Sin registros aun."); return
 lines=[datetime.fromtimestamp(e["ts"]).strftime("%d/%m %H:%M")+" "+("SUENO" if e["ans"]=="yes" else "VIGILIA")+" - "+e["tag"] for e in log[-20:]]
 await update.message.reply_text("Ultimos checks:\n\n"+chr(10).join(reversed(lines)))
async def stats_cmd(update,ctx):
 uid=update.effective_user.id;data=load_data();log=get_user(data,uid).get("log",[])
 total=len(log);suenos=sum(1 for e in log if e["ans"]=="yes");pct=round(suenos/total*100) if total else 0
 streak=0;today=datetime.now().date()
 for i in range(30):
  if any(datetime.fromtimestamp(e["ts"]).date()==today-timedelta(days=i) for e in log): streak+=1
  else: break
 await update.message.reply_text("Total: "+str(total)+"\nSuenos: "+str(suenos)+" ("+str(pct)+"%%)\nRacha: "+str(streak)+" dias")
async def frase_cmd(update,ctx):
 await update.message.reply_text(random.choice(FRASES))
async def send_check(bot,chat_id,check):
 kb=[[InlineKeyboardButton("No, despierto",callback_data="no|"+check["tag"]),InlineKeyboardButton("Si, sueno",callback_data="yes|"+check["tag"])]]
 await bot.send_message(chat_id=chat_id,text=check["tag"]+"\n\n"+check["question"]+"\n\n"+check["instruction"],reply_markup=InlineKeyboardMarkup(kb))
async def check_job(ctx):
 uid=ctx.job.data;data=load_data();u=get_user(data,uid)
 if not u["active"]: return
 iw,freq=in_window(u)
 if not iw: return
 await send_check(ctx.bot,uid,random.choice(CHECKS))
 for j in ctx.job_queue.get_jobs_by_name(str(uid)): j.schedule_removal()
 ctx.job_queue.run_repeating(check_job,interval=get_interval(u),first=get_interval(u),name=str(uid),data=uid,chat_id=uid)
async def button_callback(update,ctx):
 q=update.callback_query;await q.answer();uid=q.from_user.id;ans,tag=q.data.split("|",1)
 data=load_data();u=get_user(data,uid);u["log"].append({"ts":datetime.now().timestamp(),"ans":ans,"tag":tag})
 if len(u["log"])>500: u["log"]=u["log"][-500:]
 save_data(data);await q.edit_message_reply_markup(reply_markup=None)
 await q.message.reply_text("Sueno registrado!" if ans=="yes" else "Vigilia registrada.")
def main():
 app=Application.builder().token(TOKEN).build()
 for cmd,fn in [("start",start),("activar",activar),("desactivar",desactivar),("check",check_now),("config",config_cmd),("setdia",setdia),("setwbtb",setwbtb),("registro",registro_cmd),("stats",stats_cmd),("frase",frase_cmd)]: app.add_handler(CommandHandler(cmd,fn))
 app.add_handler(CallbackQueryHandler(button_callback))
 print("Lucido bot iniciado...")
 app.run_polling()
if __name__=="__main__": main()
