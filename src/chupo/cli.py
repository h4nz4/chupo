from __future__ import annotations

import json
import os
import sys
from contextlib import nullcontext
from pathlib import Path
from typing import Annotated, Optional

import httpx
import typer
from rich.console import Console, Group
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax
from rich.text import Text

from . import __version__
from .chevereto import parse_upload_result, upload_file

ASCII_LOGO = r"""
 

  ██████╗ ██╗  ██╗ ██╗   ██╗ ██████╗   ██████╗
 ██╔════╝ ██║  ██║ ██║   ██║ ██╔══██╗ ██╔═══██╗
 ██║      ███████║ ██║   ██║ ██████╔╝ ██║   ██║
 ██║      ██╔══██║ ██║   ██║ ██╔═══╝  ██║   ██║
 ╚██████╗ ██║  ██║ ╚██████╔╝ ██║      ╚██████╔╝
  ╚═════╝ ╚═╝  ╚═╝  ╚═════╝  ╚═╝       ╚═════╝

 
"""


def print_logo() -> None:
    console = Console()
    lines = ASCII_LOGO.strip("\n").split("\n")
    start_color = (0, 210, 255)
    end_color = (58, 123, 213)
    console.print(Text("\n"))
    n = len(lines)
    for i, line in enumerate(lines):
        t = i / (n - 1) if n > 1 else 0.0
        r = int(start_color[0] + (end_color[0] - start_color[0]) * t)
        g = int(start_color[1] + (end_color[1] - start_color[1]) * t)
        b = int(start_color[2] + (end_color[2] - start_color[2]) * t)
        console.print(Text(line, style=f"rgb({r},{g},{b})"))


app = typer.Typer(
    name="chupo",
    help="Upload images to a Chevereto site (V4 API V1 file upload).",
    pretty_exceptions_show_locals=False,
    rich_markup_mode="rich",
)


def version_callback(value: bool) -> None:
    if not value:
        return
    print_logo()
    typer.echo(f"chupo {__version__}")
    raise typer.Exit()


def _print_result_block(
    console: Console,
    path: Path,
    fmt: str,
    verbose: bool,
    image: dict | None,
    message: str,
) -> None:
    if fmt == "json" and verbose and image is not None:
        console.print(
            Panel(
                Syntax(
                    json.dumps(image, indent=2, default=str),
                    "json",
                    word_wrap=True,
                ),
                title=f"[bold]{path.name}[/bold]",
                border_style="green",
            )
        )
        return

    url = ""
    viewer = ""
    if fmt == "json" and image:
        url = str(image.get("url") or image.get("display_url") or "")
        viewer = str(image.get("url_viewer") or "")
    elif fmt == "txt":
        url = message.strip()
    elif fmt == "redirect" and image:
        url = str(image.get("url") or "")

    title = Text.assemble(("✓ ", "bold green"), (path.name, "bold white"))
    if not url and not viewer:
        console.print(
            Panel(
                Text("(no URL in response)", style="dim"),
                title=title,
                border_style="yellow",
            )
        )
        return

    # no_wrap: avoid Rich folding long URLs inside the panel (e.g. before ".gif").
    # The host terminal may still soft-wrap at the window edge.
    body_parts: list[str | Text] = []
    if url:
        body_parts.append(Text("Direct URL", style="bold dim"))
        body_parts.append(
            Text(url, style="bold cyan", no_wrap=True, overflow="ignore")
        )
    if viewer and viewer != url:
        body_parts.append(Text("Viewer", style="bold dim"))
        body_parts.append(
            Text(viewer, style="cyan", no_wrap=True, overflow="ignore")
        )

    console.print(
        Panel(
            Group(*body_parts),
            title=title,
            border_style="green",
            padding=(0, 1),
        )
    )


def _write_raw_stdout(
    fmt: str,
    rows: list[tuple[dict | None, str, httpx.Response]],
) -> None:
    first = True
    for image, message, resp in rows:
        if not first:
            sys.stdout.write("\n")
        first = False
        if fmt == "json":
            sys.stdout.write(resp.text.rstrip("\n"))
        elif fmt == "txt":
            sys.stdout.write(message.strip())
        elif fmt == "redirect":
            url = ""
            if image:
                url = str(image.get("url", "")).strip()
            sys.stdout.write(url)
    sys.stdout.write("\n")
    sys.stdout.flush()


