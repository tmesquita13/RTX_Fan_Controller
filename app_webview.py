import os
import sys
import json
import time
import ctypes
import subprocess
import threading
from pathlib import Path

import psutil
import webview
from PIL import Image, ImageDraw

from gpu_manager import GPUManager
from motherboard_manager import MotherboardManager
from fan_curve import FanCurve
from windows_optimizer import WindowsOptimizer
from win11_debloater import Win11Debloater
from game_monitor import GameMonitor

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.json"
UI_INDEX_HTML = BASE_DIR / "ui" / "index.html"


def load_config():
    default_config = {
        "theme": "turing_classic",
        "gpu_profile": "balanced",
        "gpu_zero_rpm": 55,
        "gpu_hysteresis": 3,
        "gpu_manual_speed": 50,
        "cpu_profile": "bios",
        "cpu_manual_speed": 50,
        "cpu_target_temp": 55,
        "minimize_to_tray": True,
        "ui_zoom": 100,
        "gpu_curve_points": [
            [35, 0],
            [45, 30],
            [55, 45],
            [68, 65],
            [80, 85]
        ]
    }
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                default_config.update(data)
                if "selected_turing_theme" in data:
                    default_config["theme"] = data["selected_turing_theme"]
        except Exception as e:
            print(f"[Config] Erro ao ler config.json: {e}")
    return default_config


def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)
    except Exception as e:
        print(f"[Config] Erro ao salvar config.json: {e}")


def create_tray_image():
    """Gera um ícone de ventoinha gamer neon para a bandeja do sistema."""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((4, 4, 60, 60), outline=(0, 213, 255, 255), width=4)
    draw.polygon([(32, 32), (32, 10), (44, 18)], fill=(157, 0, 255, 255))
    draw.polygon([(32, 32), (54, 32), (46, 44)], fill=(0, 213, 255, 255))
    draw.polygon([(32, 32), (32, 54), (20, 46)], fill=(157, 0, 255, 255))
    draw.polygon([(32, 32), (10, 32), (18, 20)], fill=(0, 213, 255, 255))
    draw.ellipse((26, 26, 38, 38), fill=(255, 255, 255, 255))
    return img


