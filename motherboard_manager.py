import os
import sys
import json
import time
import subprocess
import threading
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
BRIDGE_EXE = BASE_DIR / "lib" / "HardwareBridge.exe"

class MotherboardManager:
    def __init__(self):
        self.process = None
        self.running = False
        self.cpu_temp = 0.0
        self.cpu_load = 0.0
        self.temp_is_estimated = False
        self.fans = []
        self.lock = threading.Lock()
        self.start_bridge()

    def start_bridge(self):
        if not BRIDGE_EXE.exists():
            return

        try:
            self.process = subprocess.Popen(
                [str(BRIDGE_EXE), "--daemon"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
            self.running = True
            self.thread = threading.Thread(target=self._reader_loop, daemon=True)
            self.thread.start()
        except Exception as e:
            print(f"[MotherboardManager] Erro ao iniciar HardwareBridge: {e}")

    def _reader_loop(self):
        while self.running and self.process and self.process.poll() is None:
            try:
                line = self.process.stdout.readline()
                if not line:
                    break
                line = line.strip()
                if line.startswith("{") and line.endswith("}"):
                    data = json.loads(line)
                    with self.lock:
                        raw_temp = data.get("cpu_temp", 0.0)
                        self.cpu_load = data.get("cpu_load", 0.0)
                        self.fans = data.get("fans", [])
                        if raw_temp > 0.0:
                            self.cpu_temp = raw_temp
                            self.temp_is_estimated = False
                        else:
                            # Estimativa térmica baseada na curva de carga do Ryzen 5 5500
                            # Idle (0-10%): 38-42°C | Médio (30-50%): 48-55°C | Carga alta (80-100%): 65-72°C
                            self.cpu_temp = round(38.0 + (self.cpu_load * 0.33), 1)
                            self.temp_is_estimated = True
            except Exception:
                pass

    def get_data(self):
        with self.lock:
            return {
                "cpu_temp": self.cpu_temp,
                "cpu_load": self.cpu_load,
                "fans": list(self.fans),
                "temp_is_estimated": self.temp_is_estimated
            }

    def set_fan_speed(self, fan_id, speed_percent):
        if not self.process or self.process.poll() is not None:
            return False
        try:
            cmd = f"SET {fan_id} {int(speed_percent)}\n"
            self.process.stdin.write(cmd)
            self.process.stdin.flush()
            return True
        except Exception as e:
            print(f"[MotherboardManager] Erro ao enviar comando: {e}")
            return False

    def reset_fan(self, fan_id):
        if not self.process or self.process.poll() is not None:
            return False
        try:
            cmd = f"RESET {fan_id}\n"
            self.process.stdin.write(cmd)
            self.process.stdin.flush()
            return True
        except Exception:
            return False

    def reset_all(self):
        if not self.process or self.process.poll() is not None:
            return
        try:
            self.process.stdin.write("RESET_ALL\n")
            self.process.stdin.flush()
        except Exception:
            pass

    def stop(self):
        self.running = False
        self.reset_all()
        if self.process:
            try:
                self.process.stdin.write("QUIT\n")
                self.process.stdin.flush()
                self.process.terminate()
            except Exception:
                pass
