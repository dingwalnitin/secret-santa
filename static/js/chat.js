// static/js/chat.js
document.addEventListener('DOMContentLoaded', function() {
    // Ensure assignmentId is available from the template:
    // In the template: <script> const assignmentId = "{{ assignment.id }}"; </script>
    const socket = io();

    const chatForm = document.getElementById('chatForm');
    const messageInput = document.getElementById('messageInput');
    const chatMessages = document.getElementById('chatMessages');

    let connected = false;
    let joinedRoom = null;

    // Utility: add a message to chat UI
    function addMessageToChat(data, { optimistic = false } = {}) {
        if (!chatMessages) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${data.sender_type === 'gifter' ? 'message-sent' : 'message-received'}`;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        const textP = document.createElement('p');
        textP.textContent = data.message_text;

        const timeSpan = document.createElement('span');
        timeSpan.className = 'message-time';
        try {
            timeSpan.textContent = formatTime(data.timestamp || new Date().toISOString());
        } catch (e) {
            timeSpan.textContent = '';
        }

        contentDiv.appendChild(textP);
        contentDiv.appendChild(timeSpan);

        // If optimistic, add a subtle opacity and remove when actual server message arrives
        if (optimistic) {
            messageDiv.style.opacity = '0.6';
            messageDiv.dataset.optimistic = 'true';
        }

        messageDiv.appendChild(contentDiv);
        chatMessages.appendChild(messageDiv);
    }

    // Format timestamp nicely
    function formatTime(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
    }

    function scrollToBottom() {
        if (!chatMessages) return;
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function playNotificationSound() {
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();

            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);

            oscillator.frequency.value = 800;
            oscillator.type = 'sine';

            gainNode.gain.setValueAtTime(0.25, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.45);

            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.45);
        } catch (e) {
            // Ignore audio errors silently
            console.warn('Notification sound failed', e);
        }
    }

    // Socket connection handling
    socket.on('connect', function() {
        console.log('[socket] connected');
        connected = true;

        // Try to join the assignment room explicitly.
        // assignmentId should be injected by the template where chat page is rendered.
        if (typeof assignmentId !== 'undefined' && assignmentId) {
            socket.emit('join_chat', { assignment_id: assignmentId });
        } else {
            console.warn('assignmentId is not defined on the page');
        }
    });

    socket.on('connect_error', function(err) {
        console.error('[socket] connect_error', err);
    });

    socket.on('disconnect', function(reason) {
        console.log('[socket] disconnected', reason);
        connected = false;
        joinedRoom = null;
    });

    socket.on('join_ack', function(data) {
        if (data && data.success) {
            console.log('[socket] join_ack success', data.room);
            joinedRoom = data.room;
        } else {
            console.warn('[socket] join_ack failed', data && data.error);
        }
    });

    socket.on('error_message', function(data) {
        console.error('[socket] error_message', data);
        // Optionally show a flash notification in UI
        if (data && data.error) {
            showNotification(data.error, 'error');
        }
    });

    // Server sent new message (broadcast to room)
    socket.on('new_message', function(data) {
        // If an optimistic message exists at the bottom, remove it when we get confirmed server message
        // Simple heuristic: if last message is optimistic and text equals new message, remove optimistic
        try {
            const lastChild = chatMessages && chatMessages.lastElementChild;
            if (lastChild && lastChild.dataset && lastChild.dataset.optimistic === 'true') {
                const lastText = lastChild.querySelector('.message-content p')?.textContent;
                if (lastText && lastText.trim() === data.message_text.trim()) {
                    lastChild.remove();
                }
            }
        } catch (e) {
            // ignore matching errors
        }

        addMessageToChat(data);
        scrollToBottom();
        playNotificationSound();
    });

    // Typing indicator events from server (optional)
    socket.on('user_typing', function(data) {
        if (!data) return;
        if (data.typing) showTypingIndicator();
        else hideTypingIndicator();
    });

    // Form submit - send message
    if (chatForm) {
        chatForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const message = messageInput.value ? messageInput.value.trim() : '';

            if (!message) return;
            if (!connected) {
                showNotification('Not connected to chat server', 'warning');
                return;
            }
            if (!assignmentId) {
                showNotification('Missing assignment context', 'error');
                return;
            }

            // Optimistic UI
            const senderType = (chatMode === 'gifter') ? 'gifter' : 'giftee';


            scrollToBottom();

            // Emit to server with assignment_id
            socket.emit('send_message', { message: message, assignment_id: assignmentId });

            // Clear input
            messageInput.value = '';
            messageInput.focus();
        });
    }

    // Enter to send, Shift+Enter new line
    if (messageInput) {
        messageInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (chatForm) chatForm.dispatchEvent(new Event('submit', { cancelable: true }));
            }
        });

        // Typing indicator: emit typing start/stop
        let typingTimeout;
        messageInput.addEventListener('input', function() {
            if (!connected) return;
            socket.emit('typing', { typing: true, assignment_id: assignmentId });
            clearTimeout(typingTimeout);
            typingTimeout = setTimeout(() => {
                socket.emit('typing', { typing: false, assignment_id: assignmentId });
            }, 900);
        });
    }

    // Typing indicator helpers
    function showTypingIndicator() {
        if (!chatMessages) return;
        let indicator = document.getElementById('typingIndicator');
        if (indicator) return;
        indicator = document.createElement('div');
        indicator.id = 'typingIndicator';
        indicator.className = 'typing-indicator';
        indicator.innerHTML = `
            <div class="message message-received">
                <div class="message-content">
                    <div class="typing-dots">
                        <span></span><span></span><span></span>
                    </div>
                </div>
            </div>
        `;
        chatMessages.appendChild(indicator);
        scrollToBottom();
    }

    function hideTypingIndicator() {
        const indicator = document.getElementById('typingIndicator');
        if (indicator) indicator.remove();
    }

    // Small in-page notification (reuses main.js showNotification if present)
    function showNotification(msg, type = 'info') {
        if (typeof window.showNotification === 'function') {
            window.showNotification(msg, type);
            return;
        }
        // fallback simple alert
        console.log('[notification]', type, msg);
    }

    // Initial scroll to bottom
    setTimeout(scrollToBottom, 100);
});
