from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json

# Importa a lógica do outro arquivo
from main import RAGSystem, Chatbot, SYSTEM_INSTRUCTION, carregar_salas_de_apoio, detectar_interesse_sala_apoio

# --- INICIALIZAÇÃO ---
app = FastAPI()
rag_system = RAGSystem(pdf_folder_path="data")
salas_de_apoio = carregar_salas_de_apoio()
bia_bot = Chatbot(system_instruction=SYSTEM_INSTRUCTION)

# --- MIDDLEWARE (CORS) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MODELO DE DADOS ---
class ChatMessage(BaseModel):
    message: str

# --- ENDPOINT DE CHAT (COM STREAMING) ---
@app.post("/chat")
async def chat_endpoint(chat_message: ChatMessage):
    user_input = chat_message.message
    
    # Lógica híbrida para montar o prompt
    contexto_rag = rag_system.get_relevant_context(user_input)
    contexto_salas_apoio_str = ""
    if detectar_interesse_sala_apoio(user_input):
        contexto_salas_apoio_str = "\n\nContexto das Salas de Apoio (Sugira uma, se apropriado):\n---\n"
        for sala in salas_de_apoio:
            contexto_salas_apoio_str += f"- Nome: {sala['name']}, Descrição: {sala['description']}\n"
        contexto_salas_apoio_str += "---"

    prompt_final = f"""
    Contexto Relevante dos Documentos:
    ---
    {contexto_rag}
    ---
    {contexto_salas_apoio_str}

    Pergunta do Usuário: {user_input}
    """
    
    # Função geradora para o streaming
    async def stream_generator():
        response_stream = bia_bot.send_message(prompt_final)
        for chunk in response_stream:
            yield f"data: {json.dumps({'response': chunk})}\n\n"
    
    return StreamingResponse(stream_generator(), media_type="text/event-stream")

# Monta a pasta 'static' para servir o index.html
app.mount("/", StaticFiles(directory="static", html=True), name="static")