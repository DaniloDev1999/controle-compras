import streamlit as st
import streamlit.components.v1 as components

def escanear_codigo_web():
    components.html("""
    <div id="reader" style="width: 100%"></div>
    <script src="https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js"></script>
    <script>
        const reader = new Html5Qrcode("reader");
        reader.start(
            { facingMode: "environment" },
            { fps: 10, qrbox: 250 },
            (decodedText, decodedResult) => {
                const streamlitInput = window.parent.document.querySelector('input[id^="barcode_web_input"]');
                if (streamlitInput) {
                    streamlitInput.value = decodedText;
                    streamlitInput.dispatchEvent(new Event('input', { bubbles: true }));
                    reader.stop();
                    document.getElementById("reader").innerHTML = "<b>✅ Código lido: </b>" + decodedText;
                }
            },
            errorMessage => {}
        );
    </script>
    """, height=400)
