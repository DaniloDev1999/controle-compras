# barcode_scanner.py
import cv2
from pyzbar.pyzbar import decode
import streamlit as st
from streamlit_webrtc import VideoTransformerBase, webrtc_streamer

class BarcodeScanner(VideoTransformerBase):
    def __init__(self):
        self.last_barcode = None

    def transform(self, frame):
        img = frame.to_ndarray(format="bgr24")
        for barcode in decode(img):
            self.last_barcode = barcode.data.decode("utf-8")
            x, y, w, h = barcode.rect
            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
        return img

def escanear_codigo_barras():
    ctx = webrtc_streamer(key="barcode", video_transformer_factory=BarcodeScanner)
    if ctx.video_transformer and ctx.video_transformer.last_barcode:
        return ctx.video_transformer.last_barcode
    return None
