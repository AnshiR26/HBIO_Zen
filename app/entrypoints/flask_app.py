import os
import sys
import logging
import threading

if os.name != "nt":
    try:
        __import__("pysqlite3")
        sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
    except ModuleNotFoundError:
        pass

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from app.config.container import Container
from app.config.settings import IMAGE_DIR


def create_app():
    container = Container()
    app = Flask(__name__)
    CORS(app)

    if __name__ != "__main__":
        gunicorn_logger = logging.getLogger("gunicorn.error")
        app.logger.handlers = gunicorn_logger.handlers
        app.logger.setLevel(gunicorn_logger.level)
    else:
        logging.basicConfig(level=logging.INFO)
        app.logger.setLevel(logging.INFO)

    def process_webhook_async(parsed: dict) -> None:
        try:
            print("WEBHOOK DEBUG: async processing started", flush=True)

            container.handle_webhook_message_use_case.execute(
                conversation_id=parsed["conversation_id"],
                user_text=parsed["user_text"],
                authenticated=parsed.get("authenticated", False),
                user_email=parsed.get("user_email"),
                user_external_id=parsed.get("user_external_id"),
                user_id=parsed.get("user_id"),
            )

            print("WEBHOOK DEBUG: async reply sent to Zendesk", flush=True)
        except Exception as e:
            print("WEBHOOK ASYNC ERROR:", str(e), flush=True)

    @app.route("/", methods=["GET"])
    def root():
        """Lightweight probe endpoint for Azure App Service startup checks."""
        return jsonify({"status": "ok"}), 200

    @app.route("/health", methods=["GET"])
    def health():
        try:
            print("HEALTH DEBUG: /health route hit", flush=True)
            text_count = container.knowledge_store.get_text_count()
            image_count = container.knowledge_store.get_image_count()
            print(
                f"HEALTH DEBUG: documents={text_count}, images={image_count}",
                flush=True,
            )

            return jsonify(
                {
                    "status": "ok",
                    "documents_in_db": text_count,
                    "images_in_db": image_count,
                }
            ), 200
        except Exception as e:
            print("HEALTH ERROR:", str(e), flush=True)
            return jsonify(
                {
                    "status": "error",
                    "documents_in_db": 0,
                    "images_in_db": 0,
                    "error": str(e),
                }
            ), 200

    @app.route("/images/<path:filename>", methods=["GET"])
    def serve_image(filename):
        print("IMAGE DEBUG: requested file:", filename, flush=True)
        image_path = os.path.join(IMAGE_DIR, filename)
        if not os.path.exists(image_path):
            print("IMAGE DEBUG: file not found:", image_path, flush=True)
            return "Not Found", 404
        return send_file(image_path, mimetype="image/png")

    @app.route("/chat", methods=["POST"])
    def chat():
        print("CHAT DEBUG: /chat route hit", flush=True)

        try:
            data = request.get_json(silent=True) or {}
            print("CHAT DEBUG: payload received:", data, flush=True)

            question = (data.get("question") or "").strip()
            if not question:
                print("CHAT DEBUG: missing question", flush=True)
                return jsonify({"error": "Missing 'question' in request"}), 400

            result = container.answer_question_use_case.execute(question)
            print("CHAT DEBUG: answer generated", flush=True)
            print("CHAT DEBUG: images:", result.get("images", []), flush=True)

            return jsonify(
                {
                    "question": question,
                    "answer": result.get("answer", ""),
                    "images": result.get("images", []),
                }
            )
        except Exception as e:
            print("CHAT ERROR:", str(e), flush=True)
            return jsonify({"error": str(e)}), 500

    @app.route("/zendesk/webhook", methods=["POST"])
    def zendesk_webhook():
        print("WEBHOOK DEBUG: /zendesk/webhook route hit", flush=True)

        try:
            payload = request.get_json(force=True) or {}
            print("WEBHOOK DEBUG: payload received:", payload, flush=True)

            parsed = container.webhook_parser_service.parse(payload)
            print("WEBHOOK DEBUG: parsed:", parsed, flush=True)

            if not parsed["should_process"]:
                print(
                    "WEBHOOK DEBUG: ignored reason:", parsed["reason"], flush=True
                )
                return jsonify(
                    {
                        "status": "ignored",
                        "reason": parsed["reason"],
                    }
                ), 200

            worker = threading.Thread(
                target=process_webhook_async,
                args=(parsed,),
                daemon=True,
            )
            worker.start()

            print("WEBHOOK DEBUG: background worker started", flush=True)
            return jsonify({"status": "accepted"}), 200

        except Exception as e:
            print("WEBHOOK ERROR:", str(e), flush=True)
            return jsonify({"error": str(e)}), 500

    return app