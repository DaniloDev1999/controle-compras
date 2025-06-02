import streamlit.components.v1 as components
import streamlit as st

def escanear_codigo_web():
    components.html(
        """
        <video id="video" width="100%" height="300px" autoplay></video>
        <canvas id="overlay" style="position:absolute; top:0; left:0; width:100%; height:300px;"></canvas>
        <p id="output">🔍 Aguardando leitura do código...</p>
        
        <!-- Importa o QuaggaJS via CDN -->
        <script src="https://unpkg.com/quagga@0.12.1/dist/quagga.min.js"></script>
        <script>
        function startQuagga() {
            const videoElement = document.getElementById('video');
            const overlayCanvas = document.getElementById('overlay');
            const output = document.getElementById('output');
            
            // Ajusta largura/altura do canvas ao tamanho real do vídeo
            overlayCanvas.width = videoElement.clientWidth;
            overlayCanvas.height = videoElement.clientHeight;

            Quagga.init({
                inputStream: {
                    name: "Live",
                    type: "LiveStream",
                    target: videoElement,
                    constraints: {
                        facingMode: "environment",
                        width: { min: 640 },
                        height: { min: 480 },
                        aspectRatio: { min: 1, max: 100 }
                    }
                },
                locator: {
                    patchSize: "medium",
                    halfSample: true
                },
                decoder: {
                    readers: [
                        "ean_reader",      // EAN-13
                        "ean_8_reader",    // EAN-8
                        "upc_reader",      // UPC-A
                        "code_128_reader"  // Code-128
                    ]
                },
                locate: true,
                numOfWorkers: navigator.hardwareConcurrency || 4,
                frequency: 10
            }, function(err) {
                if (err) {
                    output.innerText = "❌ Erro ao iniciar leitor: " + err;
                    return;
                }
                Quagga.start();
            });

            Quagga.onProcessed(function(result) {
                const ctx = overlayCanvas.getContext('2d');
                ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
                if (result && result.box) {
                    ctx.strokeStyle = '#00F';
                    ctx.lineWidth = 2;
                    ctx.beginPath();
                    result.box.forEach((p, i) => i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y));
                    ctx.closePath();
                    ctx.stroke();
                }
            });

            Quagga.onDetected(function(data) {
                const code = data.codeResult.code;
                output.innerText = "✅ Detectado: " + code;

                // Copia para a área de transferência
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    navigator.clipboard.writeText(code).then(function() {
                        console.log("Código copiado para a área de transferência:", code);
                    }).catch(function(err) {
                        console.warn("Não foi possível copiar: ", err);
                    });
                }

                // Para o Quagga e redireciona para forçar o Streamlit a ler o parâmetro ?barcode=
                Quagga.stop();
                window.location.search = "?barcode=" + code;
            });
        }

        document.addEventListener("DOMContentLoaded", startQuagga);
        </script>
        """,
        height=350
    )
