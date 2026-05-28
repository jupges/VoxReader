# VoxReader Pro 🎙️

O **VoxReader** é uma aplicação desktop desenvolvida em Python que utiliza a síntese de voz neural da Microsoft (via engine do Microsoft Edge) para ler e acompanhar textos de arquivos TXT e PDF de forma natural e interativa.

Esta versão foi totalmente reescrita em **PySide6** (Qt6) para oferecer uma interface de alto desempenho, aceleração gráfica nativa e recursos de reprodução de áudio.

---

## ✨ Principais Recursos

- **🎙️ Voz Neural Gratuita:** Síntese de voz com alto nível de naturalidade através do motor do Microsoft Edge, sem a necessidade de chaves de API pagas.
- **📖 Acompanhamento de Leitura Inteligente (Reading Tracker):** O texto é exibido em um painel interativo que destaca a palavra exata que está sendo dita pelo narrador em tempo real, com rolagem automática da página.
- **🎛️ Reprodutor de Áudio Avançado:**
  - Linha do tempo interativa (Scrubber) para arrastar e navegar pelo áudio.
  - Ajuste dinâmico de velocidade de fala (de $0.5x$ até $2.0x$) com preservação natural do timbre de voz.
  - Exportação definitiva para arquivos `.mp3`.
- **🔒 Segurança e Perfis Locais (SQLite):**
  - Cadastro de usuários com senhas criptografadas localmente.
  - Níveis de acesso distintos (Usuários comuns visualizam apenas o próprio histórico, enquanto Administradores têm acesso ao painel global).
  - Senha mestre configurada no primeiro uso para autorização de perfis administrativos.
- **📂 Suporte a Documentos:** Leitura direta de arquivos de texto simples (`.txt`) e documentos portáteis (`.pdf`).
- **📺 Modo Tela Cheia:** Atalho nativo usando `F11` para alternar e `Escape` para fechar a tela cheia.

---

## 🛠️ Tecnologias Utilizadas

- **Python 3.10+**
- **PySide6 (Qt6):** Interface gráfica e reprodutor multimídia nativo.
- **edge-tts:** Integração com os servidores de voz neural da Microsoft.
- **PyPDF2:** Extração de caracteres de arquivos PDF.
- **SQLite3:** Banco de dados relacional local leve.

---

## 🚀 Como Executar o Projeto

### 1. Pré-requisitos
Certifique-se de ter o Python instalado em sua máquina. Em seguida, clone o repositório:

```bash
git clone https://github.com/jupges/VoxReader.git
cd VoxReader
