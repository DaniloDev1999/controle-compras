import streamlit.components.v1 as components
import streamlit as st

def escanear_codigo_web():
    # Contêiner para o valor lido
    codigo_lido = st.empty()

    # Código HTML + JS para o leitor
    components.html(
        """
        <div id="reader" width="300px"></div>
        <p id="result"></p>
        <script src="https://unpkg.com/html5-qrcode" type="text/javascript"></script>
        <script>
        const html5QrCode = new Html5Qrcode("reader");

        function onScanSuccess(decodedText, decodedResult) {
            document.getElementById("result").innerText = decodedText;
            const streamlitEvent = new Event("input", { bubbles: true });
            const streamlitInput = window.parent.document.querySelector('iframe').contentWindow.document.querySelectorAll("input[type='text']")[0];
            streamlitInput.value = decodedText;
            streamlitInput.dispatchEvent(streamlitEvent);
            html5QrCode.stop();
        }

        html5QrCode.start(
            { facingMode: "environment" },  // câmera traseira
            {
                fps: 10,
                qrbox: 250
            },
            onScanSuccess
        ).catch(err => {
            document.getElementById("result").innerText = "Erro ao acessar a câmera: " + err;
        });
        </script>
        """,
        height=400
    )
