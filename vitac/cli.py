"""CLI entry point for the VITAC benchmark."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="vitac",
    help="Voice-Interactive Terminal Agent Collaboration Benchmark",
)
console = Console()


@app.command()
def run(
    tasks: str = typer.Option("tasks/", help="Path to tasks directory"),
    primary: str = typer.Option(
        ..., help="Primary agent class (module:ClassName)"
    ),
    collaborator: str = typer.Option(
        ..., help="Collaborator agent class (module:ClassName)"
    ),
    output: str = typer.Option("results/", help="Output directory"),
    run_id: Optional[str] = typer.Option(None, help="Run ID (auto-generated if not set)"),
    task_id: Optional[str] = typer.Option(None, help="Run a single task by ID"),
    concurrency: int = typer.Option(4, help="Max concurrent trials"),
    n_attempts: int = typer.Option(1, help="Attempts per task"),
    no_rebuild: bool = typer.Option(False, help="Skip Docker image rebuild"),
    cleanup: bool = typer.Option(False, help="Remove Docker images after run"),
    text_only: bool = typer.Option(False, help="Use text-only mode (no audio)"),
) -> None:
    """Run the benchmark."""
    from datetime import datetime

    from vitac.agents.agent_factory import load_collaborator_agent, load_primary_agent
    from vitac.dataset.dataset import Dataset
    from vitac.harness.harness import Harness

    if run_id is None:
        run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")

    task_ids = [task_id] if task_id else None

    primary_agent = load_primary_agent(primary)
    collaborator_agent = load_collaborator_agent(collaborator)
    dataset = Dataset(path=Path(tasks), task_ids=task_ids)

    console.print(f"[bold]Run ID:[/bold] {run_id}")
    console.print(f"[bold]Tasks:[/bold] {len(dataset)}")
    console.print(f"[bold]Primary:[/bold] {primary_agent.name()}")
    console.print(f"[bold]Collaborator:[/bold] {collaborator_agent.name()}")
    console.print()

    harness = Harness(
        output_path=Path(output),
        run_id=run_id,
        primary=primary_agent,
        collaborator=collaborator_agent,
        dataset=dataset,
        no_rebuild=no_rebuild,
        cleanup=cleanup,
        n_concurrent_trials=concurrency,
        n_attempts=n_attempts,
        transcript_mode_override="text_only" if text_only else None,
    )

    results = harness.run()

    console.print()
    console.print(f"[bold green]Accuracy:[/bold green] {results.accuracy:.1%}")
    console.print(
        f"[bold green]Resolved:[/bold green] {results.n_resolved}/{len(results.results)}"
    )
    console.print(f"\nResults written to: {Path(output) / run_id}")


@app.command(name="list-tasks")
def list_tasks(
    tasks: str = typer.Option("tasks/", help="Path to tasks directory"),
) -> None:
    """List all available tasks."""
    from vitac.dataset.dataset import Dataset

    dataset = Dataset(path=Path(tasks))

    table = Table(title="Available Tasks")
    table.add_column("ID", style="cyan")
    table.add_column("Category")
    table.add_column("Difficulty")
    table.add_column("Transcript Mode")
    table.add_column("Expected Interactions", justify="right")

    for task in dataset:
        table.add_row(
            task.task_id,
            task.category,
            task.difficulty.value,
            task.transcript_mode.value,
            str(len(task.expected_interactions)),
        )

    console.print(table)
    console.print(f"\nTotal: {len(dataset)} tasks")


@app.command(name="validate-tasks")
def validate_tasks(
    tasks: str = typer.Option("tasks/", help="Path to tasks directory"),
) -> None:
    """Validate all task directories."""
    from vitac.dataset.dataset import validate_task_dir

    tasks_path = Path(tasks)
    if not tasks_path.is_dir():
        console.print(f"[red]Tasks directory not found: {tasks}[/red]")
        raise typer.Exit(1)

    total = 0
    valid = 0
    for task_dir in sorted(tasks_path.iterdir()):
        if not task_dir.is_dir():
            continue
        if not (task_dir / "task.yaml").exists():
            continue

        total += 1
        errors = validate_task_dir(task_dir)
        if errors:
            console.print(f"[red]INVALID[/red] {task_dir.name}:")
            for err in errors:
                console.print(f"  - {err}")
        else:
            console.print(f"[green]VALID[/green]   {task_dir.name}")
            valid += 1

    console.print(f"\n{valid}/{total} tasks valid")
    if valid < total:
        raise typer.Exit(1)


@app.command(name="show-results")
def show_results(
    results: str = typer.Argument(help="Path to results.json"),
) -> None:
    """Show results from a benchmark run."""
    import json

    from vitac.harness.models import BenchmarkResults

    results_path = Path(results)
    if not results_path.exists():
        console.print(f"[red]Results file not found: {results}[/red]")
        raise typer.Exit(1)

    bench_results = BenchmarkResults.model_validate_json(
        results_path.read_text()
    )

    console.print(f"[bold]Accuracy:[/bold] {bench_results.accuracy:.1%}")
    console.print(
        f"[bold]Resolved:[/bold] {bench_results.n_resolved}/{len(bench_results.results)}"
    )

    table = Table(title="Trial Results")
    table.add_column("Task", style="cyan")
    table.add_column("Resolved")
    table.add_column("Failure Mode")

    for r in bench_results.results:
        resolved_str = (
            "[green]YES[/green]" if r.is_resolved else "[red]NO[/red]"
        )
        table.add_row(
            r.task_id,
            resolved_str,
            r.failure_mode.value,
        )

    console.print(table)


if __name__ == "__main__":
    app()
