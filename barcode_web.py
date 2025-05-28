import streamlit.components.v1 as components
import streamlit as st

def escanear_codigo_web():
    st.markdown("### 📸 Posicione o código de barras na frente da câmera")

    components.html(
        """
        <div id="reader" width="100%"></div>
        <p id="result" style="font-weight: bold;"></p>
        <script src="https://unpkg.com/html5-qrcode" type="text/javascript"></script>
        <script>
            const html5QrCode = new Html5Qrcode("reader");

            function onScanSuccess(decodedText, decodedResult) {
                const streamlitInput = window.parent.document.querySelector('iframe').contentWindow.document.querySelectorAll("input[type='text']")[0];
                streamlitInput.value = decodedText;
                streamlitInput.dispatchEvent(new Event("input", { bubbles: true }));
                html5QrCode.stop();
            }

            Html5Qrcode.getCameras().then(devices => {
                if (devices && devices.length) {
                    html5QrCode.start(
                        { facingMode: "environment" },
                        {
                            fps: 10,
                            qrbox: 250,
                            formatsToSupport: [
                                Html5QrcodeSupportedFormats.CODE_128,
                                Html5QrcodeSupportedFormats.EAN_13,
                                Html5QrcodeSupportedFormats.EAN_8,
                                Html5QrcodeSupportedFormats.UPC_A,
                                Html5QrcodeSupportedFormats.UPC_E
                            ]
                        },
                        onScanSuccess
                    ).catch(err => {
                        document.getElementById("result").innerText = "Erro ao iniciar a câmera: " + err;
                    });
                }
            });
        </script>
        """,
        height=400
    )
