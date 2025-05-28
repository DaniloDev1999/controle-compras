import streamlit.components.v1 as components
import streamlit as st

def escanear_codigo_web():
    components.html(
        """
        <video id="video" width="400" height="300" autoplay></video>
        <p id="output">🔍 Aguardando leitura do código...</p>

        <script>
        async function startScanner() {
            const video = document.getElementById('video');
            const output = document.getElementById('output');

            if (!('BarcodeDetector' in window)) {
                output.innerText = "❌ BarcodeDetector não suportado nesse navegador.";
                return;
            }

            const detector = new BarcodeDetector({ formats: ['ean_13', 'ean_8', 'code_128', 'upc_a', 'upc_e'] });

            try {
                // AQUI AJUSTAMOS A RESOLUÇÃO
                const stream = await navigator.mediaDevices.getUserMedia({
                    video: {
                        facingMode: 'environment',
                        width: { ideal: 1280 },
                        height: { ideal: 720 }
                    }
                });

                video.srcObject = stream;

                const scanLoop = () => {
                    detector.detect(video)
                        .then(codes => {
                            if (codes.length > 0) {
                                const code = codes[0].rawValue;
                                output.innerText = "✅ Código detectado: " + code;
                                window.location.search = "?barcode=" + code;
                            } else {
                                requestAnimationFrame(scanLoop);
                            }
                        })
                        .catch(err => {
                            output.innerText = "Erro na detecção: " + err;
                        });
                };

                scanLoop();
            } catch (err) {
                output.innerText = "Erro ao acessar câmera: " + err;
            }
        }

        startScanner();
        </script>
        """,
        height=350
    )
