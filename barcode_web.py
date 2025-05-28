import streamlit.components.v1 as components
import streamlit as st

def escanear_codigo_web():
    components.html(
        """
        <video id="video" width="500" height="400" autoplay style="border: 2px solid #ccc; border-radius: 8px;"></video>
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
                const constraints = {
                    video: {
                        facingMode: { exact: "environment" },
                        width: { ideal: 1920 },
                        height: { ideal: 1080 }
                    }
                };

                const stream = await navigator.mediaDevices.getUserMedia(constraints);
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
                output.innerText = "❗ Erro ao acessar a câmera ou resolução não suportada: " + err;
            }
        }

        startScanner();
        </script>
        """,
        height=500
    )
