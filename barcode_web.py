# barcode_web.py
import streamlit.components.v1 as components

def escanear_codigo_web():
    components.html("""
    <video id="video" style="width:100%; height:auto;" autoplay muted></video>
    <p id="output" style="text-align:center;font-weight:bold;">🔍 Aguardando leitura...</p>
    <script>
      async function startScanner() {
        const video = document.getElementById('video');
        const output = document.getElementById('output');

        if (!('BarcodeDetector' in window)) {
          output.innerText = "❌ Seu navegador não suporta BarcodeDetector.";
          return;
        }

        const detector = new BarcodeDetector({
          formats: ['ean_13','ean_8','code_128','upc_a','upc_e']
        });

        // Aumenta resolução para 1280×720 (ou até 1920×1080)
        let stream;
        try {
          stream = await navigator.mediaDevices.getUserMedia({
            video: {
              facingMode: { exact: 'environment' },
              width:    { ideal: 1280, min: 640, max: 1920 },
              height:   { ideal:  720, min: 480, max: 1080 }
            }
          });
          video.srcObject = stream;
        } catch(err) {
          output.innerText = "❌ Erro ao acessar a câmera: " + err;
          return;
        }

        // Loop de escaneamento
        const scanLoop = async () => {
          try {
            const códigos = await detector.detect(video);
            if (códigos.length > 0) {
              const code = códigos[0].rawValue;
              output.innerText = "✅ Código detectado: " + code;
              // Preenche o primeiro input de texto na página Streamlit
              const parent = window.parent.document;
              const inputs = parent.querySelectorAll("input[type='text']");
              if (inputs.length > 0) {
                inputs[0].value = code;
                inputs[0].dispatchEvent(new Event("input", { bubbles: true }));
              }
              // Para o stream
              stream.getTracks().forEach(t => t.stop());
              return;
            }
          } catch(e) {
            output.innerText = "Erro na detecção: " + e;
          }
          requestAnimationFrame(scanLoop);
        };

        scanLoop();
      }

      document.addEventListener("DOMContentLoaded", startScanner);
    </script>
    """, height=500)
