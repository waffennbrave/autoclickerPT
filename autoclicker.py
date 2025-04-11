import tkinter as tk
from tkinter import ttk
from pynput.mouse import Listener as MouseListener
from pynput import keyboard
import threading
import time
import pyautogui
import win32gui
import win32con
import win32api
import win32process
import psutil  # pip install psutil

# Глобальные переменные
playing = False
start_stop_hotkey = None  # Одна горячая клавиша для старта/стопа
clicks = []             # Список записанных кликов (глобальные координаты)
record_listener = None  # Слушатель для записи кликов

# Функция для преобразования двух чисел в LPARAM для сообщений Windows
def MAKELONG(x, y):
    return (y << 16) | (x & 0xFFFF)

# Функция для записи кликов, при этом клики внутри окна автокликера не записываются
def record_clicks():
    global clicks, record_listener
    clicks.clear()  # Очищаем список кликов перед началом записи
    status_label.config(text="Запись...")
    
    # Получаем координаты окна автокликера (чтобы отсеять собственные клики)
    app_x = root.winfo_rootx()
    app_y = root.winfo_rooty()
    app_w = root.winfo_width()
    app_h = root.winfo_height()

    def on_click(x, y, button, pressed):
        # Игнорируем клики, произошедшие в пределах окна приложения
        if app_x <= x <= app_x + app_w and app_y <= y <= app_y + app_h:
            return
        if pressed:
            clicks.append((x, y))
    
    record_listener = MouseListener(on_click=on_click)
    record_listener.start()  # Запуск слушателя в отдельном потоке
    record_listener.join()   # Блокируем поток до остановки слушателя
    status_label.config(text=f"Записано: {len(clicks)} кликов")

def stop_recording():
    global record_listener
    if record_listener is not None:
        record_listener.stop()
    status_label.config(text=f"Записано: {len(clicks)} кликов")

# Функция для получения дескриптора окна процесса ProTanki.exe
def get_protanki_hwnd():
    result = []
    def enum_window(hwnd, lParam):
        if win32gui.IsWindowVisible(hwnd):
            try:
                pid = win32process.GetWindowThreadProcessId(hwnd)[1]
                proc = psutil.Process(pid)
                if proc.name().lower() == "protanki.exe":
                    lParam.append(hwnd)
            except Exception:
                pass
        return True
    win32gui.EnumWindows(enum_window, result)
    return result[0] if result else None

# Функция для воспроизведения кликов в окне ProTanki.exe
def play_clicks(speed_ms, target_hwnd):
    global playing
    playing = True
    status_label.config(text="Воспроизведение...")
    delay = speed_ms / 1000  # задержка в секундах

    while playing:
        for x, y in clicks:
            if not playing:
                break
            if target_hwnd:
                # Преобразуем глобальные координаты в координаты клиентской области целевого окна
                pt = (x, y)
                client_pt = win32gui.ScreenToClient(target_hwnd, pt)
                cx, cy = client_pt
                # Отправляем сообщения клика в окно ProTanki.exe через WinAPI
                win32gui.PostMessage(target_hwnd, win32con.WM_LBUTTONDOWN, 1, MAKELONG(cx, cy))
                win32gui.PostMessage(target_hwnd, win32con.WM_LBUTTONUP, 0, MAKELONG(cx, cy))
            else:
                # Если окно не найдено, делаем обычный клик (для отладки)
                pyautogui.click(x, y)
            time.sleep(delay)
    status_label.config(text="Остановлено")

def start_stop_playing():
    global playing
    try:
        speed_ms = int(speed_entry.get())  # скорость в миллисекундах
    except ValueError:
        status_label.config(text="Ошибка: неверная скорость")
        return
    if speed_ms <= 0:
        status_label.config(text="Ошибка: скорость должна быть больше 0!")
        return

    if playing:
        # Останавливаем автокликер
        playing = False
        status_label.config(text="Остановлено")
    else:
        target_hwnd = get_protanki_hwnd()
        if target_hwnd is None:
            status_label.config(text="Окно ProTanki.exe не найдено!")
            return
        else:
            status_label.config(text="Окно ProTanki.exe найдено!")
        
        threading.Thread(target=play_clicks, args=(speed_ms, target_hwnd), daemon=True).start()
        playing = True
        status_label.config(text="Воспроизведение...")

def listen_hotkeys():
    def on_press(key):
        global start_stop_hotkey
        try:
            k = key.char.lower()
        except:
            k = str(key).replace('Key.', '')
        if k == start_stop_hotkey:
            start_stop_playing()  # Переключаем состояние между стартом и стопом

    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()

def set_hotkey(event):
    global start_stop_hotkey
    key = event.char.lower()
    start_stop_hotkey = key
    hotkey_status_label.config(text=f"Горячая клавиша: {start_stop_hotkey}")

def clear_clicks():
    global clicks
    clicks.clear()
    status_label.config(text="Клики очищены")

# --------------------------- Интерфейс ---------------------------
root = tk.Tk()
root.title("Автокликер для ProTanki")
root.configure(bg="gray20")
root.geometry("320x500")
root.resizable(False, False)

style = ttk.Style()
style.theme_use("clam")
style.configure("TButton", background="gray30", foreground="white", font=("Arial", 10), padding=5)
style.configure("TLabel", background="gray20", foreground="white", font=("Arial", 10))
style.configure("TEntry", padding=5)

# Фрейм для управления записью кликов
frame_record = ttk.Frame(root)
frame_record.pack(pady=5)
ttk.Button(frame_record, text="Записать клики", command=lambda: threading.Thread(target=record_clicks, daemon=True).start()).pack(side=tk.LEFT, padx=5)
ttk.Button(frame_record, text="Остановить запись", command=stop_recording).pack(side=tk.LEFT, padx=5)

# Поле для ввода скорости (в миллисекундах)
ttk.Label(root, text="Скорость (мс):").pack(pady=5)
speed_entry = ttk.Entry(root)
speed_entry.insert(0, "10")  # Значение по умолчанию
speed_entry.pack()

# Фрейм для управления кликами
frame_play = ttk.Frame(root)
frame_play.pack(pady=10)
ttk.Button(frame_play, text="Начать/Остановить", command=start_stop_playing).pack(side=tk.LEFT, padx=5)

status_label = ttk.Label(root, text="Готов к работе")
status_label.pack(pady=10)

# Фрейм для горячих клавиш
frame_hotkeys = ttk.Frame(root)
frame_hotkeys.pack(pady=10)
ttk.Label(frame_hotkeys, text="Горячая клавиша:").grid(row=0, column=0, padx=5, pady=5)
hotkey_entry = ttk.Entry(frame_hotkeys)
hotkey_entry.grid(row=0, column=1, padx=5, pady=5)
hotkey_entry.bind("<KeyPress>", set_hotkey)

hotkey_status_label = ttk.Label(root, text="Горячая клавиша: не установлена")
hotkey_status_label.pack(pady=5)

ttk.Button(root, text="Очистить клики", command=clear_clicks).pack(pady=10)
ttk.Label(root, text="by brave", style="TLabel").pack(side="bottom", pady=5)

# Запуск прослушки горячих клавиш в фоновом потоке
threading.Thread(target=listen_hotkeys, daemon=True).start()

root.mainloop()
