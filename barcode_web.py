import streamlit.components.v1 as components

def escanear_codigo_web():
    components.html(
        """
        <div id="reader" style="width: 100%;"></div>
        <p id="result" style="font-weight:bold; color: green;"></p>

        <script src="https://unpkg.com/html5-qrcode" type="text/javascript"></script>
        <script>
            const html5QrCode = new Html5Qrcode("reader");

            function onScanSuccess(decodedText, decodedResult) {
                // mostra no HTML
                document.getElementById("result").innerText = "📦 Código escaneado: " + decodedText;

                // atualiza a URL com o código escaneado
                const url = new URL(window.parent.location);
                url.searchParams.set("barcode", decodedText);
                window.parent.location.href = url.toString();

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
                                Html5QrcodeSupportedFormats.EAN_13,
                                Html5QrcodeSupportedFormats.CODE_128,
                                Html5QrcodeSupportedFormats.EAN_8,
                                Html5QrcodeSupportedFormats.UPC_A,
                                Html5QrcodeSupportedFormats.UPC_E
                            ]
                        },
                        onScanSuccess
                    ).catch(err => {
                        document.getElementById("result").innerText = "Erro ao iniciar a câmera: " + err;
                    });
                } else {
                    document.getElementById("result").innerText = "Nenhuma câmera encontrada.";
                }
            }).catch(err => {
                document.getElementById("result").innerText = "Erro ao acessar a câmera: " + err;
            });
        </script>
        """,
        height=420
    )
