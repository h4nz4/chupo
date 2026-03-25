![Chupo](./logo.png)
# chupo

**chupo** is a high-performance CLI utility designed to upload images directly to a [Chevereto](https://chevereto.com/) instance. It streamlines the image sharing workflow, utilizing the [Chevereto API V1 file upload](https://v4-docs.chevereto.com/api/1/file-upload.html) endpoint for fast and reliable uploads.

[![Python >=3.13](https://img.shields.io/badge/python-3.13%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## ✨ Features

-   ⚡ **High Performance**: Built with modern Python for fast execution.
-   🛠️ **CLI-First**: Designed for speed and terminal integration using [Typer](https://typer.tiangolo.com/).
-   📊 **Beautiful Output**: Features rich, colored terminal output with progress bars via [Rich](https://rich.readthedocs.io/).
-   🚀 **Simple Setup**: Supports configuration via environment variables or CLI flags.
-   📂 **Batch Upload**: Effortlessly upload multiple files at once.

---

## 🚀 Quick Start

### 1. Installation

Install **chupo** as a global tool using [uv](https://github.com/astral-sh/uv):

```bash
uv tool install .
```

Or, if you prefer using pip:

```bash
pip install .
```

### 2. Usage

Upload a single image:

```bash
chupo photo.png -u https://mysite.com -k YOUR_API_KEY
```

Upload multiple images:

```bash
chupo a.png b.png -u https://mysite.com -k YOUR_API_KEY
```

Get detailed output for an upload:

```bash
chupo img.jpg -v
```

---

## 🛠️ Configuration

You can pass flags directly or set environment variables (flags override environment variables).

| Variable            | Flag                | Description                        |
|---------------------|---------------------|------------------------------------|
| `CHEVERETO_URL`     | `-u` / `--base-url` | Site base URL (e.g., `https://img.example.com`) |
| `CHEVERETO_API_KEY` | `-k` / `--key`      | Your Chevereto API key             |

### Options

-   `-f` / `--format`: `json` (default), `txt`, or `redirect` (matches Chevereto’s `format` parameter).
-   `-v` / `--verbose`: With `json`, prints the full `image` object returned by the server.
-   `--raw`: Print only API data to stdout (no banner or Rich UI). With `-f json`, each response body is written as-is (multiple files separated by a blank line). With `-f txt`, one URL per line. Errors go to stderr; exit code is non-zero if any upload fails.

Pipe-friendly example:

```bash
chupo photo.png -u https://mysite.com -k YOUR_API_KEY --raw -f txt
```

---

## 📋 API Scope

This client follows the **[Chevereto V4 — API V1 file upload](https://v4-docs.chevereto.com/api/1/file-upload.html)** specification (`POST /api/1/upload`, multipart `source`, `X-API-Key` header). It is optimized for modern Chevereto V4 instances.

---

## 📄 License

This project is licensed under the MIT License.
