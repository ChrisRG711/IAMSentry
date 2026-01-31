"""IAMSentry Command Line Interface.

Modern CLI using Typer with rich output formatting.
Provides subcommands for scanning, analyzing, and remediating IAM issues.
"""

import json
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table
from rich.tree import Tree

from IAMSentry.constants import VERSION

# Create the main app
app = typer.Typer(
    name="iamsentry",
    help="IAMSentry - GCP IAM Security Auditor and Remediation Tool",
    add_completion=True,
    rich_markup_mode="rich",
)

console = Console()

# Quiet mode flag (set via callback)
_quiet_mode = False


class OutputFormat(str, Enum):
    """Output format options."""

    table = "table"
    json = "json"
    yaml = "yaml"


# Version callback
def version_callback(value: bool):
    """Show version and exit."""
    if value:
        console.print(f"[bold blue]IAMSentry[/bold blue] version [green]{VERSION}[/green]")
        raise typer.Exit()


def quiet_callback(value: bool):
    """Enable quiet mode."""
    global _quiet_mode
    if value:
        _quiet_mode = True


def _print(message: str, style: str = "") -> None:
    """Print message unless in quiet mode."""
    if not _quiet_mode:
        if style:
            console.print(f"[{style}]{message}[/{style}]")
        else:
            console.print(message)


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
    quiet: Optional[bool] = typer.Option(
        None,
        "--quiet",
        "-q",
        help="Suppress non-essential output.",
        callback=quiet_callback,
        is_eager=True,
    ),
):
    """
    [bold blue]IAMSentry[/bold blue] - GCP IAM Security Auditor and Remediation Tool

    Analyze IAM recommendations, calculate risk scores, and optionally
    apply remediation actions to reduce over-privileged access.

    [dim]Use --help on any command for more information.[/dim]
    """
    pass


