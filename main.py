from app.ui import build_ui


if __name__ == "__main__":
    import gradio as gr

    demo = build_ui()
    demo.queue().launch(
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
