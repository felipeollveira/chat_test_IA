
    const chatContainer = document.getElementById("chat");
    const input = document.getElementById("userInput");
    const sendButton = document.getElementById("sendButton");

    function generateUUID() { // Public Domain/MIT
        var d = new Date().getTime();//Timestamp
        var d2 = ((typeof performance !== 'undefined') && performance.now && (performance.now()*1000)) || 0;//Time in microseconds since page-load or 0 if unsupported
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            var r = Math.random() * 16;//random number between 0 and 16
            if(d > 0){//Use timestamp until depleted
                r = (d + r)%16 | 0;
                d = Math.floor(d/16);
            } else {//Use microseconds since page-load if supported
                r = (d2 + r)%16 | 0;
                d2 = Math.floor(d2/16);
            }
            return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
        });
    }

    // Gera um ID único quando a página carrega e o armazena
    const conversationId = generateUUID();



    // Função para adicionar uma bolha de mensagem ao chat
    function appendMessage(text, sender) {
      const msgWrapper = document.createElement("div");
      msgWrapper.classList.add("message", sender);
      msgWrapper.textContent = text;
      chatContainer.appendChild(msgWrapper);
      chatContainer.scrollTop = chatContainer.scrollHeight;
      return msgWrapper;
    }

    // Função para enviar a mensagem com a nova lógica de exibição
    async function sendMessage() {
      const userMessage = input.value.trim();
      if (!userMessage) return;

      appendMessage(userMessage, "user");
      input.value = "";
      input.focus();
      sendButton.disabled = true;

      // Adiciona o indicador de digitação animado
      const typingIndicator = appendMessage("", "bia");

      typingIndicator.innerHTML = `
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
      `;
      chatContainer.scrollTop = chatContainer.scrollHeight;

      try {
        const response = await fetch("https://bia-ue6f.onrender.com/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ 
            message: userMessage,
           conversationId: conversationId 
           }),
        });

        if (!response.ok) {
          typingIndicator.textContent = "Desculpe, não consegui me conectar. 😢";
          sendButton.disabled = false;
          return;
        }

        // --- INÍCIO DA NOVA LÓGICA ---

        // 1. Acumula a resposta completa do stream em segundo plano
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullResponseText = "";
        
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          
          let buffer = "";
          buffer += decoder.decode(value, { stream: true });
          const events = buffer.split('\n\n');
          buffer = events.pop();

          for (const event of events) {
            if (event.startsWith("data: ")) {
              const jsonString = event.substring(6);
              try {
                const data = JSON.parse(jsonString);
                fullResponseText += data.response;
              } catch (e) {
                console.error("Erro no parse do JSON do stream:", jsonString, e);
              }
            }
          }
        }

        // 2. Remove o indicador de "digitando" agora que temos a resposta completa
        chatContainer.removeChild(typingIndicator);

        // 3. Divide a resposta em frases e exibe uma por uma
        const sentences = fullResponseText.split(/(?<=\.)\s*/).filter(sentence => sentence.trim() !== "");

        for (const sentence of sentences) {
          appendMessage(sentence.trim(), "bia");
          // Pausa por 1000 milissegundos (1 segundo) antes de mostrar a próxima mensagem
          await new Promise(resolve => setTimeout(resolve, 1000));
        }
        
        // --- FIM DA NOVA LÓGICA ---

      } catch (error) {
        if (chatContainer.contains(typingIndicator)) {
            chatContainer.removeChild(typingIndicator);
        }
        appendMessage("Ops, no momento estou offline.", "bia");
        console.error("Erro na requisição:", error);
      } finally {
        sendButton.disabled = false;
      }
    }

    // Event listeners para enviar a mensagem
    input.addEventListener("keypress", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        sendMessage();
      }
    });
    sendButton.addEventListener("click", sendMessage);