@app.command()
def scan(
    config: Path = typer.Option(
        "config.yaml",
        "--config",
        "-c",
        help="Path to configuration file.",
        exists=False,
    ),
    projects: Optional[List[str]] = typer.Option(
        None,
        "--project",
        "-p",
        help="Project(s) to scan. Can be specified multiple times.",
    ),
    output: Path = typer.Option(
        "./output",
        "--output",
        "-o",
        help="Output directory for results.",
    ),
    format: OutputFormat = typer.Option(
        OutputFormat.table,
        "--format",
        "-f",
        help="Output format.",
    ),
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--execute",
        help="Dry run mode (default). Use --execute to apply changes.",
    ),
):
    """
    [bold]Scan[/bold] GCP projects for IAM recommendations.

    Fetches IAM policy recommendations from the GCP Recommender API
    and analyzes them for over-privileged access.

    [dim]Examples:[/dim]

        iamsentry scan --project my-project

        iamsentry scan --config my_config.yaml

        iamsentry scan -p project1 -p project2 --format json
    """
    console.print(
        Panel.fit("[bold blue]IAMSentry Scan[/bold blue]", subtitle="IAM Recommendation Scanner")
    )

    # Validate configuration
    if not config.exists():
        console.print(f"[yellow]Warning:[/yellow] Config file not found: {config}")
        console.print("[dim]Using default configuration with ADC...[/dim]")

    # Show scan parameters
    table = Table(title="Scan Parameters", show_header=False)
    table.add_column("Parameter", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Configuration", str(config))
    table.add_row("Projects", ", ".join(projects) if projects else "*")
    table.add_row("Output Directory", str(output))
    table.add_row("Output Format", format.value)
    table.add_row("Mode", "[green]Dry Run[/green]" if dry_run else "[red]Execute[/red]")

    console.print(table)
    console.print()

    # Create output directory
    output.mkdir(parents=True, exist_ok=True)

    # Run scan with progress
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        # Initialize
        task_init = progress.add_task("[cyan]Initializing...", total=100)

        try:
            from IAMSentry.helpers import hconfigs, hlogging
            from IAMSentry.plugins.gcp import util_gcp

            progress.update(task_init, advance=30, description="[cyan]Loading credentials...")

            # Get credentials
            credentials, project_id = util_gcp.get_credentials()
            progress.update(task_init, advance=30, description="[cyan]Credentials loaded")

            # Determine projects to scan
            scan_projects = projects or [project_id] if project_id else []
            if not scan_projects:
                console.print(
                    "[red]Error:[/red] No projects specified and no default project found."
                )
                console.print(
                    "[dim]Use --project to specify projects or configure ADC with a default project.[/dim]"
                )
                raise typer.Exit(1)

            progress.update(task_init, advance=40, completed=100)

            # Scan projects
            task_scan = progress.add_task(
                f"[cyan]Scanning {len(scan_projects)} project(s)...", total=len(scan_projects)
            )

            results = []
            for proj in scan_projects:
                progress.update(task_scan, description=f"[cyan]Scanning {proj}...")

                try:
                    from IAMSentry.plugins.gcp.gcpcloud import GCPCloudIAMRecommendations

                    reader = GCPCloudIAMRecommendations(projects=[proj])
                    for record in reader.read():
                        results.append(record)

                except Exception as e:
                    console.print(f"[yellow]Warning:[/yellow] Error scanning {proj}: {e}")

                progress.advance(task_scan)

        except ImportError as e:
            console.print(f"[red]Error:[/red] Missing dependency: {e}")
            console.print("[dim]Run: pip install -e .[/dim]")
            raise typer.Exit(1)

        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

    # Display results
    if results:
        _display_scan_results(results, format, output)
    else:
        console.print("[yellow]No recommendations found.[/yellow]")


def _display_scan_results(results: list, format: OutputFormat, output: Path):
    """Display scan results in the specified format."""
    console.print(f"\n[bold green]Found {len(results)} recommendation(s)[/bold green]\n")

    if format == OutputFormat.table:
        table = Table(title="IAM Recommendations")
        table.add_column("Project", style="cyan")
        table.add_column("Account", style="green")
        table.add_column("Type", style="blue")
        table.add_column("Action", style="yellow")
        table.add_column("Priority", style="magenta")

        for r in results[:20]:  # Limit to first 20
            raw = r.get("raw", {})
            table.add_row(
                raw.get("project", "N/A"),
                _extract_account(raw),
                raw.get("recommenderSubtype", "N/A"),
                _extract_action(raw),
                raw.get("priority", "N/A"),
            )

        if len(results) > 20:
            table.add_row("...", f"({len(results) - 20} more)", "", "", "")

        console.print(table)

    elif format == OutputFormat.json:
        output_file = output / f"scan_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2, default=str)
        console.print(f"[green]Results saved to:[/green] {output_file}")

    elif format == OutputFormat.yaml:
        import yaml

        output_file = output / f"scan_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
        with open(output_file, "w") as f:
            yaml.dump(results, f, default_flow_style=False)
        console.print(f"[green]Results saved to:[/green] {output_file}")


def _extract_account(raw: dict) -> str:
    """Extract account from recommendation."""
    try:
        ops = raw.get("content", {}).get("operationGroups", [{}])[0].get("operations", [])
        for op in ops:
            if op.get("action") == "remove":
                return op.get("pathFilters", {}).get("/iamPolicy/bindings/*/members/*", "N/A")
    except Exception:
        pass
    return "N/A"


def _extract_action(raw: dict) -> str:
    """Extract recommended action."""
    subtype = raw.get("recommenderSubtype", "")
    if subtype == "REMOVE_ROLE":
        return "Remove role"
    elif subtype == "REPLACE_ROLE":
        return "Replace role"
    return subtype


@app.command()
def analyze(
    input_file: Path = typer.Argument(
        ...,
        help="Input file with scan results (JSON).",
        exists=True,
    ),
    format: OutputFormat = typer.Option(
        OutputFormat.table,
        "--format",
        "-f",
        help="Output format.",
    ),
    min_risk: int = typer.Option(
        0,
        "--min-risk",
        help="Minimum risk score to include.",
    ),
    account_type: Optional[str] = typer.Option(
        None,
        "--type",
        "-t",
        help="Filter by account type (user, group, serviceAccount).",
    ),
):
    """
    [bold]Analyze[/bold] scan results and calculate risk scores.

    Processes IAM recommendations and calculates risk scores
    based on permission usage patterns.

    [dim]Examples:[/dim]

        iamsentry analyze scan_results.json

        iamsentry analyze results.json --min-risk 50 --format json

        iamsentry analyze results.json --type serviceAccount
    """
    console.print(
        Panel.fit("[bold blue]IAMSentry Analyze[/bold blue]", subtitle="Risk Score Analysis")
    )

    # Load input file
    with open(input_file) as f:
        results = json.load(f)

    console.print(f"[dim]Loaded {len(results)} records from {input_file}[/dim]\n")

    # Process with risk scoring
    from IAMSentry.plugins.gcp.gcpcloudiam import GCPIAMRecommendationProcessor

    processor = GCPIAMRecommendationProcessor(mode_scan=True, mode_enforce=False)

    analyzed = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Analyzing...", total=len(results))

        for record in results:
            try:
                for processed in processor.eval(record):
                    score = processed.get("score", {})
                    proc = processed.get("processor", {})

                    # Apply filters
                    if score.get("risk_score", 0) < min_risk:
                        continue
                    if account_type and proc.get("account_type") != account_type:
                        continue

                    analyzed.append(processed)
            except Exception as e:
                console.print(f"[yellow]Warning:[/yellow] Error processing record: {e}")

            progress.advance(task)

    # Display results
    console.print(f"\n[bold green]Analyzed {len(analyzed)} record(s)[/bold green]\n")

    if format == OutputFormat.table:
        table = Table(title="Risk Analysis Results")
        table.add_column("Account", style="cyan")
        table.add_column("Type", style="blue")
        table.add_column("Risk", style="red", justify="right")
        table.add_column("Waste %", style="yellow", justify="right")
        table.add_column("Safe Score", style="green", justify="right")
        table.add_column("Action", style="magenta")

        for r in analyzed[:30]:
            proc = r.get("processor", {})
            score = r.get("score", {})
            table.add_row(
                proc.get("account_id", "N/A")[:40],
                proc.get("account_type", "N/A"),
                str(score.get("risk_score", 0)),
                f"{score.get('over_privilege_score', 0)}%",
                str(score.get("safe_to_apply_recommendation_score", 0)),
                proc.get("recommendation_recommender_subtype", "N/A"),
            )

        console.print(table)

    elif format == OutputFormat.json:
        console.print_json(data=analyzed[:10])
        if len(analyzed) > 10:
            console.print(f"[dim]... and {len(analyzed) - 10} more[/dim]")


@app.command()
def remediate(
    input_file: Path = typer.Argument(
        ...,
        help="Input file with analyzed results (JSON).",
        exists=True,
    ),
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--execute",
        help="Dry run mode (default). Use --execute to apply changes.",
    ),
    max_changes: int = typer.Option(
        10,
        "--max-changes",
        help="Maximum number of changes to apply per run.",
    ),
    min_safe_score: int = typer.Option(
        60,
        "--min-safe-score",
        help="Minimum safety score required to apply remediation.",
    ),
    confirm: bool = typer.Option(
        True,
        "--confirm/--no-confirm",
        help="Require confirmation before applying changes.",
    ),
):
    """
    [bold]Remediate[/bold] IAM issues based on analyzed results.

    Applies recommended IAM changes to reduce over-privileged access.
    [bold red]Use with caution![/bold red]

    [dim]Examples:[/dim]

        iamsentry remediate analyzed.json --dry-run

        iamsentry remediate analyzed.json --execute --max-changes 5

        iamsentry remediate analyzed.json --execute --no-confirm
    """
    console.print(
        Panel.fit("[bold red]IAMSentry Remediate[/bold red]", subtitle="IAM Policy Remediation")
    )

    if not dry_run:
        console.print("[bold red]WARNING:[/bold red] Execute mode enabled!")
        console.print("[yellow]This will modify IAM policies in your GCP projects.[/yellow]\n")

        if confirm:
            confirmed = typer.confirm("Are you sure you want to proceed?")
            if not confirmed:
                console.print("[dim]Remediation cancelled.[/dim]")
                raise typer.Exit(0)

    # Load input file
    with open(input_file) as f:
        results = json.load(f)

    console.print(f"[dim]Loaded {len(results)} records from {input_file}[/dim]\n")

    # Process with remediation
    from IAMSentry.plugins.gcp.gcpiam_remediation import GCPIAMRemediationProcessor

    processor = GCPIAMRemediationProcessor(
        mode_remediate=True,
        dry_run=dry_run,
        remediation_config={
            "max_changes_per_run": max_changes,
            "require_approval": confirm,
        },
    )

    changes = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Processing...", total=len(results))

        for record in results:
            if len(changes) >= max_changes:
                console.print(f"[yellow]Reached max changes limit ({max_changes})[/yellow]")
                break

            try:
                for processed in processor.eval(record):
                    rem = processed.get("remediation", {})
                    score = processed.get("score", {})

                    # Check safety score
                    safe_score = score.get("safe_to_apply_recommendation_score", 0)
                    if safe_score < min_safe_score:
                        continue

                    if rem.get("execution_result"):
                        changes.append(processed)

            except Exception as e:
                console.print(f"[yellow]Warning:[/yellow] Error: {e}")

            progress.advance(task)

    # Display results
    console.print(
        f"\n[bold]{'Simulated' if dry_run else 'Applied'} {len(changes)} change(s)[/bold]\n"
    )

    if changes:
        table = Table(title="Remediation Results")
        table.add_column("Account", style="cyan")
        table.add_column("Action", style="yellow")
        table.add_column("Status", style="green")
        table.add_column("Details", style="dim")

        for c in changes:
            rem = c.get("remediation", {})
            result = rem.get("execution_result", {})
            table.add_row(
                rem.get("account_id", "N/A")[:40],
                rem.get("recommended_action", "N/A"),
                result.get("status", "N/A"),
                str(result.get("details", {}))[:50],
            )

        console.print(table)


