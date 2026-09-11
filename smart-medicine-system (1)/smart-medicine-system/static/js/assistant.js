document.addEventListener('DOMContentLoaded', function () {
  const chatWindow = document.getElementById('chatWindow');
  const chatForm = document.getElementById('chatForm');
  const chatInput = document.getElementById('chatInput');
  const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

  function appendBubble(text, sender) {
    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble ' + sender;
    bubble.textContent = text;
    chatWindow.appendChild(bubble);
    chatWindow.scrollTop = chatWindow.scrollHeight;
  }

  function sendMessage(message) {
    if (!message.trim()) return;
    appendBubble(message, 'user');
    chatInput.value = '';

    const typingBubble = document.createElement('div');
    typingBubble.className = 'chat-bubble ai';
    typingBubble.textContent = '...';
    chatWindow.appendChild(typingBubble);
    chatWindow.scrollTop = chatWindow.scrollHeight;

    fetch('/assistant/query', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify({ message: message })
    })
      .then(res => res.json())
      .then(data => {
        typingBubble.remove();
        appendBubble(data.response, 'ai');
      })
      .catch(() => {
        typingBubble.remove();
        appendBubble('Sorry, something went wrong. Please try again.', 'ai');
      });
  }

  chatForm.addEventListener('submit', function (e) {
    e.preventDefault();
    sendMessage(chatInput.value);
  });

  document.querySelectorAll('.suggested-chip').forEach(chip => {
    chip.addEventListener('click', function () {
      sendMessage(this.getAttribute('data-question'));
    });
  });
});
