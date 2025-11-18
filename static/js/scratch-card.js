// static/js/scratch-card.js

document.addEventListener('DOMContentLoaded', function() {
    const cards = document.querySelectorAll('.scratch-card');
    let cardRevealed = false;
    
    cards.forEach(card => {
        initScratchCard(card);
    });
    
    function initScratchCard(canvas) {
        const ctx = canvas.getContext('2d');
        const wrapper = canvas.parentElement;
        
        // Set canvas size
        canvas.width = wrapper.offsetWidth;
        canvas.height = wrapper.offsetHeight;
        
        // Draw scratch surface
        drawScratchSurface(ctx, canvas.width, canvas.height);
        
        let isScratching = false;
        let scratchedArea = 0;
        
        // Mouse events
        canvas.addEventListener('mousedown', startScratching);
        canvas.addEventListener('mousemove', scratch);
        canvas.addEventListener('mouseup', stopScratching);
        canvas.addEventListener('mouseleave', stopScratching);
        
        // Touch events
        canvas.addEventListener('touchstart', (e) => {
            e.preventDefault();
            startScratching(e);
        });
        canvas.addEventListener('touchmove', (e) => {
            e.preventDefault();
            scratch(e);
        });
        canvas.addEventListener('touchend', stopScratching);
        
        function startScratching(e) {
            if (cardRevealed) return;
            isScratching = true;
            canvas.style.cursor = 'crosshair';
        }
        
        function stopScratching() {
            isScratching = false;
            canvas.style.cursor = 'pointer';
        }
        
        function scratch(e) {
            if (!isScratching || cardRevealed) return;
            
            const rect = canvas.getBoundingClientRect();
            let x, y;
            
            if (e.type.includes('touch')) {
                x = e.touches[0].clientX - rect.left;
                y = e.touches[0].clientY - rect.top;
            } else {
                x = e.clientX - rect.left;
                y = e.clientY - rect.top;
            }
            
            // Scale coordinates for canvas resolution
            x = x * (canvas.width / rect.width);
            y = y * (canvas.height / rect.height);
            
            // Create scratch effect
            ctx.globalCompositeOperation = 'destination-out';
            ctx.beginPath();
            ctx.arc(x, y, 30, 0, Math.PI * 2);
            ctx.fill();
            
            // Check scratched percentage
            scratchedArea = calculateScratchedArea(ctx, canvas.width, canvas.height);
            
            if (scratchedArea > 30 && !cardRevealed) {
                revealCard();
            }
        }
    }
    
    function drawScratchSurface(ctx, width, height) {
        // Draw gradient background
        const gradient = ctx.createLinearGradient(0, 0, width, height);
        gradient.addColorStop(0, '#667eea');
        gradient.addColorStop(1, '#764ba2');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, width, height);
        
        // Add pattern
        ctx.fillStyle = 'rgba(255, 255, 255, 0.1)';
        for (let i = 0; i < width; i += 20) {
            for (let j = 0; j < height; j += 20) {
                if ((i + j) % 40 === 0) {
                    ctx.fillRect(i, j, 10, 10);
                }
            }
        }
        
        // Add text
        ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
        ctx.font = 'bold 24px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('Scratch Here!', width / 2, height / 2);
        
        // Add decorative elements
        ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
        ctx.font = '60px Arial';
        ctx.fillText('🎁', width / 2 - 40, height / 2 - 60);
        ctx.fillText('🎄', width / 2 + 40, height / 2 - 60);
    }
    
    function calculateScratchedArea(ctx, width, height) {
        const imageData = ctx.getImageData(0, 0, width, height);
        const pixels = imageData.data;
        let transparent = 0;
        
        for (let i = 3; i < pixels.length; i += 4) {
            if (pixels[i] === 0) {
                transparent++;
            }
        }
        
        return (transparent / (pixels.length / 4)) * 100;
    }
    
    function revealCard() {
        if (cardRevealed) return;
        cardRevealed = true;
        
        // Animate all cards away
        const cards = document.querySelectorAll('.scratch-card');
        cards.forEach((card, index) => {
            setTimeout(() => {
                card.style.transition = 'all 0.5s ease';
                card.style.opacity = '0';
                card.style.transform = 'scale(0)';
            }, index * 100);
        });
        
        // Show result modal after animation
        setTimeout(() => {
            showResultModal();
            completeReveal();
        }, 1000);
    }
    
    function showResultModal() {
        const modal = document.getElementById('resultModal');
        if (modal) {
            modal.classList.add('show');
            createConfetti();
        }
    }
    
    function completeReveal() {
        // Call backend to mark reveal as complete
        fetch('/api/complete-reveal', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        }).then(response => response.json())
          .then(data => {
              if (data.success) {
                  console.log('Reveal completed successfully');
              }
          }).catch(error => {
              console.error('Error completing reveal:', error);
          });
    }
    
    function createConfetti() {
        const colors = ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe'];
        const confettiCount = 100;
        
        for (let i = 0; i < confettiCount; i++) {
            setTimeout(() => {
                const confetti = document.createElement('div');
                confetti.className = 'confetti';
                confetti.style.left = Math.random() * 100 + '%';
                confetti.style.background = colors[Math.floor(Math.random() * colors.length)];
                confetti.style.animationDelay = Math.random() * 3 + 's';
                confetti.style.animationDuration = (Math.random() * 2 + 3) + 's';
                document.body.appendChild(confetti);
                
                setTimeout(() => confetti.remove(), 6000);
            }, i * 30);
        }
    }
});