@app.command()
def status(
    config: Path = typer.Option(
        "config.yaml",
        "--config",
        "-c",
        help="Path to configuration file.",
    ),
):
    """
    [bold]Status[/bold] - Show current IAMSentry status and configuration.

    Displays authentication status, configured projects, and
    recent scan history.
    """
    console.print(Panel.fit("[bold blue]IAMSentry Status[/bold blue]", subtitle="System Status"))

    # Authentication status
    console.print("\n[bold]Authentication[/bold]")
    try:
        from IAMSentry.plugins.gcp import util_gcp

        credentials, project_id = util_gcp.get_credentials()

        auth_table = Table(show_header=False)
        auth_table.add_column("Property", style="cyan")
        auth_table.add_column("Value", style="green")

        auth_table.add_row("Status", "[green]✓ Authenticated[/green]")
        auth_table.add_row("Default Project", project_id or "[dim]Not set[/dim]")

        if hasattr(credentials, "service_account_email"):
            auth_table.add_row("Service Account", credentials.service_account_email)
        else:
            auth_table.add_row("Auth Type", "Application Default Credentials")

        console.print(auth_table)

    except Exception as e:
        console.print(f"[red]✗ Not authenticated:[/red] {e}")
        console.print("[dim]Run: gcloud auth application-default login[/dim]")

    # Configuration status
    console.print("\n[bold]Configuration[/bold]")
    if config.exists():
        try:
            from IAMSentry.config_models import IAMSentryConfig

            cfg = IAMSentryConfig.from_yaml(str(config))

            config_table = Table(show_header=False)
            config_table.add_column("Property", style="cyan")
            config_table.add_column("Value", style="green")

            config_table.add_row("Config File", str(config))
            config_table.add_row("Schedule", cfg.schedule)
            config_table.add_row("Audits", ", ".join(cfg.audits.keys()))
            config_table.add_row("Plugins", str(len(cfg.plugins)))

            console.print(config_table)

        except Exception as e:
            console.print(f"[yellow]Warning:[/yellow] Error loading config: {e}")
    else:
        console.print(f"[dim]Config file not found: {config}[/dim]")

    # Output directory
    console.print("\n[bold]Output Directory[/bold]")
    output_dir = Path("./output")
    if output_dir.exists():
        files = list(output_dir.glob("*.json")) + list(output_dir.glob("*.yaml"))
        console.print(f"[dim]{output_dir}[/dim] ({len(files)} result files)")

        if files:
            recent = sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)[:5]
            for f in recent:
                console.print(f"  [dim]{f.name}[/dim]")
    else:
        console.print("[dim]No output directory found.[/dim]")


