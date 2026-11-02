"""训练数据质检工具的 Web 入口。"""
import io
import os

import pandas as pd
from flask import Flask, jsonify, render_template, request, send_file

from inspector import clean, inspect

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

ENCODINGS = ("utf-8-sig", "gbk", "utf-8")


def _read_upload(file_storage):
    filename = file_storage.filename or ""
    if os.path.splitext(filename)[1].lower() != ".csv":
        raise ValueError("只支持 .csv 文件")

    raw = file_storage.read()
    if not raw:
        raise ValueError("文件是空的")

    last_error = None
    for encoding in ENCODINGS:
        try:
            return pd.read_csv(io.StringIO(raw.decode(encoding)))
        except (UnicodeDecodeError, pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
            last_error = exc

    raise ValueError(f"无法解析 CSV，请确认文件编码为 UTF-8 或 GBK（{last_error}）")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/inspect", methods=["POST"])
def api_inspect():
    file = request.files.get("file")
    if file is None:
        return jsonify({"error": "没有收到文件"}), 400
    try:
        return jsonify(inspect(_read_upload(file)))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/clean", methods=["POST"])
def api_clean():
    file = request.files.get("file")
    if file is None:
        return jsonify({"error": "没有收到文件"}), 400
    try:
        cleaned, _ = clean(_read_upload(file))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    buffer = io.BytesIO()
    cleaned.to_csv(buffer, index=False, encoding="utf-8-sig")
    buffer.seek(0)
    return send_file(
        buffer,
        mimetype="text/csv",
        as_attachment=True,
        download_name="cleaned.csv",
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=False)