class AppController:
    """Controlador principal do aplicativo, telemetria e controle de hardware."""
    def __init__(self):
        self.config = load_config()
        self.gpu_manager = GPUManager()
        self.mb_manager = MotherboardManager()
        self.game_monitor = GameMonitor(self.gpu_manager)
        self.window = None
        self.tray = None
        self.running = True
        self.is_fullscreen = False

        # Configuração da Curva de Fan GPU
        self.fan_curve = FanCurve(
            zero_rpm_temp=self.config.get("gpu_zero_rpm", 55),
            hysteresis=self.config.get("gpu_hysteresis", 3),
            points=self.config.get("gpu_curve_points")
        )

        # Monitoramento de Rede, Disco e CPU
        self.last_net_bytes = (0, 0)
        self.last_net_time = time.time()
        self.last_disk_io = (0, 0)
        self.boot_time = psutil.boot_time()
        self.max_cpu_temp = 40.0
        self.max_gpu_temp = 40
        self.drive_types = {}
        self._refresh_drive_types_async()
        try:
            psutil.cpu_percent(interval=None)
            net = psutil.net_io_counters()
            self.last_net_bytes = (net.bytes_recv, net.bytes_sent)
            d_io = psutil.disk_io_counters()
            if d_io:
                self.last_disk_io = (d_io.read_bytes, d_io.write_bytes)
        except Exception:
            pass

        # Armazenamento em cache da última telemetria
        self.telemetry_lock = threading.Lock()
        self.latest_telemetry = {
            "cpu_load": 0,
            "cpu_temp": 40.0,
            "cpu_max_temp": 40.0,
            "cpu_clock": "3.6G",
            "cpu_cores": [0, 0, 0, 0, 0, 0],
            "cpu_power_est": 25.0,
            "gpu_util": 0,
            "gpu_temp": 40,
            "gpu_max_temp": 40,
            "gpu_vram": "0 M",
            "gpu_vram_pct": 0,
            "gpu_vram_used_mb": 0,
            "gpu_vram_total_mb": 8151,
            "gpu_clock": 0,
            "gpu_clock_mem": 7000,
            "gpu_power": 0.0,
            "gpu_power_limit": 180.0,
            "gpu_power_pct": 0,
            "gpu_pcie": "Gen 3 x8",
            "gpu_fan": 0,
            "gpu_fan_rpm": 0,
            "cpu_fan_rpm": 1200,
            "sys_fan_rpm": 1050,
            "ram_pct": 50,
            "ram_used_gb": "8.0",
            "ram_total_gb": "24.0",
            "ram_avail_gb": "16.0",
            "ram_gb": "8.0 / 24 GB",
            "swap_used_gb": "0.1",
            "swap_total_gb": "1.5",
            "swap_pct": 5,
            "disk_pct": 10,
            "disk_used_gb": "56",
            "disk_total_gb": "465",
            "disks": [],
            "disk_read_str": "0.0 M/s",
            "disk_write_str": "0.0 M/s",
            "net_down": "↓ 0.0 K",
            "net_up": "↑ 0.0 K",
            "net_down_total_gb": "0.0",
            "net_up_total_gb": "0.0",
            "uptime_str": "0h 0m",
            "procs_count": 150,
            "date_str": time.strftime("%Y/%m/%d"),
            "time_str": time.strftime("%H:%M:%S"),
            "is_admin": self.gpu_manager.admin,
            "curve_points": self.fan_curve.points,
            "game_stats": {
                "is_running": False,
                "game_name": "",
                "game_exe": "",
                "game_theme": "default",
                "fps": 0,
                "frametime_ms": 0.0,
                "fps_1pct_low": 0,
                "session_duration": "00:00:00",
                "frametime_history": []
            }
        }

    def get_initial_config(self):
        return {
            "theme": self.config.get("theme", "turing_classic"),
            "gpu_profile": self.config.get("gpu_profile", "balanced"),
            "gpu_zero_rpm": self.config.get("gpu_zero_rpm", 55),
            "gpu_hysteresis": self.config.get("gpu_hysteresis", 3),
            "gpu_manual_speed": self.config.get("gpu_manual_speed", 50),
            "cpu_profile": self.config.get("cpu_profile", "bios"),
            "cpu_manual_speed": self.config.get("cpu_manual_speed", 50),
            "cpu_target_temp": self.config.get("cpu_target_temp", 55),
            "is_fullscreen": self.is_fullscreen,
            "is_admin": self.gpu_manager.admin,
            "curve_points": self.fan_curve.points,
            "card_opacity": self.config.get("card_opacity", 0.46),
            "card_blur": self.config.get("card_blur", 8),
            "bg_brightness": self.config.get("bg_brightness", 100),
            "custom_accent": self.config.get("custom_accent", ""),
            "scanlines": self.config.get("scanlines", True),
            "animated_bg": self.config.get("animated_bg", True),
            "particles_speed": self.config.get("particles_speed", "normal")
        }

    def request_admin(self):
        """Reinicia o aplicativo solicitando elevação de privilégios UAC."""
        try:
            import ctypes, subprocess
            if ctypes.windll.shell32.IsUserAnAdmin():
                return True
            app_py = BASE_DIR / "app_webview.py"
            cmd = f'Start-Process python -ArgumentList \'"{app_py}"\' -Verb RunAs'
            subprocess.Popen(["powershell", "-Command", cmd], creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            threading.Timer(0.8, self.close_app).start()
            return True
        except Exception as e:
            print(f"[Admin] Erro ao elevar privilégios: {e}")
            return False

    def get_telemetry_data(self):
        with self.telemetry_lock:
            return dict(self.latest_telemetry)

    def _refresh_drive_types_async(self):
        """Atualiza em segundo plano o mapeamento de tipos de mídia física (SSD vs HDD)."""
        threading.Thread(target=self._update_drive_types, daemon=True).start()

    def _update_drive_types(self):
        try:
            cmd_disks = "Get-PhysicalDisk | Select-Object DeviceId, MediaType | ConvertTo-Json"
            cmd_parts = "Get-Partition | Where-Object DriveLetter | Select-Object DiskNumber, DriveLetter | ConvertTo-Json"
            creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            
            p1 = subprocess.run(
                ["powershell", "-NoProfile", "-Command", cmd_disks],
                capture_output=True, text=True, timeout=6, creationflags=creation_flags
            )
            p2 = subprocess.run(
                ["powershell", "-NoProfile", "-Command", cmd_parts],
                capture_output=True, text=True, timeout=6, creationflags=creation_flags
            )
            disks = json.loads(p1.stdout) if p1.stdout.strip() else []
            parts = json.loads(p2.stdout) if p2.stdout.strip() else []
            if isinstance(disks, dict):
                disks = [disks]
            if isinstance(parts, dict):
                parts = [parts]

            d_map = {str(d.get("DeviceId", "")): str(d.get("MediaType", "SSD")) for d in disks}
            mapping = {}
            for pt in parts:
                dl = str(pt.get("DriveLetter", "")).upper().strip()
                dnum = str(pt.get("DiskNumber", ""))
                if dl and dl != "NONE":
                    mapping[dl] = d_map.get(dnum, "SSD")
            if mapping:
                self.drive_types.update(mapping)
        except Exception as e:
            print(f"[Storage] Erro ao identificar tipos de disco: {e}")

    def get_disks_info(self):
        """Retorna telemetria detalhada de todos os discos (SSDs, HDDs, pendrives) do sistema."""
        results = []
        try:
            partitions = psutil.disk_partitions(all=False)
        except Exception:
            partitions = []

        for p in partitions:
            mount = p.mountpoint
            if not mount or not os.path.exists(mount):
                continue
            if "cdrom" in p.opts.lower():
                continue

            try:
                usage = psutil.disk_usage(mount)
                letter = mount.rstrip("\\").replace(":", "").upper()
                lbl = ""
                try:
                    vol_name = ctypes.create_unicode_buffer(261)
                    fs_name = ctypes.create_unicode_buffer(261)
                    ctypes.windll.kernel32.GetVolumeInformationW(mount, vol_name, 261, None, None, None, fs_name, 261)
                    lbl = vol_name.value
                except Exception:
                    pass

                mtype = self.drive_types.get(letter, "SSD" if letter == "C" else "HDD")
                used_gb = usage.used / 1024**3
                total_gb = usage.total / 1024**3
                free_gb = usage.free / 1024**3

                results.append({
                    "letter": letter + ":",
                    "label": lbl,
                    "type": mtype,
                    "percent": round(usage.percent),
                    "used_gb": f"{used_gb:.0f}" if used_gb >= 10 else f"{used_gb:.1f}",
                    "total_gb": f"{total_gb:.0f}",
                    "free_gb": f"{free_gb:.0f}" if free_gb >= 10 else f"{free_gb:.1f}",
                })
            except Exception:
                continue

        results.sort(key=lambda d: (0 if d["letter"].startswith("C") else 1, d["letter"]))
        return results

    def toggle_fullscreen(self):
        if not self.window:
            return False
        self.is_fullscreen = not self.is_fullscreen
        self.window.toggle_fullscreen()
        return self.is_fullscreen

    def minimize_to_tray(self):
        if self.window:
            self.window.hide()
        return True

    def close_app(self):
        self.running = False
        try:
            self.gpu_manager.reset_to_auto()
            self.mb_manager.reset_all()
        except Exception:
            pass
        if self.tray:
            try:
                self.tray.stop()
            except Exception:
                pass
        if self.window:
            try:
                self.window.destroy()
            except Exception:
                pass
        os._exit(0)

    def set_theme(self, theme_key):
        self.config["theme"] = theme_key
        save_config(self.config)
        return True

    def set_zoom(self, zoom_percent):
        try:
            val = max(50, min(200, int(zoom_percent)))
            self.config["ui_zoom"] = val
            save_config(self.config)
            return {"success": True, "zoom": val}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def choose_custom_wallpaper(self):
        try:
            if self.window:
                files = self.window.create_file_dialog(
                    webview.OPEN_DIALOG,
                    allow_multiple=False,
                    file_types=("Imagens (*.jpg;*.jpeg;*.png;*.webp;*.bmp)", "Todos os Arquivos (*.*)")
                )
                if files and len(files) > 0:
                    chosen_path = files[0]
                    dest_file = BASE_DIR / "ui" / "images" / "custom_bg.jpg"
                    import shutil
                    shutil.copy2(chosen_path, dest_file)
                    self.config["custom_wallpaper"] = str(chosen_path)
                    self.config["theme"] = "custom"
                    save_config(self.config)
                    return {"success": True, "path": "images/custom_bg.jpg?t=" + str(int(time.time()))}
        except Exception as e:
            return {"success": False, "error": str(e)}
        return {"success": False, "error": "Seleção cancelada"}

    def save_theme_customizations(self, settings):
        try:
            if isinstance(settings, dict):
                for k, v in settings.items():
                    self.config[k] = v
                save_config(self.config)
                return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
        return {"success": False}

    def calculate_gpu_fan_speed(self, temp):
        profile = self.config.get("gpu_profile", "balanced")
        if profile == "bios":
            return 0
        elif profile == "turbo":
            return 100
        elif profile == "manual":
            return int(self.config.get("gpu_manual_speed", 55))
        elif profile == "quiet":
            # Silencioso / Eco: Zero-RPM até 60°C, acima disso rotação suave
            z_temp = self.config.get("gpu_zero_rpm", 60)
            if temp < z_temp:
                return 0
            elif temp < 70:
                return 35
            elif temp < 80:
                return 50
            else:
                return 75
        elif profile == "performance":
            # Gamer / Performance: rotação ativa sem parar para manter GPU fria
            if temp < 50:
                return 50
            elif temp < 65:
                return 65
            elif temp < 75:
                return 85
            else:
                return 100
        else: # balanced
            # Equilibrado: Zero-RPM até 50°C
            z_temp = self.config.get("gpu_zero_rpm", 50)
            if temp < z_temp:
                return 0
            elif temp < 60:
                return 45
            elif temp < 70:
                return 60
            elif temp < 80:
                return 80
            else:
                return 95

    def set_gpu_profile(self, profile):
        self.config["gpu_profile"] = profile
        if profile == "quiet":
            self.config["gpu_zero_rpm"] = 60
        elif profile == "balanced":
            self.config["gpu_zero_rpm"] = 50
        elif profile == "performance":
            self.config["gpu_zero_rpm"] = 40
        elif profile == "turbo":
            pass
        elif profile == "bios":
            self.gpu_manager.reset_to_auto()

        save_config(self.config)

        # Aplica a rotação correspondente imediatamente na GPU
        gpu_telemetry = self.gpu_manager.get_telemetry()
        current_temp = gpu_telemetry.get("temp", 45)
        target_speed = self.calculate_gpu_fan_speed(current_temp)

        if profile == "bios":
            success, msg = self.gpu_manager.reset_to_auto()
            self._last_applied_fan_spd = "bios"
        else:
            success, msg = self.gpu_manager.set_fan_speed(target_speed)
            self._last_applied_fan_spd = target_speed

        return {
            "success": success,
            "message": msg,
            "profile": profile,
            "target_speed": target_speed
        }

    def set_gpu_zero_rpm(self, temp):
        temp = int(temp)
        self.config["gpu_zero_rpm"] = temp
        save_config(self.config)
        return True

    def set_gpu_hysteresis(self, hyst):
        hyst = int(hyst)
        self.config["gpu_hysteresis"] = hyst
        save_config(self.config)
        return True

    def set_gpu_manual_speed(self, speed):
        speed = int(speed)
        self.config["gpu_manual_speed"] = speed
        self.config["gpu_profile"] = "manual"
        save_config(self.config)
        success, msg = self.gpu_manager.set_fan_speed(speed)
        self._last_applied_fan_spd = speed
        return {
            "success": success,
            "message": msg,
            "speed": speed
        }

    def set_cpu_profile(self, profile):
        self.config["cpu_profile"] = profile
        save_config(self.config)
        if profile == "bios":
            self.mb_manager.reset_all()
        elif profile == "manual":
            speed = self.config.get("cpu_manual_speed", 50)
            for fan in self.mb_manager.fans:
                self.mb_manager.set_fan_speed(fan["id"], speed)
        return True

    def set_cpu_manual_speed(self, speed):
        speed = int(speed)
        self.config["cpu_manual_speed"] = speed
        save_config(self.config)
        if self.config.get("cpu_profile") == "manual":
            for fan in self.mb_manager.fans:
                self.mb_manager.set_fan_speed(fan["id"], speed)
        return True

    def set_cpu_target_temp(self, temp):
        self.config["cpu_target_temp"] = int(temp)
        save_config(self.config)
        return True

    def reset_all_fans(self):
        self.gpu_manager.reset_to_auto()
        self.mb_manager.reset_all()
        return True

    # ================= OTIMIZAÇÕES DO WINDOWS & SWAP =================
    def get_swap_info(self):
        return WindowsOptimizer.get_swap_info()

    def set_swap_size(self, initial_mb, max_mb):
        return WindowsOptimizer.set_swap_size(int(initial_mb), int(max_mb))

    def reset_swap_auto(self):
        return WindowsOptimizer.reset_swap_auto()

    def open_virtual_memory_dialog(self):
        return WindowsOptimizer.open_virtual_memory_dialog()

    def get_optimizations_status(self):
        return WindowsOptimizer.get_optimizations_status()

    def enable_game_mode(self):
        return WindowsOptimizer.enable_game_mode()

    def disable_game_dvr(self):
        return WindowsOptimizer.disable_game_dvr()

    def optimize_network_latency(self):
        return WindowsOptimizer.optimize_network_latency()

    def set_high_performance_power(self):
        return WindowsOptimizer.set_high_performance_power()

    def purge_ram_cache(self):
        return WindowsOptimizer.purge_ram_cache()

    def apply_all_gamer_optimizations(self):
        return WindowsOptimizer.apply_all_gamer_optimizations()

    # ================= WIN11DEBLOAT (RAPHIRE) =================
    def get_debloat_status(self):
        return Win11Debloater.get_debloat_status()

    def disable_debloat_telemetry(self):
        return Win11Debloater.disable_telemetry()

    def disable_debloat_bing(self):
        return Win11Debloater.disable_bing_search()

    def disable_debloat_copilot(self):
        return Win11Debloater.disable_copilot()

    def disable_debloat_recall(self):
        return Win11Debloater.disable_ai_recall()

    def disable_debloat_suggestions(self):
        return Win11Debloater.disable_suggestions()

    def disable_debloat_widgets(self):
        return Win11Debloater.disable_widgets()

    def create_debloat_restore_point(self):
        return Win11Debloater.create_restore_point()

    def remove_debloat_apps(self):
        return Win11Debloater.remove_bloatware_apps()

    def get_debloat_apps_catalog(self):
        return Win11Debloater.get_apps_catalog()

    def remove_custom_debloat_apps(self, app_id_list):
        return Win11Debloater.remove_custom_apps(app_id_list)

    def get_debloat_ui_tweaks(self):
        return Win11Debloater.get_ui_tweaks_status()

    def apply_debloat_ui_tweaks(self, tweaks):
        return Win11Debloater.apply_ui_tweaks(tweaks)

    def launch_official_win11debloat_gui(self):
        return Win11Debloater.launch_official_gui()

    def apply_full_win11_debloat(self):
        return Win11Debloater.apply_full_win11_debloat()

    def restart_explorer(self):
        return Win11Debloater.restart_explorer()

    def launch_official_win11debloat_cli(self):
        return Win11Debloater.apply_full_win11_debloat()

    def launch_official_win11debloat_silent(self):
        return Win11Debloater.apply_full_win11_debloat()

    def start_telemetry_loop(self):
        thread = threading.Thread(target=self._telemetry_worker, daemon=True)
        thread.start()

    def _telemetry_worker(self):
        while self.running:
            try:
                # 1. GPU (RTX 5060 Ti)
                gpu_data = self.gpu_manager.get_telemetry()
                gpu_temp = gpu_data.get("temp", 0)
                self.max_gpu_temp = max(self.max_gpu_temp, gpu_temp)
                gpu_util = gpu_data.get("util_gpu", 0)
                gpu_vram_used = gpu_data.get("mem_used", 0)
                gpu_vram_total = max(1, gpu_data.get("mem_total", 8192))
                gpu_vram_pct = int(min(100, (gpu_vram_used / gpu_vram_total) * 100))
                gpu_clock = gpu_data.get("clock", 0)
                gpu_clock_mem = gpu_data.get("clock_mem", 7000)
                gpu_power = gpu_data.get("power", 0.0)
                gpu_power_limit = gpu_data.get("power_limit", 180.0)
                gpu_power_pct = int(min(100, (gpu_power / max(1, gpu_power_limit)) * 100))
                gpu_pcie = gpu_data.get("pcie", "Gen 3 x8")

                gpu_prof = self.config.get("gpu_profile", "balanced")
                if gpu_prof == "bios":
                    if getattr(self, "_last_applied_fan_spd", None) != "bios":
                        self.gpu_manager.reset_to_auto()
                        self._last_applied_fan_spd = "bios"
                    gpu_fan_speed = gpu_data.get("fan_speed", 0)
                else:
                    target_spd = self.calculate_gpu_fan_speed(gpu_temp)
                    if getattr(self, "_last_applied_fan_spd", None) != target_spd:
                        self.gpu_manager.set_fan_speed(target_spd)
                        self._last_applied_fan_spd = target_spd
                    gpu_fan_speed = gpu_data.get("fan_speed", 0) or target_spd

                # 2. CPU (Ryzen 5 5500 + ASRock B450M)
                mb_data = self.mb_manager.get_data()
                cpu_temp = mb_data.get("cpu_temp", 0.0)
                cpu_load = mb_data.get("cpu_load", 0.0)
                per_cores = []
                try:
                    per_cores = [int(x) for x in psutil.cpu_percent(percpu=True)[:6]]
                except Exception:
                    per_cores = [int(cpu_load)] * 6

                if cpu_load <= 0:
                    try:
                        cpu_load = psutil.cpu_percent(interval=None)
                    except Exception:
                        cpu_load = 0.0

                if cpu_temp <= 0:
                    cpu_temp = round(38.0 + (cpu_load * 0.33), 1)

                self.max_cpu_temp = max(self.max_cpu_temp, cpu_temp)
                cpu_power_est = round(18.0 + (cpu_load / 100.0) * 47.0, 1)

                cpu_clock = "3.6G"
                try:
                    freq = psutil.cpu_freq()
                    if freq and freq.current:
                        cpu_clock = f"{freq.current / 1000.0:.1f}G"
                except Exception:
                    pass

                cpu_prof = self.config.get("cpu_profile", "bios")
                if cpu_prof == "curve":
                    target_temp = self.config.get("cpu_target_temp", 55)
                    if cpu_temp > target_temp:
                        spd = min(100, int(40 + (cpu_temp - target_temp) * 3))
                    else:
                        spd = 35
                    for fan in mb_data.get("fans", []):
                        self.mb_manager.set_fan_speed(fan["id"], spd)

                # Rotações físicas (RPM) dos coolers da CPU, Gabinete e GPU
                fans_list = mb_data.get("fans", [])
                cpu_fan_rpm = 0
                sys_fan_rpm = 0

                for f in fans_list:
                    name_l = f.get("name", "").lower()
                    rpm = int(f.get("rpm", 0))
                    if "cpu" in name_l:
                        cpu_fan_rpm = rpm
                    elif "fan" in name_l or "chassis" in name_l or "sys" in name_l:
                        if rpm > 0 and sys_fan_rpm == 0:
                            sys_fan_rpm = rpm

                if cpu_fan_rpm <= 0 and len(fans_list) > 0:
                    cpu_fan_rpm = int(fans_list[0].get("rpm", 0))

                # Estimativa baseada no perfil térmico do Ryzen 5 5500 se o tacômetro não estiver exposto
                if cpu_fan_rpm <= 0:
                    cpu_fan_rpm = int(980 + min(1300, max(0, (cpu_temp - 35) * 32)))

                if sys_fan_rpm <= 0:
                    sys_fan_rpm = int(850 + min(650, max(0, (cpu_temp - 40) * 18)))

                # GPU Fan RPM exato
                actual_gpu_fan_rpm = gpu_data.get("fan_rpm", 0)
                if gpu_fan_speed <= 0:
                    actual_gpu_fan_rpm = 0
                elif actual_gpu_fan_rpm <= 0:
                    actual_gpu_fan_rpm = int(gpu_fan_speed * 25.5)

                # 3. RAM & Swap
                ram_pct = 0
                ram_str = "0 / 0 GB"
                used_gb_str = "0.0"
                total_gb_str = "0.0"
                avail_gb_str = "0.0"
                swap_used_str = "0.0"
                swap_total_str = "0.0"
                swap_pct = 0
                try:
                    vmem = psutil.virtual_memory()
                    ram_pct = round(vmem.percent)
                    used_gb = vmem.used / (1024 ** 3)
                    total_gb = vmem.total / (1024 ** 3)
                    avail_gb = vmem.available / (1024 ** 3)
                    ram_str = f"{used_gb:.1f} / {round(total_gb)} GB"
                    used_gb_str = f"{used_gb:.1f}"
                    total_gb_str = f"{total_gb:.1f}"
                    avail_gb_str = f"{avail_gb:.1f}"

                    swap = psutil.swap_memory()
                    swap_used_str = f"{swap.used / 1024**3:.1f}"
                    swap_total_str = f"{swap.total / 1024**3:.1f}"
                    swap_pct = round(swap.percent)
                except Exception:
                    pass

                # 4. Todos os Discos (SSDs / HDDs) & I/O
                disks_data = self.get_disks_info()
                disk_pct = disks_data[0]["percent"] if disks_data else 0
                disk_used_str = disks_data[0]["used_gb"] if disks_data else "0"
                disk_total_str = disks_data[0]["total_gb"] if disks_data else "0"
                disk_read_str = "0.0 M/s"
                disk_write_str = "0.0 M/s"
                now = time.time()
                dt = max(0.5, now - self.last_net_time)

                try:
                    d_io = psutil.disk_io_counters()
                    if d_io and self.last_disk_io[0] > 0:
                        dr = (d_io.read_bytes - self.last_disk_io[0]) / dt
                        dw = (d_io.write_bytes - self.last_disk_io[1]) / dt
                        disk_read_str = f"{dr / (1024*1024):.1f} M/s" if dr >= 1024*1024 else f"{dr/1024:.0f} K/s"
                        disk_write_str = f"{dw / (1024*1024):.1f} M/s" if dw >= 1024*1024 else f"{dw/1024:.0f} K/s"
                    if d_io:
                        self.last_disk_io = (d_io.read_bytes, d_io.write_bytes)
                except Exception:
                    pass

                # 5. Rede (Download / Upload)
                down_rate_str = "↓ 0.0 K"
                up_rate_str = "↑ 0.0 K"
                net_down_tot_gb = "0.0"
                net_up_tot_gb = "0.0"
                try:
                    net = psutil.net_io_counters()
                    d_down = (net.bytes_recv - self.last_net_bytes[0]) / dt
                    d_up = (net.bytes_sent - self.last_net_bytes[1]) / dt
                    self.last_net_bytes = (net.bytes_recv, net.bytes_sent)
                    self.last_net_time = now

                    net_down_tot_gb = f"{net.bytes_recv / 1024**3:.1f}"
                    net_up_tot_gb = f"{net.bytes_sent / 1024**3:.1f}"

                    if d_down >= 1024 * 1024:
                        down_rate_str = f"↓ {d_down / (1024 * 1024):.1f} M"
                    else:
                        down_rate_str = f"↓ {d_down / 1024:.0f} K"

                    if d_up >= 1024 * 1024:
                        up_rate_str = f"↑ {d_up / (1024 * 1024):.1f} M"
                    else:
                        up_rate_str = f"↑ {d_up / 1024:.0f} K"
                except Exception:
                    pass

                # 6. Uptime e Processos
                uptime_s = now - self.boot_time
                uptime_str = f"{int(uptime_s // 3600)}h {int((uptime_s % 3600) // 60)}m"
                procs_count = 150
                try:
                    procs_count = len(psutil.pids())
                except Exception:
                    pass

                # 7. Data e Hora
                cur_time = time.localtime()
                date_str = time.strftime("%Y/%m/%d", cur_time)
                time_str = time.strftime("%H:%M:%S", cur_time)

                # 8. Detecção Automática e Métricas de Jogo Ativo (FPS, Frametime, 1% Low)
                try:
                    self.game_monitor.scan_active_game()
                    game_stats = self.game_monitor.calculate_game_metrics(gpu_util, gpu_clock, gpu_temp)
                except Exception as eg:
                    game_stats = {
                        "is_running": False,
                        "game_name": "",
                        "game_exe": "",
                        "game_theme": "default",
                        "fps": 0,
                        "frametime_ms": 0.0,
                        "fps_1pct_low": 0,
                        "session_duration": "00:00:00",
                        "frametime_history": []
                    }

                with self.telemetry_lock:
                    self.latest_telemetry = {
                        "cpu_load": cpu_load,
                        "cpu_temp": cpu_temp,
                        "cpu_max_temp": self.max_cpu_temp,
                        "cpu_clock": cpu_clock,
                        "cpu_cores": per_cores,
                        "cpu_power_est": cpu_power_est,
                        "cpu_fan_rpm": cpu_fan_rpm,
                        "sys_fan_rpm": sys_fan_rpm,
                        "gpu_util": gpu_util,
                        "gpu_temp": gpu_temp,
                        "gpu_max_temp": self.max_gpu_temp,
                        "gpu_vram": f"{gpu_vram_used} M",
                        "gpu_vram_used_mb": gpu_vram_used,
                        "gpu_vram_total_mb": gpu_vram_total,
                        "gpu_vram_pct": gpu_vram_pct,
                        "gpu_clock": gpu_clock,
                        "gpu_clock_mem": gpu_clock_mem,
                        "gpu_power": gpu_power,
                        "gpu_power_limit": gpu_power_limit,
                        "gpu_power_pct": gpu_power_pct,
                        "gpu_pcie": gpu_pcie,
                        "gpu_fan": gpu_fan_speed,
                        "gpu_fan_rpm": actual_gpu_fan_rpm,
                        "gpu_profile": gpu_prof,
                        "ram_pct": ram_pct,
                        "ram_gb": ram_str,
                        "ram_used_gb": used_gb_str,
                        "ram_total_gb": total_gb_str,
                        "ram_avail_gb": avail_gb_str,
                        "swap_used_gb": swap_used_str,
                        "swap_total_gb": swap_total_str,
                        "swap_pct": swap_pct,
                        "disk_pct": disk_pct,
                        "disk_used_gb": disk_used_str,
                        "disk_total_gb": disk_total_str,
                        "disks": disks_data,
                        "disk_read_str": disk_read_str,
                        "disk_write_str": disk_write_str,
                        "net_down": down_rate_str,
                        "net_up": up_rate_str,
                        "net_down_total_gb": net_down_tot_gb,
                        "net_up_total_gb": net_up_tot_gb,
                        "uptime_str": uptime_str,
                        "procs_count": procs_count,
                        "date_str": date_str,
                        "time_str": time_str,
                        "is_admin": self.gpu_manager.admin,
                        "curve_points": self.fan_curve.points,
                        "game_stats": game_stats
                    }

            except Exception as e:
                print(f"[TelemetryLoop] Erro: {e}")

            time.sleep(1.0)


class JSApi:
    """Objeto limpo exposto ao JavaScript via window.pywebview.api."""
    def __init__(self, controller):
        self._controller = controller

    def get_initial_config(self):
        return self._controller.get_initial_config()

    def get_telemetry(self):
        return self._controller.get_telemetry_data()

    def request_admin(self):
        return self._controller.request_admin()

    def toggle_fullscreen(self):
        return self._controller.toggle_fullscreen()

    def minimize_to_tray(self):
        return self._controller.minimize_to_tray()

    def close_app(self):
        return self._controller.close_app()

    def set_theme(self, theme_key):
        return self._controller.set_theme(theme_key)

    def set_gpu_profile(self, profile):
        return self._controller.set_gpu_profile(profile)

    def set_gpu_zero_rpm(self, temp):
        return self._controller.set_gpu_zero_rpm(temp)

    def set_gpu_hysteresis(self, hyst):
        return self._controller.set_gpu_hysteresis(hyst)

    def set_gpu_manual_speed(self, speed):
        return self._controller.set_gpu_manual_speed(speed)

    def set_cpu_profile(self, profile):
        return self._controller.set_cpu_profile(profile)

    def set_cpu_manual_speed(self, speed):
        return self._controller.set_cpu_manual_speed(speed)

    def set_cpu_target_temp(self, temp):
        return self._controller.set_cpu_target_temp(temp)

    def reset_all_fans(self):
        return self._controller.reset_all_fans()

    # Otimizações Windows & Swap
    def get_swap_info(self):
        return self._controller.get_swap_info()

    def set_swap_size(self, initial_mb, max_mb):
        return self._controller.set_swap_size(initial_mb, max_mb)

    def reset_swap_auto(self):
        return self._controller.reset_swap_auto()

    def open_virtual_memory_dialog(self):
        return self._controller.open_virtual_memory_dialog()

    def get_optimizations_status(self):
        return self._controller.get_optimizations_status()

    def enable_game_mode(self):
        return self._controller.enable_game_mode()

    def disable_game_dvr(self):
        return self._controller.disable_game_dvr()

    def optimize_network_latency(self):
        return self._controller.optimize_network_latency()

    def set_high_performance_power(self):
        return self._controller.set_high_performance_power()

    def purge_ram_cache(self):
        return self._controller.purge_ram_cache()

    def apply_all_gamer_optimizations(self):
        return self._controller.apply_all_gamer_optimizations()

    # Escala e Zoom da Interface
    def set_zoom(self, zoom_percent):
        return self._controller.set_zoom(zoom_percent)

    # Suíte de Debloat Nativa e Offline
    def get_debloat_status(self):
        return self._controller.get_debloat_status()

    def disable_debloat_telemetry(self):
        return self._controller.disable_debloat_telemetry()

    def disable_debloat_bing(self):
        return self._controller.disable_debloat_bing()

    def disable_debloat_copilot(self):
        return self._controller.disable_debloat_copilot()

    def disable_debloat_recall(self):
        return self._controller.disable_debloat_recall()

    def disable_debloat_suggestions(self):
        return self._controller.disable_debloat_suggestions()

    def disable_debloat_widgets(self):
        return self._controller.disable_debloat_widgets()

    def create_debloat_restore_point(self):
        return self._controller.create_debloat_restore_point()

    def remove_debloat_apps(self):
        return self._controller.remove_debloat_apps()

    def get_debloat_apps_catalog(self):
        return self._controller.get_debloat_apps_catalog()

    def remove_custom_debloat_apps(self, app_id_list):
        return self._controller.remove_custom_debloat_apps(app_id_list)

    def get_debloat_ui_tweaks(self):
        return self._controller.get_debloat_ui_tweaks()

    def apply_debloat_ui_tweaks(self, tweaks):
        return self._controller.apply_debloat_ui_tweaks(tweaks)

    def launch_official_win11debloat_gui(self):
        return self._controller.launch_official_win11debloat_gui()

    def apply_full_win11_debloat(self):
        return self._controller.apply_full_win11_debloat()

    def restart_explorer(self):
        return self._controller.restart_explorer()

    def launch_official_win11debloat_cli(self):
        return self._controller.apply_full_win11_debloat()

    def launch_official_win11debloat_silent(self):
        return self._controller.apply_full_win11_debloat()


def setup_tray(controller):
    """Inicializa o ícone de notificação na bandeja do sistema (System Tray)."""
    try:
        import pystray
        image = create_tray_image()

        def on_open(icon=None, item=None):
            if controller.window:
                controller.window.show()
                controller.window.restore()

        def on_fullscreen(icon=None, item=None):
            controller.toggle_fullscreen()

        def on_reset(icon=None, item=None):
            controller.reset_all_fans()

        def on_exit(icon=None, item=None):
            controller.close_app()

        menu = pystray.Menu(
            pystray.MenuItem("⚡ Abrir Painel LCD", on_open, default=True),
            pystray.MenuItem("🔲 Alternar Tela Cheia (F11)", on_fullscreen),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("🚨 Restaurar Fans para BIOS", on_reset),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("✕ Sair e Fechar Completamente", on_exit)
        )

        tray = pystray.Icon("Aegis_Gaming_HUD", image, "Aegis Gaming HUD & Hardware Center", menu)
        tray.default_action = on_open
        controller.tray = tray
        tray.run()
    except Exception as e:
        print(f"[Tray] Erro ao iniciar bandeja: {e}")


def check_admin_elevation():
    """
    Verifica se o processo está em modo Administrador.
    Se iniciado sem privilégios (ex: ao clicar em 'Run' no VS Code),
    solicita automaticamente a elevação UAC do Windows e reabre o app como Administrador.
    """
    try:
        import ctypes
        if ctypes.windll.shell32.IsUserAnAdmin():
            return True
        if "--no-elevation" in sys.argv:
            return False

        print("[Admin] Permissões de Administrador necessárias. Solicitando UAC do Windows...")
        script_path = str(Path(__file__).resolve())
        args = [f'"{script_path}"'] + [f'"{a}"' for a in sys.argv[1:]]
        params = " ".join(args)
        # Usa pythonw para não exibir janela preta de console
        python_exe = sys.executable
        if python_exe.lower().endswith("python.exe"):
            pythonw_candidate = python_exe[:-4] + "w.exe"
            if os.path.exists(pythonw_candidate):
                python_exe = pythonw_candidate

        ret = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", python_exe, params, str(BASE_DIR), 1
        )
        if ret > 32:
            sys.exit(0)
    except Exception as e:
        print(f"[Admin] Aviso: Não foi possível elevar automaticamente: {e}")
    return False


