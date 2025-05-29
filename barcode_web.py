# barcode_web.py
import streamlit.components.v1 as components

def escanear_codigo_web():
    # aqui vai todo o seu srcdoc com o QuaggaJS configurado
    srcdoc = r"""
    <div id="scanner-container" style="position:relative;width:100%;max-width:500px;margin:auto;">
      <video id="video" style="width:100%;"></video>
      <canvas id="overlay" style="position:absolute;top:0;left:0;width:100%;"></canvas>
    </div>
    <p id="output" style="text-align:center;font-weight:bold;">🔍 Aguardando leitura...</p>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/quagga/0.12.1/quagga.min.js"></script>
    <script>
      function startQuagga() {
        Quagga.init({
          inputStream: {
            name: "Live",
            type: "LiveStream",
            target: document.querySelector("#scanner-container"),
            constraints: { facingMode: "environment", width:640, height:480 }
          },
          decoder: { readers: ["ean_reader","code_128_reader","upc_reader"] },
          locate: true
        }, function(err) {
          if (err) {
            document.getElementById("output").innerText = "❗ Erro: " + err.message;
            return;
          }
          Quagga.start();
        });

        Quagga.onProcessed(function(result) {
          const ctx = document.getElementById('overlay').getContext('2d');
          ctx.clearRect(0,0,ctx.canvas.width,ctx.canvas.height);
          if (result && result.box) {
            ctx.strokeStyle = '#00F'; ctx.lineWidth = 2;
            ctx.beginPath();
            result.box.forEach((p,i) => i===0 ? ctx.moveTo(p.x,p.y) : ctx.lineTo(p.x,p.y));
            ctx.closePath(); ctx.stroke();
          }
        });

        Quagga.onDetected(function(data) {
          const code = data.codeResult.code;
          document.getElementById("output").innerText = "✅ " + code;
          Quagga.stop();
          // dispara de volta para o Streamlit via query param
          window.location.search = "?barcode=" + code;
        });
      }
      document.addEventListener("DOMContentLoaded", startQuagga);
    </script>
    """

    # agora injetamos o iframe com srcdoc executável
    iframe = f"""
    <iframe
      srcdoc="{srcdoc.replace('"','&quot;')}"
      style="border:none;"
      width="100%" height="600px"
      allow="camera; microphone; autoplay"
    ></iframe>
    """

    # e aqui sim renderizamos como HTML
    components.html(iframe, height=620, scrolling=False)
