// static/js/spin-wheel.js
document.addEventListener('DOMContentLoaded', function() {
    const canvas = document.getElementById('wheelCanvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const spinButton = document.getElementById('spinButton');

    // Wheel configuration
    const segments = 8;
    const segmentAngle = (Math.PI * 2) / segments;
    const colors = [
        '#667eea', '#764ba2', '#f093fb', '#f5576c',
        '#4facfe', '#00f2fe', '#43e97b', '#38f9d7'
    ];

    let currentAngle = 0;
    let spinning = false;
    let spinAngleStart = 0;
    let spinTime = 0;
    let spinTimeTotal = 0;

    drawWheel(); // initial draw with placeholders
    createPointer();

    spinButton.addEventListener('click', function() {
        if (!spinning) {
            spin();
        }
    });

    function drawWheel() {
        const centerX = canvas.width / 2;
        const centerY = canvas.height / 2;
        const radius = Math.min(centerX, centerY) - 10;

        ctx.clearRect(0, 0, canvas.width, canvas.height);

        for (let i = 0; i < segments; i++) {
            const angle = i * segmentAngle;
            ctx.beginPath();
            ctx.moveTo(centerX, centerY);
            ctx.arc(centerX, centerY, radius, angle, angle + segmentAngle);
            ctx.closePath();
            ctx.fillStyle = colors[i % colors.length];
            ctx.fill();
            ctx.strokeStyle = '#fff';
            ctx.lineWidth = 3;
            ctx.stroke();

            // Draw placeholder text (hidden style)
            ctx.save();
            ctx.translate(centerX, centerY);
            ctx.rotate(angle + segmentAngle / 2);
            ctx.textAlign = 'center';
            ctx.fillStyle = 'rgba(255,255,255,0.9)';
            ctx.font = 'bold 18px Arial';
            // Show placeholder (e.g. "???") while spinning/not revealed
            ctx.fillText('???', radius / 2, 10);
            ctx.restore();
        }

        // center circle
        ctx.beginPath();
        ctx.arc(centerX, centerY, 30, 0, Math.PI * 2);
        ctx.fillStyle = '#fff';
        ctx.fill();
        ctx.strokeStyle = '#667eea';
        ctx.lineWidth = 5;
        ctx.stroke();
    }

    function createPointer() {
        const container = canvas.parentElement;
        const pointer = document.createElement('div');
        pointer.className = 'wheel-pointer';
        pointer.style.position = 'absolute';
        pointer.style.top = '0';
        pointer.style.left = '50%';
        pointer.style.transform = 'translateX(-50%)';
        pointer.style.width = '0';
        pointer.style.height = '0';
        pointer.style.borderLeft = '20px solid transparent';
        pointer.style.borderRight = '20px solid transparent';
        pointer.style.borderTop = '40px solid #ef4444';
        pointer.style.filter = 'drop-shadow(0 5px 10px rgba(0, 0, 0, 0.3))';
        pointer.style.zIndex = '10';

        container.style.position = 'relative';
        container.insertBefore(pointer, canvas);
    }

    function spin() {
        spinning = true;
        spinButton.disabled = true;
        spinButton.textContent = 'Spinning...';

        spinTimeTotal = Math.random() * 2000 + 3000; // 3-5s
        spinAngleStart = Math.random() * 10 + 10; // initial speed in degrees
        spinTime = 0;

        requestAnimationFrame(rotateWheel);
    }

    function rotateWheel(timestamp) {
        // Use a simple time-step approach
        spinTime += 30;

        if (spinTime >= spinTimeTotal) {
            stopRotateWheel();
            return;
        }

        const spinAngle = spinAngleStart - easeOut(spinTime, 0, spinAngleStart, spinTimeTotal);
        currentAngle += (spinAngle * Math.PI) / 180;

        // draw rotated wheel
        ctx.save();
        ctx.translate(canvas.width / 2, canvas.height / 2);
        ctx.rotate(currentAngle);
        ctx.translate(-canvas.width / 2, -canvas.height / 2);
        drawWheel(); // draw placeholders (rotated)
        ctx.restore();

        requestAnimationFrame(rotateWheel);
    }

    function stopRotateWheel() {
        spinning = false;

        // small bounce effect then reveal
        let bounces = 6;
        let bounceAngle = 0.15;

        function bounce() {
            if (bounces <= 0) {
                revealWinner();
                return;
            }

            currentAngle += bounceAngle;
            bounceAngle *= -0.5;
            bounces--;

            ctx.save();
            ctx.translate(canvas.width / 2, canvas.height / 2);
            ctx.rotate(currentAngle);
            ctx.translate(-canvas.width / 2, -canvas.height / 2);
            drawWheel();
            ctx.restore();

            setTimeout(bounce, 80);
        }

        bounce();
    }

    function easeOut(t, b, c, d) {
        const ts = (t /= d) * t;
        const tc = ts * t;
        return b + c * (tc + -3 * ts + 3 * t);
    }

    function revealWinner() {
        // compute selected segment
        // wheel rotation: currentAngle radians, pointer at top (angle 0). Convert to segment index.
        const normalizedAngle = (currentAngle % (Math.PI * 2) + (Math.PI * 2)) % (Math.PI * 2);
        // pointer points to top (angle = 0). The segment at (2π - normalizedAngle) is at pointer.
        const pointerAngle = (Math.PI * 2 - normalizedAngle + (segmentAngle / 2));
        const selectedIndex = Math.floor(pointerAngle / segmentAngle) % segments;

        // redraw wheel and draw actual name on selected segment
        ctx.save();
        ctx.translate(canvas.width / 2, canvas.height / 2);
        ctx.rotate(currentAngle);
        ctx.translate(-canvas.width / 2, -canvas.height / 2);
        drawWheel(); // placeholders
        // draw name on selected segment
        drawNameOnSegment(selectedIndex, gifteeName);
        ctx.restore();

        // show result modal and mark reveal
        const modal = document.getElementById('resultModal');
        if (modal) {
            // set the name in modal
            const el = modal.querySelector('#gifteeName');
            if (el) el.textContent = gifteeName;
            modal.classList.add('show');
            createConfetti();
            completeReveal();
        }

        spinButton.disabled = false;
        spinButton.textContent = '🎲 SPIN THE WHEEL';
    }

    function drawNameOnSegment(index, name) {
        const centerX = canvas.width / 2;
        const centerY = canvas.height / 2;
        const radius = Math.min(centerX, centerY) - 10;
        const angle = index * segmentAngle;

        // draw text rotated to segment center (but inverse rotate so it appears upright)
        ctx.save();
        ctx.translate(centerX, centerY);
        ctx.rotate(angle + segmentAngle / 2);
        ctx.textAlign = 'center';
        ctx.fillStyle = '#fff';
        ctx.font = 'bold 20px Arial';
        // draw name slightly closer to edge
        ctx.fillText(name, radius / 2, 10);
        ctx.restore();
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
        const confettiCount = 80;

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
            }, i * 20);
        }
    }
});
