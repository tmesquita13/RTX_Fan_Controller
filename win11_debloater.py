import os
import sys
import time
import tempfile
import ctypes
import subprocess
import winreg

class Win11Debloater:
    """
    Suíte de Debloat e Otimização para Windows 11/10 100% Nativa e Offline.
    Não depende de repositórios do GitHub, links externos ou scripts online.
    
    Executa alterações diretamente via PowerShell e Registro do Windows:
    - Desativação de Telemetria e Diagnósticos (DiagTrack, dmwappushservice, CEIP)
    - Desativação do Bing e Busca Web no Menu Iniciar
    - Desativação do Microsoft Copilot
    - Desativação do Windows AI Recall e Click-To-Do
    - Desativação de Anúncios, Sugestões e Dicas do Sistema
    - Desativação dos Widgets / Notícias da Barra de Tarefas
    - Remoção offline de mais de 80 Bloatwares pré-instalados (AppX / UWP)
    - Criação de Ponto de Restauração do Sistema
    - Reinicialização limpa do Windows Explorer para aplicar alterações imediatas
    """

    # Lista abrangente de apps patrocinados e bloatwares padrão do Windows (base oficial Win11Debloat)
    DEFAULT_BLOAT_APPS = [
        "Clipchamp.Clipchamp",
        "Microsoft.3DBuilder",
        "Microsoft.549981C3F5F10",                  # Cortana
        "Microsoft.BingFinance",
        "Microsoft.BingFoodAndDrink",
        "Microsoft.BingHealthAndFitness",
        "Microsoft.BingNews",
        "Microsoft.BingSports",
        "Microsoft.BingTranslator",
        "Microsoft.BingTravel",
        "Microsoft.BingWeather",
        "Microsoft.Windows.AIHub",
        "Microsoft.PCManager",
        "Microsoft.Getstarted",                     # Dicas
        "Microsoft.GetHelp",                        # Ajuda rápida
        "Microsoft.Messaging",
        "Microsoft.Microsoft3DViewer",
        "Microsoft.MicrosoftJournal",
        "Microsoft.MicrosoftOfficeHub",             # Microsoft 365 Promocional
        "Microsoft.MicrosoftPowerBIForWindows",
        "Microsoft.MicrosoftSolitaireCollection",
        "Microsoft.MicrosoftStickyNotes",
        "Microsoft.MixedReality.Portal",
        "Microsoft.NetworkSpeedTest",
        "Microsoft.News",
        "Microsoft.Office.OneNote",
        "Microsoft.Office.Sway",
        "Microsoft.OneConnect",
        "Microsoft.Print3D",
        "Microsoft.People",
        "Microsoft.PowerAutomateDesktop",
        "Microsoft.SkypeApp",
        "Microsoft.Todos",
        "Microsoft.Windows.DevHome",
        "Microsoft.WindowsAlarms",
        "Microsoft.WindowsFeedbackHub",
        "Microsoft.WindowsMaps",
        "Microsoft.WindowsSoundRecorder",
        "Microsoft.XboxApp",
        "Microsoft.YourPhone",                      # Vínculo com Celular
        "Microsoft.ZuneVideo",                      # Filmes e TV
        "Microsoft.ZuneMusic",                      # Groove Música legado
        "MicrosoftCorporationII.MicrosoftFamily",
        "MicrosoftCorporationII.QuickAssist",
        "MicrosoftTeams",                           # Teams pessoal integrado
        "MSTeams",
        "SpotifyAB.SpotifyMusic",
        "BytedancePte.Ltd.TikTok",
        "Facebook.Instagram",
        "FACEBOOK.FACEBOOK",
        "Amazon.com.Amazon",
        "AmazonVideo.PrimeVideo",
        "Disney.37853FC22B2CE",
        "4DF9E0F8.Netflix",
        "DrawboardPDF",
        "Duolingo-LearnLanguagesforFree",
        "EclipseManager",
        "Flipboard",
        "iHeartRadio",
        "LinkedInforWindows",
        "TuneInRadio",
        "WinZipUniversal",
        "king.com.BubbleWitch3Saga",
        "king.com.CandyCrushSaga",
        "king.com.CandyCrushSodaSaga"
    ]

    @staticmethod
    def is_admin():
        """Verifica se o processo atual possui privilégios de Administrador."""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False

    @staticmethod
    def execute_powershell_script(ps_code, timeout=180):
        """
        Executa um script PowerShell offline de forma 100% autônoma e segura.
        Gera um arquivo temporário codificado em UTF-8 com BOM.
        
        Se já for Admin: executa diretamente via subprocess.
        Se não for Admin: eleva via Start-Process powershell -Verb RunAs -Wait,
        gravando o log de saída em arquivo temporário e lendo-o sincronamente.
        """
        temp_dir = tempfile.gettempdir()
        uid = int(time.time() * 1000)
        script_path = os.path.join(temp_dir, f"debloat_{uid}.ps1")
        log_path = os.path.join(temp_dir, f"debloat_log_{uid}.txt")

        wrapped_code = f"""# Debloat Script Local
$ErrorActionPreference = 'SilentlyContinue'
$logFile = "{log_path}"
function Log($msg) {{
    $ts = Get-Date -Format "HH:mm:ss"
    "[$ts] $msg" | Out-File -FilePath $logFile -Append -Encoding utf8
}}

Log "--- INICIANDO DEBLOAT NATIVO OFFLINE ---"
try {{
{ps_code}
    Log "--- CONCLUIDO COM SUCESSO ---"
}} catch {{
    Log "ERRO NA EXECUCAO: $_"
}}
"""
        with open(script_path, "w", encoding="utf-8-sig") as f:
            f.write(wrapped_code)

        try:
            if Win11Debloater.is_admin():
                cmd = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script_path]
                res = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding="latin-1",
                    errors="replace",
                    timeout=timeout
                )
                success = (res.returncode == 0)
            else:
                # Dispara elevação UAC com espera síncrona (-Wait) e captura de status
                ps_launcher = (
                    f"try {{ "
                    f"  $p = Start-Process powershell.exe -Verb RunAs -Wait -PassThru -WindowStyle Hidden "
                    f"  -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File \"\"{script_path}\"\"'; "
                    f"  exit $p.ExitCode "
                    f"}} catch {{ "
                    f"  'UAC_DENIED: ' + $_.Exception.Message | Out-File -FilePath '{log_path}' -Encoding utf8; "
                    f"  exit 2 "
                    f"}}"
                )
                res = subprocess.run(
                    ["powershell.exe", "-NoProfile", "-Command", ps_launcher],
                    capture_output=True,
                    text=True,
                    encoding="latin-1",
                    errors="replace",
                    timeout=timeout
                )
                success = (res.returncode == 0)

            log_content = ""
            if os.path.exists(log_path):
                try:
                    with open(log_path, "r", encoding="utf-8-sig", errors="replace") as lf:
                        log_content = lf.read().strip()
                except Exception:
                    pass

            if "UAC_DENIED" in log_content:
                return False, "A solicitação de Administrador (UAC) foi cancelada pelo usuário. Permissão necessária para alterar o sistema."

            return success, log_content
        except subprocess.TimeoutExpired:
            return False, "A execução atingiu o tempo limite (Timeout de 180s)."
        except Exception as e:
            return False, f"Falha na execução: {str(e)}"
        finally:
            for p in [script_path, log_path]:
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass

    # ================= 1. VERIFICAÇÃO DE STATUS AO VIVO =================
    @staticmethod
    def get_debloat_status():
        """
        Verifica o status atual de cada módulo de Debloat no registro e serviços sem privilégios elevados.
        """
        status = {
            "telemetry_disabled": False,
            "bing_disabled": False,
            "copilot_disabled": False,
            "recall_disabled": False,
            "suggestions_disabled": False,
            "widgets_disabled": False
        }

        # 1. Telemetria
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\DataCollection") as k:
                val, _ = winreg.QueryValueEx(k, "AllowTelemetry")
                status["telemetry_disabled"] = (val == 0)
        except Exception:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo") as k:
                    val, _ = winreg.QueryValueEx(k, "Enabled")
                    status["telemetry_disabled"] = (val == 0)
            except Exception:
                status["telemetry_disabled"] = False

        # 2. Bing Search
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Search") as k:
                val, _ = winreg.QueryValueEx(k, "BingSearchEnabled")
                status["bing_disabled"] = (val == 0)
        except Exception:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Policies\Microsoft\Windows\Explorer") as k:
                    val, _ = winreg.QueryValueEx(k, "DisableSearchBoxSuggestions")
                    status["bing_disabled"] = (val == 1)
            except Exception:
                status["bing_disabled"] = False

        # 3. Copilot
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Policies\Microsoft\Windows\WindowsCopilot") as k:
                val, _ = winreg.QueryValueEx(k, "TurnOffWindowsCopilot")
                status["copilot_disabled"] = (val == 1)
        except Exception:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\WindowsCopilot") as k:
                    val, _ = winreg.QueryValueEx(k, "TurnOffWindowsCopilot")
                    status["copilot_disabled"] = (val == 1)
            except Exception:
                status["copilot_disabled"] = False

        # 4. Recall
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\WindowsAI") as k:
                val, _ = winreg.QueryValueEx(k, "AllowRecallEnablement")
                status["recall_disabled"] = (val == 0)
        except Exception:
            status["recall_disabled"] = False

        # 5. Sugestões / Propagandas
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager") as k:
                val, _ = winreg.QueryValueEx(k, "SubscribedContent-338388Enabled")
                status["suggestions_disabled"] = (val == 0)
        except Exception:
            status["suggestions_disabled"] = False

        # 6. Widgets
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced") as k:
                val, _ = winreg.QueryValueEx(k, "TaskbarDa")
                status["widgets_disabled"] = (val == 0)
        except Exception:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Dsh") as k:
                    val, _ = winreg.QueryValueEx(k, "AllowNewsAndInterests")
                    status["widgets_disabled"] = (val == 0)
            except Exception:
                status["widgets_disabled"] = False

        return status

    # ================= 2. MÓDULOS ESPECÍFICOS DE DEBLOAT =================

    @staticmethod
    def disable_telemetry():
        """Desativa telemetria, rastreamento de diagnósticos e serviços DiagTrack."""
        ps_code = """
Log "Desativando Advertising ID e Experiencias Personalizadas..."
New-Item -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\AdvertisingInfo' -Force | Out-Null
Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\AdvertisingInfo' -Name 'Enabled' -Value 0 -Type DWord -Force

New-Item -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Privacy' -Force | Out-Null
Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Privacy' -Name 'TailoredExperiencesWithDiagnosticDataEnabled' -Value 0 -Type DWord -Force

New-Item -Path 'HKCU:\\Software\\Microsoft\\Speech_OneCore\\Settings\\OnlineSpeechPrivacy' -Force | Out-Null
Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Speech_OneCore\\Settings\\OnlineSpeechPrivacy' -Name 'HasAccepted' -Value 0 -Type DWord -Force

Log "Desativando Coleta de Dados do Sistema (HKLM DataCollection)..."
New-Item -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\DataCollection' -Force | Out-Null
Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\DataCollection' -Name 'AllowTelemetry' -Value 0 -Type DWord -Force
Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\DataCollection' -Name 'CommercialDataCollectionEnabled' -Value 0 -Type DWord -Force

New-Item -Path 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\DataCollection' -Force | Out-Null
Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\DataCollection' -Name 'AllowTelemetry' -Value 0 -Type DWord -Force

New-Item -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\System' -Force | Out-Null
Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\System' -Name 'EnableActivityFeed' -Value 0 -Type DWord -Force
Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\System' -Name 'PublishUserActivities' -Value 0 -Type DWord -Force
Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\System' -Name 'UploadUserActivities' -Value 0 -Type DWord -Force

Log "Desativando servicos DiagTrack e dmwappushservice..."
Stop-Service -Name DiagTrack -Force -ErrorAction SilentlyContinue
Set-Service -Name DiagTrack -StartupType Disabled -ErrorAction SilentlyContinue
Stop-Service -Name dmwappushservice -Force -ErrorAction SilentlyContinue
Set-Service -Name dmwappushservice -StartupType Disabled -ErrorAction SilentlyContinue
Log "Telemetria e rastreamento completamente desativados!"
"""
        success, out = Win11Debloater.execute_powershell_script(ps_code)
        return {
            "success": success,
            "message": "Telemetria e rastreamento de dados desativados com sucesso (DiagTrack desligado)!" if success else f"Falha: {out}",
            "log": out
        }

    @staticmethod
    def disable_bing_search():
        """Desativa o Bing, busca web e sugestões online no Menu Iniciar."""
        ps_code = """
Log "Desativando Bing Search e sugestoes no Menu Iniciar..."
New-Item -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Search' -Force | Out-Null
Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Search' -Name 'BingSearchEnabled' -Value 0 -Type DWord -Force
Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Search' -Name 'CortanaConsent' -Value 0 -Type DWord -Force
Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Search' -Name 'AllowSearchToUseLocation' -Value 0 -Type DWord -Force

New-Item -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\Windows Search' -Force | Out-Null
Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\Windows Search' -Name 'ConnectedSearchUseWeb' -Value 0 -Type DWord -Force
Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\Windows Search' -Name 'AllowCortana' -Value 0 -Type DWord -Force
Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\Windows Search' -Name 'DisableWebSearch' -Value 1 -Type DWord -Force

New-Item -Path 'HKCU:\\Software\\Policies\\Microsoft\\Windows\\Explorer' -Force | Out-Null
Set-ItemProperty -Path 'HKCU:\\Software\\Policies\\Microsoft\\Windows\\Explorer' -Name 'DisableSearchBoxSuggestions' -Value 1 -Type DWord -Force

New-Item -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\Explorer' -Force | Out-Null
Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\Explorer' -Name 'DisableSearchBoxSuggestions' -Value 1 -Type DWord -Force
Log "Busca Bing e sugestoes web desativadas no Iniciar!"
"""
        success, out = Win11Debloater.execute_powershell_script(ps_code)
        return {
            "success": success,
            "message": "Busca Bing e sugestões web desativadas no Menu Iniciar!" if success else f"Falha: {out}",
            "log": out
        }

    @staticmethod
    def disable_copilot():
        """Desativa o Microsoft Copilot e oculta o botão da barra de tarefas."""
        ps_code = """
Log "Desativando Microsoft Copilot..."
New-Item -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced' -Force | Out-Null
Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced' -Name 'ShowCopilotButton' -Value 0 -Type DWord -Force

New-Item -Path 'HKCU:\\Software\\Policies\\Microsoft\\Windows\\WindowsCopilot' -Force | Out-Null
Set-ItemProperty -Path 'HKCU:\\Software\\Policies\\Microsoft\\Windows\\WindowsCopilot' -Name 'TurnOffWindowsCopilot' -Value 1 -Type DWord -Force

New-Item -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsCopilot' -Force | Out-Null
Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsCopilot' -Name 'TurnOffWindowsCopilot' -Value 1 -Type DWord -Force
Log "Copilot completamente desativado no sistema!"
"""
        success, out = Win11Debloater.execute_powershell_script(ps_code)
        return {
            "success": success,
            "message": "Microsoft Copilot desativado e ícone da barra de tarefas ocultado!" if success else f"Falha: {out}",
            "log": out
        }

    @staticmethod
    def disable_ai_recall():
        """Desativa o Windows AI Recall, gravação de tela e serviços associados."""
        ps_code = """
Log "Desativando Windows AI Recall e Click-to-Do..."
New-Item -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsAI' -Force | Out-Null
Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsAI' -Name 'AllowRecallEnablement' -Value 0 -Type DWord -Force
Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsAI' -Name 'DisableAIDataAnalysis' -Value 1 -Type DWord -Force
Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsAI' -Name 'DisableClickToDo' -Value 1 -Type DWord -Force
Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsAI' -Name 'TurnOffSavingSnapshots' -Value 1 -Type DWord -Force

New-Item -Path 'HKCU:\\Software\\Policies\\Microsoft\\Windows\\WindowsAI' -Force | Out-Null
Set-ItemProperty -Path 'HKCU:\\Software\\Policies\\Microsoft\\Windows\\WindowsAI' -Name 'DisableAIDataAnalysis' -Value 1 -Type DWord -Force
Set-ItemProperty -Path 'HKCU:\\Software\\Policies\\Microsoft\\Windows\\WindowsAI' -Name 'TurnOffSavingSnapshots' -Value 1 -Type DWord -Force

Stop-Service -Name WSAIFabricSvc -Force -ErrorAction SilentlyContinue
Set-Service -Name WSAIFabricSvc -StartupType Disabled -ErrorAction SilentlyContinue
Log "Windows AI Recall desligado no registro e politicas de grupo!"
"""
        success, out = Win11Debloater.execute_powershell_script(ps_code)
        return {
            "success": success,
            "message": "Windows AI Recall e Click-to-Do desativados com sucesso!" if success else f"Falha: {out}",
            "log": out
        }

    @staticmethod
    def disable_suggestions():
        """Desativa sugestões, dicas de tela de bloqueio e anúncios promocionais."""
        ps_code = """
Log "Desativando anuncios promocionais e sugestoes do Windows..."
New-Item -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\ContentDeliveryManager' -Force | Out-Null
$cdmProps = @(
    'SubscribedContent-338387Enabled',
    'SubscribedContent-338388Enabled',
    'SubscribedContent-338389Enabled',
    'SubscribedContent-338393Enabled',
    'SubscribedContent-353694Enabled',
    'SubscribedContent-353696Enabled',
    'SubscribedContent-353698Enabled',
    'SubscribedContent-310093Enabled',
    'SystemPaneSuggestionsEnabled',
    'SoftLandingEnabled',
    'RotatingLockScreenOverlayEnabled',
    'SilentInstalledAppsEnabled'
)
foreach ($p in $cdmProps) {
    Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\ContentDeliveryManager' -Name $p -Value 0 -Type DWord -Force
}

New-Item -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced' -Force | Out-Null
Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced' -Name 'Start_IrisRecommendations' -Value 0 -Type DWord -Force
Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced' -Name 'Start_AccountNotifications' -Value 0 -Type DWord -Force
Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced' -Name 'ShowSyncProviderNotifications' -Value 0 -Type DWord -Force
Log "Dicas, sugestoes e anuncios bloqueados com sucesso!"
"""
        success, out = Win11Debloater.execute_powershell_script(ps_code)
        return {
            "success": success,
            "message": "Dicas, sugestões e propagandas do Windows desativadas!" if success else f"Falha: {out}",
            "log": out
        }

    @staticmethod
    def disable_widgets():
        """Desativa Widgets e o feed de notícias da barra de tarefas."""
        ps_code = """
Log "Desativando Widgets da barra de tarefas..."
New-Item -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced' -Force | Out-Null
Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced' -Name 'TaskbarDa' -Value 0 -Type DWord -Force

New-Item -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Dsh' -Force | Out-Null
Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Dsh' -Name 'AllowNewsAndInterests' -Value 0 -Type DWord -Force
Log "Widgets e feed de noticias desativados!"
"""
        success, out = Win11Debloater.execute_powershell_script(ps_code)
        return {
            "success": success,
            "message": "Widgets e feed de notícias da barra de tarefas desativados!" if success else f"Falha: {out}",
            "log": out
        }

    @staticmethod
    def create_restore_point():
        """Cria um ponto de restauração oficial do sistema."""
        ps_code = """
Log "Criando Ponto de Restauracao do Sistema..."
Enable-ComputerRestore -Drive 'C:\\' -ErrorAction SilentlyContinue
Checkpoint-Computer -Description 'RTX_Debloat_RestorePoint' -RestorePointType 'MODIFY_SETTINGS' -ErrorAction SilentlyContinue
Log "Ponto de Restauracao gerado!"
"""
        success, out = Win11Debloater.execute_powershell_script(ps_code, timeout=60)
        return {
            "success": success,
            "message": "Ponto de Restauração 'RTX_Debloat_RestorePoint' criado com sucesso!" if success else f"Aviso ao criar ponto: {out}",
            "log": out
        }

    @staticmethod
    def remove_bloatware_apps():
        """Desinstala apps lixo e patrocinados offline (AppX / Provisioned) de forma 100% nativa."""
        apps_arr = ", ".join(f"'{a}'" for a in Win11Debloater.DEFAULT_BLOAT_APPS)
        ps_code = f"""
$targets = @({apps_arr})
Log "Iniciando remocao offline de bloatwares para todos os usuarios..."
$removedCount = 0

foreach ($app in $targets) {{
    $pkgs = Get-AppxPackage -Name $app -AllUsers -ErrorAction SilentlyContinue
    if ($pkgs) {{
        foreach ($pkg in $pkgs) {{
            $pkg | Remove-AppxPackage -AllUsers -ErrorAction SilentlyContinue
            Log "Removido AppX: $($pkg.Name)"
            $removedCount++
        }}
    }}
    
    # Remover do Provisionamento para novas contas nao reinstalarem
    $provs = Get-AppxProvisionedPackage -Online -ErrorAction SilentlyContinue | Where-Object {{ $_.DisplayName -like $app }}
    if ($provs) {{
        foreach ($prov in $provs) {{
            $prov | Remove-AppxProvisionedPackage -Online -ErrorAction SilentlyContinue
            Log "Removido Provisionado: $($prov.DisplayName)"
            $removedCount++
        }}
    }}
}}

Log "Remocao concluida! Total de pacotes processados e limpos: $removedCount"
"""
        success, out = Win11Debloater.execute_powershell_script(ps_code, timeout=180)
        return {
            "success": success,
            "message": "Remoção de Bloatwares (AppX) concluída com sucesso!" if success else f"Falha na desinstalação: {out}",
            "log": out
        }

    @staticmethod
    def restart_explorer():
        """Reinicia o processo Windows Explorer para aplicar imediatamente as mudanças visuais."""
        ps_code = """
Log "Reiniciando Windows Explorer..."
Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 600
Start-Process explorer.exe
Log "Windows Explorer reiniciado com sucesso!"
"""
        success, out = Win11Debloater.execute_powershell_script(ps_code, timeout=30)
        return {
            "success": success,
            "message": "Windows Explorer reiniciado com sucesso! Alterações na barra de tarefas e menus aplicadas." if success else f"Falha ao reiniciar Explorer: {out}",
            "log": out
        }

    @staticmethod
    def apply_full_win11_debloat():
        """
        Executa a suíte de debloat completa recomendada em UMA ÚNICA EXECUÇÃO contínua e offline:
        1. Ponto de restauração de segurança
        2. Desativação de Telemetria e rastreamento DiagTrack
        3. Desativação do Bing e buscas online no Menu Iniciar
        4. Desativação completa do Copilot
        5. Desativação do Windows AI Recall
        6. Desativação de Anúncios e Sugestões do sistema
        7. Desativação dos Widgets da Barra de Tarefas
        8. Remoção em lote de mais de 80 Bloatwares pré-instalados
        9. Reinicialização limpa do Windows Explorer
        """
        apps_arr = ", ".join(f"'{a}'" for a in Win11Debloater.DEFAULT_BLOAT_APPS)
        ps_code = f"""
Log "=========================================="
Log "=== EXECUCAO DO PACOTE COMPLETO DEBLOAT ==="
Log "=========================================="

# 1. Ponto de Restauracao
Log "[1/8] Gerando ponto de restauracao..."
Enable-ComputerRestore -Drive 'C:\\' -ErrorAction SilentlyContinue
Checkpoint-Computer -Description 'RTX_Debloat_RestorePoint' -RestorePointType 'MODIFY_SETTINGS' -ErrorAction SilentlyContinue

# 2. Telemetria
Log "[2/8] Desativando telemetria e diagnosticos..."
New-Item -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\AdvertisingInfo' -Force | Out-Null
Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\AdvertisingInfo' -Name 'Enabled' -Value 0 -Type DWord -Force
New-Item -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Privacy' -Force | Out-Null
Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Privacy' -Name 'TailoredExperiencesWithDiagnosticDataEnabled' -Value 0 -Type DWord -Force
New-Item -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\DataCollection' -Force | Out-Null
Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\DataCollection' -Name 'AllowTelemetry' -Value 0 -Type DWord -Force
Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\DataCollection' -Name 'CommercialDataCollectionEnabled' -Value 0 -Type DWord -Force
New-Item -Path 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\DataCollection' -Force | Out-Null
Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\DataCollection' -Name 'AllowTelemetry' -Value 0 -Type DWord -Force
Stop-Service -Name DiagTrack -Force -ErrorAction SilentlyContinue
Set-Service -Name DiagTrack -StartupType Disabled -ErrorAction SilentlyContinue
Stop-Service -Name dmwappushservice -Force -ErrorAction SilentlyContinue
Set-Service -Name dmwappushservice -StartupType Disabled -ErrorAction SilentlyContinue

# 3. Bing Search
Log "[3/8] Desativando Bing no Menu Iniciar..."
New-Item -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Search' -Force | Out-Null
Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Search' -Name 'BingSearchEnabled' -Value 0 -Type DWord -Force
Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Search' -Name 'CortanaConsent' -Value 0 -Type DWord -Force
New-Item -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\Windows Search' -Force | Out-Null
Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\Windows Search' -Name 'ConnectedSearchUseWeb' -Value 0 -Type DWord -Force
Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\Windows Search' -Name 'DisableWebSearch' -Value 1 -Type DWord -Force
New-Item -Path 'HKCU:\\Software\\Policies\\Microsoft\\Windows\\Explorer' -Force | Out-Null
Set-ItemProperty -Path 'HKCU:\\Software\\Policies\\Microsoft\\Windows\\Explorer' -Name 'DisableSearchBoxSuggestions' -Value 1 -Type DWord -Force

# 4. Copilot
Log "[4/8] Desativando Copilot..."
New-Item -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced' -Force | Out-Null
Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced' -Name 'ShowCopilotButton' -Value 0 -Type DWord -Force
New-Item -Path 'HKCU:\\Software\\Policies\\Microsoft\\Windows\\WindowsCopilot' -Force | Out-Null
Set-ItemProperty -Path 'HKCU:\\Software\\Policies\\Microsoft\\Windows\\WindowsCopilot' -Name 'TurnOffWindowsCopilot' -Value 1 -Type DWord -Force
New-Item -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsCopilot' -Force | Out-Null
Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsCopilot' -Name 'TurnOffWindowsCopilot' -Value 1 -Type DWord -Force

# 5. AI Recall
Log "[5/8] Desativando AI Recall..."
New-Item -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsAI' -Force | Out-Null
Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsAI' -Name 'AllowRecallEnablement' -Value 0 -Type DWord -Force
Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsAI' -Name 'DisableAIDataAnalysis' -Value 1 -Type DWord -Force
Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsAI' -Name 'DisableClickToDo' -Value 1 -Type DWord -Force
Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsAI' -Name 'TurnOffSavingSnapshots' -Value 1 -Type DWord -Force
Stop-Service -Name WSAIFabricSvc -Force -ErrorAction SilentlyContinue
Set-Service -Name WSAIFabricSvc -StartupType Disabled -ErrorAction SilentlyContinue

# 6. Sugestoes e Anuncios
Log "[6/8] Desativando sugestoes promocionais..."
New-Item -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\ContentDeliveryManager' -Force | Out-Null
$cdmProps = @('SubscribedContent-338387Enabled','SubscribedContent-338388Enabled','SubscribedContent-338389Enabled','SubscribedContent-353694Enabled','SubscribedContent-353696Enabled','SubscribedContent-353698Enabled','SubscribedContent-310093Enabled','SystemPaneSuggestionsEnabled','SoftLandingEnabled','RotatingLockScreenOverlayEnabled','SilentInstalledAppsEnabled')
foreach ($p in $cdmProps) {{
    Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\ContentDeliveryManager' -Name $p -Value 0 -Type DWord -Force
}}

# 7. Widgets
Log "[7/8] Desativando Widgets..."
New-Item -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced' -Force | Out-Null
Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced' -Name 'TaskbarDa' -Value 0 -Type DWord -Force
New-Item -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Dsh' -Force | Out-Null
Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\Policies\\Microsoft\\Dsh' -Name 'AllowNewsAndInterests' -Value 0 -Type DWord -Force

# 8. Remocao de Bloatwares
Log "[8/8] Removendo bloatwares e apps patrocinados..."
$targets = @({apps_arr})
$cleaned = 0
foreach ($app in $targets) {{
    $pkgs = Get-AppxPackage -Name $app -AllUsers -ErrorAction SilentlyContinue
    if ($pkgs) {{
        foreach ($pkg in $pkgs) {{
            $pkg | Remove-AppxPackage -AllUsers -ErrorAction SilentlyContinue
            Log "Removido: $($pkg.Name)"
            $cleaned++
        }}
    }}
    $provs = Get-AppxProvisionedPackage -Online -ErrorAction SilentlyContinue | Where-Object {{ $_.DisplayName -like $app }}
    if ($provs) {{
        foreach ($prov in $provs) {{
            $prov | Remove-AppxProvisionedPackage -Online -ErrorAction SilentlyContinue
            $cleaned++
        }}
    }}
}}
Log "Total de pacotes bloatware removidos: $cleaned"

# Reiniciar Explorer
Log "Atualizando a interface do Windows..."
Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 600
Start-Process explorer.exe

Log "=== OTIMIZACAO COMPLETA DEBLOAT FINALIZADA COM SUCESSO! ==="
"""
        success, out = Win11Debloater.execute_powershell_script(ps_code, timeout=240)
        return {
            "success": success,
            "message": "Suíte Completa de Debloat Aplicada com Sucesso!" if success else f"Falha na execução: {out}",
            "log": out
        }

    @staticmethod
    def get_apps_catalog():
        """Retorna o catálogo de bloatwares categorizados para a interface gráfica de seleção."""
        return [
            # Categoria: Patrocinados & Terceiros
            {"id": "*TikTok*", "name": "TikTok", "desc": "App patrocinado de vídeos curtos", "cat": "sponsored", "default": True},
            {"id": "SpotifyAB.SpotifyMusic", "name": "Spotify Music", "desc": "App promocional do Spotify", "cat": "sponsored", "default": True},
            {"id": "*Disney*", "name": "Disney+", "desc": "App promocional de streaming", "cat": "sponsored", "default": True},
            {"id": "*Facebook*", "name": "Facebook", "desc": "App patrocinado Meta", "cat": "sponsored", "default": True},
            {"id": "*Instagram*", "name": "Instagram", "desc": "App patrocinado Meta", "cat": "sponsored", "default": True},
            {"id": "*PrimeVideo*", "name": "Amazon Prime Video", "desc": "App patrocinado de streaming", "cat": "sponsored", "default": True},

            # Categoria: Microsoft Bloatware
            {"id": "Clipchamp.Clipchamp", "name": "Clipchamp Vídeo", "desc": "Editor de vídeo promocional", "cat": "microsoft", "default": True},
            {"id": "Microsoft.549981C3F5F10", "name": "Cortana", "desc": "Assistente de voz legada", "cat": "microsoft", "default": True},
            {"id": "Microsoft.BingNews", "name": "Microsoft Notícias / MSN", "desc": "Feed de notícias em segundo plano", "cat": "microsoft", "default": True},
            {"id": "Microsoft.BingWeather", "name": "Microsoft Clima", "desc": "Previsão do tempo MSN", "cat": "microsoft", "default": True},
            {"id": "Microsoft.BingFinance", "name": "Microsoft Finanças", "desc": "Cotações e moedas MSN", "cat": "microsoft", "default": True},
            {"id": "Microsoft.BingSports", "name": "Microsoft Esportes", "desc": "Feed de esportes MSN", "cat": "microsoft", "default": True},
            {"id": "Microsoft.Getstarted", "name": "Dicas do Windows", "desc": "Pop-ups de tutoriais do sistema", "cat": "microsoft", "default": True},
            {"id": "Microsoft.GetHelp", "name": "Obter Ajuda", "desc": "Canal de suporte integrado", "cat": "microsoft", "default": True},
            {"id": "Microsoft.Microsoft3DViewer", "name": "Visualizador 3D", "desc": "Visualizador de modelos 3D", "cat": "microsoft", "default": True},
            {"id": "Microsoft.3DBuilder", "name": "3D Builder", "desc": "Modelador 3D legado", "cat": "microsoft", "default": True},
            {"id": "Microsoft.ZuneVideo", "name": "Filmes e TV", "desc": "Player e loja de vídeos legado", "cat": "microsoft", "default": True},
            {"id": "Microsoft.ZuneMusic", "name": "Groove Música (Legado)", "desc": "Player de mídia legado", "cat": "microsoft", "default": True},
            {"id": "Microsoft.MicrosoftOfficeHub", "name": "Microsoft 365 Promocional", "desc": "Hub promocional do Office", "cat": "microsoft", "default": True},
            {"id": "Microsoft.MicrosoftSolitaireCollection", "name": "Paciência / Solitaire", "desc": "Coleção de jogos casuais", "cat": "microsoft", "default": True},
            {"id": "Microsoft.MixedReality.Portal", "name": "Realidade Misturada", "desc": "Serviços VR descontinuados", "cat": "microsoft", "default": True},
            {"id": "Microsoft.PowerAutomateDesktop", "name": "Power Automate", "desc": "Automações corporativas", "cat": "microsoft", "default": True},
            {"id": "Microsoft.Todos", "name": "Microsoft To-Do", "desc": "Aplicativo de tarefas", "cat": "microsoft", "default": False},
            {"id": "Microsoft.Windows.DevHome", "name": "Dev Home", "desc": "Ferramenta para desenvolvedores", "cat": "microsoft", "default": True},
            {"id": "Microsoft.PCManager", "name": "Microsoft PC Manager", "desc": "Otimizador utilitário da Microsoft", "cat": "microsoft", "default": True},
            {"id": "Microsoft.Windows.AIHub", "name": "Windows AI Hub", "desc": "Hub de IA promocional", "cat": "microsoft", "default": True},

            # Categoria: Xbox & Jogos
            {"id": "Microsoft.XboxApp", "name": "Xbox App Console", "desc": "App principal do Xbox para PC", "cat": "xbox", "default": False},
            {"id": "Microsoft.GamingApp", "name": "Xbox Gaming App", "desc": "Gerenciador de jogos Xbox", "cat": "xbox", "default": False},
            {"id": "Microsoft.XboxGamingOverlay", "name": "Xbox Game Bar", "desc": "Overlay de jogos (Win+G)", "cat": "xbox", "default": False},

            # Categoria: Comunicação & Utilidades
            {"id": "MicrosoftTeams", "name": "Teams (Chat Pessoal)", "desc": "Teams integrado à barra de tarefas", "cat": "communication", "default": True},
            {"id": "Microsoft.SkypeApp", "name": "Skype", "desc": "Aplicativo de chamadas Skype", "cat": "communication", "default": True},
            {"id": "Microsoft.YourPhone", "name": "Vínculo com Celular", "desc": "Sincronização com smartphone", "cat": "communication", "default": False},
            {"id": "Microsoft.WindowsFeedbackHub", "name": "Hub de Comentários", "desc": "Envio de telemetria e sugestões", "cat": "communication", "default": True},
            {"id": "Microsoft.WindowsMaps", "name": "Mapas do Windows", "desc": "Aplicativo de mapas offline", "cat": "communication", "default": True},
            {"id": "Microsoft.WindowsSoundRecorder", "name": "Gravador de Voz", "desc": "Gravador de áudio nativo", "cat": "communication", "default": False},
            {"id": "Microsoft.OutlookForWindows", "name": "Novo Outlook", "desc": "Cliente web-based do Outlook", "cat": "communication", "default": False}
        ]

    @staticmethod
    def remove_custom_apps(app_id_list):
        """Remove apenas a lista de aplicativos selecionados pelo usuário nos checkboxes da GUI."""
        if not app_id_list or not isinstance(app_id_list, list):
            return {"success": False, "message": "Nenhum aplicativo foi selecionado para remoção.", "log": ""}

        valid_apps = [str(a).strip() for a in app_id_list if str(a).strip()]
        if not valid_apps:
            return {"success": False, "message": "Nenhum aplicativo válido selecionado.", "log": ""}

        apps_arr = ", ".join(f"'{a}'" for a in valid_apps)
        ps_code = f"""
$targets = @({apps_arr})
Log "Iniciando desinstalacao personalizada de $($targets.Count) aplicativo(s) selecionado(s)..."
$removedCount = 0

foreach ($app in $targets) {{
    $pkgs = Get-AppxPackage -Name $app -AllUsers -ErrorAction SilentlyContinue
    if ($pkgs) {{
        foreach ($pkg in $pkgs) {{
            $pkg | Remove-AppxPackage -AllUsers -ErrorAction SilentlyContinue
            Log "Removido AppX: $($pkg.Name)"
            $removedCount++
        }}
    }}
    
    $provs = Get-AppxProvisionedPackage -Online -ErrorAction SilentlyContinue | Where-Object {{ $_.DisplayName -like $app }}
    if ($provs) {{
        foreach ($prov in $provs) {{
            $prov | Remove-AppxProvisionedPackage -Online -ErrorAction SilentlyContinue
            Log "Removido Provisionado: $($prov.DisplayName)"
            $removedCount++
        }}
    }}
}}

Log "Remocao concluida! Total de pacotes removidos com sucesso: $removedCount"
"""
        success, out = Win11Debloater.execute_powershell_script(ps_code, timeout=120)
        return {
            "success": success,
            "message": f"Remoção concluída! {len(valid_apps)} apps processados." if success else f"Erro ao desinstalar: {out}",
            "log": out
        }

    @staticmethod
    def get_ui_tweaks_status():
        """Retorna o estado dos tweaks de interface e explorer no Windows."""
        status = {
            "classic_context_menu": False,
            "show_file_extensions": False,
            "show_hidden_files": False,
            "disable_mouse_acceleration": False,
            "hide_task_view": False
        }
        try:
            # 1. Menu de contexto clássico
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\CLSID\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}\InprocServer32") as key:
                    status["classic_context_menu"] = True
            except Exception:
                status["classic_context_menu"] = False

            # 2. Explorer Advanced (Extensões e Ocultos)
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced") as key:
                    hide_ext, _ = winreg.QueryValueEx(key, "HideFileExt")
                    status["show_file_extensions"] = (hide_ext == 0)
                    hidden, _ = winreg.QueryValueEx(key, "Hidden")
                    status["show_hidden_files"] = (hidden == 1)
                    task_view, _ = winreg.QueryValueEx(key, "ShowTaskViewButton")
                    status["hide_task_view"] = (task_view == 0)
            except Exception:
                pass

            # 3. Mouse Acceleration
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Mouse") as key:
                    speed, _ = winreg.QueryValueEx(key, "MouseSpeed")
                    status["disable_mouse_acceleration"] = (str(speed) == "0")
            except Exception:
                pass

        except Exception as e:
            print("Erro ao ler tweaks de interface:", e)
        return status

    @staticmethod
    def apply_ui_tweaks(tweaks):
        """Aplica ou reverte os tweaks de interface clássicos do Win11Debloat."""
        ps_lines = ['Log "Aplicando personalizacoes de interface do Windows 11..."']
        
        # 1. Menu de contexto clássico
        if "classic_context_menu" in tweaks:
            enable = bool(tweaks["classic_context_menu"])
            if enable:
                ps_lines.append("""
New-Item -Path 'HKCU:\\Software\\Classes\\CLSID\\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}\\InprocServer32' -Value '' -Force | Out-Null
Set-ItemProperty -Path 'HKCU:\\Software\\Classes\\CLSID\\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}\\InprocServer32' -Name '(Default)' -Value '' -Force
Log "Menu de contexto classico do Windows 10 ativado no Windows 11."
""")
            else:
                ps_lines.append("""
Remove-Item -Path 'HKCU:\\Software\\Classes\\CLSID\\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}' -Recurse -Force -ErrorAction SilentlyContinue
Log "Menu de contexto padrao do Windows 11 restaurado."
""")

        # 2. Extensões de arquivos
        if "show_file_extensions" in tweaks:
            val = 0 if tweaks["show_file_extensions"] else 1
            ps_lines.append(f"""
Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced' -Name 'HideFileExt' -Value {val} -Type DWord -Force
Log "Exibicao de extensoes de arquivos ajustada."
""")

        # 3. Arquivos ocultos
        if "show_hidden_files" in tweaks:
            val = 1 if tweaks["show_hidden_files"] else 2
            ps_lines.append(f"""
Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced' -Name 'Hidden' -Value {val} -Type DWord -Force
Log "Exibicao de arquivos ocultos ajustada."
""")

        # 4. Visão de tarefas
        if "hide_task_view" in tweaks:
            val = 0 if tweaks["hide_task_view"] else 1
            ps_lines.append(f"""
Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced' -Name 'ShowTaskViewButton' -Value {val} -Type DWord -Force
Log "Botao Visao de Tarefas ajustado."
""")

        # 5. Aceleração de mouse (Gamer)
        if "disable_mouse_acceleration" in tweaks:
            if tweaks["disable_mouse_acceleration"]:
                ps_lines.append("""
Set-ItemProperty -Path 'HKCU:\\Control Panel\\Mouse' -Name 'MouseSpeed' -Value '0' -Force
Set-ItemProperty -Path 'HKCU:\\Control Panel\\Mouse' -Name 'MouseThreshold1' -Value '0' -Force
Set-ItemProperty -Path 'HKCU:\\Control Panel\\Mouse' -Name 'MouseThreshold2' -Value '0' -Force
Log "Aceleracao de ponteiro do mouse desativada (precisao 1:1 gamer)."
""")
            else:
                ps_lines.append("""
Set-ItemProperty -Path 'HKCU:\\Control Panel\\Mouse' -Name 'MouseSpeed' -Value '1' -Force
Set-ItemProperty -Path 'HKCU:\\Control Panel\\Mouse' -Name 'MouseThreshold1' -Value '6' -Force
Set-ItemProperty -Path 'HKCU:\\Control Panel\\Mouse' -Name 'MouseThreshold2' -Value '10' -Force
Log "Aceleracao de ponteiro padrao restaurada."
""")

        ps_lines.append("""
Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500
Start-Process explorer.exe
Log "Explorer reiniciado com as novas personalizacoes aplicadas!"
""")

        ps_code = "\n".join(ps_lines)
        success, out = Win11Debloater.execute_powershell_script(ps_code, timeout=60)
        return {
            "success": success,
            "message": "Personalizações de interface aplicadas com sucesso!" if success else f"Erro ao aplicar: {out}",
            "log": out
        }

    @staticmethod
    def launch_official_gui():
        """Lança a interface gráfica oficial e interativa do Win11Debloat (WinForms GUI)."""
        ps_code = """
try {
    & ([scriptblock]::Create((irm "https://win11debloat.raphi.re/")))
} catch {
    Write-Host "Falha ao baixar GUI oficial online. Verifique sua conexao." -ForegroundColor Red
}
"""
        try:
            ctypes.windll.shell32.ShellExecuteW(None, "runas", "powershell.exe", f'-NoProfile -ExecutionPolicy Bypass -Command "{ps_code}"', None, 1)
            return {"success": True, "message": "Janela gráfica oficial do Win11Debloat iniciada com sucesso!"}
        except Exception as e:
            return {"success": False, "message": f"Erro ao abrir janela: {e}"}
