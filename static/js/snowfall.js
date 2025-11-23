function createSnowfall() {
    const snowfallContainer = document.getElementById('snowfall');
    if (!snowfallContainer) return;

    const snowflakeCount = 15;

    for (let i = 0; i < snowflakeCount; i++) {
        const snowflake = document.createElement('div');
        snowflake.className = 'snowflake';
        snowflake.style.left = Math.random() * window.innerWidth + 'px';
        snowflake.style.animationDuration = (Math.random() * 5 + 8) + 's';
        snowflake.style.animationDelay = Math.random() * 2 + 's';
        snowfallContainer.appendChild(snowflake);
    }
}

function updateChristmasConfetti() {
    const confettiScript = document.querySelector('script[src*="main.js"]');
    if (!confettiScript) return;

    const style = document.createElement('style');
    style.textContent = `
        .confetti.christmas {
            animation: christmasConfetti 3s ease-out forwards;
        }

        @keyframes christmasConfetti {
            0% {
                transform: translateY(0) translateX(0) rotateZ(0deg);
                opacity: 1;
            }
            100% {
                transform: translateY(100vh) translateX(100px) rotateZ(720deg);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);
}

document.addEventListener('DOMContentLoaded', function() {
    createSnowfall();
    updateChristmasConfetti();
});

window.addEventListener('resize', function() {
    const snowfallContainer = document.getElementById('snowfall');
    if (snowfallContainer && snowfallContainer.children.length === 0) {
        createSnowfall();
    }
});
