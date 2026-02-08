"""
AI Museum Guide MVP - Main Gradio Application

A smart museum guide system that recognizes artworks from photos
and provides audio narrations in professional or casual style.
"""

import asyncio
import io
import tempfile
from typing import Optional, Tuple
import gradio as gr
from PIL import Image

from config import config
from services.recognition import get_recognition_service
from services.narration import get_narration_service
from services.tts import get_tts_service


# Style mapping
STYLE_MAP = {
    "专业版": "professional",
    "趣解版": "casual"
}


async def process_image_async(
    image: Optional[Image.Image],
    style_cn: str
) -> Tuple[str, str, str, str, Optional[str]]:
    """
    Process uploaded image and return artwork information with audio.

    Args:
        image: PIL Image from user upload
        style_cn: Chinese style name ("专业版" or "趣解版")

    Returns:
        Tuple of (artwork_name, artist_info, hall_info, narration, audio_path)
    """
    if image is None:
        return ("", "", "", "请上传艺术品照片", None)

    style = STYLE_MAP.get(style_cn, "professional")

    # Get services
    recognition_service = get_recognition_service()
    narration_service = get_narration_service()
    tts_service = get_tts_service()

    # 1. Recognize artwork
    recognition_result = await recognition_service.recognize(image)

    if not recognition_result.get("success"):
        error_msg = recognition_result.get("error", "识别失败，请重试")
        return ("", "", "", error_msg, None)

    artwork = recognition_result.get("artwork", {})

    # 2. Extract artwork info
    artwork_name = artwork.get("name_cn", "Unknown")
    artist = artwork.get("artist", "Unknown")
    year = artwork.get("year", "")
    artist_info = f"{artist} / {year}" if year else artist

    # 3. Get hall info
    hall_info = ""
    if artwork.get("halls"):
        hall = artwork["halls"]
        hall_info = f"{hall.get('floor', '')}F - {hall.get('hall_name', '')}"
    elif recognition_result.get("source") in {"vlm", "kimi"}:
        hall_info = "展厅信息暂无（识别结果）"

    # 4. Generate narration
    narration_result = await narration_service.generate_narration(artwork, style)
    narration = ""
    if narration_result.get("success"):
        narration = narration_result.get("narration", "")
    else:
        narration = f"讲解生成失败: {narration_result.get('error', '')}"

    # 5. Generate audio
    audio_path = None
    if narration and artwork.get("id"):
        tts_result = await tts_service.synthesize(
            narration,
            artwork["id"],
            style
        )
        if tts_result.get("success"):
            audio_data = tts_result.get("audio_data")
            if audio_data:
                with tempfile.NamedTemporaryFile(
                    suffix=".wav", delete=False
                ) as f:
                    f.write(audio_data)
                    audio_path = f.name
            else:
                audio_url = tts_result.get("audio_url")
                if audio_url:
                    audio_path = audio_url
        else:
            error_detail = tts_result.get("error")
            if error_detail:
                narration = f"{narration}\n\n语音生成失败: {error_detail}"
    elif narration:
        # For VLM results without database ID, generate direct audio
        audio_data = await tts_service.synthesize_direct(narration, style)
        if audio_data:
            # Save to temporary file
            with tempfile.NamedTemporaryFile(
                suffix=".wav", delete=False
            ) as f:
                f.write(audio_data)
                audio_path = f.name

    return (artwork_name, artist_info, hall_info, narration, audio_path)


def process_image(
    image: Optional[Image.Image],
    style_cn: str
) -> Tuple[str, str, str, str, Optional[str]]:
    """Sync wrapper for async process_image_async."""
    return asyncio.run(process_image_async(image, style_cn))


def create_ui() -> gr.Blocks:
    """Create and configure the Gradio UI."""

    # Custom CSS for better styling
    custom_css = """
    .main-title {
        text-align: center;
        margin-bottom: 10px;
    }
    .subtitle {
        text-align: center;
        color: #666;
        margin-bottom: 20px;
    }
    .result-box {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 15px;
        margin: 5px 0;
    }
    """

    with gr.Blocks(
        title="AI 博物馆导览",
        css=custom_css,
        theme=gr.themes.Soft()
    ) as app:

        # Header
        gr.Markdown(
            "# AI 博物馆导览",
            elem_classes=["main-title"]
        )
        gr.Markdown(
            "拍摄或上传艺术品照片，即可获得智能讲解",
            elem_classes=["subtitle"]
        )

        with gr.Row():
            # Left column: Input
            with gr.Column(scale=1):
                image_input = gr.Image(
                    label="上传艺术品照片",
                    type="pil",
                    sources=["upload", "clipboard"],
                    height=300
                )

                style_radio = gr.Radio(
                    choices=["专业版", "趣解版"],
                    value="专业版",
                    label="选择讲解风格",
                    info="专业版：艺术史视角深度解读 | 趣解版：轻松有趣的第一人称讲述"
                )

                submit_btn = gr.Button(
                    "开始识别",
                    variant="primary",
                    size="lg"
                )

                # Tips
                gr.Markdown("""
                **使用提示：**
                - 支持直接拍照或上传图片
                - 建议正对艺术品拍摄，避免遮挡
                - 识别后可切换讲解风格
                """)

            # Right column: Output
            with gr.Column(scale=1):
                artwork_name = gr.Textbox(
                    label="艺术品名称",
                    interactive=False,
                    elem_classes=["result-box"]
                )

                artist_info = gr.Textbox(
                    label="作者 / 年代",
                    interactive=False,
                    elem_classes=["result-box"]
                )

                hall_info = gr.Textbox(
                    label="所在展厅",
                    interactive=False,
                    elem_classes=["result-box"]
                )

                narration_text = gr.Textbox(
                    label="讲解内容",
                    lines=8,
                    interactive=False,
                    elem_classes=["result-box"]
                )

                audio_output = gr.Audio(
                    label="语音讲解",
                    type="filepath",
                    interactive=False
                )

        # Event bindings
        submit_btn.click(
            fn=process_image,
            inputs=[image_input, style_radio],
            outputs=[
                artwork_name,
                artist_info,
                hall_info,
                narration_text,
                audio_output
            ]
        )

        # Also trigger on style change after image is uploaded
        style_radio.change(
            fn=process_image,
            inputs=[image_input, style_radio],
            outputs=[
                artwork_name,
                artist_info,
                hall_info,
                narration_text,
                audio_output
            ]
        )

        # Footer
        gr.Markdown("""
        ---
        **AI 博物馆导览 MVP** | Powered by ModelScope & Supabase

        *本应用使用 Qwen-VL 进行图像识别，Qwen 生成讲解文本，GLM-TTS 合成语音*
        """)

    return app


def main():
    """Main entry point."""
    # Validate configuration
    missing = config.validate()
    if missing:
        print(f"Warning: Missing configuration: {', '.join(missing)}")
        print("Some features may not work properly.")

    # Create and launch app
    app = create_ui()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False
    )


if __name__ == "__main__":
    main()