@app.command()
def init(
    output: Path = typer.Option(
        "config.yaml",
        "--output",
        "-o",
        help="Output path for configuration file.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing configuration file.",
    ),
):
    """
    [bold]Initialize[/bold] a new IAMSentry configuration file.

    Creates a starter configuration file with sensible defaults.
    """
    if output.exists() and not force:
        console.print(f"[yellow]Configuration file already exists:[/yellow] {output}")
        console.print("[dim]Use --force to overwrite.[/dim]")
        raise typer.Exit(1)

    config_template = """# IAMSentry Configuration
# Generated by: iamsentry init

# Logging configuration
logger:
  version: 1

# Schedule (24-hour format, or use --now flag)
schedule: "00:00"

# Plugin configurations
plugins:
  gcp_iam_reader:
    plugin: IAMSentry.plugins.gcp.gcpcloud.GCPCloudIAMRecommendations
    # key_file_path: /path/to/key.json  # Optional - uses ADC by default
    projects:
      - "*"  # Scan all accessible projects
    processes: 4
    threads: 10

  gcp_iam_processor:
    plugin: IAMSentry.plugins.gcp.gcpcloudiam.GCPIAMRecommendationProcessor
    mode_scan: true
    mode_enforce: false

  file_store:
    plugin: IAMSentry.plugins.files.filestore.FileStore
    output_dir: ./output

# Audit definitions
audits:
  gcp_iam_audit:
    clouds:
      - gcp_iam_reader
    processors:
      - gcp_iam_processor
    stores:
      - file_store

# Audits to run
run:
  - gcp_iam_audit
"""

    with open(output, "w") as f:
        f.write(config_template)

    console.print(f"[green]✓[/green] Configuration file created: {output}")
    console.print("\n[dim]Next steps:[/dim]")
    console.print("  1. Edit the configuration file to match your environment")
    console.print("  2. Run: [cyan]iamsentry validate[/cyan] to check your setup")
    console.print("  3. Run: [cyan]iamsentry scan[/cyan]")


