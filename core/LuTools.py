#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LuTools v4.0 - Professional Remote PC Management Bot
Переработан на aiogram 2.25.1 с исправлением всех ошибок
Минимальные зависимости - только системные методы для скриншотов
"""

import asyncio
import os
import sys
import json
import time
import signal
import threading
import platform
import ctypes
import psutil
import logging
import subprocess
import shutil
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

# AIOGRAM imports
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, CallbackQuery, InputFile, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('LuTools.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Игнорирование сигнала Ctrl+C
signal.signal(signal.SIGINT, signal.SIG_IGN)

# ============= КОНФИГУРАЦИЯ =============
class Config:
    """Конфигурация приложения"""
    # НАСТРОЙТЕ ЭТИ ПАРАМЕТРЫ!
    BOT_TOKEN = '8317044568:AAGv40EWvS5Bli-kmg6Vb-7iyq8E8Lntufs'  # Замените на свой токен!
    ADMIN_ID = 5929120983  # Ваш Telegram ID
    
    # Настройки
    MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB
    ITEMS_PER_PAGE = 6
    MONITOR_INTERVAL = 300  # 5 минут
    SCREENSHOT_TIMEOUT = 10  # Уменьшено для надежности
    SCREENSHOT_QUALITY = 85
    LOG_FILE = 'LuTools.log'
    STARTUP_TIME = time.time()

# ============= МОДЕЛИ ДАННЫХ =============
@dataclass
class UserSettings:
    """Настройки пользователя"""
    auto_cleanup: bool = True
    last_activity: datetime = field(default_factory=datetime.now)

class BotState(Enum):
    """Состояния бота"""
    MAIN_MENU = "main"
    PROCESS_MANAGER = "processes"
    MONITORING = "monitoring"

# ============= УТИЛИТЫ ДЛЯ ИМЕН ПРОЦЕССОВ =============
class ProcessUtils:
    """Утилиты для работы с процессами и их именами"""
    
    # Словарь соответствия имен процессов понятным названиям
    PROCESS_NAME_MAP = {
        'msedge.exe': 'Microsoft Edge',
        'chrome.exe': 'Google Chrome',
        'firefox.exe': 'Mozilla Firefox',
        'opera.exe': 'Opera Browser',
        'brave.exe': 'Brave Browser',
        'teams.exe': 'Microsoft Teams',
        'zoom.exe': 'Zoom',
        'discord.exe': 'Discord',
        'telegram.exe': 'Telegram',
        'whatsapp.exe': 'WhatsApp',
        'slack.exe': 'Slack',
        'code.exe': 'Visual Studio Code',
        'pycharm.exe': 'PyCharm',
        'idea.exe': 'IntelliJ IDEA',
        'notepad++.exe': 'Notepad++',
        'winword.exe': 'Microsoft Word',
        'excel.exe': 'Microsoft Excel',
        'powerpnt.exe': 'Microsoft PowerPoint',
        'outlook.exe': 'Microsoft Outlook',
        'acrobat.exe': 'Adobe Acrobat',
        'photoshop.exe': 'Adobe Photoshop',
        'illustrator.exe': 'Adobe Illustrator',
        'spotify.exe': 'Spotify',
        'vlc.exe': 'VLC Media Player',
        'steam.exe': 'Steam',
        'javaw.exe': 'Java Application',
        'python.exe': 'Python',
        'pythonw.exe': 'Python (Windowed)',
        'node.exe': 'Node.js',
        'docker.exe': 'Docker',
        'postgres.exe': 'PostgreSQL',
        'mysql.exe': 'MySQL',
        'mongod.exe': 'MongoDB',
        'nginx.exe': 'Nginx',
        'apache.exe': 'Apache',
    }
    
    # Системные процессы, которые нужно игнорировать
    SYSTEM_PROCESSES = [
        'system', 'system idle process', 'svchost.exe', 'csrss.exe', 
        'wininit.exe', 'services.exe', 'lsass.exe', 'winlogon.exe', 
        'dwm.exe', 'explorer.exe', 'taskhostw.exe', 'taskhost.exe',
        'ctfmon.exe', 'conhost.exe', 'rundll32.exe', 'smss.exe',
        'spoolsv.exe', 'searchindexer.exe', 'searchprotocolhost.exe',
        'searchfilterhost.exe', 'wmpnetwk.exe', 'audiodg.exe',
        'wlanext.exe', 'dashost.exe', 'dllhost.exe',
        'sihost.exe', 'runtimebroker.exe', 'fontdrvhost.exe',
        'mousocoreworker.exe', 'securityhealthservice.exe',
        'compattelrunner.exe', 'microsoft.photos.exe',
        'applicationframehost.exe', 'shellexperiencehost.exe',
        'startmenuexperiencehost.exe', 'textinputhost.exe',
        'lockapp.exe', 'notepad.exe', 'write.exe', 'wordpad.exe',
        'mspaint.exe', 'snippingtool.exe', 'stikynot.exe',
        'calc.exe', 'calculator.exe', 'charmap.exe',
        'cleanmgr.exe', 'dfrgui.exe', 'diskmgmt.msc', 'eventvwr.msc',
        'fsquirt.exe', 'magnify.exe', 'msconfig.exe', 'msinfo32.exe',
        'mstsc.exe', 'narrator.exe', 'osk.exe', 'perfmon.exe',
        'regedit.exe', 'resmon.exe', 'sdclt.exe', 'services.msc',
        'shrpubw.exe', 'syskey.exe', 'taskmgr.exe', 'utilman.exe',
        'wmplayer.exe', 'wscript.exe'
    ]
    
    @staticmethod
    def get_friendly_name(process_name: str) -> str:
        """Получение понятного имени для процесса"""
        name_lower = process_name.lower()
        
        # Проверяем в словаре
        for proc_key, friendly_name in ProcessUtils.PROCESS_NAME_MAP.items():
            if name_lower == proc_key.lower():
                return friendly_name
        
        # Если не нашли, возвращаем оригинальное имя без расширения
        if '.' in process_name:
            base_name = process_name.split('.')[0]
            # Делаем первую букву заглавной и добавляем пробелы перед заглавными буквами
            result = ''
            for i, char in enumerate(base_name):
                if char.isupper() and i > 0 and base_name[i-1].islower():
                    result += ' ' + char
                else:
                    result += char
            return result.title()
        return process_name
    
    @staticmethod
    def is_system_process(process_name: str, username: str = "") -> bool:
        """Проверка, является ли процесс системным"""
        name_lower = process_name.lower()
        username_lower = username.lower() if username else ""
        
        # Проверяем по имени
        if name_lower in [p.lower() for p in ProcessUtils.SYSTEM_PROCESSES]:
            return True
        
        # Проверяем по имени пользователя (системные учетки)
        system_users = ['system', 'local service', 'network service', 'nt authority\\system']
        if any(sys_user in username_lower for sys_user in system_users):
            return True
        
        return False

# ============= СИСТЕМА МОНИТОРИНГА =============
class ActivityMonitor:
    """Мониторинг активности пользователя"""
    
    def __init__(self):
        self.activity_log = []
        self.is_monitoring = False
        self.monitor_thread = None
        self.process_cache = {}
        
    def start_monitoring(self):
        """Запуск мониторинга активности"""
        if not self.is_monitoring:
            self.is_monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_worker, daemon=True)
            self.monitor_thread.start()
            logger.info("Мониторинг активности запущен")
            return True
        return False
    
    def stop_monitoring(self):
        """Остановка мониторинга активности"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        logger.info("Мониторинг активности остановлен")
        return True
    
    def _monitor_worker(self):
        """Поток мониторинга активности"""
        while self.is_monitoring:
            try:
                current_time = datetime.now()
                active_processes = self._get_active_processes()
                
                if active_processes:
                    activity_record = {
                        'timestamp': current_time,
                        'processes': active_processes,
                        'idle_time': self._get_idle_time_windows()
                    }
                    
                    self.activity_log.append(activity_record)
                    
                    # Ограничение размера лога
                    if len(self.activity_log) > 1000:
                        self.activity_log = self.activity_log[-1000:]
                    
                    logger.debug(f"Записана активность: {len(active_processes)} процессов")
                
                time.sleep(Config.MONITOR_INTERVAL)
                
            except Exception as e:
                logger.error(f"Ошибка в мониторинге: {e}")
                time.sleep(10)
    
    def _get_active_processes(self) -> List[Dict]:
        """Получение активных пользовательских процессов"""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent']):
                try:
                    info = proc.info
                    process_name = info['name'] or ''
                    
                    if not process_name or process_name.strip() == '':
                        continue
                    
                    # Проверяем, не системный ли это процесс
                    if ProcessUtils.is_system_process(process_name, info['username']):
                        continue
                    
                    # Получаем понятное имя
                    friendly_name = ProcessUtils.get_friendly_name(process_name)
                    
                    # Пропускаем процессы с нулевой активностью
                    cpu_percent = info['cpu_percent'] or 0
                    memory_percent = info['memory_percent'] or 0
                    
                    if cpu_percent < 0.1 and memory_percent < 0.1:
                        continue
                    
                    processes.append({
                        'name': friendly_name,
                        'original_name': process_name,
                        'pid': info['pid'],
                        'username': info['username'] or 'N/A',
                        'cpu_percent': cpu_percent,
                        'memory_percent': memory_percent
                    })
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            logger.debug(f"Найдено {len(processes)} активных процессов")
            return processes
            
        except Exception as e:
            logger.error(f"Ошибка получения процессов: {e}")
            return []
    
    def _get_idle_time_windows(self):
        """Получение времени бездействия пользователя для Windows"""
        try:
            if platform.system() == "Windows":
                class LASTINPUTINFO(ctypes.Structure):
                    _fields_ = [
                        ('cbSize', ctypes.c_uint),
                        ('dwTime', ctypes.c_uint)
                    ]

                last_input_info = LASTINPUTINFO()
                last_input_info.cbSize = ctypes.sizeof(last_input_info)
                
                ctypes.windll.user32.GetLastInputInfo(ctypes.byref(last_input_info))
                tick_count = ctypes.windll.kernel32.GetTickCount()
                idle_time_ms = tick_count - last_input_info.dwTime
                
                return idle_time_ms / 1000.0
        except Exception as e:
            logger.error(f"Ошибка получения времени бездействия: {e}")
        
        return 0
    
    def get_activity_summary(self, hours=24):
        """Получение сводки активности"""
        if not self.activity_log:
            return "📭 Нет данных об активности"
        
        now = datetime.now()
        recent_activities = [a for a in self.activity_log 
                           if (now - a['timestamp']).total_seconds() <= hours * 3600]
        
        if not recent_activities:
            return "📭 Нет данных за последние 24 часа"
        
        total_records = len(recent_activities)
        idle_time_total = sum(a['idle_time'] for a in recent_activities)
        avg_idle = idle_time_total / total_records if total_records > 0 else 0
        
        # Сбор статистики по процессам
        process_stats = {}
        for activity in recent_activities:
            for proc in activity.get('processes', []):
                name = proc['name']
                process_stats[name] = process_stats.get(name, 0) + 1
        
        report_lines = [
            f"📊 Сводка активности за {hours} часов:",
            f"📈 Всего записей: {total_records}",
            f"⏱ Среднее время бездействия: {avg_idle:.1f} сек",
            f"🖥 Часто используемые приложения:"
        ]
        
        # Топ-5 процессов
        if process_stats:
            sorted_processes = sorted(process_stats.items(), key=lambda x: x[1], reverse=True)[:5]
            for proc, count in sorted_processes:
                percentage = (count / total_records) * 100
                report_lines.append(f"  • {proc}: {count} записей ({percentage:.1f}%)")
        else:
            report_lines.append("  • Нет данных о приложениях")
        
        return "\n".join(report_lines)

