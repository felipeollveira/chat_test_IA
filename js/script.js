const chatContainer = document.getElementById("chat");
    const input = document.getElementById("userInput");

    // Função para adicionar mensagem ao chat
    function appendMessage(text, sender) {
      const msgWrapper = document.createElement("div");
      msgWrapper.classList.add("message", sender);
      
      const textNode = document.createTextNode(text);
      msgWrapper.appendChild(textNode);

      chatContainer.appendChild(msgWrapper);
      chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    
    // Função para enviar a mensagem com a nova lógica de exibição
    async function sendMessage() {
      const userMessage = input.value.trim();
      if (!userMessage) return;

      appendMessage(userMessage, "user");
      input.value = "";
      input.focus();

      // Adiciona um feedback visual de que a IA está "digitando"
      const typingIndicator = document.createElement("div");
      typingIndicator.classList.add("message", "bia");
      typingIndicator.textContent = "Bia está digitando...";
      chatContainer.appendChild(typingIndicator);
      chatContainer.scrollTop = chatContainer.scrollHeight;

      try {
        const response = await fetch("https://26ab4bc6655f.ngrok-free.app/chat", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ message: userMessage }),
        });

        // Remove o indicador de "digitando"
        chatContainer.removeChild(typingIndicator);

        if (!response.ok) {
          appendMessage("Desculpe, não consegui me conectar. 😢", "bia");
          return;
        }

        const data = await response.json();
        const fullResponse = data.response;

        // --- INÍCIO DA NOVA LÓGICA ---

        // 1. Divide a resposta completa em frases, mantendo o ponto final.
        // A expressão regular /(?<=\.)\s*/ divide o texto APÓS cada ponto,
        // removendo espaços em branco que possam vir depois.
        const sentences = fullResponse.split(/(?<=\.)\s*/).filter(sentence => sentence.trim() !== "");

        // 2. Exibe cada frase como uma mensagem separada com um atraso.
        for (const sentence of sentences) {
          appendMessage(sentence.trim(), "bia");
          // Pausa por 800 milissegundos antes de mostrar a próxima mensagem
          await new Promise(resolve => setTimeout(resolve, 1000));
        }
        // --- FIM DA NOVA LÓGICA ---

      } catch (error) {
        // Remove o indicador de "digitando" em caso de erro também
        if (chatContainer.contains(typingIndicator)) {
            chatContainer.removeChild(typingIndicator);
        }
        appendMessage("Não foi possível conectar à Bia. Verifique se o servidor local está rodando.", "bia");
        console.error("Erro na requisição:", error);
      }
    }

    // Pressionar o botão também envia a mensagem
    document.getElementById("sendButton").addEventListener("click", sendMessage);

    