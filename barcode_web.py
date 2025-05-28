import streamlit as st

def escanear_codigo_web():
    st.markdown("""
    <script src="https://unpkg.com/html5-qrcode"></script>
    <div id="reader" width="300px"></div>
    <script>
        function iniciarScanner() {
            const scanner = new Html5Qrcode("reader");
            scanner.start(
                { facingMode: "environment" },
                { fps: 10, qrbox: 250 },
                (decodedText, decodedResult) => {
                    const streamlitEvent = new Event("streamlit:barcode");
                    streamlitEvent.detail = decodedText;
                    document.dispatchEvent(streamlitEvent);
                    scanner.stop();
                },
                errorMessage => {
                    // console.log("Erro leitura:", errorMessage);
                }
            );
        }

        document.addEventListener("DOMContentLoaded", iniciarScanner);
    </script>
    """, unsafe_allow_html=True)

    # Capturar o valor do código
    barcode = st.experimental_get_query_params().get("barcode", [""])[0]
    return barcode if barcode else None
