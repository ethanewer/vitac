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
    system: str = typer.Option(
        ..., help="Built-in voice system name (e.g. minimax-m2-voice)"
    ),
    collab_system: Optional[str] = typer.Option(
        None, help="Built-in voice system for the collaborator (defaults to --system)"
    ),
    tasks: str = typer.Option("tasks/", help="Path to tasks directory"),
    output: str = typer.Option("results/", help="Output directory"),
    run_id: Optional[str] = typer.Option(
        None, help="Run ID (auto-generated if not set)"
    ),
    task_id: Optional[str] = typer.Option(None, help="Run a single task by ID"),
    difficulty: Optional[str] = typer.Option(
        None, help="Filter tasks by difficulty (easy, medium, hard)"
    ),
    concurrency: int = typer.Option(4, help="Max concurrent trials"),
    n_attempts: int = typer.Option(1, help="Attempts per task"),
    no_rebuild: bool = typer.Option(False, help="Skip Docker image rebuild"),
    cleanup: bool = typer.Option(False, help="Remove Docker images after run"),
    text_only: bool = typer.Option(False, help="Use text-only mode (no audio)"),
) -> None:
    """Run the benchmark with a built-in voice system."""
    from datetime import datetime

    from vitac.agents.opencode_agents import (
        BUILT_IN_SYSTEMS,
        VoiceSystemCollaboratorAgent,
        VoiceSystemPrimaryAgent,
    )
    from vitac.dataset.dataset import Dataset
    from vitac.harness.harness import Harness

    if system not in BUILT_IN_SYSTEMS:
        console.print(f"[red]Unknown system: {system}[/red]")
        console.print(f"Available systems: {', '.join(BUILT_IN_SYSTEMS)}")
        raise typer.Exit(1)

    if collab_system and collab_system not in BUILT_IN_SYSTEMS:
        console.print(f"[red]Unknown collaborator system: {collab_system}[/red]")
        console.print(f"Available systems: {', '.join(BUILT_IN_SYSTEMS)}")
        raise typer.Exit(1)

    if run_id is None:
        run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")

    task_ids = [task_id] if task_id else None

    primary_agent = VoiceSystemPrimaryAgent(system=system, collab_system=collab_system)
    collaborator_agent = VoiceSystemCollaboratorAgent()

    dataset = Dataset(path=Path(tasks), task_ids=task_ids)

    # Filter by difficulty if specified
    if difficulty:
        from vitac.types import TaskDifficulty

        try:
            target_difficulty = TaskDifficulty(difficulty)
        except ValueError:
            console.print(f"[red]Invalid difficulty: {difficulty}[/red]")
            console.print("Options: easy, medium, hard")
            raise typer.Exit(1)
        dataset.filter_by_difficulty(target_difficulty)

    console.print(f"[bold]Run ID:[/bold] {run_id}")
    console.print(f"[bold]System:[/bold] {system}")
    console.print(f"[bold]Collaborator system:[/bold] {collab_system or system}")
    console.print(f"[bold]Tasks:[/bold] {len(dataset)}")
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


@app.command(name="list-systems")
def list_systems() -> None:
    """List all available built-in voice systems."""
    from vitac.agents.opencode_agents import BUILT_IN_SYSTEMS

    table = Table(title="Built-in Voice Systems")
    table.add_column("System Name", style="cyan")
    for system in BUILT_IN_SYSTEMS:
        table.add_row(system)
    console.print(table)


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

    bench_results = BenchmarkResults.model_validate_json(results_path.read_text())

    console.print(f"[bold]Accuracy:[/bold] {bench_results.accuracy:.1%}")
    console.print(
        f"[bold]Resolved:[/bold] {bench_results.n_resolved}/{len(bench_results.results)}"
    )

    table = Table(title="Trial Results")
    table.add_column("Task", style="cyan")
    table.add_column("Resolved")
    table.add_column("Failure Mode")

    for r in bench_results.results:
        resolved_str = "[green]YES[/green]" if r.is_resolved else "[red]NO[/red]"
        table.add_row(
            r.task_id,
            resolved_str,
            r.failure_mode.value,
        )

    console.print(table)


if __name__ == "__main__":
    app()