# ============= УТИЛИТЫ =============
class Utils:
    """Утилиты для работы с системой"""
    
    @staticmethod
    def is_admin() -> bool:
        """Проверка прав администратора"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    
    @staticmethod
    def clean_temp_files():
        """Очистка временных файлов"""
        try:
            # Очищаем папку screenshots
            screenshots_dir = Path('screenshots')
            if screenshots_dir.exists():
                for file in screenshots_dir.glob('screen_*'):
                    try:
                        file.unlink()
                    except:
                        pass
                        
            # Очищаем папку downloads от старых файлов (старше 1 дня)
            downloads_dir = Path('downloads')
            if downloads_dir.exists():
                current_time = time.time()
                for file in downloads_dir.glob('*'):
                    try:
                        if file.is_file():
                            file_age = current_time - file.stat().st_mtime
                            if file_age > 86400:  # 24 часа
                                file.unlink()
                    except:
                        pass
                        
            logger.info("Временные файлы очищены")
        except Exception as e:
            logger.error(f"Ошибка удаления временных файлов: {e}")
    
    @staticmethod
    def get_system_info():
        """Получение информации о системе"""
        try:
            info = {}
            info['platform'] = platform.platform()
            info['processor'] = platform.processor()
            info['architecture'] = platform.architecture()[0]
            info['python_version'] = platform.python_version()
            
            # Информация о памяти
            mem = psutil.virtual_memory()
            info['memory_total'] = mem.total // (1024**3)
            info['memory_available'] = mem.available // (1024**3)
            info['memory_percent'] = mem.percent
            
            # Информация о диске
            disk = psutil.disk_usage('/')
            info['disk_total'] = disk.total // (1024**3)
            info['disk_free'] = disk.free // (1024**3)
            info['disk_percent'] = disk.percent
            
            # Информация о процессоре
            info['cpu_count'] = psutil.cpu_count()
            info['cpu_percent'] = psutil.cpu_percent(interval=0.1)
            
            return info
        except Exception as e:
            logger.error(f"Ошибка получения информации о системе: {e}")
            return {}
    
    @staticmethod
    def take_screenshot() -> Optional[str]:
        """Создание скриншота - УЛУЧШЕННАЯ И НАДЕЖНАЯ ВЕРСИЯ"""
        try:
            # Создаем папку для скриншотов если не существует
            screenshots_dir = Path('screenshots')
            screenshots_dir.mkdir(exist_ok=True)
            
            filename = screenshots_dir / f"screen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            
            if platform.system() == "Windows":
                # Метод 1: Простой PowerShell скрипт (самый надежный)
                try:
                    # Экранируем обратные слеши для PowerShell
                    filepath_escaped = str(filename).replace('\\', '\\\\')
                    
                    ps_script = f"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$screen = [System.Windows.Forms.Screen]::PrimaryScreen
$bounds = $screen.Bounds

$bitmap = New-Object System.Drawing.Bitmap($bounds.Width, $bounds.Height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)

$graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
$graphics.Dispose()

$bitmap.Save('{filepath_escaped}', [System.Drawing.Imaging.ImageFormat]::Jpeg)
$bitmap.Dispose()

Write-Output "DONE"
                    """
                    
                    # Выполняем PowerShell
                    result = subprocess.run(
                        ['powershell', '-Command', ps_script],
                        capture_output=True, 
                        text=True, 
                        timeout=Config.SCREENSHOT_TIMEOUT,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    
                    if result.returncode == 0 and filename.exists():
                        file_size = filename.stat().st_size
                        if file_size > 1024:  # Минимум 1KB
                            logger.info(f"Скриншот создан через PowerShell: {file_size / 1024:.1f} KB")
                            return str(filename)
                    
                except Exception as e:
                    logger.error(f"PowerShell метод не сработал: {e}")
                
                # Метод 2: Используем pyautogui если установлен
                try:
                    import pyautogui
                    screenshot = pyautogui.screenshot()
                    
                    # Уменьшаем размер если слишком большой
                    max_width = 1920
                    if screenshot.width > max_width:
                        scale = max_width / screenshot.width
                        new_height = int(screenshot.height * scale)
                        screenshot = screenshot.resize((max_width, new_height))
                    
                    screenshot.save(str(filename), 'JPEG', quality=Config.SCREENSHOT_QUALITY)
                    
                    if filename.exists():
                        logger.info(f"Скриншот создан через pyautogui: {filename.stat().st_size / 1024:.1f} KB")
                        return str(filename)
                        
                except ImportError:
                    logger.warning("pyautogui не установлен")
                except Exception as e:
                    logger.error(f"Ошибка pyautogui: {e}")
                
                # Метод 3: Используем mss если установлен
                try:
                    import mss
                    import mss.tools
                    with mss.mss() as sct:
                        monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                        screenshot = sct.grab(monitor)
                        mss.tools.to_jpg(screenshot.rgb, screenshot.size, output=str(filename))
                    
                    if filename.exists():
                        logger.info(f"Скриншот создан через mss: {filename.stat().st_size / 1024:.1f} KB")
                        return str(filename)
                        
                except ImportError:
                    logger.warning("mss не установлен")
                except Exception as e:
                    logger.error(f"Ошибка mss: {e}")
                
                # Метод 4: Команда Windows (последний шанс)
                try:
                    # Используем nircmd если есть
                    nircmd_path = Path("nircmd.exe")
                    if nircmd_path.exists():
                        subprocess.run([str(nircmd_path), "savescreenshot", str(filename)], 
                                     timeout=Config.SCREENSHOT_TIMEOUT)
                    else:
                        # Пробуем sshotcmd
                        subprocess.run(["sshotcmd", "/capture", "/file", str(filename)], 
                                     timeout=Config.SCREENSHOT_TIMEOUT, shell=True)
                    
                    if filename.exists():
                        logger.info(f"Скриншот создан через команду: {filename.stat().st_size / 1024:.1f} KB")
                        return str(filename)
                        
                except Exception as e:
                    logger.error(f"Командный метод не сработал: {e}")
                    
            else:
                # Для Linux
                try:
                    # Пробуем scrot
                    subprocess.run(['scrot', '-q', '85', str(filename)], 
                                 check=True, timeout=Config.SCREENSHOT_TIMEOUT)
                    return str(filename)
                except:
                    try:
                        # Пробуем gnome-screenshot
                        subprocess.run(['gnome-screenshot', '-f', str(filename)], 
                                     check=True, timeout=Config.SCREENSHOT_TIMEOUT)
                        return str(filename)
                    except:
                        pass
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка создания скриншота: {e}")
            return None

# ============= КЛАВИАТУРЫ =============
class Keyboards:
    """Клавиатуры бота"""
    
    @staticmethod
    def main_menu() -> ReplyKeyboardMarkup:
        """Главное меню"""
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        buttons = [
            '📸 Скриншот',
            '📁 Файловый менеджер',
            '🔄 Менеджер процессов',
            '👁 Мониторинг активности',
            '📊 Статистика системы',
            '🔔 Уведомление',
            'ℹ️ Информация',
            '🛑 Остановить LuTools'
        ]
        for i in range(0, len(buttons), 2):
            if i + 1 < len(buttons):
                keyboard.row(KeyboardButton(buttons[i]), KeyboardButton(buttons[i+1]))
            else:
                keyboard.add(KeyboardButton(buttons[i]))
        return keyboard
    
    @staticmethod
    def stop_confirm() -> ReplyKeyboardMarkup:
        """Подтверждение остановки"""
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.row(KeyboardButton('✅ Да, остановить'), KeyboardButton('❌ Нет, продолжить работу'))
        return keyboard
    
    @staticmethod
    def create_process_keyboard(processes: List[Dict], page: int = 0, total_pages: int = 1) -> InlineKeyboardMarkup:
        """Создание инлайн-клавиатуры для управления процессами"""
        keyboard = InlineKeyboardMarkup(row_width=2)
        
        # Кнопки процессов для текущей страницы
        start_idx = page * Config.ITEMS_PER_PAGE
        end_idx = start_idx + Config.ITEMS_PER_PAGE
        
        for process in processes[start_idx:end_idx]:
            pid = process['pid']
            friendly_name = process['friendly_name']
            
            # Обрезаем имя если слишком длинное
            display_name = (friendly_name[:15] + "...") if len(friendly_name) > 15 else friendly_name
            
            keyboard.add(
                InlineKeyboardButton(
                    f"❌ {display_name}",
                    callback_data=f"kill_{pid}"
                ),
                InlineKeyboardButton(
                    f"📊 {process['cpu_percent']:.1f}%/{process['memory_percent']:.1f}%",
                    callback_data=f"info_{pid}"
                )
            )
        
        # Кнопки навигации
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"proc_prev_{page-1}"))
        
        nav_buttons.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="no_action"))
        
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"proc_next_{page+1}"))
        
        if nav_buttons:
            keyboard.row(*nav_buttons)
        
        # Дополнительные кнопки
        keyboard.row(
            InlineKeyboardButton("🔄 Обновить список", callback_data="proc_refresh"),
            InlineKeyboardButton("🔙 В главное меню", callback_data="main_menu")
        )
        
        return keyboard
    
    @staticmethod
    def monitoring_menu() -> InlineKeyboardMarkup:
        """Меню мониторинга активности"""
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("▶️ Запустить мониторинг", callback_data="mon_start"),
            InlineKeyboardButton("⏹ Остановить мониторинг", callback_data="mon_stop"),
            InlineKeyboardButton("📊 Сводка за 24ч", callback_data="mon_summary"),
            InlineKeyboardButton("📈 Подробный отчет", callback_data="mon_detailed"),
            InlineKeyboardButton("🔙 В главное меню", callback_data="main_menu")
        )
        return keyboard

