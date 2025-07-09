from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

import os
import json
from chatbot import Chatbot
from pypdf import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS

# --- Configurações ---
PALAVRAS_PROIBIDAS = ["hitler", "nazismo", "morte"]
SALAS_DE_APOIO_PATH = "salas_de_apoio.json"
PDF_DATA_FOLDER = "data"
FAISS_INDEX_PATH = "faiss_index_bia"

# --- FastAPI Setup ---
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# --- Utilitários ---
def mensagem_inadequada(texto):
    return any(p in texto.lower() for p in PALAVRAS_PROIBIDAS)

def carregar_salas_de_apoio(path=SALAS_DE_APOIO_PATH):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("salasDeApoio", [])
    except Exception as e:
        print(f"Erro ao carregar Salas de Apoio: {e}")
        return []

def detectar_interesse_sala_apoio(user_input):
    gatilhos = [
        "nota", "prova", "matéria", "estudar", "aprendizado",
        "ansioso com a escola", "sozinho", "isolado", "sem amigos", "dificuldade",
        "ajuda", "apoio", "conselho"
    ]
    return any(g in user_input.lower() for g in gatilhos)

def selecionar_sala_relevante(user_input, salas_disponiveis):
    sugestoes = []
    user_input_lower = user_input.lower()
    for sala in salas_disponiveis:
        desc_lower = sala['description'].lower()
        if ("estudo" in desc_lower or "acadêmico" in desc_lower) and \
           ("estudar" in user_input_lower or "nota" in user_input_lower or "dificuldade" in user_input_lower):
            sugestoes.append(sala)
        elif ("social" in desc_lower or "amigos" in desc_lower) and \
             ("sozinho" in user_input_lower or "isolado" in user_input_lower or "sem amigos" in user_input_lower):
            sugestoes.append(sala)
        elif "ansiedade" in user_input_lower and "bem-estar" in desc_lower:
            sugestoes.append(sala)
        if len(sugestoes) >= 2:
            break
    return sugestoes or salas_disponiveis[:2]

# --- RAG System ---
class RAGSystem:
    def __init__(self, pdf_folder_path=PDF_DATA_FOLDER):
        print("Iniciando o sistema RAG...")
        self.embeddings_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.vector_store = self._load_or_create_vector_store(pdf_folder_path)
        print("Indexação/Carregamento concluído. Sistema RAG pronto.")

    def _load_or_create_vector_store(self, folder_path):
        if os.path.exists(FAISS_INDEX_PATH):
            print(f"Carregando índice FAISS de '{FAISS_INDEX_PATH}'...")
            return FAISS.load_local(FAISS_INDEX_PATH, self.embeddings_model, allow_dangerous_deserialization=True)
        else:
            print("Criando novo índice FAISS...")
            raw_text = self._load_pdfs_from_folder(folder_path)
            if not raw_text:
                print("AVISO: Nenhum texto encontrado nos PDFs.")
                return FAISS.from_texts([""], self.embeddings_model)
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            chunks = text_splitter.split_text(raw_text)
            vector_store = FAISS.from_texts(chunks, self.embeddings_model)
            vector_store.save_local(FAISS_INDEX_PATH)
            return vector_store

    def _load_pdfs_from_folder(self, folder_path):
        raw_text = ""
        for filename in os.listdir(folder_path):
            if filename.endswith(".pdf"):
                try:
                    reader = PdfReader(os.path.join(folder_path, filename))
                    for page in reader.pages:
                        raw_text += page.extract_text() or ""
                except Exception as e:
                    print(f"Erro ao ler '{filename}': {e}")
        return raw_text

    def get_relevant_context(self, query, k=3):
        results = self.vector_store.similarity_search(query, k=k)
        return "\n\n".join([doc.page_content for doc in results])

# --- Instrução de sistema da Bia ---
SYSTEM_INSTRUCTION = """
Sua missão é ser a "Bia", um ombro amigo digital que oferece um espaço seguro, acolhedor e, acima de tudo, humano. Você usa as informações fornecidas para dar respostas informadas e empáticas.

--- REGRAS DE PERSONALIDADE E CONVERSA ---

1.  **Aqueça a Conversa:** Se o usuário iniciar com uma saudação simples e curta (como "oi", "olá", "e aí"), responda de forma igualmente leve e amigável. Retribua o cumprimento e faça uma pergunta aberta e gentil, sem pular direto para "como você se sente?".
    * **Exemplo BOM para "Oii":** "Oii, tudo bem? Que bom te ver por aqui! 😊"
    * **Exemplo RUIM para "Oii":** "Entendi. Pode me contar mais sobre como você está se sentindo?"

2.  **Acompanhe o Ritmo do Usuário:** Espelhe o tom da conversa. Se o usuário for direto ao ponto sobre um problema, seja direta no apoio. Se ele for mais vago ou casual, mantenha a conversa leve até que ele demonstre que quer se aprofundar.

3.  **Evite Respostas Robóticas:** Nunca use frases de preenchimento que não façam sentido no contexto. Dizer "Entendi" para um "oi" é um exemplo claro do que NÃO fazer. Sua resposta deve ser sempre uma reação lógica e natural à mensagem anterior.

--- REGRAS DE FUNCIONALIDADE E CONTEXTO ---

4.  **Use o Contexto dos Documentos (RAG):** Para perguntas sobre bullying, saúde mental, direitos, etc., baseie sua resposta no "Contexto Relevante dos Documentos". Cite-o de forma natural ("Li em um de nossos guias que...").

5.  **Use o Contexto das Salas de Apoio:** Se o "Contexto das Salas de Apoio" for fornecido (porque o usuário mencionou estudos, solidão, etc.), use essa lista para sugerir GENTILMENTE UMA sala que pareça mais adequada. Não liste todas.

6.  **Seja Empática, Não Clínica:** Lembre-se sempre: você não é uma terapeuta. Acolha os sentimentos, mas NUNCA dê diagnósticos ou conselhos médicos. Sua função é ouvir e conectar.
"""

# --- Instância global ---
rag_system = RAGSystem()
salas_de_apoio = carregar_salas_de_apoio()
bia_bot = Chatbot(system_instruction=SYSTEM_INSTRUCTION)

class ChatInput(BaseModel):
    message: str

@app.post("/chat")
def chat(input: ChatInput):
    user_input = input.message.strip()

    if mensagem_inadequada(user_input):
        return {"response": "Esse assunto é muito delicado para eu tratar aqui. Converse com um adulto de confiança ou um profissional. 💙"}

    contexto_rag = rag_system.get_relevant_context(user_input)

    contexto_salas_apoio_str = ""
    if detectar_interesse_sala_apoio(user_input) and salas_de_apoio:
        salas_sugeridas = selecionar_sala_relevante(user_input, salas_de_apoio)
        if salas_sugeridas:
            contexto_salas_apoio_str = "\n\nContexto das Salas de Apoio Sugeridas:\n---\n"
            for sala in salas_sugeridas:
                contexto_salas_apoio_str += f"- Nome: {sala['name']} — {sala['description']}\n"
            contexto_salas_apoio_str += "---"

    prompt_final = f"""
Contexto Relevante dos Documentos:
---
{contexto_rag}
---
{contexto_salas_apoio_str}

Pergunta do Usuário: {user_input}
"""
    prompt_final = "\n".join([l.strip() for l in prompt_final.splitlines() if l.strip()])

    try:
        response_stream = bia_bot.send_message(prompt_final)
        full_response = "".join([chunk.text for chunk in response_stream])
        return {"response": full_response}
    except Exception as e:
        return {"response": f"Bia teve um problema ao responder: {e}"}