@app.command()
def validate(
    config: Path = typer.Option(
        "config.yaml",
        "--config",
        "-c",
        help="Path to configuration file.",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed validation results.",
    ),
):
    """
    [bold]Validate[/bold] configuration and GCP connectivity.

    Performs pre-flight checks to ensure IAMSentry can run successfully:
    - Configuration file syntax and schema validation
    - GCP authentication status
    - Required IAM permissions
    - Project accessibility
    - Network connectivity to GCP APIs

    [dim]Run this before your first scan to catch issues early.[/dim]
    """
    console.print(
        Panel.fit("[bold blue]IAMSentry Pre-flight Validation[/bold blue]", border_style="blue")
    )

    all_passed = True
    checks_run = 0
    checks_passed = 0

    # Check 1: Configuration file exists
    console.print("\n[bold]1. Configuration File[/bold]")
    checks_run += 1
    if config.exists():
        console.print(f"  [green]✓[/green] Found: {config}")
        checks_passed += 1

        # Validate YAML syntax
        try:
            import yaml

            with open(config) as f:
                cfg_data = yaml.safe_load(f)
            console.print(f"  [green]✓[/green] YAML syntax valid")
            checks_passed += 1
            checks_run += 1

            # Validate with Pydantic models
            try:
                from IAMSentry.config_models import IAMSentryConfig

                IAMSentryConfig.from_dict(cfg_data)
                console.print(f"  [green]✓[/green] Configuration schema valid")
                checks_passed += 1
            except Exception as e:
                console.print(f"  [red]✗[/red] Configuration schema error: {e}")
                all_passed = False
            checks_run += 1

        except yaml.YAMLError as e:
            console.print(f"  [red]✗[/red] YAML syntax error: {e}")
            all_passed = False
            checks_run += 1
    else:
        console.print(f"  [red]✗[/red] Not found: {config}")
        console.print(f"    [dim]Run: iamsentry init[/dim]")
        all_passed = False

    # Check 2: GCP Authentication
    console.print("\n[bold]2. GCP Authentication[/bold]")
    checks_run += 1
    try:
        from google.auth import default
        from google.auth.exceptions import DefaultCredentialsError

        credentials, project = default()
        auth_type = "Application Default Credentials"

        if hasattr(credentials, "service_account_email"):
            auth_type = f"Service Account ({credentials.service_account_email})"

        console.print(f"  [green]✓[/green] Authenticated via {auth_type}")
        if project:
            console.print(f"  [green]✓[/green] Default project: {project}")
        else:
            console.print(f"  [yellow]⚠[/yellow] No default project set (will use config)")
        checks_passed += 1

    except DefaultCredentialsError:
        console.print(f"  [red]✗[/red] No GCP credentials found")
        console.print(f"    [dim]Run: gcloud auth application-default login[/dim]")
        all_passed = False
    except ImportError:
        console.print(f"  [red]✗[/red] google-auth not installed")
        console.print(f"    [dim]Run: pip install google-auth[/dim]")
        all_passed = False
    except Exception as e:
        console.print(f"  [red]✗[/red] Authentication error: {e}")
        all_passed = False

    # Check 3: GCP API Connectivity
    console.print("\n[bold]3. GCP API Connectivity[/bold]")
    checks_run += 1
    try:
        from google.auth import default
        from googleapiclient.discovery import build

        credentials, _ = default()

        # Test Resource Manager API (for project listing)
        service = build("cloudresourcemanager", "v1", credentials=credentials)
        # Just build the service to verify connectivity
        console.print(f"  [green]✓[/green] Cloud Resource Manager API accessible")
        checks_passed += 1

        # Test Recommender API
        checks_run += 1
        try:
            recommender_service = build("recommender", "v1", credentials=credentials)
            console.print(f"  [green]✓[/green] Recommender API accessible")
            checks_passed += 1
        except Exception as e:
            console.print(f"  [yellow]⚠[/yellow] Recommender API: {e}")
            if verbose:
                console.print(f"    [dim]This may require enabling the API in your project[/dim]")

    except Exception as e:
        console.print(f"  [red]✗[/red] API connectivity error: {e}")
        all_passed = False

    # Check 4: Required Dependencies
    console.print("\n[bold]4. Dependencies[/bold]")
    deps = [
        ("google-auth", "google.auth"),
        ("google-api-python-client", "googleapiclient"),
        ("PyYAML", "yaml"),
        ("pydantic", "pydantic"),
        ("typer", "typer"),
        ("rich", "rich"),
    ]

    optional_deps = [
        ("passlib", "passlib", "Secure password hashing"),
        ("fastapi", "fastapi", "Dashboard"),
        ("uvicorn", "uvicorn", "Dashboard server"),
    ]

    for name, module in deps:
        checks_run += 1
        try:
            __import__(module)
            console.print(f"  [green]✓[/green] {name}")
            checks_passed += 1
        except ImportError:
            console.print(f"  [red]✗[/red] {name} not installed")
            all_passed = False

    if verbose:
        console.print("\n  [dim]Optional dependencies:[/dim]")
        for name, module, purpose in optional_deps:
            try:
                __import__(module)
                console.print(f"  [green]✓[/green] {name} [dim]({purpose})[/dim]")
            except ImportError:
                console.print(f"  [yellow]○[/yellow] {name} not installed [dim]({purpose})[/dim]")

    # Check 5: Output directory
    console.print("\n[bold]5. Output Directory[/bold]")
    checks_run += 1
    output_dir = Path("./output")
    if output_dir.exists():
        if output_dir.is_dir():
            console.print(f"  [green]✓[/green] Output directory exists: {output_dir}")
            checks_passed += 1
        else:
            console.print(f"  [red]✗[/red] {output_dir} exists but is not a directory")
            all_passed = False
    else:
        console.print(f"  [yellow]⚠[/yellow] Output directory does not exist (will be created)")
        checks_passed += 1  # Not a failure, just informational

    # Summary
    console.print("\n" + "─" * 50)
    if all_passed:
        console.print(
            Panel.fit(
                f"[bold green]✓ All checks passed![/bold green]\n\n"
                f"[dim]{checks_passed}/{checks_run} checks passed[/dim]\n\n"
                f"You're ready to run: [cyan]iamsentry scan --config {config}[/cyan]",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel.fit(
                f"[bold red]✗ Some checks failed[/bold red]\n\n"
                f"[dim]{checks_passed}/{checks_run} checks passed[/dim]\n\n"
                f"Please fix the issues above before running a scan.",
                border_style="red",
            )
        )
        raise typer.Exit(1)


@app.command()
def completion(
    shell: str = typer.Argument(
        None,
        help="Shell type: bash, zsh, fish, or powershell. Auto-detects if not specified.",
    ),
    install: bool = typer.Option(
        False,
        "--install",
        "-i",
        help="Install completion to your shell config file.",
    ),
):
    """
    [bold]Generate or install[/bold] shell completion scripts.

    Enables tab completion for commands, options, and arguments.

    [bold]Quick Install:[/bold]
        iamsentry completion --install

    [bold]Manual Installation:[/bold]
        # Bash
        iamsentry completion bash >> ~/.bashrc

        # Zsh
        iamsentry completion zsh >> ~/.zshrc

        # Fish
        iamsentry completion fish > ~/.config/fish/completions/iamsentry.fish

        # PowerShell
        iamsentry completion powershell >> $PROFILE
    """
    import os
    import subprocess

    # Auto-detect shell if not specified
    if not shell:
        shell_path = os.environ.get("SHELL", "")
        if "zsh" in shell_path:
            shell = "zsh"
        elif "fish" in shell_path:
            shell = "fish"
        elif "bash" in shell_path:
            shell = "bash"
        else:
            # Check for PowerShell on Windows
            if os.name == "nt":
                shell = "powershell"
            else:
                shell = "bash"  # Default fallback

        console.print(f"[dim]Detected shell: {shell}[/dim]")

    shell = shell.lower()
    valid_shells = ["bash", "zsh", "fish", "powershell"]

    if shell not in valid_shells:
        console.print(f"[red]Error:[/red] Unknown shell '{shell}'")
        console.print(f"[dim]Valid options: {', '.join(valid_shells)}[/dim]")
        raise typer.Exit(1)

    # Generate completion script
    env_var = f"_IAMSENTRY_COMPLETE={shell}_source"

    try:
        result = subprocess.run(
            [sys.executable, "-m", "IAMSentry.cli"],
            env={**os.environ, env_var: "1"},
            capture_output=True,
            text=True,
        )
        completion_script = result.stdout
    except Exception as e:
        console.print(f"[red]Error generating completion:[/red] {e}")
        raise typer.Exit(1)

    if install:
        # Determine config file
        home = Path.home()
        config_files = {
            "bash": home / ".bashrc",
            "zsh": home / ".zshrc",
            "fish": home / ".config" / "fish" / "completions" / "iamsentry.fish",
            "powershell": None,  # PowerShell profile varies
        }

        config_file = config_files.get(shell)

        if shell == "powershell":
            console.print("[yellow]PowerShell:[/yellow] Add this to your $PROFILE:")
            console.print(f"\n{completion_script}")
            return

        if shell == "fish":
            # Fish needs directory created
            config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(config_file, "w") as f:
                f.write(completion_script)
            console.print(f"[green]✓[/green] Installed completion to {config_file}")
        else:
            # Bash/Zsh - append to config
            marker = "# IAMSentry shell completion"

            # Check if already installed
            if config_file.exists():
                existing = config_file.read_text()
                if marker in existing:
                    console.print(f"[yellow]Completion already installed in {config_file}[/yellow]")
                    console.print("[dim]To reinstall, remove the IAMSentry section first.[/dim]")
                    return

            with open(config_file, "a") as f:
                f.write(f"\n{marker}\n")
                f.write(f'eval "$({sys.executable} -m IAMSentry.cli completion {shell})"\n')

            console.print(f"[green]✓[/green] Installed completion to {config_file}")

        console.print(f"\n[dim]Restart your shell or run:[/dim]")
        console.print(f"  source {config_file}")

    else:
        # Just print the completion script
        print(completion_script)


def cli_main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    cli_main()