@app.command()
def main(
    files: Annotated[
        list[Path],
        typer.Argument(
            ...,
            help="Image file paths to upload.",
            exists=True,
            file_okay=True,
            dir_okay=False,
        ),
    ],
    base_url: Annotated[
        Optional[str],
        typer.Option(
            "--base-url",
            "-u",
            envvar="CHEVERETO_URL",
            help="Chevereto site base URL (or CHEVERETO_URL).",
        ),
    ] = None,
    api_key: Annotated[
        Optional[str],
        typer.Option(
            "--key",
            "-k",
            envvar="CHEVERETO_API_KEY",
            help="API key, sent as X-API-Key (or CHEVERETO_API_KEY).",
        ),
    ] = None,
    response_format: Annotated[
        str,
        typer.Option(
            "--format",
            "-f",
            help="API response format: json, txt, or redirect.",
        ),
    ] = "json",
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Print full JSON image payload on success.",
        ),
    ] = False,
    raw: Annotated[
        bool,
        typer.Option(
            "--raw",
            help="Print only API output to stdout (no logo or Rich UI). "
            "json: response body per file; txt: URL line; redirect: viewer URL. "
            "Errors go to stderr.",
        ),
    ] = False,
    show_version: Annotated[
        Optional[bool],
        typer.Option(
            "--version",
            help="Show version and exit.",
            callback=version_callback,
            is_eager=True,
        ),
    ] = None,
) -> None:
    """Upload one or more files (Chevereto V4 API V1 file upload)."""
    if not raw:
        print_logo()

    site = (base_url or os.environ.get("CHEVERETO_URL") or "").strip()
    key = (api_key or os.environ.get("CHEVERETO_API_KEY") or "").strip()
    if not site:
        typer.secho(
            "Error: set --base-url / -u or CHEVERETO_URL.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)
    if not key:
        typer.secho(
            "Error: set --key / -k or CHEVERETO_API_KEY.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    fmt = response_format.lower().strip()
    if fmt not in ("json", "txt", "redirect"):
        typer.secho(
            "Error: --format must be json, txt, or redirect.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    console = Console()
    successes: list[tuple[Path, dict | None, str, httpx.Response]] = []
    errors: list[tuple[Path, str]] = []
    n = len(files)

    timeout = httpx.Timeout(120.0, connect=30.0)
    status_ctx = (
        nullcontext()
        if raw
        else console.status(
            "[bold cyan]Starting…[/bold cyan]",
            spinner="dots",
            spinner_style="cyan",
        )
    )
    with httpx.Client(timeout=timeout) as client:
        with status_ctx as status:
            for i, path in enumerate(files, start=1):
                if not raw:
                    short = (
                        path.name
                        if len(path.name) <= 56
                        else path.name[:26] + "…" + path.name[-26:]
                    )
                    status.update(
                        f"[bold cyan]Uploading[/bold cyan] [white]{short}[/white] "
                        f"[dim]({i}/{n})[/dim]"
                    )
                try:
                    resp = upload_file(client, site, key, path, fmt)
                    ok, message, image = parse_upload_result(
                        resp, fmt, site_base=site
                    )
                    if not ok:
                        errors.append((path, message))
                        continue
                    successes.append((path, image, message, resp))
                except (httpx.HTTPError, OSError) as exc:
                    errors.append((path, str(exc)))

    if raw:
        for path, err in errors:
            sys.stderr.write(f"{path.name}: {err}\n")
        if successes:
            _write_raw_stdout(
                fmt,
                [(image, message, resp) for _, image, message, resp in successes],
            )
        if errors and not successes:
            raise typer.Exit(code=1)
        if errors:
            raise typer.Exit(code=1)
        return

    console.print()
    if successes:
        console.print(Rule("[bold green]Uploaded[/bold green]", style="green"))
        for path, image, message, _resp in successes:
            console.print()
            _print_result_block(console, path, fmt, verbose, image, message)

    if errors:
        console.print()
        console.print(Rule("[bold red]Failed[/bold red]", style="red"))
        for path, err in errors:
            console.print()
            console.print(Text.assemble(("✗ ", "bold red"), (path.name, "bold white")))
            console.print(Text(f"  {err}", style="red", overflow="fold"))

    console.print()
    if errors and not successes:
        console.print("[red]All uploads failed.[/red]")
        raise typer.Exit(code=1)
    if errors:
        console.print("[yellow]Finished with errors.[/yellow]")
        raise typer.Exit(code=1)
    console.print("[bold green]Done.[/bold green]")


def run() -> None:
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print_logo()
    app()


if __name__ == "__main__":
    run()