def main():
    check_admin_elevation()
    controller = AppController()
    start_fullscreen = "--fullscreen" in sys.argv
    controller.is_fullscreen = start_fullscreen

    api = JSApi(controller)

    # Cria janela nativa PyWebView usando Microsoft Edge Chromium (WebView2)
    window = webview.create_window(
        title="Aegis Gaming HUD & Hardware Center",
        url=str(UI_INDEX_HTML),
        js_api=api,
        width=1040,
        height=660,
        min_size=(800, 480),
        fullscreen=start_fullscreen,
        background_color="#090D14"
    )
    controller.window = window

    controller.start_telemetry_loop()

    # Intercepta minimização e clique de fechar (X) da janela para enviar para a bandeja
    def on_minimized():
        window.hide()

    def on_closing():
        # Se fechar pelo X da janela do Windows, apenas oculta na bandeja em vez de matar o processo
        window.hide()
        return False  # Cancela o fechamento destrutivo do WinForms

    window.events.minimized += on_minimized
    window.events.closing += on_closing

    tray_thread = threading.Thread(target=setup_tray, args=(controller,), daemon=True)
    tray_thread.start()

    webview.start(debug=False)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        err_msg = traceback.format_exc()
        try:
            with open(BASE_DIR / "crash.log", "w", encoding="utf-8") as f:
                f.write(err_msg)
        except Exception:
            pass
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0,
                f"Erro ao iniciar o aplicativo:\n\n{e}\n\nDetalhes salvos em crash.log",
                "Aegis Gaming HUD - Erro",
                0x10
            )
        except Exception:
            pass
        raise
