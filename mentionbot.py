import discord
import asyncio
from discord.ext import commands
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from datetime import datetime
import os
import pytz
from keep_alive import keep_alive

# โหลดตัวแปรสิ่งแวดล้อมจาก .env
load_dotenv()

# กำหนด intents
intents = discord.Intents.all()

# กำหนดการเข้าถึง API Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name('src/vernal-vine-437414-q3-e5d419b8331f.json', scope)
client = gspread.authorize(creds)

# สร้างบอท Discord
bot = commands.Bot(command_prefix='!', intents=intents)

# ตัวแปรเก็บเวลาแจ้งเตือน
last_alert_times = {}

# กำหนดเขตเวลา Bangkok
bangkok_tz = pytz.timezone('Asia/Bangkok')

async def update_boss_info():
    await bot.wait_until_ready()  # รอให้บอทพร้อม
    channel = bot.get_channel(1291030429519843382)  # ใช้ ID ของช่องที่คุณระบุ

    if channel is None:
        print("ไม่สามารถค้นหาช่องที่มี ID ดังกล่าว กรุณาตรวจสอบ ID ของช่อง.")
        return

    while not bot.is_closed():
        # อ่านข้อมูลจาก Google Sheets
        sheet = client.open_by_key('1jAffyojzejCF0CiiB_CdOUxmZpqinTHe9hjF9nrpK4c').sheet1
        data = sheet.get_all_values()[1:23]  # ข้อมูลในช่วง A2:F23

        now = datetime.now(bangkok_tz)  # เวลาปัจจุบันในเขตเวลา กรุงเทพ
        current_time_str = now.strftime('%H:%M')  # เวลาปัจจุบันในรูปแบบ HH:MM

        for row in data:
            if not any(row):  # ข้ามแถวที่ว่าง
                continue

            boss_name = row[0]  # ชื่อบอสในเซลล์ A
            boss_map = row[1]   # ชื่อแมพ B
            spawn_time_str = row[4]  # เวลาเกิดในเซลล์ E

            if spawn_time_str == current_time_str:
                if boss_name not in last_alert_times or (now - last_alert_times[boss_name]).seconds >= 60:
                    await channel.send(f"@BossSlayer \nบอสมาแล้วจ้าาา! {boss_name} \nแมพ {boss_map} \nเกิดเวลา {current_time_str}")
                    last_alert_times[boss_name] = now  # บันทึกเวลาปัจจุบัน

        await asyncio.sleep(15)  # รอ 15 วินาทีก่อนอัปเดตข้อมูลอีกครั้ง

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    keep_alive()  # เรียกใช้ฟังก์ชันเพื่อให้บอททำงานตลอดเวลา
    bot.loop.create_task(update_boss_info())  # เรียกใช้ฟังก์ชัน update_boss_info

async def clear_cache():
    while not bot.is_closed():
        await asyncio.sleep(10800)  # รอ 3 ชั่วโมง (3 * 60 * 60)
        last_alert_times.clear()  # ลบแคชทุกๆ 3 ชั่วโมง
        print("ล้างแคชเรียบร้อยแล้ว")

@bot.command()
async def clearcache(ctx):
    last_alert_times.clear()  # ลบแคช
    await ctx.send("แคชถูกลบเรียบร้อยแล้ว!")  # แจ้งเตือนว่าการลบแคชเสร็จสมบูรณ์

@bot.command()
async def test(ctx):
    await ctx.send("กำลังทดสอบฟังก์ชัน update_boss_info...")  # แจ้งเตือนว่าฟังก์ชันกำลังทำงาน
    await update_boss_info()  # เรียกใช้ฟังก์ชันทดสอบ

token = os.getenv('DISCORD_BOT_TOKEN')
if token is None:
    raise ValueError("Token ไม่ได้ถูกตั้งค่าในตัวแปรสิ่งแวดล้อม")

server_on()

bot.run(token)
