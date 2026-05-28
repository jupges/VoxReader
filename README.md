# VoxReader Desktop - Conversor Neural 🎙️

O **VoxReader** é uma aplicação desktop desenvolvida em Python que utiliza inteligência artificial para converter textos de arquivos TXT e PDF em áudio de alta fidelidade. O sistema utiliza os motores de síntese de voz neural da Microsoft (via engine do Microsoft Edge), dispensando a necessidade de chaves de API pagas.

Esta versão foi construída utilizando a interface moderna do **CustomTkinter** e o reprodutor de áudio integrado do **Pygame Mixer**.

---

## ✨ Principais Recursos

- **🎙️ Conversão Neural Integrada:** Geração de voz natural em português (Brasil e Portugal) utilizando os perfis gratuitos da Microsoft.
- **📂 Importação de Documentos:** Suporte para extração automática de caracteres de arquivos de texto simples (`.txt`) e documentos (`.pdf`).
- **🎧 Reprodutor de Áudio Local:** Player integrado utilizando o `pygame.mixer` para ouvir a prévia do áudio sintetizado diretamente no app.
- **💾 Exportação de MP3:** Opção para salvar o áudio final de forma definitiva em qualquer pasta do computador.
- **🕒 Histórico Local de Conversão:**
  - Registro de conversões anteriores em uma tabela de dados integrada (`Treeview`).
  - Lógica de busca rápida por nome de arquivo.
  - Opção de localizar o arquivo salvo diretamente no Explorador de Arquivos do Windows com apenas um clique.
- **🔒 Segurança e Perfis Isolados (SQLite):**
  - Isolamento de histórico por usuário.
  - Perfis de nível "Administrador" exigem validação por Senha Mestre (configurada na primeira inicialização do app).
  - Administradores têm permissão de auditar o histórico global do aplicativo.
- **📺 Modo Tela Cheia:** Atalho usando a tecla `F11` para alternar e `Escape` para fechar a tela cheia.

---

## 🛠️ Requisitos e Instalação

### 1. Clonar o repositório
```bash
git clone https://github.com/jupges/VoxReader.git
cd VoxReader
