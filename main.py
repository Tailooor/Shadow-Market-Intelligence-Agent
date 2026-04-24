import argparse
import logging
import sys

import gradio as gr

from app.ui import build_ui


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler("shadow_market.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Shadow-Market Intelligence Agent")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind the Gradio server")
    parser.add_argument("--port", type=int, default=7860, help="Port to bind the Gradio server")
    parser.add_argument("--share", action="store_true", help="Create a public Gradio share link")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()

    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    logger.info("Starting Shadow-Market Intelligence Agent on %s:%d", args.host, args.port)

    demo = build_ui()
    demo.queue().launch(
        server_name=args.host,
        server_port=args.port,
        share=args.share,
        theme=gr.themes.Soft(
            primary_hue="slate",
            secondary_hue="blue",
            neutral_hue="zinc",
        ),
        css="""
        .gradio-container { max-width: 1280px !important; }
        .hero {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 45%, #134e4a 100%);
            color: #f8fafc;
            border-radius: 20px;
            padding: 24px;
            margin-bottom: 18px;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08);
        }
        .hero h1 {
            margin: 0 0 6px 0;
            color: #f8fafc;
            font-weight: 800;
            letter-spacing: -0.02em;
        }
        .hero p {
            margin: 0;
            color: #dbeafe;
            font-weight: 500;
        }
        """,
    )


if __name__ == "__main__":
    main()
