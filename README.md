VoxReader Desktop - Conversor Neural 🎙️
O VoxReader é uma aplicação desktop desenvolvida em Python que utiliza a tecnologia de Vozes Neurais da Azure para converter arquivos de texto (.txt) e documentos (.pdf) em áudios de alta qualidade no formato MP3.

🚀 Funcionalidades
Autenticação de Usuários: Sistema de login e cadastro com diferentes níveis de acesso (Padrão e Administrador).

Segurança: Proteção de criação de perfis administrativos via Senha Mestre.

Conversão Inteligente: Suporte a arquivos .txt e extração de texto de arquivos .pdf.

Persistência de Dados: Histórico completo de conversões armazenado localmente em banco de dados SQLite.

Gerenciamento de Arquivos: Função para salvar MP3 localmente e abrir a pasta de destino diretamente pela interface.

Integração com Nuvem: Consumo da API de Speech Services da Microsoft Azure.

🛠️ Tecnologias e Stack
Linguagem: Python 3.10+

Interface Gráfica: CustomTkinter (UI Moderna e Responsiva).

Banco de Dados: SQLite3.

Engine de Áudio: Azure Cognitive Services (Speech SDK).

Manipulação de PDF: PyPDF2.

📦 Requisitos e Dependências
Para rodar o projeto a partir do código-fonte, você precisará de uma chave de API da Azure (Speech Services).

Bibliotecas Necessárias:
Bash
pip install customtkinter azure-cognitiveservices-speech PyPDF2
⚙️ Como Executar
Opção 1: Via Executável (Recomendado para Usuários)
Acesse a aba Releases deste repositório.

Baixe o arquivo VoxReader.exe.

Execute o arquivo. Na primeira execução, o sistema solicitará a configuração de uma Senha Mestre para o banco de dados local.

Opção 2: Via Código-Fonte (Desenvolvedores)
Clone o repositório:

Bash
git clone https://github.com/seu-usuario/voxreader.git
Instale as dependências listadas acima.

Execute o script principal:

Bash
python VoxReader.py
📋 Instruções de Uso
Configuração Inicial: Defina uma Senha Mestre (necessária para criar perfis de Administrador).

Cadastro: Crie um perfil informando sua Azure API Key e a Região (ex: brazilsouth).

Conversão:

Selecione um arquivo .txt ou .pdf.

Clique em "Carregar Vozes" para buscar as opções neurais em português.

Clique em "Converter" e aguarde o processamento.

Histórico: Verifique suas conversões passadas na aba "Histórico" e abra o local onde os arquivos foram salvos.

🏛️ Arquitetura do Projeto
O projeto segue o padrão de Arquitetura em Camadas (Layered Architecture), separando:

UI (Interface): Gerenciada pelo CustomTkinter.

Business Logic: Processamento de threads para TTS e extração de PDF.

Data Access: Persistência via SQLite para usuários e logs de conversão.
