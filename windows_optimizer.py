import os
import sys
import ctypes
import subprocess
import winreg
import psutil

class WindowsOptimizer:
    """
    Módulo profissional de otimização do Windows para Jogos e Hardware.
    Permite gerenciar Memória Virtual (Swap/Pagefile), Plano de Energia,
    Modo de Jogo, Otimização de Rede e Limpeza de Cache de Memória.
    """

    @staticmethod
    def is_admin():
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False

    @staticmethod
    def run_elevated_ps(cmd_string):
        """
        Executa comando PowerShell como Administrador se necessário.
        """
        if WindowsOptimizer.is_admin():
            cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd_string]
            res = subprocess.run(cmd, capture_output=True, text=True)
            return res.returncode == 0, res.stdout + res.stderr
        else:
            # Invoca via UAC do Windows (ShellExecute runas)
            ps_args = f"-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command \"{cmd_string}\""
            ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", "powershell.exe", ps_args, None, 1)
            # Retorno > 32 indica sucesso na invocação do UAC
            return ret > 32, "Comando enviado para elevação UAC"

    # ================= 1. MEMÓRIA VIRTUAL (SWAP / PAGEFILE) =================
    @staticmethod
    def get_swap_info():
        """
        Retorna informações detalhadas sobre a memória virtual (Swap/Pagefile).
        """
        swap = psutil.swap_memory()
        ram = psutil.virtual_memory()

        # Lê configuração atual no Registro
        paging_files = []
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management") as k:
                val, _ = winreg.QueryValueEx(k, "PagingFiles")
                if isinstance(val, list):
                    paging_files = val
                elif isinstance(val, str):
                    paging_files = [val]
        except Exception:
            paging_files = ["?:\\pagefile.sys"]

        is_auto = any("?:" in pf for pf in paging_files) or len(paging_files) == 0

        total_gb = round(swap.total / (1024 ** 3), 1)
        used_gb = round(swap.used / (1024 ** 3), 1)
        free_gb = round(swap.free / (1024 ** 3), 1)
        ram_total_gb = round(ram.total / (1024 ** 3), 1)

        return {
            "total_gb": total_gb,
            "used_gb": used_gb,
            "free_gb": free_gb,
            "pct": swap.percent,
            "ram_total_gb": ram_total_gb,
            "is_auto": is_auto,
            "paging_files_raw": paging_files,
            "status_str": "Automático do Windows" if is_auto else "Personalizado (Tamanho Fixo Otimizado)"
        }

    @staticmethod
    def set_swap_size(initial_mb=8192, max_mb=16384):
        """
        Configura o arquivo de paginação (pagefile.sys) na unidade C: com tamanho inicial e máximo.
        Recomendado para 24 GB de RAM: 8192 MB (8 GB) inicial e 16384 MB (16 GB) máximo.
        """
        ps_cmd = (
            f"$cs = Get-CimInstance Win32_ComputerSystem; "
            f"Set-CimInstance -InputObject $cs -Property @{{AutomaticManagedPagefile = $false}}; "
            f"Set-ItemProperty -Path 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Memory Management' "
            f"-Name 'PagingFiles' -Value @('C:\\pagefile.sys {initial_mb} {max_mb}');"
        )
        success, out = WindowsOptimizer.run_elevated_ps(ps_cmd)
        return {
            "success": success,
            "message": f"Memória Swap configurada para {initial_mb//1024} GB inicial / {max_mb//1024} GB máximo na unidade C:." if success else f"Falha ao configurar swap: {out}"
        }

    @staticmethod
    def reset_swap_auto():
        """
        Restaura o gerenciamento automático da memória virtual pelo Windows.
        """
        ps_cmd = (
            "$cs = Get-CimInstance Win32_ComputerSystem; "
            "Set-CimInstance -InputObject $cs -Property @{AutomaticManagedPagefile = $true}; "
            "Set-ItemProperty -Path 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Memory Management' "
            "-Name 'PagingFiles' -Value @('?:\\pagefile.sys');"
        )
        success, out = WindowsOptimizer.run_elevated_ps(ps_cmd)
        return {
            "success": success,
            "message": "Gerenciamento de Memória Virtual restaurado para o modo Automático do Windows." if success else f"Falha: {out}"
        }

    @staticmethod
    def open_virtual_memory_dialog():
        """
        Abre o painel gráfico oficial do Windows de propriedades avançadas do sistema.
        """
        try:
            subprocess.Popen(["SystemPropertiesAdvanced.exe"])
            return {"success": True, "message": "Painel de propriedades do Windows aberto."}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # ================= 2. OTIMIZAÇÕES GERAIS PARA JOGOS =================
    @staticmethod
    def get_optimizations_status():
        """
        Obtém o status de todas as otimizações do Windows.
        """
        status = {}

        # 1. Modo de Jogo (Game Mode)
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\GameBar") as k:
                status["game_mode"] = (winreg.QueryValueEx(k, "AllowAutoGameMode")[0] == 1)
        except Exception:
            status["game_mode"] = False

        # 2. Xbox GameDVR (Gravação em segundo plano - false é bom para FPS)
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"System\GameConfigStore") as k:
                dvr_val = winreg.QueryValueEx(k, "GameDVR_Enabled")[0]
                status["game_dvr_disabled"] = (dvr_val == 0)
        except Exception:
            status["game_dvr_disabled"] = False

        # 3. Otimização de Latência de Rede (Network Throttling Index & System Responsiveness)
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Windows NT\CurrentVersion\Multimedia\SystemProfile") as k:
                pass
        except Exception:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile") as k:
                    throttling = winreg.QueryValueEx(k, "NetworkThrottlingIndex")[0]
                    resp = winreg.QueryValueEx(k, "SystemResponsiveness")[0]
                    status["network_optimized"] = (throttling == 0xFFFFFFFF or throttling == -1) and (resp == 0)
            except Exception:
                status["network_optimized"] = False

        # 4. Plano de Energia
        try:
            res = subprocess.run(["powercfg", "/getactivescheme"], capture_output=True, text=True)
            active_out = res.stdout.lower()
            status["high_performance"] = ("alto desempenho" in active_out or "desempenho m" in active_out or "ultimate" in active_out)
            status["active_power_plan"] = res.stdout.strip()
        except Exception:
            status["high_performance"] = False
            status["active_power_plan"] = "Desconhecido"

        return status

    @staticmethod
    def enable_game_mode():
        """
        Ativa o Game Mode do Windows no Registro.
        """
        try:
            key_path = r"Software\Microsoft\GameBar"
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as k:
                winreg.SetValueEx(k, "AllowAutoGameMode", 0, winreg.REG_DWORD, 1)
            return {"success": True, "message": "Modo de Jogo do Windows ativado com sucesso!"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @staticmethod
    def disable_game_dvr():
        """
        Desativa a gravação passiva do Xbox GameDVR para eliminar micro-stutters e liberar FPS.
        """
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"System\GameConfigStore") as k:
                winreg.SetValueEx(k, "GameDVR_Enabled", 0, winreg.REG_DWORD, 0)
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\GameDVR") as k:
                winreg.SetValueEx(k, "AppCaptureEnabled", 0, winreg.REG_DWORD, 0)
            return {"success": True, "message": "Gravação de fundo do Xbox GameDVR desativada!"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @staticmethod
    def optimize_network_latency():
        """
        Remove o throttling de rede e dedica 100% da prioridade da CPU para jogos.
        """
        ps_cmd = (
            "Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Multimedia\\SystemProfile' "
            "-Name 'NetworkThrottlingIndex' -Value 0xFFFFFFFF; "
            "Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Multimedia\\SystemProfile' "
            "-Name 'SystemResponsiveness' -Value 0;"
        )
        success, out = WindowsOptimizer.run_elevated_ps(ps_cmd)
        return {
            "success": success,
            "message": "Latência de rede otimizada (Network Throttling desativado e prioridade 100% para jogos)!" if success else f"Falha: {out}"
        }

    @staticmethod
    def set_high_performance_power():
        """
        Ativa o plano de energia de Desempenho Máximo (Ultimate Performance) ou Alto Desempenho.
        """
        # Tenta duplicar Ultimate Performance scheme se não existir
        subprocess.run(["powercfg", "-duplicatescheme", "e9a42b02-d5df-448d-aa00-03f14749eb61"], capture_output=True)
        # Ativa Alto Desempenho ou Ultimate
        res = subprocess.run(["powercfg", "/setactive", "e9a42b02-d5df-448d-aa00-03f14749eb61"], capture_output=True)
        if res.returncode != 0:
            # Fallback para Alto Desempenho clássico
            subprocess.run(["powercfg", "/setactive", "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"], capture_output=True)
        return {"success": True, "message": "Plano de Energia de Alto Desempenho ativado!"}

    @staticmethod
    def purge_ram_cache():
        """
        Esvazia o cache em espera (Working Sets) para liberar RAM física instantaneamente.
        """
        freed_count = 0
        try:
            # Invoca EmptyWorkingSet para processos acessíveis
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    handle = ctypes.windll.kernel32.OpenProcess(0x1F0FFF, False, proc.info['pid'])
                    if handle:
                        ctypes.windll.psapi.EmptyWorkingSet(handle)
                        ctypes.windll.kernel32.CloseHandle(handle)
                        freed_count += 1
                except Exception:
                    pass
            return {"success": True, "message": f"Cache de memória liberado com sucesso ({freed_count} processos otimizados)!"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @staticmethod
    def apply_all_gamer_optimizations():
        """
        Aplica todas as otimizações recomendadas de uma só vez (1-clique).
        """
        results = []
        r1 = WindowsOptimizer.enable_game_mode()
        results.append("Modo de Jogo: " + ("OK" if r1["success"] else "Falha"))

        r2 = WindowsOptimizer.disable_game_dvr()
        results.append("GameDVR Desativado: " + ("OK" if r2["success"] else "Falha"))

        r3 = WindowsOptimizer.optimize_network_latency()
        results.append("Rede Otimizada: " + ("OK" if r3["success"] else "Falha"))

        r4 = WindowsOptimizer.set_high_performance_power()
        results.append("Energia Alto Desempenho: " + ("OK" if r4["success"] else "Falha"))

        r5 = WindowsOptimizer.set_swap_size(8192, 16384)
        results.append("Memória Swap (8-16 GB): " + ("OK" if r5["success"] else "Falha"))

        WindowsOptimizer.purge_ram_cache()

        return {
            "success": True,
            "message": "Pacote Gamer Completo Aplicado:\n" + "\n".join(results)
        }

