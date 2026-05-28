import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk
import PyPDF2
import edge_tts
import asyncio
import threading
import os
import shutil
import sqlite3
import subprocess
from datetime import datetime
import pygame

def setup_database():
    """Cria e atualiza o banco de dados preservando os perfis locais."""
    conn = sqlite3.connect("voxreader.db")
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Configuracoes (
            chave TEXT PRIMARY KEY,
            valor TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')
    
    try:
        cursor.execute("SELECT api_key FROM Usuarios LIMIT 1")
        cursor.execute("SELECT id, username, password, role FROM Usuarios")
        usuarios_antigos = cursor.fetchall()
        
        cursor.execute("DROP TABLE Usuarios")
        cursor.execute('''
            CREATE TABLE Usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL
            )
        ''')
        for user in usuarios_antigos:
            cursor.execute("INSERT INTO Usuarios (id, username, password, role) VALUES (?, ?, ?, ?)", user)
    except sqlite3.OperationalError:
        pass
    
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
        self.geometry("1000x680")
        
        # Variável de controle de tela cheia
        self.is_fullscreen = False
        
        # Configurar atalhos de tela cheia
        self.bind("<F11>", self.toggle_fullscreen)
        self.bind("<Escape>", self.exit_fullscreen)

        # Aparência do CustomTkinter
        ctk.set_appearance_mode("Dark")
        self.configure(fg_color="#121214")

        setup_database()

        try:
            pygame.mixer.init()
            self.pygame_available = True
        except Exception as e:
            self.pygame_available = False
            print(f"Erro ao carregar o mixer de áudio: {e}")

        self.current_user = None  
        self.file_path = None
        self.temp_audio_path = "temp_audio.mp3"
        
        self.voices = {
            "Francisca (Feminino - Neural)": "pt-BR-FranciscaNeural",
            "Antonio (Masculino - Neural)": "pt-BR-AntonioNeural",
            "Thalita (Feminino - Neural)": "pt-BR-ThalitaNeural",
            "Duarte (Masculino - Portugal)": "pt-PT-DuarteNeural",
            "Raquel (Feminino - Portugal)": "pt-PT-RaquelNeural",
        }
        self.current_conversion_id = None
        self.conversion_loading = False

        if not self.check_first_setup():
            self.show_first_setup_screen()
        else:
            self.show_login_screen()

    # ==========================================
    # CONTROLE DE TELA CHEIA
    # ==========================================
    def toggle_fullscreen(self, event=None):
        """Alterna o estado de tela cheia do aplicativo."""
        self.is_fullscreen = not self.is_fullscreen
        self.attributes("-fullscreen", self.is_fullscreen)
        return "break"

    def exit_fullscreen(self, event=None):
        """Força a saída do modo tela cheia ao pressionar Escape."""
        if self.is_fullscreen:
            self.is_fullscreen = False
            self.attributes("-fullscreen", False)
        return "break"

    # ==========================================
    # UTILITÁRIOS E ANIMAÇÕES DA INTERFACE
    # ==========================================
    def clear_window(self):
        self.stop_audio()
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_rowconfigure(0, weight=1)
        for widget in self.winfo_children():
            widget.destroy()

    def check_first_setup(self):
        conn = sqlite3.connect("voxreader.db")
        cursor = conn.cursor()
        cursor.execute("SELECT valor FROM Configuracoes WHERE chave='senha_mestre'")
        row = cursor.fetchone()
        conn.close()
        return row is not None

    def animate_loading(self, text_prefix, is_running_check):
        frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        def step(idx):
            if is_running_check():
                self.update_status(f"{text_prefix} {frames[idx % len(frames)]}", "#FBA94C")
                self.after(80, lambda: step(idx + 1))
        step(0)

    def animate_sidebar_open(self, target_width, current_width=0):
        """Anima a abertura do menu lateral aumentando a largura progressivamente."""
        if current_width < target_width:
            next_width = current_width + 15
            if next_width > target_width:
                next_width = target_width
            self.sidebar_frame.configure(width=next_width)
            self.after(10, lambda: self.animate_sidebar_open(target_width, next_width))

    def update_status(self, msg, color):
        self.lbl_status.configure(text=msg, text_color=color)

    # ==========================================
    # TELA DE SETUP DA SENHA MESTRE
    # ==========================================
    def show_first_setup_screen(self):
        self.clear_window()
        
        setup_container = ctk.CTkFrame(self, width=450, height=420, fg_color="#1A1A1E", corner_radius=16, border_width=1, border_color="#29292E")
        setup_container.place(relx=0.5, rely=0.5, anchor="center")
        
        ctk.CTkLabel(setup_container, text="Configuração Inicial", font=("Segoe UI", 26, "bold"), text_color="#00B37E").pack(pady=(45, 5))
        
        desc_text = "Como esta é a primeira inicialização do VoxReader,\npor favor defina uma Senha Mestre.\nEla protege a criação de novos perfis Administradores."
        ctk.CTkLabel(setup_container, text=desc_text, font=("Segoe UI", 12), text_color="#7C7C8A", justify="center").pack(pady=(0, 20))

        self.entry_master_pass = ctk.CTkEntry(
            setup_container, 
            placeholder_text="Defina a Senha Mestre", 
            show="*", 
            width=300, 
            height=45, 
            fg_color="#202024", 
            border_color="#29292E", 
            text_color="#FFFFFF",
            placeholder_text_color="#7C7C8A",
            corner_radius=8
        )
        self.entry_master_pass.pack(pady=15)

        btn_save = ctk.CTkButton(
            setup_container, 
            text="Salvar e Prosseguir", 
            width=300, 
            height=45, 
            fg_color="#00B37E", 
            hover_color="#129E74", 
            font=("Segoe UI", 14, "bold"),
            corner_radius=8,
            command=self.save_master_pass
        )
        btn_save.pack(pady=15)

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

        messagebox.showinfo("Sucesso", "Senha Mestre configurada com sucesso!")
        self.show_register_screen()

    # ==========================================
    # TELAS DE LOGIN & CADASTRO LOCAL
    # ==========================================
    def show_login_screen(self):
        self.clear_window()
        
        login_container = ctk.CTkFrame(self, width=420, height=480, fg_color="#1A1A1E", corner_radius=16, border_width=1, border_color="#29292E")
        login_container.place(relx=0.5, rely=0.5, anchor="center")
        
        ctk.CTkLabel(login_container, text="VoxReader", font=("Segoe UI", 32, "bold"), text_color="#00B37E").pack(pady=(40, 5))
        ctk.CTkLabel(login_container, text="Acesse seu painel local", font=("Segoe UI", 13), text_color="#7C7C8A").pack(pady=(0, 30))
        
        self.entry_login_user = ctk.CTkEntry(
            login_container, 
            placeholder_text="Nome de usuário", 
            width=300, 
            height=45, 
            fg_color="#202024", 
            border_color="#29292E", 
            text_color="#FFFFFF",
            placeholder_text_color="#7C7C8A",
            corner_radius=8
        )
        self.entry_login_user.pack(pady=10)

        self.entry_login_pass = ctk.CTkEntry(
            login_container, 
            placeholder_text="Senha", 
            show="*", 
            width=300, 
            height=45, 
            fg_color="#202024", 
            border_color="#29292E", 
            text_color="#FFFFFF",
            placeholder_text_color="#7C7C8A",
            corner_radius=8
        )
        self.entry_login_pass.pack(pady=10)

        btn_login = ctk.CTkButton(
            login_container, 
            text="Entrar no Painel", 
            width=300, 
            height=45, 
            fg_color="#00B37E", 
            hover_color="#129E74", 
            text_color="#FFFFFF",
            font=("Segoe UI", 14, "bold"),
            corner_radius=8,
            command=self.process_login
        )
        btn_login.pack(pady=(25, 10))

        btn_go_register = ctk.CTkButton(
            login_container, 
            text="Criar nova conta local", 
            width=300, 
            height=40, 
            fg_color="transparent", 
            hover_color="#202024", 
            text_color="#7C7C8A",
            font=("Segoe UI", 13),
            corner_radius=8,
            command=self.show_register_screen
        )
        btn_go_register.pack()

    def show_register_screen(self):
        self.clear_window()
        
        register_container = ctk.CTkFrame(self, width=420, height=520, fg_color="#1A1A1E", corner_radius=16, border_width=1, border_color="#29292E")
        register_container.place(relx=0.5, rely=0.5, anchor="center")
        
        ctk.CTkLabel(register_container, text="Novo Perfil Local", font=("Segoe UI", 28, "bold"), text_color="#00B37E").pack(pady=(30, 5))
        ctk.CTkLabel(register_container, text="Crie suas credenciais de acesso local", font=("Segoe UI", 12), text_color="#7C7C8A").pack(pady=(0, 20))
        
        self.reg_user = ctk.CTkEntry(
            register_container, 
            placeholder_text="Defina o Usuário", 
            width=300, 
            height=45, 
            fg_color="#202024", 
            border_color="#29292E", 
            text_color="#FFFFFF",
            placeholder_text_color="#7C7C8A",
            corner_radius=8
        )
        self.reg_user.pack(pady=8)

        self.reg_pass = ctk.CTkEntry(
            register_container, 
            placeholder_text="Defina a Senha", 
            show="*", 
            width=300, 
            height=45, 
            fg_color="#202024", 
            border_color="#29292E", 
            text_color="#FFFFFF",
            placeholder_text_color="#7C7C8A",
            corner_radius=8
        )
        self.reg_pass.pack(pady=8)

        self.role_frame = ctk.CTkFrame(register_container, fg_color="transparent")
        self.role_frame.pack(pady=8, fill="x", padx=60)
        
        ctk.CTkLabel(self.role_frame, text="Nível de Acesso:", font=("Segoe UI", 12), text_color="#7C7C8A").pack(side="left")
        
        self.reg_role = ctk.CTkComboBox(
            self.role_frame, 
            values=["Padrão", "Administrador"], 
            width=160, 
            height=35,
            fg_color="#202024",
            border_color="#29292E",
            button_color="#202024",
            button_hover_color="#29292E",
            corner_radius=8,
            command=self.toggle_master_pass
        )
        self.reg_role.set("Padrão")
        self.reg_role.pack(side="right")

        self.reg_master_pass = ctk.CTkEntry(
            register_container, 
            placeholder_text="Senha Mestre de Autorização", 
            show="*", 
            width=300, 
            height=45, 
            fg_color="#202024", 
            border_color="#FBA94C",
            text_color="#FFFFFF",
            placeholder_text_color="#7C7C8A",
            corner_radius=8
        )

        btn_save = ctk.CTkButton(
            register_container, 
            text="Criar Conta", 
            width=300, 
            height=45, 
            fg_color="#00B37E", 
            hover_color="#129E74", 
            text_color="#FFFFFF",
            font=("Segoe UI", 14, "bold"),
            corner_radius=8,
            command=self.process_register
        )
        btn_save.pack(pady=(25, 5))

        btn_back = ctk.CTkButton(
            register_container, 
            text="Voltar para Login", 
            width=300, 
            height=40, 
            fg_color="transparent", 
            hover_color="#202024", 
            text_color="#7C7C8A",
            font=("Segoe UI", 13),
            corner_radius=8,
            command=self.show_login_screen
        )
        btn_back.pack()

    def toggle_master_pass(self, choice):
        if choice == "Administrador":
            self.reg_master_pass.pack(pady=8, after=self.role_frame)
        else:
            self.reg_master_pass.pack_forget()

    def process_register(self):
        user = self.reg_user.get().strip()
        pwd = self.reg_pass.get().strip()
        role = self.reg_role.get()

        if not user or not pwd:
            messagebox.showwarning("Erro", "Preencha todos os campos!")
            return

        if role == "Administrador":
            master_input = self.reg_master_pass.get().strip()
            conn = sqlite3.connect("voxreader.db")
            cur = conn.cursor()
            cur.execute("SELECT valor FROM Configuracoes WHERE chave='senha_mestre'")
            real_master = cur.fetchone()[0]
            conn.close()

            if master_input != real_master:
                messagebox.showerror("Acesso Negado", "Senha Mestre incorreta!")
                return

        try:
            conn = sqlite3.connect("voxreader.db")
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Usuarios (username, password, role) VALUES (?, ?, ?)", (user, pwd, role))
            conn.commit()
            conn.close()
            messagebox.showinfo("Sucesso", "Perfil criado localmente! Faça o login.")
            self.show_login_screen()
        except sqlite3.IntegrityError:
            messagebox.showerror("Erro", "Esse nome de usuário já existe.")
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def process_login(self):
        user = self.entry_login_user.get().strip()
        pwd = self.entry_login_pass.get().strip()

        conn = sqlite3.connect("voxreader.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, role FROM Usuarios WHERE username=? AND password=?", (user, pwd))
        row = cursor.fetchone()
        conn.close()

        if row:
            self.current_user = {"id": row[0], "username": row[1], "role": row[2]}
            self.show_main_app()
        else:
            messagebox.showerror("Erro", "Usuário ou senha incorretos.")

    # ==========================================
    # PAINEL DASHBOARD (DENTRO DO APP)
    # ==========================================
    def show_main_app(self):
        self.clear_window()
        
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # ----------------------------------------------------
        # MENU LATERAL COM ANIMAÇÃO DE LARGURA
        # ----------------------------------------------------
        self.sidebar_frame = ctk.CTkFrame(self, width=0, fg_color="#1A1A1E", corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_propagate(False)
        
        # Iniciando a animação de abertura (de 0 a 240 pixels de largura)
        self.animate_sidebar_open(240)
        
        ctk.CTkLabel(self.sidebar_frame, text="VoxReader", font=("Segoe UI", 25, "bold"), text_color="#00B37E").pack(pady=(35, 2))
        ctk.CTkLabel(self.sidebar_frame, text="Neural TTS Suite", font=("Segoe UI", 11, "italic"), text_color="#7C7C8A").pack(pady=(0, 30))
        
        # Botões de Navegação com hover dinâmico
        self.btn_nav_conversor = ctk.CTkButton(
            self.sidebar_frame, 
            text="🎙️  Conversor", 
            font=("Segoe UI", 13, "bold"),
            height=42, 
            fg_color="transparent", 
            text_color="#7C7C8A", 
            hover_color="#252529",
            anchor="w",
            corner_radius=8,
            command=lambda: self.show_screen("conversor")
        )
        self.btn_nav_conversor.pack(fill="x", padx=15, pady=5)
        
        self.btn_nav_historico = ctk.CTkButton(
            self.sidebar_frame, 
            text="🕒  Histórico", 
            font=("Segoe UI", 13, "bold"),
            height=42, 
            fg_color="transparent", 
            text_color="#7C7C8A", 
            hover_color="#252529",
            anchor="w",
            corner_radius=8,
            command=lambda: self.show_screen("historico")
        )
        self.btn_nav_historico.pack(fill="x", padx=15, pady=5)
        
        self.btn_nav_instrucoes = ctk.CTkButton(
            self.sidebar_frame, 
            text="💡  Instruções", 
            font=("Segoe UI", 13, "bold"),
            height=42, 
            fg_color="transparent", 
            text_color="#7C7C8A", 
            hover_color="#252529",
            anchor="w",
            corner_radius=8,
            command=lambda: self.show_screen("instrucoes")
        )
        self.btn_nav_instrucoes.pack(fill="x", padx=15, pady=5)
        
        # Botão adicional para alternar tela cheia na interface
        self.btn_nav_fullscreen = ctk.CTkButton(
            self.sidebar_frame, 
            text="📺  Tela Cheia (F11)", 
            font=("Segoe UI", 13, "bold"),
            height=42, 
            fg_color="transparent", 
            text_color="#7C7C8A", 
            hover_color="#252529",
            anchor="w",
            corner_radius=8,
            command=self.toggle_fullscreen
        )
        self.btn_nav_fullscreen.pack(fill="x", padx=15, pady=5)
        
        spacer = ctk.CTkLabel(self.sidebar_frame, text="", height=1)
        spacer.pack(fill="y", expand=True)
        
        # Rodapé do Perfil de Usuário
        profile_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="#202024", corner_radius=12)
        profile_frame.pack(fill="x", padx=15, pady=20)
        
        username = self.current_user['username']
        if len(username) > 12:
            username = username[:10] + "..."
            
        role_label = "Admin" if self.current_user['role'] == "Administrador" else "User"
        
        user_info_frame = ctk.CTkFrame(profile_frame, fg_color="transparent")
        user_info_frame.pack(fill="x", padx=10, pady=(10, 5))
        ctk.CTkLabel(user_info_frame, text=f"👤 {username}", font=("Segoe UI", 12, "bold"), text_color="#FFFFFF", anchor="w").pack(side="left")
        ctk.CTkLabel(user_info_frame, text=role_label, font=("Segoe UI", 9, "bold"), text_color="#00B37E").pack(side="right", padx=5)
        
        ctk.CTkButton(
            profile_frame, 
            text="Sair do Painel", 
            height=28, 
            fg_color="#F25D27", 
            hover_color="#C24018", 
            text_color="#FFFFFF",
            font=("Segoe UI", 11, "bold"),
            corner_radius=8,
            command=self.logout
        ).pack(fill="x", padx=10, pady=(5, 10))

        # ----------------------------------------------------
        # ÁREA DE CONTEÚDO (PAINEL DINÂMICO)
        # ----------------------------------------------------
        self.content_frame = ctk.CTkFrame(self, fg_color="#121214", corner_radius=0)
        self.content_frame.grid(row=0, column=1, sticky="nsew")
        
        self.setup_conversor_screen()
        self.setup_historico_screen()
        self.setup_instrucoes_screen()
        
        self.show_screen("conversor")

    def show_screen(self, screen_name):
        self.btn_nav_conversor.configure(fg_color="transparent", text_color="#7C7C8A")
        self.btn_nav_historico.configure(fg_color="transparent", text_color="#7C7C8A")
        self.btn_nav_instrucoes.configure(fg_color="transparent", text_color="#7C7C8A")
        
        self.frame_conversor.pack_forget()
        self.frame_historico.pack_forget()
        self.frame_instrucoes.pack_forget()
        
        if screen_name == "conversor":
            self.btn_nav_conversor.configure(fg_color="#00B37E", text_color="#FFFFFF")
            self.frame_conversor.pack(fill="both", expand=True, padx=30, pady=30)
        elif screen_name == "historico":
            self.btn_nav_historico.configure(fg_color="#00B37E", text_color="#FFFFFF")
            self.frame_historico.pack(fill="both", expand=True, padx=30, pady=30)
            self.load_history()
        elif screen_name == "instrucoes":
            self.btn_nav_instrucoes.configure(fg_color="#00B37E", text_color="#FFFFFF")
            self.frame_instrucoes.pack(fill="both", expand=True, padx=30, pady=30)

    def logout(self):
        self.current_user = None
        self.stop_audio()
        self.show_login_screen()

    # ==========================================
    # DESIGN DA TELA DO CONVERSOR
    # ==========================================
    def setup_conversor_screen(self):
        self.frame_conversor = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        
        title_frame = ctk.CTkFrame(self.frame_conversor, fg_color="transparent")
        title_frame.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(title_frame, text="🎙️ Conversor de Áudio Neural", font=("Segoe UI", 24, "bold"), text_color="#FFFFFF", anchor="w").pack(side="left")
        
        # Card de Seleção de Arquivo com bordas destacadas
        card_file = ctk.CTkFrame(self.frame_conversor, fg_color="#1A1A1E", corner_radius=12, border_width=1, border_color="#29292E")
        card_file.pack(fill="x", pady=10)
        
        ctk.CTkLabel(card_file, text="Etapa 1: Selecionar o Arquivo de Origem", font=("Segoe UI", 14, "bold"), text_color="#00B37E").pack(anchor="w", padx=20, pady=(15, 5))
        
        file_action_frame = ctk.CTkFrame(card_file, fg_color="transparent")
        file_action_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        self.btn_select_file = ctk.CTkButton(
            file_action_frame, 
            text="Importar TXT / PDF", 
            font=("Segoe UI", 12, "bold"),
            fg_color="#202024",
            border_width=1,
            border_color="#29292E",
            hover_color="#2D2D33",
            text_color="#FFFFFF",
            width=160,
            height=38,
            corner_radius=8,
            command=self.select_file
        )
        self.btn_select_file.pack(side="left")
        
        self.lbl_file = ctk.CTkLabel(file_action_frame, text="Nenhum arquivo importado...", font=("Segoe UI", 12, "italic"), text_color="#7C7C8A")
        self.lbl_file.pack(side="left", padx=20)
        
        # Card de Seleção de Vozes
        card_voice = ctk.CTkFrame(self.frame_conversor, fg_color="#1A1A1E", corner_radius=12, border_width=1, border_color="#29292E")
        card_voice.pack(fill="x", pady=10)
        
        ctk.CTkLabel(card_voice, text="Etapa 2: Escolha de Voz Neural", font=("Segoe UI", 14, "bold"), text_color="#00B37E").pack(anchor="w", padx=20, pady=(15, 5))
        
        voice_action_frame = ctk.CTkFrame(card_voice, fg_color="transparent")
        voice_action_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        ctk.CTkLabel(voice_action_frame, text="Selecione o perfil de voz:", font=("Segoe UI", 12), text_color="#FFFFFF").pack(side="left")
        
        self.combo_voice = ctk.CTkComboBox(
            voice_action_frame, 
            values=list(self.voices.keys()), 
            width=320,
            height=38,
            fg_color="#202024",
            border_color="#29292E",
            button_color="#202024",
            button_hover_color="#2D2D33",
            corner_radius=8
        )
        self.combo_voice.pack(side="left", padx=20)
        
        # Painel de Progresso e Ação
        action_container = ctk.CTkFrame(self.frame_conversor, fg_color="transparent")
        action_container.pack(fill="x", pady=15)
        
        self.btn_convert = ctk.CTkButton(
            action_container, 
            text="✨ Iniciar Conversão Neural", 
            font=("Segoe UI", 14, "bold"),
            fg_color="#00B37E", 
            hover_color="#129E74", 
            text_color="#FFFFFF",
            height=45,
            corner_radius=8,
            command=self.start_conversion
        )
        self.btn_convert.pack(fill="x", pady=(0, 10))
        
        self.progress_bar = ctk.CTkProgressBar(action_container, height=6, progress_color="#00B37E", fg_color="#202024", corner_radius=3)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", pady=5)
        
        self.lbl_status = ctk.CTkLabel(action_container, text="Status: Pronto para converter", font=("Segoe UI", 12, "italic"), text_color="#7C7C8A")
        self.lbl_status.pack(pady=2)
        
        # Card do Reprodutor de Áudio
        card_player = ctk.CTkFrame(self.frame_conversor, fg_color="#1A1A1E", corner_radius=12, border_width=1, border_color="#29292E")
        card_player.pack(fill="x", pady=10)
        
        ctk.CTkLabel(card_player, text="Reprodutor Neural & Exportação", font=("Segoe UI", 14, "bold"), text_color="#00B37E").pack(anchor="w", padx=20, pady=(15, 5))
        
        player_control_frame = ctk.CTkFrame(card_player, fg_color="transparent")
        player_control_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        self.btn_play = ctk.CTkButton(
            player_control_frame, 
            text="▶ Ouvir Áudio", 
            font=("Segoe UI", 12, "bold"),
            fg_color="#202024",
            border_width=1,
            border_color="#29292E",
            hover_color="#2D2D33",
            text_color="#FFFFFF",
            width=130,
            height=38,
            corner_radius=8,
            state="disabled",
            command=self.play_audio
        )
        self.btn_play.pack(side="left", padx=(0, 10))
        
        self.btn_stop = ctk.CTkButton(
            player_control_frame, 
            text="■ Parar", 
            font=("Segoe UI", 12, "bold"),
            fg_color="#202024",
            border_width=1,
            border_color="#29292E",
            hover_color="#2D2D33",
            text_color="#FFFFFF",
            width=110,
            height=38,
            corner_radius=8,
            state="disabled",
            command=self.stop_audio
        )
        self.btn_stop.pack(side="left", padx=(0, 10))
        
        self.btn_save = ctk.CTkButton(
            player_control_frame, 
            text="💾 Exportar MP3 definitivo", 
            font=("Segoe UI", 12, "bold"),
            fg_color="#00B37E",
            hover_color="#129E74",
            text_color="#FFFFFF",
            height=38,
            corner_radius=8,
            state="disabled",
            command=self.save_mp3
        )
        self.btn_save.pack(side="right")

    # ==========================================
    # DESIGN DA TELA DE HISTÓRICO
    # ==========================================
    def setup_historico_screen(self):
        self.frame_historico = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        
        title_frame = ctk.CTkFrame(self.frame_historico, fg_color="transparent")
        title_frame.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(title_frame, text="🕒 Histórico de Conversão", font=("Segoe UI", 24, "bold"), text_color="#FFFFFF", anchor="w").pack(side="left")
        
        search_card = ctk.CTkFrame(self.frame_historico, fg_color="#1A1A1E", corner_radius=12, border_width=1, border_color="#29292E")
        search_card.pack(fill="x", pady=(0, 15))
        
        self.entry_search = ctk.CTkEntry(
            search_card, 
            placeholder_text="Buscar histórico por nome de arquivo...", 
            width=360, 
            height=38,
            fg_color="#202024",
            border_color="#29292E",
            text_color="#FFFFFF",
            placeholder_text_color="#7C7C8A",
            corner_radius=8
        )
        self.entry_search.pack(side="left", padx=15, pady=12)
        
        ctk.CTkButton(
            search_card, 
            text="Buscar", 
            font=("Segoe UI", 12, "bold"),
            fg_color="#00B37E",
            hover_color="#129E74",
            text_color="#FFFFFF",
            width=100,
            height=38,
            corner_radius=8,
            command=self.load_history
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            search_card, 
            text="Recarregar", 
            font=("Segoe UI", 12, "bold"),
            fg_color="#202024",
            border_width=1,
            border_color="#29292E",
            hover_color="#2D2D33",
            text_color="#FFFFFF",
            width=100,
            height=38,
            corner_radius=8,
            command=self.load_history
        ).pack(side="left", padx=5)

        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "Treeview", 
            background="#1A1A1E", 
            foreground="#E1E1E6", 
            fieldbackground="#1A1A1E", 
            rowheight=32,
            font=("Segoe UI", 11),
            bordercolor="#29292E",
            borderwidth=1
        )
        style.configure(
            "Treeview.Heading", 
            background="#202024", 
            foreground="#FFFFFF", 
            font=("Segoe UI", 11, "bold"),
            bordercolor="#29292E",
            borderwidth=1
        )
        style.map('Treeview', background=[('selected', '#00B37E')], foreground=[('selected', '#FFFFFF')])

        columns = ("ID", "Usuário", "Arquivo", "Voz", "Data", "Salvo?")
        
        tree_container = ctk.CTkFrame(self.frame_historico, fg_color="#1A1A1E", corner_radius=12, border_width=1, border_color="#29292E")
        tree_container.pack(fill="both", expand=True, pady=(0, 15))
        
        self.tree = ttk.Treeview(tree_container, columns=columns, show="headings")
        
        for col in columns:
            self.tree.heading(col, text=col)
            
        self.tree.column("ID", width=40, anchor="center")
        self.tree.column("Usuário", width=100, anchor="center")
        self.tree.column("Arquivo", width=240, anchor="w")
        self.tree.column("Voz", width=150, anchor="center")
        self.tree.column("Data", width=120, anchor="center")
        self.tree.column("Salvo?", width=70, anchor="center")

        scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side="right", fill="y", padx=(0, 2), pady=2)
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.btn_open_saved = ctk.CTkButton(
            self.frame_historico, 
            text="📂 Localizar Arquivo Exportado no Explorador de Arquivos", 
            font=("Segoe UI", 12, "bold"),
            fg_color="#00B37E",
            hover_color="#129E74",
            text_color="#FFFFFF",
            height=40,
            corner_radius=8,
            command=self.open_saved_location
        )
        self.btn_open_saved.pack(fill="x")

    # ==========================================
    # DESIGN DA TELA DE INSTRUÇÕES
    # ==========================================
    def setup_instrucoes_screen(self):
        self.frame_instrucoes = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        
        title_frame = ctk.CTkFrame(self.frame_instrucoes, fg_color="transparent")
        title_frame.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(title_frame, text="💡 Instruções & Detalhes do App", font=("Segoe UI", 24, "bold"), text_color="#FFFFFF", anchor="w").pack(side="left")
        
        text_card = ctk.CTkFrame(self.frame_instrucoes, fg_color="#1A1A1E", corner_radius=12, border_width=1, border_color="#29292E")
        text_card.pack(fill="both", expand=True)
        
        instrucoes = """COMO UTILIZAR O VOXREADER NEURAL:

1. IMPORTAÇÃO DE DOCUMENTOS:
   • Na aba Conversor, clique em 'Importar TXT / PDF' para carregar seus arquivos de texto locais (.txt ou .pdf). O aplicativo lerá e extrairá automaticamente todos os caracteres legíveis do seu documento.

2. SELEÇÃO DE VOZ:
   • Escolha um dos perfis de voz neural em português pré-carregados no menu suspenso. O aplicativo utiliza os motores de síntese neural gratuitos do Microsoft Edge, o que significa alta naturalidade e zero necessidade de chaves de API.

3. CONVERSÃO INTELIGENTE:
   • Clique no botão verde 'Iniciar Conversão Neural'. O sistema enviará o texto processado para síntese de voz na nuvem de alta fidelidade da Microsoft.
   • Uma barra de progresso animada indicará o andamento da operação.

4. REPRODUÇÃO E SALVAMENTO:
   • Terminada a síntese, os botões 'Ouvir' e 'Exportar' estarão desbloqueados.
   • É possível ouvir a prévia diretamente pelo aplicativo sem abrir tocadores externos.
   • Ao clicar em 'Exportar MP3 definitivo', escolha a pasta desejada no seu computador para guardar o arquivo.
   • O caminho salvo ficará registrado no seu histórico de usuário local, permitindo que você localize o arquivo com um único clique a qualquer momento através do botão 'Localizar Arquivo'.
   
=========================================
SISTEMA DE SEGURANÇA LOCAL:
• Os perfis de usuário são isolados localmente. Um usuário comum não tem acesso ao histórico de conversão de outros usuários.
• Perfis de nível 'Administrador' têm acesso completo a todos os registros de conversão realizados no aplicativo.
• A criação de novos administradores exige a Senha Mestre criada na primeira inicialização.
• Dica de Atalho: Pressione F11 a qualquer momento para entrar/sair do modo Tela Cheia."""

        textbox = ctk.CTkTextbox(text_card, fg_color="transparent", text_color="#E1E1E6", font=("Segoe UI", 12), wrap="word")
        textbox.pack(fill="both", expand=True, padx=20, pady=20)
        textbox.insert("0.0", instrucoes)
        textbox.configure(state="disabled")

    # ==========================================
    # LÓGICA DE NEGÓCIO E SÍNTESE ASSÍNCRONA
    # ==========================================
    def select_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("Textos e PDFs", "*.txt *.pdf")])
        if filepath:
            self.file_path = filepath
            self.lbl_file.configure(text=os.path.basename(filepath), text_color="#FFFFFF")

    def start_conversion(self):
        if not self.file_path: 
            return messagebox.showwarning("Aviso", "Selecione um arquivo!")
        selected_voice = self.combo_voice.get()
        if selected_voice not in self.voices: 
            return messagebox.showwarning("Aviso", "Selecione uma voz válida!")
        
        self.btn_convert.configure(state="disabled")
        self.current_conversion_id = None 
        
        self.progress_bar.configure(mode="indeterminate")
        self.progress_bar.start()
        
        self.conversion_loading = True
        self.animate_loading("Status: Convertendo... (Aguarde)", lambda: self.conversion_loading)
        
        voice_code = self.voices[selected_voice]
        threading.Thread(target=self.process_conversion, args=(voice_code, selected_voice), daemon=True).start()

    def process_conversion(self, voice_code, display_voice_name):
        try:
            texto = self.extract_text()
            if not texto.strip(): 
                self.conversion_loading = False
                self.after(0, self.stop_conversion_ui_elements, "Erro: Documento sem texto.", "#FF3333")
                return

            self.after(0, self.stop_audio)

            async def run_tts():
                communicate = edge_tts.Communicate(texto, voice_code)
                await communicate.save(self.temp_audio_path)
            
            asyncio.run(run_tts())
            
            self.conversion_loading = False
            self.after(0, self.on_conversion_success, os.path.basename(self.file_path), display_voice_name)
                
        except Exception as e:
            self.conversion_loading = False
            self.after(0, self.stop_conversion_ui_elements, f"Erro na conversão: {str(e)}", "#FF3333")

    def stop_conversion_ui_elements(self, msg, color):
        self.progress_bar.stop()
        self.progress_bar.set(0)
        self.update_status(msg, color)
        self.btn_convert.configure(state="normal")

    def on_conversion_success(self, filename, voice_name):
        self.progress_bar.stop()
        self.progress_bar.set(1.0)
        self.update_status("Status: Conversão Concluída!", "#00B37E")
        self.btn_play.configure(state="normal")
        self.btn_stop.configure(state="normal")
        self.btn_save.configure(state="normal")
        self.btn_convert.configure(state="normal")
        
        self.log_conversion_to_db(filename, voice_name)

    def extract_text(self):
        texto = ""
        if self.file_path.lower().endswith('.pdf'):
            reader = PyPDF2.PdfReader(self.file_path)
            for page in reader.pages: 
                texto += (page.extract_text() or "") + " "
        else:
            with open(self.file_path, 'r', encoding='utf-8') as f: 
                texto = f.read()
        return texto

    # ==========================================
    # SISTEMA DE ÁUDIO ROBUSTO (PYGAME MIXER)
    # ==========================================
    def play_audio(self):
        if not os.path.exists(self.temp_audio_path):
            messagebox.showerror("Erro", "Nenhum arquivo de áudio temporário encontrado.")
            return

        self.stop_audio()
        
        if self.pygame_available:
            try:
                pygame.mixer.music.load(self.temp_audio_path)
                pygame.mixer.music.play()
                self.update_status("Status: Tocando áudio...", "#00B37E")
            except Exception as e:
                try:
                    os.startfile(self.temp_audio_path)
                except:
                    messagebox.showerror("Erro", f"Falha ao reproduzir: {str(e)}")
        else:
            try:
                os.startfile(self.temp_audio_path)
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível abrir o arquivo de áudio.\n{str(e)}")

    def stop_audio(self):
        if self.pygame_available:
            try:
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
                self.update_status("Status: Áudio parado", "#7C7C8A")
            except:
                pass

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

    # ==========================================
    # GESTÃO DE HISTÓRICO LOCAL
    # ==========================================
    def log_conversion_to_db(self, filename, voice_name):
        try:
            agora = datetime.now().strftime("%d/%m/%Y %H:%M")
            conn = sqlite3.connect("voxreader.db")
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Historico (usuario_id, arquivo, voz, data_hora, caminho_salvo) VALUES (?, ?, ?, ?, NULL)",
                           (self.current_user["id"], filename, voice_name, agora))
            
            self.current_conversion_id = cursor.lastrowid
            
            conn.commit()
            conn.close()
            self.after(0, self.load_history)
        except Exception as e:
            print("Erro ao salvar histórico:", e)

    def load_history(self):
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
            foi_salvo = "Sim" if row[5] else "Não"
            display_row = (row[0], row[1], row[2], row[3], row[4], foi_salvo)
            self.tree.insert("", "end", values=display_row)
            
        conn.close()

    def open_saved_location(self):
        selected = self.tree.focus()
        if not selected:
            messagebox.showinfo("Aviso", "Selecione um registro na tabela primeiro!")
            return
        
        item_id = self.tree.item(selected)['values'][0]
        
        conn = sqlite3.connect("voxreader.db")
        cursor = conn.cursor()
        cursor.execute("SELECT caminho_salvo FROM Historico WHERE id=?", (item_id,))
        row = cursor.fetchone()
        conn.close()

        if row and row[0]:
            caminho = os.path.normpath(row[0])
            if os.path.exists(caminho):
                subprocess.Popen(f'explorer /select,"{caminho}"')
            else:
                messagebox.showerror("Erro", "O arquivo foi movido ou excluído do computador.")
        else:
            messagebox.showinfo("Aviso", "Este áudio nunca foi salvo no dispositivo.")


if __name__ == "__main__":
    app = VoxReaderApp()
    app.mainloop()