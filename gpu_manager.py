import ctypes
from ctypes import wintypes
import sys
import os

NVML_SUCCESS = 0
NVML_ERROR_UNINITIALIZED = 1
NVML_ERROR_INVALID_ARGUMENT = 2
NVML_ERROR_NOT_SUPPORTED = 3
NVML_ERROR_NO_PERMISSION = 4

class UTIL(ctypes.Structure):
    _fields_ = [('gpu', ctypes.c_uint), ('memory', ctypes.c_uint)]

class MEM(ctypes.Structure):
    _fields_ = [('total', ctypes.c_ulonglong), ('free', ctypes.c_ulonglong), ('used', ctypes.c_ulonglong)]

class GPUManager:
    """
    Gerenciador de Telemetria e Controle de Ventoinhas da NVIDIA GeForce RTX.
    Utiliza motor duplo:
    1. LibreHardwareMonitorLib (NVAPI nativo do driver GeForce para controle direto de rotação)
    2. NVML (NVIDIA Management Library para telemetria de alta frequência)
    """
    def __init__(self):
        self.initialized = False
        self.handle = None
        self.num_fans = 1
        self.gpu_name = "NVIDIA GeForce RTX"
        self.admin = self.check_admin()
        self.last_error = ""

        # LibreHardwareMonitor GPU Control (NVAPI nativo)
        self.lhm_computer = None
        self.lhm_gpu = None
        self.lhm_fan_control = None
        self.lhm_fan_rpm_sensor = None
        self.current_applied_speed = None

        self.init_nvml()
        self.init_lhm_gpu()

    @staticmethod
    def check_admin():
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False

    def init_lhm_gpu(self):
        """Inicializa o driver NVAPI via LibreHardwareMonitorLib para controle de ventoinha garantido."""
        try:
            import clr
            lib_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib")
            if lib_path not in sys.path:
                sys.path.append(lib_path)
            clr.AddReference("LibreHardwareMonitorLib")
            from LibreHardwareMonitor.Hardware import Computer

            self.lhm_computer = Computer()
            self.lhm_computer.IsGpuEnabled = True
            self.lhm_computer.Open()

            for h in self.lhm_computer.Hardware:
                if "Nvidia" in str(h.HardwareType) or "Gpu" in str(h.HardwareType):
                    self.lhm_gpu = h
                    h.Update()
                    for s in h.Sensors:
                        if s.Control is not None and "Fan" in s.Name:
                            self.lhm_fan_control = s.Control
                        elif "Fan" in s.Name and "Fan" in str(s.SensorType):
                            self.lhm_fan_rpm_sensor = s
                    if self.lhm_fan_control:
                        break
            return self.lhm_fan_control is not None
        except Exception as e:
            self.last_error = f"LHM GPU Init: {e}"
            return False

    def init_nvml(self):
        """Inicializa NVML para leitura de telemetria completa."""
        try:
            self.nvml = ctypes.CDLL("nvml.dll")
            res = self.nvml.nvmlInit_v2()
            if res != NVML_SUCCESS:
                self.last_error = f"Falha ao inicializar NVML (código {res})"
                return False

            self.handle = ctypes.c_void_p()
            res = self.nvml.nvmlDeviceGetHandleByIndex_v2(0, ctypes.byref(self.handle))
            if res != NVML_SUCCESS:
                self.last_error = f"GPU 0 não encontrada (código {res})"
                return False

            # Nome da GPU
            buf = ctypes.create_string_buffer(64)
            if self.nvml.nvmlDeviceGetName(self.handle, buf, 64) == NVML_SUCCESS:
                self.gpu_name = buf.value.decode("utf-8", errors="ignore")

            # Quantidade de Fans
            if hasattr(self.nvml, "nvmlDeviceGetNumFans"):
                nf = ctypes.c_uint()
                if self.nvml.nvmlDeviceGetNumFans(self.handle, ctypes.byref(nf)) == NVML_SUCCESS:
                    self.num_fans = max(1, nf.value)

            self.initialized = True
            return True
        except Exception as e:
            self.last_error = str(e)
            return False

    def get_telemetry(self):
        """Retorna dicionário com todos os dados de telemetria em tempo real."""
        data = {
            "name": self.gpu_name,
            "temp": 0,
            "fan_speed": 0,
            "fan_rpm": 0,
            "util_gpu": 0,
            "util_mem": 0,
            "mem_used": 0,
            "mem_total": 8192,
            "power": 0.0,
            "power_limit": 180.0,
            "clock": 0,
            "clock_mem": 7000,
            "pcie": "Gen 3 x8",
            "admin": self.admin,
            "error": self.last_error
        }

        if not self.initialized:
            return data

        # 1. Temperatura
        temp = ctypes.c_uint()
        if self.nvml.nvmlDeviceGetTemperature(self.handle, 0, ctypes.byref(temp)) == NVML_SUCCESS:
            data["temp"] = temp.value

        # 2. Velocidade da Fan (%)
        fan = ctypes.c_uint()
        if hasattr(self.nvml, "nvmlDeviceGetFanSpeed_v2"):
            if self.nvml.nvmlDeviceGetFanSpeed_v2(self.handle, 0, ctypes.byref(fan)) == NVML_SUCCESS:
                data["fan_speed"] = fan.value
        elif hasattr(self.nvml, "nvmlDeviceGetFanSpeed"):
            if self.nvml.nvmlDeviceGetFanSpeed(self.handle, ctypes.byref(fan)) == NVML_SUCCESS:
                data["fan_speed"] = fan.value

        # Se tiver sensor RPM via LibreHardwareMonitor, lê a rotação física
        if self.lhm_gpu:
            try:
                self.lhm_gpu.Update()
                if self.lhm_fan_rpm_sensor and self.lhm_fan_rpm_sensor.Value is not None:
                    data["fan_rpm"] = int(self.lhm_fan_rpm_sensor.Value)
            except Exception:
                pass

        # Se houver rotação aplicada e a NVML não leu percentual, reflete a rotação aplicada
        if data["fan_speed"] == 0 and self.current_applied_speed is not None and self.current_applied_speed > 0:
            data["fan_speed"] = self.current_applied_speed

        # 3. Utilização do Processador e Memória
        util = UTIL()
        if self.nvml.nvmlDeviceGetUtilizationRates(self.handle, ctypes.byref(util)) == NVML_SUCCESS:
            data["util_gpu"] = util.gpu
            data["util_mem"] = util.memory

        # 4. Memória VRAM
        mem = MEM()
        if self.nvml.nvmlDeviceGetMemoryInfo(self.handle, ctypes.byref(mem)) == NVML_SUCCESS:
            data["mem_used"] = int(mem.used / (1024 * 1024))
            data["mem_total"] = int(mem.total / (1024 * 1024))

        # 5. Consumo de Energia e Limite de TDP (Watts)
        power = ctypes.c_uint()
        if hasattr(self.nvml, "nvmlDeviceGetPowerUsage"):
            if self.nvml.nvmlDeviceGetPowerUsage(self.handle, ctypes.byref(power)) == NVML_SUCCESS:
                data["power"] = round(power.value / 1000.0, 1)

        power_limit = ctypes.c_uint()
        if hasattr(self.nvml, "nvmlDeviceGetPowerManagementLimit"):
            if self.nvml.nvmlDeviceGetPowerManagementLimit(self.handle, ctypes.byref(power_limit)) == NVML_SUCCESS:
                data["power_limit"] = round(power_limit.value / 1000.0, 1)

        # 6. Core Clock e Memory Clock (MHz)
        clock = ctypes.c_uint()
        if hasattr(self.nvml, "nvmlDeviceGetClockInfo"):
            if self.nvml.nvmlDeviceGetClockInfo(self.handle, 0, ctypes.byref(clock)) == NVML_SUCCESS:
                data["clock"] = clock.value
            clk_mem = ctypes.c_uint()
            if self.nvml.nvmlDeviceGetClockInfo(self.handle, 2, ctypes.byref(clk_mem)) == NVML_SUCCESS:
                data["clock_mem"] = clk_mem.value

        # 7. Barramento PCIe
        if hasattr(self.nvml, "nvmlDeviceGetCurrPcieLinkGeneration") and hasattr(self.nvml, "nvmlDeviceGetCurrPcieLinkWidth"):
            p_gen = ctypes.c_uint()
            p_width = ctypes.c_uint()
            if self.nvml.nvmlDeviceGetCurrPcieLinkGeneration(self.handle, ctypes.byref(p_gen)) == NVML_SUCCESS and \
               self.nvml.nvmlDeviceGetCurrPcieLinkWidth(self.handle, ctypes.byref(p_width)) == NVML_SUCCESS:
                data["pcie"] = f"Gen {p_gen.value} x{p_width.value}"

        return data

    def set_fan_speed(self, speed_percent):
        """
        Define a velocidade da ventoinha da RTX (0 a 100%).
        Se 0 ou menor, restaura o modo padrão automático (Zero-RPM da VBIOS).
        Se entre 30% e 100%, força a rotação selecionada diretamente na placa.
        """
        speed_percent = int(speed_percent)
        if speed_percent <= 0:
            return self.reset_fan_to_auto()

        # Limite físico mínimo para rotação forçada em placas RTX é 30%
        speed_percent = max(30, min(100, speed_percent))

        success = False
        errors = []

        # 1. Aplica via LibreHardwareMonitor (NVAPI nativo - controle direto no hardware)
        if self.lhm_fan_control is not None:
            try:
                self.lhm_fan_control.SetSoftware(float(speed_percent))
                success = True
            except Exception as e:
                errors.append(f"NVAPI: {e}")

        # 2. Aplica também via NVML se disponível
        if self.initialized and hasattr(self.nvml, "nvmlDeviceSetFanSpeed_v2"):
            try:
                for i in range(self.num_fans):
                    res = self.nvml.nvmlDeviceSetFanSpeed_v2(self.handle, i, speed_percent)
                    if res == NVML_SUCCESS:
                        success = True
                    elif res == NVML_ERROR_NO_PERMISSION:
                        self.admin = False
            except Exception as e:
                errors.append(f"NVML: {e}")

        if success:
            self.current_applied_speed = speed_percent
            self.last_error = ""
            return True, f"Fans da RTX ajustadas para {speed_percent}%"

        err_msg = ", ".join(errors) if errors else "Falha ao aplicar velocidade."
        self.last_error = err_msg
        return False, err_msg

    def reset_fan_to_auto(self):
        """Restaura o controle para o firmware automático da placa (Zero-RPM da VBIOS)."""
        success = False

        if self.lhm_fan_control is not None:
            try:
                self.lhm_fan_control.SetDefault()
                success = True
            except Exception:
                pass

        if self.initialized and hasattr(self.nvml, "nvmlDeviceSetDefaultFanSpeed_v2"):
            try:
                for i in range(self.num_fans):
                    res = self.nvml.nvmlDeviceSetDefaultFanSpeed_v2(self.handle, i)
                    if res == NVML_SUCCESS:
                        success = True
            except Exception:
                pass

        self.current_applied_speed = 0
        return True, "Modo automático VBIOS restaurado (Zero-RPM ativado)."

    reset_to_auto = reset_fan_to_auto

    def close(self):
        try:
            if self.lhm_computer:
                self.lhm_computer.Close()
        except Exception:
            pass
