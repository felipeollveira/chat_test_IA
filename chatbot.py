

from gen.config import API_KEY, MODEL_NAME
import google.generativeai as genai

class Chatbot:
    def __init__(self, system_instruction):
        try:
            genai.configure(api_key=API_KEY)
            
            model = genai.GenerativeModel(
                model_name=MODEL_NAME,
                system_instruction=system_instruction
            )
            
            self.chat = model.start_chat(history=[])
            #print("🤖 Bia iniciada com sucesso! Conexão com a API estabelecida.")
        
        except Exception as e:
            print(f"❌ Erro na inicialização do chatbot: {e}")
            self.chat = None

    def send_message(self, message):
        """
        Envia uma mensagem para o chat e retorna a resposta em streaming.
        O 'stream=True' é a chave para receber a resposta em pedaços.
        """
        if not self.chat:
            return iter(["❌ Chat não foi inicializado corretamente."])

        try:
            response = self.chat.send_message(message, stream=True)
            return response
        except Exception as e:
            return iter([f"❌ Erro ao enviar mensagem: {e}"])