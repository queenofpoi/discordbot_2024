import discord
import os
import asyncio
from discord.ext import commands
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from datetime import datetime

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


# ฟังก์ชันจัดรูปแบบข้อความ
def format_boss_info(boss_data):
    formatted_message = ""
    for boss in boss_data:
        formatted_message += (
            f"👹 **ชื่อบอส**: {boss['ชื่อบอส']}\n"
            f"🗺️ **แมพ**: {boss['แมพ']}\n"
            f"📉 **เวลาตาย**: {boss['เวลาตาย']}\n"
            f"📅 **เวลาเกิด**: {boss['เวลาเกิด']}\n"
            "================\n"
        )
    return formatted_message.strip()


async def update_boss_info():
    await bot.wait_until_ready()
    channel_id = 1291030429519843382  # เปลี่ยนเป็น Channel ID ของคุณ
    channel = bot.get_channel(channel_id)
    if channel is None:
        print("ไม่สามารถเข้าถึงช่องที่กำหนด กรุณาตรวจสอบ ID ของช่อง")
        return

    # เก็บข้อความที่บอทเคยส่งไว้ในตัวแปร message
    message = None
    async for msg in channel.history(limit=100):
        if msg.author == bot.user:
            message = msg
            break

    while not bot.is_closed():
        try:
            # ดึงข้อมูลจาก Google Sheets
            spreadsheet = client.open("BossFINRO")
            worksheet = spreadsheet.sheet1
            data = worksheet.get('A1:E23')
            headers = data[0]
            records = [dict(zip(headers, row)) for row in data[1:] if any(row)]

            # จัดรูปแบบข้อมูล
            formatted_message = format_boss_info(records)

            # แสดงข้อความหรือแก้ไขข้อความเดิม
            if message is None:
                # ถ้าไม่มีข้อความในแชนแนล ให้ส่งข้อความใหม่แล้วเก็บไว้ในตัวแปร
                message = await channel.send(formatted_message)
            else:
                # ถ้ามีข้อความอยู่แล้ว ให้แก้ไขข้อความนั้นแทน
                await message.edit(content=formatted_message)

            # รอ 10 นาที (600 วินาที) ก่อนอัปเดตข้อมูลใหม่
            await asyncio.sleep(600)

        except Exception as e:
            print(f"เกิดข้อผิดพลาด: {e}")
            await asyncio.sleep(60)


class BossSelector(discord.ui.Select):
    def __init__(self, boss_names):
        # สร้างตัวเลือกโดยใช้ชื่อบอสในเซลที่กำหนดแทนการแสดงเลขเซล
        options = [
            discord.SelectOption(label=boss, value=str(index))
            for index, boss in enumerate(boss_names, start=3)
        ]
        super().__init__(placeholder='เลือกบอสที่ต้องการแก้ไขเวลา', options=options)

    async def callback(self, interaction: discord.Interaction):
        # ใช้ value ของการเลือกเพื่อระบุแถวที่ต้องการเข้าถึง
        selected_row = int(self.values[0])  # แถวที่ถูกเลือก เช่น A3, A5, ...
        boss_name = next(option.label for option in self.options if option.value == str(selected_row))  # หาชื่อบอสที่ตรงกับค่า value
        await interaction.response.send_message(f'คุณเลือกบอส: {boss_name}. กรุณาใส่เวลาใหม่ในรูปแบบ HH:MM:', ephemeral=True)

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        try:
            # รับข้อความเวลาตายใหม่จากผู้ใช้
            msg = await bot.wait_for('message', check=check, timeout=30.0)
            new_time = msg.content

            if validate_time(new_time):
                worksheet = client.open("BossFINRO").sheet1
                worksheet.update(range_name=f'C{selected_row}', values=[[new_time]])  # แก้ไขให้ใช้ named arguments
                await interaction.channel.send(f'เวลาตายของ {boss_name} ได้ถูกอัปเดตเป็น {new_time}.')

                # ลบข้อความที่ใช้ในการเลือกบอสและเวลาตาย
                await msg.delete()  # ลบข้อความของผู้ใช้
                await interaction.message.delete()  # ลบข้อความของบอทที่ใช้ในการแสดงตัวเลือก

                await update_boss_info()  # อัปเดตข้อมูลบอสในแชนแนลที่กำหนด
            else:
                await interaction.channel.send("รูปแบบเวลาไม่ถูกต้อง กรุณาใส่เวลาในรูปแบบ HH:MM.")

        except asyncio.TimeoutError:
            await interaction.channel.send('หมดเวลา กรุณาลองใหม่.')


def validate_time(time_str):
    """ตรวจสอบรูปแบบเวลา HH:MM"""
    return len(time_str) == 5 and time_str[2] == ':' and time_str[:2].isdigit() and time_str[3:].isdigit() and 0 <= int(time_str[:2]) < 24 and 0 <= int(time_str[3:]) < 60


@bot.command()
async def b(ctx):
    """คำสั่ง !b สำหรับเลือกเซลและอัปเดตเวลา"""
    # ดึงข้อมูลบอสจาก Google Sheets เฉพาะเซล A3, A5, A7, A9, A11, A13, A15, A17, A19, A21, A23
    worksheet = client.open("BossFINRO").sheet1
    # ดึงข้อมูลทั้งหมดจากคอลัมน์ A ช่วง A3:A23 แล้วกรองเฉพาะเซลล์ที่ต้องการ
    all_boss_names = worksheet.col_values(1)[2:23]  # ดึงคอลัมน์ A ทั้งหมดแล้วเลือกแถวที่ 3 ถึง 23 (0-based index)

    # เลือกเฉพาะเซลล์ A3, A5, A7, ... A23
    boss_names = [all_boss_names[i] for i in range(0, len(all_boss_names), 2)]

    view = discord.ui.View()
    view.add_item(BossSelector(boss_names))
    await ctx.send("กรุณาเลือกบอส:", view=view)


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    bot.loop.create_task(update_boss_info())


token = os.getenv('DISCORD_BOT_TOKEN')
if token is None:
    raise ValueError("Token ไม่ได้ถูกตั้งค่าในตัวแปรสิ่งแวดล้อม")

bot.run(token)
