import email.message
import smtplib
import threading
import firebase_admin
from firebase_admin import credentials, firestore
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen
from kivymd.app import MDApp
from kivymd.uix.button import MDFlatButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.snackbar import Snackbar

# Carregar credenciais do Firebase
cred = credentials.Certificate('credencial.json')  # Altere para o caminho do seu arquivo de credenciais
firebase_admin.initialize_app(cred)

# Inicializar Firestore
db = firestore.client()

# Variável global para armazenar o usuário logado
usuario_logado = None
usuarios = {}

# Definindo as classes de telas
class LoginScreen(Screen):
    pass

class CadastroScreen(Screen):
    pass

class MenuScreen(Screen):
    pass

class DoacaoScreen(Screen):
    pass

class MeAjudaScreen(Screen):
    pass

class EditarDadosScreen(Screen):
    pass


class MainApp(MDApp):
    def build(self):
        self.dialog = None
        self.title = "Ajuda-Click"
        return Builder.load_file('main.kv')

    def on_start(self):
        # Carregar usuários ao iniciar o aplicativo
        self.load_usuarios()

    def toggle_senha(self, instance, campo_senha):
        campo_senha.password = not campo_senha.password
        instance.icon = "eye" if not campo_senha.password else "eye-off"

    def load_usuarios(self):
        """Carregar usuários do Firestore"""
        global usuarios
        usuarios = {}
        usuarios_ref = db.collection('usuarios')
        docs = usuarios_ref.stream()
        for doc in docs:
            usuarios[doc.id] = doc.to_dict()

    def save_usuario_firestore(self, cpf, dados_usuario):
        """Salvar um usuário no Firestore usando CPF como ID"""
        db.collection('usuarios').document(cpf).set(dados_usuario)

    def realizar_login(self, cpf, senha):
        global usuario_logado
        if cpf in usuarios and usuarios[cpf]['senha'] == senha:
            usuario_logado = cpf
            self.root.current = 'menu'
        else:
            self.show_alert_dialog("Erro", "CPF ou senha incorretos")

    def validar_cpf(self, cpf: str) -> bool:
        """Validação de CPF."""
        cpf = ''.join([char for char in cpf if char.isdigit()])
        if len(cpf) != 11 or cpf == cpf[0] * 11:
            return False
        soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
        digito1 = 11 - (soma % 11)
        digito1 = digito1 if digito1 < 10 else 0
        soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
        digito2 = 11 - (soma % 11)
        digito2 = digito2 if digito2 < 10 else 0
        return cpf[-2:] == f"{digito1}{digito2}"

    def realizar_cadastro(self, cpf, nome, celular, endereco, email, senha):
        if cpf in usuarios:
            self.show_alert_dialog("Erro", "CPF já cadastrado")
            return
        if not self.validar_cpf(cpf):
            self.show_alert_dialog("Erro", "CPF inválido. Por favor, insira um CPF válido.")
            return
        # Novo usuário
        novo_usuario = {
            'nome': nome,
            'celular': celular,
            'endereco': endereco,
            'email': email,
            'senha': senha
        }
        # Salvar no Firestore usando o CPF como ID
        self.save_usuario_firestore(cpf, novo_usuario)
        # Atualizar localmente
        usuarios[cpf] = novo_usuario
        self.show_alert_dialog("Sucesso", "Cadastro realizado com sucesso")
        self.root.current = 'login'

    def acao_me_ajuda(self, descricao):
        self.enviar_email(descricao)
        self.show_alert_dialog("Sucesso", "E-mail enviado com sucesso")
        self.root.current = 'menu'

    def enviar_email(self, descricao):
        global usuario_logado
        usuario = usuarios.get(usuario_logado, {})
        usuario_detalhes = f"""
            <p><b>CPF:</b> {usuario_logado}</p>
            <p><b>Nome:</b> {usuario.get('nome', '')}</p>
            <p><b>E-mail:</b> {usuario.get('email', '')}</p>
            <p><b>Celular:</b> {usuario.get('celular', '')}</p>
            <p><b>Endereço:</b> {usuario.get('endereco', '')}</p>
        """

        def enviar():
            try:
                corpo_email = f"""
                <p><b>Descrição:</b> {descricao}</p>
                {usuario_detalhes}
                """
                msg = email.message.EmailMessage()
                msg['Subject'] = "Solicitação de Ajuda"
                msg['From'] = 'clickajuda10@gmail.com'
                msg['To'] = 'clickajuda10@gmail.com'
                password = 'oecxipyntabokmmy'
                msg.set_content(corpo_email, subtype='html')
                with smtplib.SMTP('smtp.gmail.com', 587) as server:
                    server.starttls()
                    server.login(msg['From'], password)
                    server.send_message(msg)
                print("E-mail enviado com sucesso")
            except Exception as e:
                print(f"Erro ao enviar e-mail: {e}")

        threading.Thread(target=enviar).start()

    def show_alert_dialog(self, title, message):
        if not self.dialog:
            self.dialog = MDDialog(
                title=title,
                text=message,
                buttons=[
                    MDFlatButton(
                        text="Fechar",
                        on_release=self.close_dialog
                    ),
                ],
            )
        self.dialog.open()

    def close_dialog(self, *args):
        if self.dialog:
            self.dialog.dismiss()
            self.dialog = None

    def preencher_dados_edicao(self):
        global usuario_logado
        if usuario_logado:
            usuario = usuarios[usuario_logado]
            editar_screen = self.root.get_screen('editar_dados')
            editar_screen.ids.cpf.text = usuario_logado  # CPF exibido
            editar_screen.ids.nome.text = usuario['nome']
            editar_screen.ids.celular.text = usuario['celular']
            editar_screen.ids.endereco.text = usuario['endereco']
            editar_screen.ids.email.text = usuario['email']
            editar_screen.ids.senha.text = usuario['senha']

    def salvar_dados_edicao(self, nome, celular, endereco, email, senha):
        """Salvar dados do usuário no Firestore"""
        global usuario_logado
        if usuario_logado:
            try:
                # Atualizar localmente
                usuarios[usuario_logado] = {
                    'nome': nome,
                    'celular': celular,
                    'endereco': endereco,
                    'email': email,
                    'senha': senha
                }
                # Atualizar no Firestore usando o CPF como ID
                self.save_usuario_firestore(usuario_logado, usuarios[usuario_logado])
                self.show_alert_dialog("Sucesso", "Dados atualizados com sucesso")
            except Exception as e:
                self.show_alert_dialog("Erro", f"Erro ao salvar dados: {e}")

    def logout(self):
        global usuario_logado
        usuario_logado = None
        self.root.current = 'login'

    def acao_doacao(self, descricao):
        self.enviar_email_doacao(descricao)
        self.show_alert_dialog("Sucesso", "E-mail enviado com sucesso")
        self.root.current = 'menu'

    def enviar_email_doacao(self, descricao):
        global usuario_logado
        usuario = usuarios.get(usuario_logado, {})
        usuario_detalhes = f"""
        <p><b>CPF:</b> {usuario_logado}</p>
        <p><b>Nome:</b> {usuario.get('nome', '')}</p>
        <p><b>E-mail:</b> {usuario.get('email', '')}</p>
        <p><b>Celular:</b> {usuario.get('celular', '')}</p>
        <p><b>Endereço:</b> {usuario.get('endereco', '')}</p>
        """

        def enviar():
            try:
                corpo_email = f"""
                <p><b>Descrição da Doação:</b> {descricao}</p>
                {usuario_detalhes}
                """
                msg = email.message.EmailMessage()
                msg['Subject'] = "Doação Recebida"
                msg['From'] = 'clickajuda10@gmail.com'
                msg['To'] = 'clickajuda10@gmail.com'
                password = 'oecxipyntabokmmy'
                msg.set_content(corpo_email, subtype='html')
                with smtplib.SMTP('smtp.gmail.com', 587) as server:
                    server.starttls()
                    server.login(msg['From'], password)
                    server.send_message(msg)
                print("E-mail enviado com sucesso")
            except Exception as e:
                print(f"Erro ao enviar e-mail: {e}")

        threading.Thread(target=enviar).start()

    def salvar_dados(self, cpf, nome, celular, endereco, email, senha):
        """Salvar dados do usuário no Firestore e atualizar localmente"""
        if not nome or not celular or not endereco or not email or not senha:
            self.mostrar_feedback("Todos os campos são obrigatórios.")
            return
        try:
            # Chamada para salvar no banco de dados
            self.save_usuario_firestore(cpf, {
                'nome': nome,
                'celular': celular,
                'endereco': endereco,
                'email': email,
                'senha': senha
            })
            usuarios[cpf] = {
                'nome': nome,
                'celular': celular,
                'endereco': endereco,
                'email': email,
                'senha': senha
            }
            self.mostrar_feedback("Dados salvos com sucesso!")
            self.root.current = 'menu'
        except Exception as e:
            self.mostrar_feedback(f"Erro ao salvar dados: {e}")

    def mostrar_feedback(self, mensagem):
        """Mostrar uma mensagem de feedback ao usuário usando Snackbar"""
        Snackbar(text=mensagem).open()


if __name__ == "__main__":
    MainApp().run()
