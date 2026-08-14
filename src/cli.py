from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .organizer import organize_photos

app = typer.Typer(help="Organiza suas fotos por data extraída do EXIF.")
console = Console()


@app.command()
def organize(
    sources: list[Path] = typer.Argument(
        ...,
        help="Pastas e/ou arquivos de origem das fotos",
    ),
    output: Path = typer.Option(
        Path("output"),
        "--output", "-o",
        help="Pasta de destino das fotos organizadas",
    ),
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--no-dry-run",
        help="Apenas mostra o que seria feito, sem copiar",
    ),
    rename_with_date: bool = typer.Option(
        False,
        "--rename",
        help="Renomeia as fotos copiadas com a data no nome",
    ),
):
    actions = organize_photos(sources, output, dry_run=dry_run, rename_with_date=rename_with_date)

    copied = [a for a in actions if not a.skipped]
    skipped = [a for a in actions if a.skipped]

    table = Table(title="Plano de organização")
    table.add_column("Origem", style="cyan")
    table.add_column("Destino", style="green")
    table.add_column("Status", style="yellow")

    for action in copied:
        table.add_row(str(action.source), str(action.destination), "ok" if not dry_run else "pronto para copiar")
    for action in skipped:
        table.add_row(str(action.source), "-", action.skipped_reason)

    console.print(table)

    if dry_run:
        console.print(
            f"\n[bold]{len(copied)}[/bold] fotos prontas para organizar, "
            f"[bold]{len(skipped)}[/bold] ignoradas. Rode com [bold]--no-dry-run[/bold] para copiar de verdade."
        )
    else:
        console.print(f"\n[bold]{len(copied)}[/bold] fotos organizadas, [bold]{len(skipped)}[/bold] ignoradas.")


if __name__ == "__main__":
    app()
