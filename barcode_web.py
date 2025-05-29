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
          output.innerText = "❌ BarcodeDetector não suportado neste navegador.";
          return;
        }

        const detector = new BarcodeDetector({
          formats: ['ean_13','ean_8','code_128','upc_a','upc_e']
        });

        try {
          const stream = await navigator.mediaDevices.getUserMedia({
            video: {
              facingMode: { exact: 'environment' },
              width:    { ideal: 1280, min: 640, max: 1920 },
              height:   { ideal:  720, min: 480, max: 1080 }
            }
          });
          video.srcObject = stream;
        } catch(err) {
          output.innerText = "❌ Erro ao acessar câmera: " + err;
          return;
        }

        const scanLoop = async () => {
          try {
            const codes = await detector.detect(video);
            if (codes.length > 0) {
              const code = codes[0].rawValue;
              output.innerText = "✅ Código detectado: " + code;
              // preenche o campo do Streamlit diretamente:
              const parent = window.parent.document;
              const input = parent.querySelector('input[placeholder="📦 Código de barras"]');
              if (input) {
                input.value = code;
                input.dispatchEvent(new Event('input', { bubbles: true }));
              }
              return;  // para de escanear
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
