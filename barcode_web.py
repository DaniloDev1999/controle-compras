import streamlit.components.v1 as components

def escanear_codigo_web():
    components.html(
        """
        <div id="scanner-container" style="position:relative; width:100%; max-width:500px; margin:auto;">
          <video id="video" style="width:100%; border:1px solid #ccc; border-radius:8px;"></video>
          <canvas id="overlay" style="position:absolute; top:0; left:0; width:100%;"></canvas>
        </div>
        <p id="output" style="text-align:center; font-weight:bold;">🔍 Aguardando leitura do código...</p>

        <!-- QuaggaJS -->
        <script src="https://cdnjs.cloudflare.com/ajax/libs/quagga/0.12.1/quagga.min.js"></script>
        <script>
        function startQuagga() {
          Quagga.init({
            inputStream: {
              name: "Live",
              type: "LiveStream",
              target: document.querySelector('#video'),
              constraints: {
                facingMode: "environment",
                width: { exact: 1280 },
                height: { exact: 720 }
              }
            },
            decoder: {
              readers: ["ean_reader","ean_8_reader","code_128_reader","upc_reader","upc_e_reader"]
            },
            locate: true,
            numOfWorkers: navigator.hardwareConcurrency || 2
          }, function(err) {
            if (err) {
              document.getElementById("output").innerText = "❗ Erro ao iniciar Quagga: " + err;
              return;
            }
            Quagga.start();
          });

          Quagga.onProcessed(function(result) {
            var ctx = document.getElementById('overlay').getContext('2d');
            ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
            if (result && result.boxes) {
              result.boxes.filter(b => b !== result.box).forEach(box => {
                ctx.strokeStyle = 'rgba(255, 255, 255, .5)';
                ctx.lineWidth = 2;
                ctx.beginPath();
                box.forEach((p, i) => {
                  ctx[i===0 ? 'moveTo' : 'lineTo'](p.x, p.y);
                });
                ctx.closePath();
                ctx.stroke();
              });
            }
            if (result && result.box) {
              ctx.strokeStyle = '#00F';
              ctx.lineWidth = 2;
              ctx.beginPath();
              result.box.forEach((p, i) => {
                ctx[i===0 ? 'moveTo' : 'lineTo'](p.x, p.y);
              });
              ctx.closePath();
              ctx.stroke();
            }
          });

          Quagga.onDetected(function(data) {
            var code = data.codeResult.code;
            document.getElementById("output").innerText = "✅ Código detectado: " + code;
            Quagga.stop();
            // envia para o Streamlit via query string
            window.location.search = "?barcode=" + code;
          });
        }

        document.addEventListener("DOMContentLoaded", startQuagga);
        </script>
        """,
        height=600,
    )