# ============= ОСНОВНОЙ КЛАСС БОТА =============
class LuToolsBot:
    """Основной класс бота LuTools"""
    
    def __init__(self):
        # Проверка токена
        if Config.BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
            logger.error("❌ Токен бота не установлен!")
            print("\n" + "="*60)
            print("❌ ОШИБКА: Токен бота не установлен!")
            print("Пожалуйста, установите токен в файле LuTools.py")
            print("Найдите строку: BOT_TOKEN = 'YOUR_BOT_TOKEN_HERE'")
            print("и замените на ваш токен от @BotFather")
            print("="*60)
            input("\nНажмите Enter для выхода...")
            sys.exit(1)
        
        # Инициализация бота
        self.bot = Bot(token=Config.BOT_TOKEN)
        self.storage = MemoryStorage()
        self.dp = Dispatcher(self.bot, storage=self.storage)
        
        # Инициализация компонентов
        self.user_settings = UserSettings()
        self.current_state = BotState.MAIN_MENU
        self.is_running = True
        self.monitor = ActivityMonitor()
        self.process_messages = {}
        self.waiting_for_stop_confirm = False
        
        # Создание папок
        self._create_dirs()
        
        # Регистрация обработчиков
        self._register_handlers()
        
        logger.info("LuTools Bot инициализирован")
    
    def _create_dirs(self):
        """Создание необходимых директорий"""
        folders = ['downloads', 'screenshots']
        for folder in folders:
            os.makedirs(folder, exist_ok=True)
    
    def _register_handlers(self):
        """Регистрация обработчиков сообщений"""
        
        @self.dp.message_handler(commands=['start', 'help'])
        async def handle_start(message: Message):
            if message.from_user.id == Config.ADMIN_ID:
                await self._send_welcome(message)
            else:
                await self._log_unauthorized_access(message)
        
        @self.dp.message_handler(commands=['status'])
        async def handle_status(message: Message):
            if message.from_user.id == Config.ADMIN_ID:
                await self._send_status(message)
        
        @self.dp.message_handler(commands=['stop'])
        async def handle_stop_command(message: Message):
            if message.from_user.id == Config.ADMIN_ID:
                await self._handle_stop_request(message)
        
        @self.dp.message_handler(commands=['screenshot'])
        async def handle_screenshot_command(message: Message):
            if message.from_user.id == Config.ADMIN_ID:
                await self._take_screenshot(message)
        
        @self.dp.message_handler(commands=['processes'])
        async def handle_processes_command(message: Message):
            if message.from_user.id == Config.ADMIN_ID:
                await self._show_processes(message)
        
        @self.dp.callback_query_handler(lambda c: True)
        async def handle_callback_query(callback_query: CallbackQuery):
            if callback_query.from_user.id == Config.ADMIN_ID:
                await self._handle_callback(callback_query)
            else:
                await self.bot.answer_callback_query(callback_query.id, "❌ Доступ запрещен")
        
        @self.dp.message_handler(content_types=['text'])
        async def handle_text(message: Message):
            if message.from_user.id == Config.ADMIN_ID:
                await self._handle_user_message(message)
            else:
                await self._log_unauthorized_access(message)
        
        @self.dp.message_handler(content_types=['document'])
        async def handle_document(message: Message):
            if message.from_user.id == Config.ADMIN_ID:
                await self._handle_file_upload(message)
    
    async def _send_welcome(self, message: Message):
        """Приветственное сообщение"""
        welcome_text = f"""
🤖 Добро пожаловать в LuTools v4.0! 

Профессиональная система удаленного управления ПК

🔹 Основные команды:
• /start - Начать работу
• /status - Проверить состояние
• /stop - Остановить бота
• /screenshot - Быстрый скриншот
• /processes - Список процессов

📊 Статус системы:
• Пользователь: {os.getlogin()}
• ОС: {platform.platform()}
• Время работы: {int(time.time() - Config.STARTUP_TIME)} сек
• Админ ID: {Config.ADMIN_ID}

💡 Используйте кнопки меню ниже для управления.
        """
        
        await message.answer(
            welcome_text,
            parse_mode='Markdown',
            reply_markup=Keyboards.main_menu()
        )
    
    async def _send_status(self, message: Message):
        """Отправка статуса бота"""
        uptime = int(time.time() - Config.STARTUP_TIME)
        hours, remainder = divmod(uptime, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        sys_info = Utils.get_system_info()
        
        status_text = f"""
📊 Статус LuTools:

✅ Состояние: Активен
⏱ Время работы: {hours}ч {minutes}м {seconds}с
👤 Пользователь: {os.getlogin()}
🖥 ОС: {platform.platform()}
📝 Логи: LuTools.log

Системные ресурсы:
• Память: {sys_info.get('memory_percent', 0)}% использовано
• Диск: {sys_info.get('disk_percent', 0)}% использовано
• CPU: {sys_info.get('cpu_percent', 0)}%
• Мониторинг: {'✅ Активен' if self.monitor.is_monitoring else '❌ Не активен'}

Бот работает стабильно
        """
        
        await message.answer(status_text, parse_mode='Markdown')
    
    async def _handle_stop_request(self, message: Message):
        """Обработка запроса на остановку"""
        self.waiting_for_stop_confirm = True
        await message.answer(
            "⚠️ Подтверждение остановки\n\n"
            "Вы уверены, что хотите остановить LuTools?\n"
            "Бот будет полностью выключен.\n\n"
            "Все функции мониторинга будут остановлены.",
            parse_mode='Markdown',
            reply_markup=Keyboards.stop_confirm()
        )
    
    async def _handle_user_message(self, message: Message):
        """Обработка сообщений от администратора"""
        try:
            text = message.text
            
            if self.waiting_for_stop_confirm:
                if text == '✅ Да, остановить':
                    await self._stop_bot(message)
                    return
                elif text == '❌ Нет, продолжить работу':
                    self.waiting_for_stop_confirm = False
                    await message.answer(
                        "✅ Работа продолжается",
                        reply_markup=Keyboards.main_menu()
                    )
                    return
            
            if text == '🛑 Остановить LuTools':
                await self._handle_stop_request(message)
            
            elif text == '📸 Скриншот':
                await self._take_screenshot(message)
            
            elif text == '📊 Статистика системы':
                await self._show_system_stats(message)
            
            elif text == '🔄 Менеджер процессов':
                await self._show_processes(message)
            
            elif text == '👁 Мониторинг активности':
                await self._show_monitoring_menu(message)
            
            elif text == '📁 Файловый менеджер':
                await self._show_file_manager(message)
            
            elif text == '🔔 Уведомление':
                await message.answer(
                    "📝 Как отправить уведомление:\n\n"
                    "1. Нажмите кнопку '🔔 Уведомление'\n"
                    "2. Введите текст уведомления\n"
                    "3. Нажмите отправить\n\n"
                    "На компьютере появится всплывающее окно с вашим текстом.",
                    parse_mode='Markdown'
                )
            
            elif text == 'ℹ️ Информация':
                await self._send_welcome(message)
            
            else:
                await message.answer(
                    "ℹ️ Используйте кнопки меню для управления.",
                    reply_markup=Keyboards.main_menu()
                )
            
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}")
            await message.answer(
                "❌ Произошла ошибка при обработке команды",
                reply_markup=Keyboards.main_menu()
            )
    
    async def _handle_callback(self, callback_query: CallbackQuery):
        """Обработка callback запросов"""
        try:
            data = callback_query.data
            
            await self.bot.answer_callback_query(callback_query.id)
            
            if data == "main_menu":
                try:
                    await callback_query.message.delete()
                except:
                    pass
                await self._send_welcome(callback_query.message)
                return
            
            elif data.startswith("kill_"):
                pid = int(data.split("_")[1])
                await self._kill_process(callback_query, pid)
                return
            
            elif data.startswith("proc_prev_"):
                page = int(data.split("_")[2])
                await self._update_process_list(callback_query.message, page)
                return
            
            elif data.startswith("proc_next_"):
                page = int(data.split("_")[2])
                await self._update_process_list(callback_query.message, page)
                return
            
            elif data == "proc_refresh":
                await self._update_process_list(callback_query.message, 0)
                return
            
            elif data == "mon_start":
                if self.monitor.start_monitoring():
                    await self.bot.answer_callback_query(
                        callback_query.id,
                        "✅ Мониторинг активности запущен",
                        show_alert=True
                    )
                else:
                    await self.bot.answer_callback_query(
                        callback_query.id,
                        "⚠️ Мониторинг уже запущен",
                        show_alert=True
                    )
            
            elif data == "mon_stop":
                if self.monitor.stop_monitoring():
                    await self.bot.answer_callback_query(
                        callback_query.id,
                        "✅ Мониторинг активности остановлен",
                        show_alert=True
                    )
                else:
                    await self.bot.answer_callback_query(
                        callback_query.id,
                        "⚠️ Мониторинг уже остановлен",
                        show_alert=True
                    )
            
            elif data == "mon_summary":
                summary = self.monitor.get_activity_summary()
                await callback_query.message.answer(summary, parse_mode='Markdown')
            
            elif data == "mon_detailed":
                await self._show_detailed_monitoring(callback_query.message)
            
            elif data.startswith("info_"):
                pid = int(data.split("_")[1])
                await self._show_process_info(callback_query.message, pid)
            
            elif data == "no_action":
                pass  # Ничего не делаем для кнопки-заглушки
            
            else:
                await self.bot.answer_callback_query(
                    callback_query.id,
                    "Команда не распознана"
                )
            
        except Exception as e:
            logger.error(f"Ошибка обработки callback: {e}")
            try:
                await self.bot.answer_callback_query(
                    callback_query.id,
                    f"❌ Ошибка: {str(e)[:50]}",
                    show_alert=True
                )
            except:
                pass
    
    async def _update_process_list(self, message: Message, page: int = 0):
        """Обновление списка процессов"""
        try:
            processes = self._get_processes_list()
            
            if not processes:
                try:
                    await message.edit_text(
                        "📭 Нет активных пользовательских процессов для отображения\n\n"
                        "Все процессы могут быть системными или скрытыми.",
                        parse_mode='Markdown'
                    )
                except:
                    await message.answer(
                        "📭 Нет активных пользовательских процессов для отображения",
                        parse_mode='Markdown',
                        reply_markup=Keyboards.main_menu()
                    )
                return
            
            total_processes = len(processes)
            total_pages = max(1, (total_processes + Config.ITEMS_PER_PAGE - 1) // Config.ITEMS_PER_PAGE)
            page = max(0, min(page, total_pages - 1))
            
            message_text = f"""
🔄 Менеджер процессов

📊 Активных процессов: {total_processes}
📄 Страница: {page + 1} из {total_pages}
🕐 Обновлено: {datetime.now().strftime('%H:%M:%S')}

Для завершения процесса нажмите ❌
            """
            
            keyboard = Keyboards.create_process_keyboard(processes, page, total_pages)
            
            try:
                await message.edit_text(
                    message_text,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
            except:
                # Если не удалось редактировать, отправляем новое сообщение
                await message.answer(
                    message_text,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
            
        except Exception as e:
            logger.error(f"Ошибка обновления списка процессов: {e}")
    
    def _get_processes_list(self) -> List[Dict]:
        """Получение списка пользовательских процессов"""
        try:
            processes = []
            
            # Получаем текущего пользователя
            current_user = os.getlogin().lower()
            
            for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'status']):
                try:
                    pinfo = proc.info
                    process_name = pinfo['name'] or ''
                    
                    if not process_name or process_name.strip() == '':
                        continue
                    
                    username = pinfo['username'] or ''
                    username_lower = username.lower()
                    
                    # Пропускаем системные процессы
                    if ProcessUtils.is_system_process(process_name, username):
                        continue
                    
                    # Пропускаем процессы других пользователей
                    if current_user not in username_lower and 'service' not in username_lower:
                        continue
                    
                    # Получаем понятное имя
                    friendly_name = ProcessUtils.get_friendly_name(process_name)
                    
                    # Получаем использование ресурсов
                    cpu_percent = pinfo['cpu_percent'] or 0
                    memory_percent = pinfo['memory_percent'] or 0
                    status = pinfo['status'] or 'running'
                    
                    # Добавляем только если процесс активен
                    if cpu_percent > 0 or memory_percent > 0 or status in ['running', 'sleeping']:
                        processes.append({
                            'pid': pinfo['pid'],
                            'name': process_name,
                            'friendly_name': friendly_name,
                            'username': username,
                            'cpu_percent': cpu_percent,
                            'memory_percent': memory_percent,
                            'status': status
                        })
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                except Exception as e:
                    logger.debug(f"Ошибка обработки процесса: {e}")
                    continue
            
            # Сортировка по использованию памяти (по убыванию)
            processes.sort(key=lambda x: x['memory_percent'], reverse=True)
            
            logger.info(f"Найдено {len(processes)} пользовательских процессов")
            return processes
            
        except Exception as e:
            logger.error(f"Ошибка получения списка процессов: {e}")
            return []
    
    async def _show_process_info(self, message: Message, pid: int):
        """Показ информации о процессе"""
        try:
            proc = psutil.Process(pid)
            
            with proc.oneshot():
                info = {
                    'pid': pid,
                    'name': proc.name(),
                    'exe': proc.exe() if proc.exe() else 'N/A',
                    'cmdline': ' '.join(proc.cmdline()) if proc.cmdline() else 'N/A',
                    'username': proc.username(),
                    'status': proc.status(),
                    'create_time': datetime.fromtimestamp(proc.create_time()).strftime('%Y-%m-%d %H:%M:%S') if proc.create_time() else 'N/A',
                    'cpu_percent': proc.cpu_percent(interval=0.1),
                    'memory_percent': proc.memory_percent(),
                    'memory_info': proc.memory_info(),
                    'num_threads': proc.num_threads(),
                }
            
            # Форматируем информацию
            friendly_name = ProcessUtils.get_friendly_name(info['name'])
            
            info_text = f"""
📋 Информация о процессе

Основное:
• PID: {info['pid']}
• Имя: {info['name']}
• Понятное имя: {friendly_name}
• Пользователь: {info['username']}
• Статус: {info['status']}

Ресурсы:
• CPU: {info['cpu_percent']:.1f}%
• Память: {info['memory_percent']:.1f}%
• RSS: {info['memory_info'].rss / 1024 / 1024:.1f} MB
• VMS: {info['memory_info'].vms / 1024 / 1024:.1f} MB
• Потоки: {info['num_threads']}

Детали:
• Исполняемый файл: {info['exe'][:100]}
• Командная строка: {info['cmdline'][:100]}
• Время создания: {info['create_time']}
            """
            
            await message.answer(info_text, parse_mode='Markdown')
            
        except psutil.NoSuchProcess:
            await message.answer(f"❌ Процесс с PID {pid} не найден")
        except Exception as e:
            logger.error(f"Ошибка получения информации о процессе {pid}: {e}")
            await message.answer(f"❌ Ошибка получения информации о процессе: {str(e)[:100]}")
    
    async def _take_screenshot(self, message: Message):
        """Создание скриншота"""
        try:
            msg = await message.answer(
                "📸 Создание скриншота...\n\nПожалуйста, подождите 5-10 секунд...",
                parse_mode='Markdown'
            )
            
            screenshot_file = Utils.take_screenshot()
            
            if screenshot_file and os.path.exists(screenshot_file):
                file_size = os.path.getsize(screenshot_file) / 1024  # KB
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                try:
                    with open(screenshot_file, 'rb') as photo:
                        if file_size < 1024 * 5:  # Если меньше 5MB
                            await message.answer_photo(
                                photo,
                                caption=f"📸 Скриншот • {timestamp}\n📦 Размер: {file_size:.1f} KB\n✅ Успешно создан!"
                            )
                        else:
                            # Если файл слишком большой, отправляем как документ
                            await message.answer_document(
                                InputFile(photo),
                                caption=f"📸 Скриншот • {timestamp}\n📦 Размер: {file_size:.1f} KB"
                            )
                    
                    logger.info(f"Скриншот отправлен: {screenshot_file} ({file_size:.1f} KB)")
                    
                    # Удаляем файл после отправки
                    try:
                        os.remove(screenshot_file)
                    except:
                        pass
                    
                    # Удаляем сообщение о создании
                    try:
                        await msg.delete()
                    except:
                        pass
                        
                except Exception as e:
                    await message.answer(f"❌ Ошибка отправки скриншота: {str(e)[:100]}")
                    
            else:
                try:
                    await msg.edit_text(
                        "❌ Не удалось создать скриншот\n\n"
                        "Рекомендуемые действия:\n"
                        "1. Установите библиотеку mss: pip install mss\n"
                        "2. Или установите pyautogui: pip install pyautogui\n"
                        "3. Для Windows убедитесь, что PowerShell доступен\n\n"
                        "Альтернатива:\n"
                        "Используйте PrtScn кнопку и сохраните скриншот вручную",
                        parse_mode='Markdown'
                    )
                except:
                    await message.answer(
                        "❌ Не удалось создать скриншот. Установите mss или pyautogui.",
                        parse_mode='Markdown'
                    )
            
        except Exception as e:
            logger.error(f"Ошибка создания скриншота: {e}")
            await message.answer(
                f"❌ Ошибка создания скриншота: {str(e)[:100]}",
                reply_markup=Keyboards.main_menu()
            )
    
    async def _kill_process(self, callback_query: CallbackQuery, pid: int):
        """Завершение процесса по PID"""
        try:
            # Проверяем, существует ли процесс
            try:
                proc = psutil.Process(pid)
                proc_name = proc.name()
                proc_username = proc.username()
            except psutil.NoSuchProcess:
                await self.bot.answer_callback_query(
                    callback_query.id,
                    f"❌ Процесс PID:{pid} не найден",
                    show_alert=True
                )
                await self._update_process_list(callback_query.message, 0)
                return
            
            # Проверяем, не системный ли это процесс
            if ProcessUtils.is_system_process(proc_name, proc_username):
                await self.bot.answer_callback_query(
                    callback_query.id,
                    f"❌ Нельзя завершить системный процесс: {proc_name}",
                    show_alert=True
                )
                return
            
            # Получаем понятное имя
            friendly_name = ProcessUtils.get_friendly_name(proc_name)
            
            # Завершаем процесс
            try:
                proc.terminate()
                proc.wait(timeout=3)
                
                await self.bot.answer_callback_query(
                    callback_query.id,
                    f"✅ Процесс '{friendly_name}' (PID:{pid}) завершен",
                    show_alert=True
                )
                
                logger.info(f"Процесс завершен: {friendly_name} (PID:{pid})")
                
                # Обновляем список после небольшой задержки
                await asyncio.sleep(1)
                await self._update_process_list(callback_query.message, 0)
                    
            except psutil.TimeoutExpired:
                # Пробуем принудительно завершить
                try:
                    proc.kill()
                    await self.bot.answer_callback_query(
                        callback_query.id,
                        f"⚠️ Процесс '{friendly_name}' (PID:{pid}) принудительно завершен",
                        show_alert=True
                    )
                    await asyncio.sleep(1)
                    await self._update_process_list(callback_query.message, 0)
                except:
                    await self.bot.answer_callback_query(
                        callback_query.id,
                        f"❌ Не удалось завершить процесс '{friendly_name}' (PID:{pid})",
                        show_alert=True
                    )
            
        except psutil.AccessDenied:
            await self.bot.answer_callback_query(
                callback_query.id,
                f"❌ Нет прав для завершения процесса PID:{pid}",
                show_alert=True
            )
        except Exception as e:
            logger.error(f"Ошибка завершения процесса {pid}: {e}")
            await self.bot.answer_callback_query(
                callback_query.id,
                f"❌ Ошибка: {str(e)[:50]}",
                show_alert=True
            )
    
    async def _show_processes(self, message: Message):
        """Отображение списка процессов"""
        try:
            processes = self._get_processes_list()
            
            if not processes:
                await message.answer(
                    "📭 Нет активных пользовательских процессов для отображения\n\n"
                    "Возможные причины:\n"
                    "1. Все процессы системные\n"
                    "2. Нет активных пользовательских процессов\n"
                    "3. Ограничения прав доступа",
                    parse_mode='Markdown',
                    reply_markup=Keyboards.main_menu()
                )
                return
            
            total_processes = len(processes)
            total_pages = max(1, (total_processes + Config.ITEMS_PER_PAGE - 1) // Config.ITEMS_PER_PAGE)
            
            message_text = f"""
🔄 Менеджер процессов

📊 Активных процессов: {total_processes}
📄 Страница: 1 из {total_pages}
🕐 Обновлено: {datetime.now().strftime('%H:%M:%S')}

Для завершения процесса нажмите ❌
            """
            
            keyboard = Keyboards.create_process_keyboard(processes, 0, total_pages)
            
            await message.answer(
                message_text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Ошибка отображения процессов: {e}")
            await message.answer(
                f"❌ Ошибка получения списка процессов: {str(e)[:100]}",
                reply_markup=Keyboards.main_menu()
            )
    
    async def _show_monitoring_menu(self, message: Message):
        """Отображение меню мониторинга активности"""
        menu_text = f"""
👁 Мониторинг активности

Функции:
• ▶️ Запуск постоянного мониторинга
• ⏹ Остановка мониторинга
• 📊 Получение сводки активности
• 📈 Подробный отчет

Что отслеживается:
✓ Активные процессы (без системных)
✓ Время бездействия
✓ Использование CPU
✓ Статистика по программам

Текущий статус: {'✅ Активен' if self.monitor.is_monitoring else '❌ Не активен'}

Записей в логе: {len(self.monitor.activity_log)}
        """
        
        await message.answer(
            menu_text,
            parse_mode='Markdown',
            reply_markup=Keyboards.monitoring_menu()
        )
    
    async def _show_detailed_monitoring(self, message: Message):
        """Отображение подробного отчета мониторинга"""
        if not self.monitor.activity_log:
            await message.answer("📭 Нет данных мониторинга для отображения", parse_mode='Markdown')
            return
        
        # Получаем последние 10 записей
        recent_activities = self.monitor.activity_log[-10:]
        
        report_lines = ["📈 Последние записи мониторинга:"]
        
        for i, activity in enumerate(recent_activities[::-1], 1):
            timestamp = activity['timestamp'].strftime('%H:%M:%S')
            processes = activity.get('processes', [])
            idle_time = activity.get('idle_time', 0)
            
            report_lines.append(f"\n{i}. {timestamp} (бездействие: {idle_time:.1f} сек)")
            
            if processes:
                process_groups = {}
                for proc in processes:
                    name = proc['name']
                    process_groups[name] = process_groups.get(name, 0) + 1
                
                for name, count in list(process_groups.items())[:3]:
                    report_lines.append(f"   • {name}" + (f" (x{count})" if count > 1 else ""))
                
                if len(process_groups) > 3:
                    report_lines.append(f"   • ... и еще {len(process_groups) - 3} процессов")
            else:
                report_lines.append("   • Нет активных процессов")
        
        report_text = "\n".join(report_lines)
        
        await message.answer(report_text, parse_mode='Markdown')
    
    async def _show_system_stats(self, message: Message):
        """Отображение статистики системы"""
        sys_info = Utils.get_system_info()
        
        stats_text = f"""
📊 Статистика системы

Основная информация:
• ОС: {sys_info.get('platform', 'Unknown')}
• Процессор: {sys_info.get('processor', 'Unknown')[:50]}
• Архитектура: {sys_info.get('architecture', 'Unknown')}
• Python: {sys_info.get('python_version', 'Unknown')}

Использование памяти:
• Всего: {sys_info.get('memory_total', 0)} GB
• Доступно: {sys_info.get('memory_available', 0)} GB
• Использовано: {sys_info.get('memory_percent', 0)}%

Использование диска:
• Всего: {sys_info.get('disk_total', 0)} GB
• Свободно: {sys_info.get('disk_free', 0)} GB
• Использовано: {sys_info.get('disk_percent', 0)}%

Процессор:
• Ядер: {sys_info.get('cpu_count', 0)}
• Загрузка: {sys_info.get('cpu_percent', 0)}%

Активность:
• Мониторинг: {'✅ Включен' if self.monitor.is_monitoring else '❌ Выключен'}
• Процессы: {len(psutil.pids())} активных
• Пользователь: {os.getlogin()}
        """
        
        await message.answer(stats_text, parse_mode='Markdown')
    
    async def _show_file_manager(self, message: Message):
        """Отображение файлового менеджера"""
        current_dir = os.getcwd()
        downloads_dir = os.path.join(current_dir, 'downloads')
        
        if not os.path.exists(downloads_dir):
            os.makedirs(downloads_dir)
        
        try:
            files = os.listdir(downloads_dir)
            file_list = []
            total_size = 0
            
            for file in files:
                filepath = os.path.join(downloads_dir, file)
                if os.path.isfile(filepath):
                    size = os.path.getsize(filepath) / 1024  # KB
                    total_size += size
                    file_list.append(f"  • {file} ({size:.1f} KB)")
            
            if file_list:
                files_text = "\n".join(file_list[:10])
                if len(file_list) > 10:
                    files_text += f"\n  • ... и еще {len(file_list) - 10} файлов"
            else:
                files_text = "  📭 Папка пуста"
                
        except Exception as e:
            files_text = f"  ❌ Ошибка чтения папки: {str(e)[:50]}"
            total_size = 0
        
        fm_text = f"""
📁 Файловый менеджер

Текущая директория: {current_dir}

Папка загрузок (downloads):
{files_text}

Общий размер: {total_size:.1f} KB

Инструкция:
1. Отправьте файл боту для загрузки на компьютер
2. Файлы сохраняются в папке downloads/

Доступные команды:
• Отправьте любой файл для загрузки
        """
        
        await message.answer(fm_text, parse_mode='Markdown')
    
    async def _handle_file_upload(self, message: Message):
        """Обработка загрузки файлов"""
        try:
            file_info = await self.bot.get_file(message.document.file_id)
            downloaded_file = await self.bot.download_file(file_info.file_path)
            
            filename = message.document.file_name
            filepath = os.path.join('downloads', filename)
            
            os.makedirs('downloads', exist_ok=True)
            
            counter = 1
            base_name, extension = os.path.splitext(filename)
            while os.path.exists(filepath):
                filename = f"{base_name}_{counter}{extension}"
                filepath = os.path.join('downloads', filename)
                counter += 1
            
            with open(filepath, 'wb') as new_file:
                new_file.write(downloaded_file)
            
            filesize = os.path.getsize(filepath) / 1024  # KB
            
            await message.reply(
                f"✅ Файл успешно загружен!\n"
                f"📁 Имя: {filename}\n"
                f"📦 Размер: {filesize:.1f} KB\n"
                f"📁 Путь: {filepath}",
                parse_mode='Markdown'
            )
            
            logger.info(f"Файл загружен: {filename} ({filesize:.1f} KB)")
            
        except Exception as e:
            logger.error(f"Ошибка загрузки файла: {e}")
            await message.reply(f"❌ Ошибка загрузки файла: {str(e)[:100]}")
    
    async def _send_notification(self, message: Message):
        """Отправка уведомления на компьютер"""
        try:
            text = message.text
            
            if platform.system() == "Windows":
                ctypes.windll.user32.MessageBoxW(
                    0,
                    f"📩 LuTools Notification\n\n{text}\n\n"
                    f"Отправлено: {datetime.now().strftime('%H:%M:%S')}",
                    '🔔 LuTools Professional',
                    0x40
                )
            else:
                try:
                    subprocess.run(['notify-send', 'LuTools Notification', text])
                except:
                    pass
            
            await message.answer(
                f"✅ Уведомление отправлено на компьютер\n"
                f"📝 Текст: {text[:100]}",
                parse_mode='Markdown'
            )
            
            logger.info(f"Уведомление отправлено: {text}")
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления: {e}")
            await message.answer("❌ Не удалось отправить уведомление")
    
    async def _log_unauthorized_access(self, message: Message):
        """Логирование несанкционированного доступа"""
        alert = f"🚨 Попытка несанкционированного доступа!\n\n"
        alert += f"👤 Пользователь: {message.from_user.first_name}\n"
        alert += f"🆔 ID: {message.from_user.id}\n"
        if hasattr(message, 'text') and message.text:
            alert += f"✉️ Сообщение: {message.text}\n"
        else:
            alert += f"✉️ Тип: Файл\n"
        alert += f"⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        try:
            await self.bot.send_message(Config.ADMIN_ID, alert, parse_mode='Markdown')
        except:
            pass
        
        logger.warning(f"Несанкционированный доступ от ID: {message.from_user.id}")
    
    async def _stop_bot(self, message: Message):
        """Остановка бота"""
        try:
            logger.info("Начало процедуры остановки бота")
            
            self.monitor.stop_monitoring()
            
            await message.answer(
                "🛑 Остановка LuTools...\n\n"
                "Происходит завершение всех процессов...",
                parse_mode='Markdown'
            )
            
            await asyncio.sleep(2)
            
            await message.answer(
                "✅ LuTools остановлен\n\n"
                "Все функции отключены:\n"
                "• Мониторинг активности\n"
                "• Управление процессами\n"
                "• Системное наблюдение\n\n"
                "Для запуска запустите скрипт снова.",
                parse_mode='Markdown'
            )
            
            logger.info("LuTools остановлен по команде из Telegram")
            
            Utils.clean_temp_files()
            
            # Останавливаем event loop
            loop = asyncio.get_event_loop()
            loop.stop()
            
        except Exception as e:
            logger.error(f"Ошибка остановки бота: {e}")
    
    async def on_startup(self, dp):
        """Действия при запуске бота"""
        logger.info("Бот запускается...")
        
        try:
            startup_msg = f"""
🚀 LuTools Professional v4.0 запущен!

⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
💻 Система: {platform.platform()}
👤 Пользователь: {os.getlogin()}
📊 Мониторинг: АКТИВЕН

✅ Бот готов к работе!

🛑 Для остановки используйте /stop или кнопку "Остановить LuTools"
            """
            
            await self.bot.send_message(
                Config.ADMIN_ID,
                startup_msg,
                parse_mode='Markdown',
                reply_markup=Keyboards.main_menu()
            )
            logger.info("Сообщение о запуске отправлено")
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения о запуске: {e}")
        
        # Запускаем мониторинг активности
        self.monitor.start_monitoring()
        logger.info("Мониторинг активности запущен")
    
    async def on_shutdown(self, dp):
        """Действия при остановке бота"""
        logger.info("Бот останавливается...")
        self.monitor.stop_monitoring()
        Utils.clean_temp_files()
        await self.bot.close()
    
    def run(self):
        """Запуск бота"""
        logger.info("Запуск LuTools Bot...")
        
        if not Utils.is_admin():
            logger.warning("Бот запущен без прав администратора")
        
        Utils.clean_temp_files()
        
        # Запускаем бота
        executor.start_polling(
            self.dp,
            skip_updates=True,
            on_startup=self.on_startup,
            on_shutdown=self.on_shutdown,
            timeout=20,
            relax=0.1,
            fast=True
        )

# ============= ТОЧКА ВХОДА =============
def main():
    """Точка входа в приложение"""
    print("=" * 60)
    print("            LuTools Professional v4.0")
    print("     Enhanced Remote PC Management System")
    print("     Powered by aiogram 2.25.1")
    print("=" * 60)
    print()
    
    if Config.BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        print("❌ ОШИБКА: Токен бота не установлен!")
        print("Пожалуйста, установите токен в файле LuTools.py")
        print("Найдите строку: BOT_TOKEN = 'YOUR_BOT_TOKEN_HERE'")
        print("и замените на ваш токен от @BotFather")
        input("\nНажмите Enter для выхода...")
        return
    
    print("🔧 Инициализация системы...")
    print(f"👤 Администратор: ID {Config.ADMIN_ID}")
    print(f"💻 ОС: {platform.platform()}")
    print(f"🐍 Python: {platform.python_version()}")
    
    print("\n🔍 Проверка зависимостей...")
    
    try:
        import aiogram
        print("✅ aiogram установлен")
    except ImportError:
        print("❌ aiogram не установлен!")
        print("Установите: pip install aiogram==2.25.1")
        input("\nНажмите Enter для выхода...")
        return
    
    try:
        import psutil
        print("✅ psutil установлен")
    except ImportError:
        print("❌ psutil не установлен!")
        print("Установите: pip install psutil")
        input("\nНажмите Enter для выхода...")
        return
    
    print("\n📦 Рекомендуемые библиотеки для скриншотов:")
    print("   Для Windows:")
    print("   • pyautogui: pip install pyautogui")
    print("   • mss: pip install mss")
    print("   Для Linux:")
    print("   • scrot: sudo apt-get install scrot")
    print("   • gnome-screenshot: sudo apt-get install gnome-screenshot")
    
    print("\n🚀 Запуск всех модулей...")
    print("=" * 60)
    print()
    print("📊 Активные модули:")
    print("  • 🤖 Telegram Bot Interface (aiogram)")
    print("  • 👁 Enhanced Activity Monitoring System")
    print("  • 🔄 Smart Process Manager")
    print("  • 📸 Screenshot Capture (системные методы)")
    print("  • 📊 System Statistics")
    print("  • 📁 File Upload Manager")
    print("  • 🔔 Desktop Notifications")
    print()
    print("📝 Логи сохраняются в LuTools.log")
    print()
    print("🛑 Для остановки:")
    print("   1. Отправьте /stop в Telegram")
    print("   2. Подтвердите остановку")
    print()
    print("📱 Управление через Telegram:")
    print("   1. Отправьте /start вашему боту")
    print("   2. Используйте кнопки меню для управления")
    print()
    print("=" * 60)
    
    try:
        bot = LuToolsBot()
        bot.run()
    except KeyboardInterrupt:
        print("\n🛑 Остановка по запросу пользователя...")
        logger.info("Bot остановлен пользователем (Ctrl+C)")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        logger.critical(f"Критическая ошибка: {e}")
    
    print("👋 LuTools завершил работу")

if __name__ == "__main__":
    main()