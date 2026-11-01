# ⚡ RTX Fan Controller & Aegis Gaming SensorPanel HUD

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Windows%2011%20%7C%2010-0078D6?style=for-the-badge&logo=windows&logoColor=white" alt="Windows 11">
  <img src="https://img.shields.io/badge/Python-3.12%20(64--bit)-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.12">
  <img src="https://img.shields.io/badge/GPU-NVIDIA%20GeForce%20RTX-76B900?style=for-the-badge&logo=nvidia&logoColor=white" alt="NVIDIA GeForce">
  <img src="https://img.shields.io/badge/UI-PyWebView%20%2B%20Chromium-00E5FF?style=for-the-badge&logo=googlechrome&logoColor=white" alt="PyWebView Edge Chromium">
</p>

Aplicativo completo de alta performance para **Controle Térmico Inteligente de Ventoinhas (Fans)**, **SensorPanel HUD Gamer em Tela Cheia Borderless** (ideal para monitores principais ou telas LCD secundárias de gabinete 3.5", 5", 7", etc.), **Otimizador do Windows** e **Win11 Debloater Offline**.

---

## 🎯 Destaques e Funcionalidades

### 🎮 SensorPanel HUD Gamer
* **Design Glassmorphism Moderno**: Visual gamer neon com anéis dinâmicos rotativos, mostradores circulares e efeitos de profundidade.
* **11+ Temas Oficiais Inspirados nos Maiores Jogos**:
  * 💣 **Counter-Strike 2 (CS2)** (Laranja tático, poeira de combate e hazard stripes)
  * 🎯 **Valorant** (Vermelho Radianite, ciano brilhante e geometria angular)
  * ⚔️ **League of Legends (LoL)** (Ouro Hextech, azul arcano e runas celestiais)
  * 🌴 **GTA V / GTA VI** (Pôr do sol degradê Vice City, rosa choque e azul turquesa)
  * 🪖 **Call of Duty: Warzone** (Verde fosfórico militar e grade topográfica)
  * 🦹 **Fortnite** (Fenda cósmica roxa, tempestade e ouro Royale)
  * ⛏️ **Minecraft** (Blocos de Netherite, circuitos ativos de Redstone e Diamante)
  * 💍 **Elden Ring** (Ouro místico da Térvore e runas arcanas)
  * 🦾 **Cyberpunk 2077** (Amarelo neon Samurai, glitches e vermelho Arasaka)
  * 🏆 **Apex Legends** (Vermelho Apex Predator e grafite de titânio)
  * 📱 **Turing Classic** (Visual cósmico fiel com anéis roxo/ciano)
* **Escala e Zoom Vetorial 100% Nítido**: Suporte a zoom de 50% até 200% via renderização vetorial subpixel, mantendo texto e ícones perfeitamente cristalinos em qualquer resolução.
* **Auto-Game Tracker**: Identifica automaticamente jogos em execução (CS2, Valorant, GTA, Warzone, Elden Ring, etc.) e exibe contador de FPS, frametime e tempo de sessão ao vivo.

---

### ❄️ Controle Térmico Avançado de Fans
* **Motor Duplo de Alta Confiabilidade**:
  1. **NVAPI Nativo** (via `LibreHardwareMonitorLib`): Permite controle manual ou por curva da ventoinha da GPU com modo Zero RPM (0 dB em idle).
  2. **NVML (NVIDIA Management Library)**: Telemetria de alta frequência para temperatura, clock, VRAM e consumo elétrico.
* **Curva de Ventoinha Personalizável**:
  * Definição de pontos de curva customizados temperatura vs % rotação.
  * Histerese térmica para evitar aceleração/desaceleração contínua (*fan hunting*).
  * Perfis rápidos: *Silencioso*, *Equilibrado*, *Performance*, *Manual* e *Curva*.

---

### 📊 Telemetria Completa de Hardware
* **Processador (CPU)**: Uso total %, relógio (GHz), temperatura ao vivo, pico máximo (°C), consumo elétrico estimado (Watts) e uso individual dos 6 núcleos físicos.
* **Placa de Vídeo (GPU)**: Uso %, temperatura ao vivo, pico máximo, clock do chip (MHz), clock da memória VRAM (MHz), consumo elétrico em Watts vs TDP (180W), uso de VRAM (MB/GB) e largura de barramento PCIe.
* **Memória RAM & Swap**: Consumo em GB, percentual em uso, memória livre disponível e paginação Swap/Virtual.
* **Armazenamento Multi-Disco**:
  * Detecção automática de **todos os SSDs e HDDs** do sistema (`C:`, `D:`, etc.).
  * Distinção visual inteligente entre SSD e HDD com cores dedicadas.
  * Taxa de transferência em tempo real (Leitura e Escrita I/O em MB/s).
* **Rede**: Velocidade instantânea de Download e Upload, além do volume total transferido na sessão (GB).
* **Sistema**: Uptime contínuo do PC, contagem de processos em execução, data e hora.

---

### ⚡ Windows Optimizer & Win11 Debloater Offline
* **Otimizador do Windows**:
  * Gerenciamento de Memória Virtual (Pagefile/Swap).
  * Ativação do Plano de Energia de Desempenho Máximo.
  * Otimização de latência de rede (TCP/IP).
  * Limpeza de memória standby / cache do sistema.
* **Debloater 100% Offline**:
  * Desativação de telemetria e diagnósticos do Windows.
  * Remoção do Bing/busca web no Menu Iniciar.
  * Desativação de Copilot e Recall.
  * Remoção de mais de 80 bloatwares e aplicativos pré-instalados da Microsoft Store.

---

## 🛠️ Tecnologias Utilizadas

* **Linguagem**: Python 3.12 (64-bit)
* **Frontend**: HTML5, CSS3 Moderno (Glassmorphism), JavaScript ES6+
* **Engine de Renderização**: [PyWebView](https://pywebview.flowrl.com/) com Microsoft Edge Chromium (WebView2)
* **Telemetria de Hardware**: `psutil`, NVIDIA Management Library (`nvml.dll`), `LibreHardwareMonitorLib` (.NET CLR via `pythonnet`)
* **Bridge de Placa-Mãe**: `HardwareBridge.exe` em C# .NET

---

## 🚀 Como Executar

### Pré-requisitos
* **Windows 10 ou 11 (64-bit)**
* **Python 3.12 (64-bit)**
* Placa de vídeo **NVIDIA GeForce** (série GTX/RTX) com drivers atualizados

### Instalação Rápida
1. Clone o repositório:
   ```bash
   git clone https://github.com/tmesquita13/RTX_Fan_Controller.git
   cd RTX_Fan_Controller
   ```

2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

3. Inicie o programa:
   * Basta dar dois cliques em **`Iniciar_Programa.bat`**.

---

## ⌨️ Atalhos de Teclado

| Tecla | Ação |
| :--- | :--- |
| **F11** | Alterna entre Tela Cheia Borderless e Janela |
| **ESC** | Sai do modo tela cheia |
| **Ctrl +** | Aumenta o Zoom da Interface (+5%) |
| **Ctrl -** | Diminui o Zoom da Interface (-5%) |
| **Ctrl 0** | Restaura o Zoom para 100% Padrão |
| **Ctrl + Scroll** | Ajuste dinâmico de zoom com a roda do mouse |

---

## 📄 Licença

Distribuído sob a licença MIT. Veja `LICENSE` para mais detalhes.
