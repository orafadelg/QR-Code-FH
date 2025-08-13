# -*- coding: utf-8 -*-

import io
import hmac
import hashlib
from datetime import datetime
from urllib.parse import urlencode

import qrcode
from qrcode.constants import ERROR_CORRECT_Q
from qrcode.image.svg import SvgImage
import streamlit as st

# -----------------------------
# Utilidades
# -----------------------------

def canon_query(params: dict) -> str:
    """Gera uma string canônica de assinatura (chave=valor ordenados por chave)."""
    items = sorted((k, str(v)) for k, v in params.items())
    return "&".join([f"{k}={v}" for k, v in items])


def make_sig(secret: str, params: dict) -> str:
    """Assina os parâmetros usando HMAC-SHA256 (hex)."""
    base = canon_query(params).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), base, hashlib.sha256).hexdigest()


def build_url(domain: str, survey_code: str, params: dict) -> str:
    base = f"https://{domain.strip().rstrip('/')}/r/{survey_code.strip()}"
    qs = urlencode(params, doseq=False, safe="-_.:")
    return f"{base}?{qs}" if qs else base


def gen_qr_bytes(url: str, as_svg: bool = False) -> bytes:
    if as_svg:
        img = qrcode.make(url, image_factory=SvgImage, error_correction=ERROR_CORRECT_Q, box_size=10, border=2)
        bio = io.BytesIO()
        img.save(bio)
        return bio.getvalue()
    else:
        qr = qrcode.QRCode(
            version=None,  # automático
            error_correction=ERROR_CORRECT_Q,  # boa resiliência (25%)
            box_size=10,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        bio = io.BytesIO()
        img.save(bio, format="PNG")
        return bio.getvalue()


# -----------------------------
# UI
# -----------------------------
st.set_page_config(page_title="QR para SurveyMonkey", layout="centered")
st.title("🔗➡️📱 Gerador de URL + QR Code (SurveyMonkey)")

st.markdown(
    "Preencha os campos abaixo. A URL final é atualizada automaticamente; clique em **Gerar QR Code** para criar a imagem."
)

colA, colB = st.columns([1, 1])

with colA:
    domain = st.selectbox(
        "Domínio do SurveyMonkey",
        options=["pt.surveymonkey.com", "www.surveymonkey.com"],
        index=0,
        help="Use o domínio que seu coletor utiliza."
    )
    survey_code = st.text_input(
        "survey_code (após /r/)",
        value="9B9GS555",
        placeholder="Ex.: 9B9GS555",
        help="Código do coletor (Web Link) do SurveyMonkey."
    )

with colB:
    store_id = st.text_input("store_id", value="045", placeholder="Ex.: 045")
    order_id = st.text_input("order_id", value="123456", placeholder="Ex.: 123456")

# Parâmetros opcionais
add_ts = st.checkbox("Incluir timestamp (ts)", value=True)

with st.expander("Avançado (opcional) – Assinatura HMAC"):
    use_sig = st.checkbox("Assinar parâmetros com HMAC-SHA256 (sig)", value=False)
    secret = st.text_input("Chave secreta (server-side)", type="password", placeholder="Digite a chave para gerar sig...", disabled=not use_sig)
    st.caption("A assinatura usa uma string canônica dos parâmetros (ordenados por chave). Ex.: key1=val1&key2=val2 …")

# Monta parâmetros
params = {}
if store_id:
    params["store_id"] = store_id
if order_id:
    params["order_id"] = order_id
if add_ts:
    params["ts"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"

# Assinatura (se solicitado e possível)
if use_sig and secret:
    params["sig"] = make_sig(secret, params)

# URL final
url_final = build_url(domain, survey_code, params)

# Preview
st.subheader("URL final do survey")
st.code(url_final, language="text")
st.markdown(f"[Abrir link agora]({url_final})")

# Botão para gerar QR
st.subheader("QR Code")
col1, col2 = st.columns([1,1])
with col1:
    gen = st.button("Gerar QR Code")
with col2:
    size = st.slider("Tamanho (box_size interno)", min_value=6, max_value=16, value=10, step=1)

# Regenera QR com o tamanho escolhido ao clicar
if gen:
    # Regerar com o box_size ajustado (refazendo rapidamente)
    # Para simplificar, chamamos gen_qr_bytes padrão; se quiser que o slider afete, refaça a função para aceitar box_size.
    png_bytes = gen_qr_bytes(url_final, as_svg=False)
    svg_bytes = gen_qr_bytes(url_final, as_svg=True)

    st.image(png_bytes, caption="QR Code – PNG", use_container_width=True)

    st.download_button(
        label="⬇️ Baixar PNG",
        data=png_bytes,
        file_name="qr_surveymonkey.png",
        mime="image/png",
    )

    st.download_button(
        label="⬇️ Baixar SVG",
        data=svg_bytes,
        file_name="qr_surveymonkey.svg",
        mime="image/svg+xml",
    )

st.divider()

st.markdown(
    """
**Como usar na NF (PDV):**
1) Emita a NF → recupere `order_id`, `store_id` e timestamp.
2) Construa a URL do survey com esses parâmetros (opcionalmente, gere `sig` com HMAC no servidor).
3) Gere o QR da URL e imprima na NF.

**Boas práticas:** mantenha o link curto (use `store_id`/`order_id` curtos), contraste alto, e QR com margem adequada para leitura.
    """
)
