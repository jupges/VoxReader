import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk
import PyPDF2
import azure.cognitiveservices.speech as speechsdk
import threading
import os
import shutil
import ctypes
import sqlite3
import subprocess
from datetime import datetime

# Configuração visual do CustomTkinter
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

def setup_database():
    """Cria o banco de dados e as tabelas com a nova estrutura."""
    conn = sqlite3.connect("voxreader.db")
    cursor = conn.cursor()
    
    # Tabela de Configurações Globais (Para a Senha Mestre)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Configuracoes (
            chave TEXT PRIMARY KEY,
            valor TEXT NOT NULL
        )
    ''')
    
    # Tabela de Usuários
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            api_key TEXT NOT NULL,
            region TEXT NOT NULL
        )
    ''')
    
    # Tabela de Histórico (Agora com 'caminho_salvo')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            arquivo TEXT NOT NULL,
            voz TEXT NOT NULL,
            data_hora TEXT NOT NULL,
            caminho_salvo TEXT,
            FOREIGN KEY(usuario_id) REFERENCES Usuarios(id)
        )
    ''')
    conn.commit()
    conn.close()


class VoxReaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("VoxReader Desktop - Conversor Neural")
        self.geometry("820x700")
        self.resizable(False, False)

        # Inicializa o Banco de Dados
        setup_database()

        # Variáveis de estado
        self.current_user = None  
        self.file_path = None
        self.temp_audio_path = "temp_audio.mp3"
        self.voices = {}
        self.current_conversion_id = None # Guarda o ID da última conversão para atualizar o 'Salvo'

        # Verifica se é a primeira vez rodando o app (Setup da Senha Mestre)
        if not self.check_first_setup():
            self.show_first_setup_screen()
        else:
            self.show_login_screen()

    # ==========================================
    # VERIFICAÇÃO E SETUP INICIAL
    # ==========================================
    def check_first_setup(self):
        conn = sqlite3.connect("voxreader.db")
        cursor = conn.cursor()
        cursor.execute("SELECT valor FROM Configuracoes WHERE chave='senha_mestre'")
        row = cursor.fetchone()
        conn.close()
        return row is not None

    def show_first_setup_screen(self):
        self.clear_window()
        frame = ctk.CTkFrame(self)
        frame.pack(pady=100, padx=150, fill="both", expand=True)

        ctk.CTkLabel(frame, text="Bem-vindo ao VoxReader!", font=("Arial", 24, "bold"), text_color="green").pack(pady=(30, 10))
        ctk.CTkLabel(frame, text="Como é a sua primeira vez, defina uma Senha Mestre.\nEla será exigida sempre que alguém tentar criar um perfil de Administrador.", justify="center").pack(pady=10)

        self.entry_master_pass = ctk.CTkEntry(frame, placeholder_text="Digite a Senha Mestre", show="*", width=300)
        self.entry_master_pass.pack(pady=20)

        ctk.CTkButton(frame, text="Salvar e Continuar", width=300, command=self.save_master_pass).pack(pady=10)

    def save_master_pass(self):
        senha = self.entry_master_pass.get().strip()
        if len(senha) < 4:
            messagebox.showwarning("Aviso", "A Senha Mestre deve ter pelo menos 4 caracteres.")
            return

        conn = sqlite3.connect("voxreader.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Configuracoes (chave, valor) VALUES ('senha_mestre', ?)", (senha,))
        conn.commit()
        conn.close()

        messagebox.showinfo("Sucesso", "Senha Mestre configurada! Agora faça seu cadastro.")
        self.show_register_screen()

    # ==========================================
    # SISTEMA DE NAVEGAÇÃO E AUTENTICAÇÃO
    # ==========================================
    def clear_window(self):
        for widget in self.winfo_children():
            widget.destroy()

    def show_login_screen(self):
        self.clear_window()
        self.login_frame = ctk.CTkFrame(self)
        self.login_frame.pack(pady=80, padx=200, fill="both", expand=True)

        ctk.CTkLabel(self.login_frame, text="VoxReader Login", font=("Arial", 24, "bold")).pack(pady=30)

        self.entry_login_user = ctk.CTkEntry(self.login_frame, placeholder_text="Usuário", width=250)
        self.entry_login_user.pack(pady=10)

        self.entry_login_pass = ctk.CTkEntry(self.login_frame, placeholder_text="Senha", show="*", width=250)
        self.entry_login_pass.pack(pady=10)

        ctk.CTkButton(self.login_frame, text="Entrar", width=250, command=self.process_login).pack(pady=20)
        ctk.CTkButton(self.login_frame, text="Criar Novo Perfil", width=250, fg_color="gray", command=self.show_register_screen).pack(pady=5)

    def show_register_screen(self):
        self.clear_window()
        self.register_frame = ctk.CTkFrame(self)
        self.register_frame.pack(pady=20, padx=150, fill="both", expand=True)

        ctk.CTkLabel(self.register_frame, text="Criar Perfil", font=("Arial", 20, "bold")).pack(pady=10)

        self.reg_user = ctk.CTkEntry(self.register_frame, placeholder_text="Nome de Usuário", width=300)
        self.reg_user.pack(pady=5)

        self.reg_pass = ctk.CTkEntry(self.register_frame, placeholder_text="Senha", show="*", width=300)
        self.reg_pass.pack(pady=5)

        ctk.CTkLabel(self.register_frame, text="Tipo de Perfil:").pack(pady=(5, 0))
        self.reg_role = ctk.CTkComboBox(self.register_frame, values=["Padrão", "Administrador"], width=300, command=self.toggle_master_pass)
        self.reg_role.set("Padrão")
        self.reg_role.pack(pady=5)

        # Campo da Senha Mestre (Fica oculto por padrão)
        self.reg_master_pass = ctk.CTkEntry(self.register_frame, placeholder_text="Senha Mestre (Autorização)", show="*", width=300, border_color="red")

        ctk.CTkLabel(self.register_frame, text="Credenciais da Azure (Obrigatório):").pack(pady=(10, 0))
        self.reg_api = ctk.CTkEntry(self.register_frame, placeholder_text="API Key da Azure", width=300)
        self.reg_api.pack(pady=5)

        self.reg_region = ctk.CTkEntry(self.register_frame, placeholder_text="Região (Ex: brazilsouth)", width=300)
        self.reg_region.pack(pady=5)

        ctk.CTkButton(self.register_frame, text="Salvar Perfil", width=300, fg_color="green", command=self.process_register).pack(pady=15)
        ctk.CTkButton(self.register_frame, text="Voltar", width=300, fg_color="gray", command=self.show_login_screen).pack(pady=5)

    def toggle_master_pass(self, choice):
        """Mostra ou esconde o campo de senha mestre dependendo do perfil escolhido."""
        if choice == "Administrador":
            self.reg_master_pass.pack(pady=5, after=self.reg_role)
        else:
            self.reg_master_pass.pack_forget()

    def process_register(self):
        user = self.reg_user.get().strip()
        pwd = self.reg_pass.get().strip()
        role = self.reg_role.get()
        api = self.reg_api.get().strip()
        region = self.reg_region.get().strip()

        if not user or not pwd or not api or not region:
            messagebox.showwarning("Erro", "Preencha todos os campos!")
            return

        # VERIFICAÇÃO DA SENHA MESTRE SE FOR ADMIN
        if role == "Administrador":
            master_input = self.reg_master_pass.get().strip()
            conn = sqlite3.connect("voxreader.db")
            cur = conn.cursor()
            cur.execute("SELECT valor FROM Configuracoes WHERE chave='senha_mestre'")
            real_master = cur.fetchone()[0]
            conn.close()

            if master_input != real_master:
                messagebox.showerror("Acesso Negado", "Senha Mestre incorreta! Não é possível criar um Administrador.")
                return

        try:
            conn = sqlite3.connect("voxreader.db")
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Usuarios (username, password, role, api_key, region) VALUES (?, ?, ?, ?, ?)", 
                           (user, pwd, role, api, region))
            conn.commit()
            conn.close()
            messagebox.showinfo("Sucesso", "Perfil criado com sucesso! Faça o login.")
            self.show_login_screen()
        except sqlite3.IntegrityError:
            messagebox.showerror("Erro", "Esse nome de usuário já existe.")
        except Exception as e:
            messagebox.showerror("Erro BD", str(e))

    def process_login(self):
        user = self.entry_login_user.get().strip()
        pwd = self.entry_login_pass.get().strip()

        conn = sqlite3.connect("voxreader.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Usuarios WHERE username=? AND password=?", (user, pwd))
        row = cursor.fetchone()
        conn.close()

        if row:
            self.current_user = {
                "id": row[0], "username": row[1], "role": row[3], "api_key": row[4], "region": row[5]
            }
            self.show_main_app()
        else:
            messagebox.showerror("Erro", "Usuário ou senha incorretos.")

    # ==========================================
    # TELA PRINCIPAL (APÓS LOGIN)
    # ==========================================
    def show_main_app(self):
        self.clear_window()
        
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(header, text=f"👤 Logado como: {self.current_user['username']} ({self.current_user['role']})", font=("Arial", 12, "bold")).pack(side="left")
        ctk.CTkButton(header, text="Sair", width=80, fg_color="red", height=24, command=self.logout).pack(side="right")

        self.tabview = ctk.CTkTabview(self, width=780, height=600)
        self.tabview.pack(pady=5, padx=10, expand=True, fill="both")

        self.tab_main = self.tabview.add("Conversor")
        self.tab_history = self.tabview.add("Histórico")
        self.tab_help = self.tabview.add("Instruções")

        self.setup_main_tab()
        self.setup_history_tab()
        self.setup_help_tab()

    def logout(self):
        self.current_user = None
        self.stop_audio()
        self.show_login_screen()

    # (Métodos visuais das abas mantidos idênticos, vou resumir abaixo)
    def setup_main_tab(self):
        self.frame_file = ctk.CTkFrame(self.tab_main)
        self.frame_file.pack(pady=10, padx=10, fill="x")
        self.btn_select_file = ctk.CTkButton(self.frame_file, text="1. Selecionar Arquivo (.txt, .pdf)", command=self.select_file)
        self.btn_select_file.pack(pady=10, padx=10, side="left")
        self.lbl_file = ctk.CTkLabel(self.frame_file, text="Nenhum arquivo selecionado...", text_color="gray")
        self.lbl_file.pack(pady=10, padx=10, side="left")

        self.frame_convert = ctk.CTkFrame(self.tab_main)
        self.frame_convert.pack(pady=10, padx=10, fill="x")
        self.btn_load_voices = ctk.CTkButton(self.frame_convert, text="Carregar Vozes da Nuvem", width=180, command=self.fetch_voices)
        self.btn_load_voices.pack(pady=10, padx=10, side="left")
        self.combo_voice = ctk.CTkComboBox(self.frame_convert, values=["Clique em Carregar Vozes primeiro..."], width=300)
        self.combo_voice.pack(pady=10, padx=10, side="left")

        self.btn_convert = ctk.CTkButton(self.tab_main, text="3. Converter para MP3", command=self.start_conversion, fg_color="green", hover_color="darkgreen", height=40)
        self.btn_convert.pack(pady=15)

        self.lbl_status = ctk.CTkLabel(self.tab_main, text="Status: Aguardando ação...", font=("Arial", 12, "italic"))
        self.lbl_status.pack(pady=5)

        self.frame_player = ctk.CTkFrame(self.tab_main)
        self.frame_player.pack(pady=10, padx=10, fill="x")
        self.btn_play = ctk.CTkButton(self.frame_player, text="▶ Play", width=80, state="disabled", command=self.play_audio)
        self.btn_play.pack(pady=10, padx=10, side="left")
        self.btn_stop = ctk.CTkButton(self.frame_player, text="■ Stop", width=80, state="disabled", command=self.stop_audio)
        self.btn_stop.pack(pady=10, padx=10, side="left")
        self.btn_save = ctk.CTkButton(self.frame_player, text="💾 Salvar MP3", state="disabled", command=self.save_mp3)
        self.btn_save.pack(pady=10, padx=10, side="right")

    def setup_history_tab(self):
        search_frame = ctk.CTkFrame(self.tab_history)
        search_frame.pack(fill="x", pady=5, padx=10)
        
        self.entry_search = ctk.CTkEntry(search_frame, placeholder_text="Buscar por nome do arquivo...", width=300)
        self.entry_search.pack(side="left", padx=10, pady=10)
        
        ctk.CTkButton(search_frame, text="Buscar", width=80, command=self.load_history).pack(side="left", padx=5)
        ctk.CTkButton(search_frame, text="Atualizar", width=80, fg_color="gray", command=self.load_history).pack(side="left", padx=5)

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#2b2b2b", foreground="white", fieldbackground="#2b2b2b", rowheight=25)
        style.map('Treeview', background=[('selected', '#1f538d')])

        # Coluna 'Salvo?' adicionada
        columns = ("ID", "Usuário", "Arquivo", "Voz", "Data", "Salvo?")
        self.tree = ttk.Treeview(self.tab_history, columns=columns, show="headings", height=13)
        
        for col in columns:
            self.tree.heading(col, text=col)
            
        self.tree.column("ID", width=30, anchor="center")
        self.tree.column("Usuário", width=100, anchor="center")
        self.tree.column("Arquivo", width=220, anchor="w")
        self.tree.column("Voz", width=130, anchor="center")
        self.tree.column("Data", width=110, anchor="center")
        self.tree.column("Salvo?", width=60, anchor="center")

        self.tree.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Botão para abrir o arquivo salvo
        self.btn_open_saved = ctk.CTkButton(self.tab_history, text="📂 Abrir Local do Arquivo", command=self.open_saved_location)
        self.btn_open_saved.pack(pady=10)

        self.load_history()

    def setup_help_tab(self):
        instrucoes = "Bem vindo ao VoxReader! \nA criação de perfis Admin é protegida pela Senha Mestre.\nVocê pode converter os áudios e, ao salvá-los no PC, o caminho fica guardado na aba Histórico."
        textbox = ctk.CTkTextbox(self.tab_help, width=700, height=450)
        textbox.pack(pady=10, padx=10, expand=True, fill="both")
        textbox.insert("0.0", instrucoes)
        textbox.configure(state="disabled")

    # ==========================================
    # LÓGICA DO HISTÓRICO E SALVAMENTO
    # ==========================================
    def log_conversion_to_db(self, filename, voice_name):
        """Salva a conversão no BD e guarda o ID gerado (O arquivo começa como NÃO SALVO)."""
        try:
            agora = datetime.now().strftime("%d/%m/%Y %H:%M")
            conn = sqlite3.connect("voxreader.db")
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Historico (usuario_id, arquivo, voz, data_hora, caminho_salvo) VALUES (?, ?, ?, ?, NULL)",
                           (self.current_user["id"], filename, voice_name, agora))
            
            # Pega o ID que acabou de ser gerado
            self.current_conversion_id = cursor.lastrowid
            
            conn.commit()
            conn.close()
            # Atualiza a tabela com segurança visual
            self.after(0, self.load_history)
        except Exception as e:
            print("Erro ao salvar histórico:", e)

    def load_history(self):
        """Busca o histórico e avalia se a coluna 'caminho_salvo' tem algo."""
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        search_term = f"%{self.entry_search.get().strip()}%"
        conn = sqlite3.connect("voxreader.db")
        cursor = conn.cursor()

        if self.current_user["role"] == "Administrador":
            query = '''SELECT h.id, u.username, h.arquivo, h.voz, h.data_hora, h.caminho_salvo 
                       FROM Historico h JOIN Usuarios u ON h.usuario_id = u.id 
                       WHERE h.arquivo LIKE ? ORDER BY h.id DESC'''
            cursor.execute(query, (search_term,))
        else:
            query = '''SELECT h.id, u.username, h.arquivo, h.voz, h.data_hora, h.caminho_salvo 
                       FROM Historico h JOIN Usuarios u ON h.usuario_id = u.id 
                       WHERE h.usuario_id = ? AND h.arquivo LIKE ? ORDER BY h.id DESC'''
            cursor.execute(query, (self.current_user["id"], search_term))

        rows = cursor.fetchall()
        for row in rows:
            # Lógica para preencher "Sim" ou "Não" na coluna Salvo?
            foi_salvo = "Sim" if row[5] else "Não"
            display_row = (row[0], row[1], row[2], row[3], row[4], foi_salvo)
            self.tree.insert("", "end", values=display_row)
            
        conn.close()

    def open_saved_location(self):
        """Abre o Windows Explorer marcando o arquivo que o usuário salvou."""
        selected = self.tree.focus()
        if not selected:
            messagebox.showinfo("Aviso", "Selecione um registro na tabela primeiro!")
            return
        
        # O ID da conversão está na coluna 0 da tabela
        item_id = self.tree.item(selected)['values'][0]
        
        conn = sqlite3.connect("voxreader.db")
        cursor = conn.cursor()
        cursor.execute("SELECT caminho_salvo FROM Historico WHERE id=?", (item_id,))
        row = cursor.fetchone()
        conn.close()

        if row and row[0]: # Se existir um caminho salvo
            caminho = os.path.normpath(row[0])
            if os.path.exists(caminho):
                # Comando nativo do Windows que abre a pasta e já clica no arquivo para o usuário
                subprocess.Popen(f'explorer /select,"{caminho}"')
            else:
                messagebox.showerror("Erro", "O arquivo foi movido ou excluído do computador.")
        else:
            messagebox.showinfo("Aviso", "Este áudio foi apenas convertido e ouvido, mas nunca foi salvo no dispositivo.")

    # ==========================================
    # LÓGICA DO CONVERSOR
    # ==========================================
    def select_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("Textos e PDFs", "*.txt *.pdf")])
        if filepath:
            self.file_path = filepath
            self.lbl_file.configure(text=os.path.basename(filepath), text_color="white")

    def fetch_voices(self):
        api_key = self.current_user["api_key"]
        region = self.current_user["region"]
        self.update_status("Status: Conectando à Azure...", "yellow")
        threading.Thread(target=self._get_azure_voices_thread, args=(api_key, region), daemon=True).start()

    def _get_azure_voices_thread(self, api_key, region):
        try:
            speech_config = speechsdk.SpeechConfig(subscription=api_key, region=region)
            synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
            result = synthesizer.get_voices_async("pt-BR").get()
            
            if result.reason == speechsdk.ResultReason.VoicesListRetrieved:
                self.voices.clear()
                for voice in result.voices:
                    self.voices[f"{voice.local_name} ({voice.gender.name})"] = voice.short_name
                self.combo_voice.configure(values=list(self.voices.keys()))
                if self.voices: self.combo_voice.set(list(self.voices.keys())[0])
                self.update_status("Status: Vozes carregadas!", "green")
            else:
                self.update_status("Erro: Chave Azure inválida.", "red")
        except Exception:
            self.update_status("Erro ao buscar vozes. Sem internet.", "red")

    def start_conversion(self):
        if not self.file_path: return messagebox.showwarning("Aviso", "Selecione um arquivo!")
        selected_voice = self.combo_voice.get()
        if selected_voice not in self.voices: return
        
        self.btn_convert.configure(state="disabled")
        self.update_status("Status: Convertendo... (Aguarde)", "yellow")

        # Reseta o ID atual, pois é uma nova conversão
        self.current_conversion_id = None 
        
        threading.Thread(target=self.process_conversion, args=(
            self.current_user["api_key"], self.current_user["region"], self.voices[selected_voice], selected_voice), daemon=True).start()

    def process_conversion(self, api_key, region, voice_code, display_voice_name):
        try:
            texto = self.extract_text()
            if not texto.strip(): 
                self.after(0, self.update_status, "Erro: PDF sem texto.", "red")
                self.after(0, lambda: self.btn_convert.configure(state="normal"))
                return

            speech_config = speechsdk.SpeechConfig(subscription=api_key, region=region)
            speech_config.speech_synthesis_voice_name = voice_code
            
            self.after(0, self.stop_audio)

            audio_config = speechsdk.audio.AudioOutputConfig(filename=self.temp_audio_path)
            synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
            result = synthesizer.speak_text_async(texto).get()
            
            # ATUALIZAÇÃO IMPORTANTE: Força a liberação do arquivo da memória! 
            # Sem isso, o Windows Media Player não consegue ler o arquivo.
            del synthesizer
            del audio_config
            
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                # ATUALIZAÇÃO IMPORTANTE: Usar o self.after envia o comando para a Thread Principal.
                # Isso impede que os botões fiquem "congelados" e ignorem os cliques.
                self.after(0, self.on_conversion_success, os.path.basename(self.file_path), display_voice_name)
            else:
                self.after(0, self.update_status, f"Erro: {result.cancellation_details.reason}", "red")
                self.after(0, lambda: self.btn_convert.configure(state="normal"))
                
        except Exception as e:
            self.after(0, self.update_status, "Erro interno.", "red")
            self.after(0, lambda: self.btn_convert.configure(state="normal"))

    def on_conversion_success(self, filename, voice_name):
        """Atualiza a interface gráfica e salva no BD de forma 100% segura"""
        self.update_status("Status: Conversão Concluída!", "green")
        self.btn_play.configure(state="normal")
        self.btn_stop.configure(state="normal")
        self.btn_save.configure(state="normal")
        self.btn_convert.configure(state="normal")
        
        self.log_conversion_to_db(filename, voice_name)

    def extract_text(self):
        texto = ""
        if self.file_path.lower().endswith('.pdf'):
            reader = PyPDF2.PdfReader(self.file_path)
            for page in reader.pages: texto += (page.extract_text() or "") + " "
        else:
            with open(self.file_path, 'r', encoding='utf-8') as f: texto = f.read()
        return texto

    def update_status(self, msg, color):
        self.lbl_status.configure(text=msg, text_color=color)

    def play_audio(self):
        if not os.path.exists(self.temp_audio_path): 
            return

        self.stop_audio() 
        abs_path = os.path.abspath(self.temp_audio_path)
        
        # Tenta tocar invisível pelo sistema nativo (Plano A)
        err_open = ctypes.windll.winmm.mciSendStringW(f'open "{abs_path}" type mpegvideo alias app_audio', None, 0, None)
        err_play = ctypes.windll.winmm.mciSendStringW("play app_audio", None, 0, None)
        
        # Correção: Se NÃO abriu internamente (err_open) OU se abriu mas não tocou (err_play),
        # ele obrigatoriamente aciona o Plano B (Media Player / App Padrão do Windows)
        if err_open != 0 or err_play != 0:
            try:
                os.startfile(abs_path)
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível abrir o aplicativo de áudio do Windows.\n{str(e)}")

    def stop_audio(self):
        try:
            ctypes.windll.winmm.mciSendStringW("stop app_audio", None, 0, None)
            ctypes.windll.winmm.mciSendStringW("close app_audio", None, 0, None)
        except: pass

    def save_mp3(self):
        self.stop_audio() 
        save_path = filedialog.asksaveasfilename(defaultextension=".mp3", filetypes=[("Arquivo MP3", "*.mp3")], title="Salvar Áudio Como")
        if save_path:
            try:
                shutil.copy(self.temp_audio_path, save_path)
                messagebox.showinfo("Sucesso", "Arquivo salvo com sucesso!")
                
                if self.current_conversion_id:
                    conn = sqlite3.connect("voxreader.db")
                    cursor = conn.cursor()
                    cursor.execute("UPDATE Historico SET caminho_salvo = ? WHERE id = ?", (save_path, self.current_conversion_id))
                    conn.commit()
                    conn.close()
                    self.load_history()
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível salvar: {str(e)}")

if __name__ == "__main__":
    app = VoxReaderApp()
    app.mainloop()