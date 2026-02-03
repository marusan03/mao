"""
Docker Sandbox Manager for MAO

Manages Docker AI Sandboxes to run MAO in isolated MicroVM environments.
This protects the host system while allowing full agent functionality.

Architecture:
    Host
      └─ Docker Sandbox (MicroVM)
           └─ MAO tmux session
                ├─ CTO (pane 0)
                ├─ Agent-1 (pane 1) → worktree-1/
                ├─ Agent-2 (pane 2) → worktree-2/
                └─ ...
"""

import subprocess
import shutil
from pathlib import Path
from typing import Optional, List


class SandboxManager:
    """Docker Sandbox management for MAO projects."""

    TEMPLATE_NAME = "mao-sandbox:latest"

    def __init__(self, project_path: Path):
        """Initialize SandboxManager.

        Args:
            project_path: Path to the project directory to run in sandbox
        """
        self.project_path = project_path.resolve()
        self.sandbox_name = f"mao-{self.project_path.name}"

    def is_available(self) -> bool:
        """Check if Docker Sandbox is available.

        Returns:
            True if docker sandbox command is available
        """
        if not shutil.which("docker"):
            return False

        result = subprocess.run(
            ["docker", "sandbox", "--help"],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0

    def is_running(self) -> bool:
        """Check if the sandbox is currently running.

        Returns:
            True if sandbox with this name is running
        """
        result = subprocess.run(
            ["docker", "sandbox", "ls", "--format", "{{.Name}}"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return False
        return self.sandbox_name in result.stdout.splitlines()

    def list_sandboxes(self) -> List[dict]:
        """List all MAO sandboxes.

        Returns:
            List of sandbox info dictionaries
        """
        result = subprocess.run(
            ["docker", "sandbox", "ls", "--format", "{{.Name}}\t{{.Status}}"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return []

        sandboxes = []
        for line in result.stdout.strip().splitlines():
            if not line:
                continue
            parts = line.split("\t")
            name = parts[0]
            status = parts[1] if len(parts) > 1 else "unknown"
            # Only show MAO-related sandboxes
            if name.startswith("mao-"):
                sandboxes.append({"name": name, "status": status})
        return sandboxes

    def template_exists(self) -> bool:
        """Check if the MAO sandbox template image exists.

        Returns:
            True if mao-sandbox:latest image exists locally
        """
        result = subprocess.run(
            ["docker", "images", "-q", self.TEMPLATE_NAME],
            capture_output=True,
            text=True,
        )
        return bool(result.stdout.strip())

    def build_template(self) -> bool:
        """Build the MAO sandbox template image.

        Returns:
            True if build succeeded
        """
        dockerfile = Path(__file__).parent.parent / "docker" / "Dockerfile.mao-sandbox"
        if not dockerfile.exists():
            return False

        cmd = [
            "docker",
            "build",
            "-t",
            self.TEMPLATE_NAME,
            "-f",
            str(dockerfile),
            str(dockerfile.parent),
        ]
        result = subprocess.run(cmd)
        return result.returncode == 0

    def start(
        self,
        prompt: Optional[str] = None,
        use_custom_template: bool = True,
        model: str = "sonnet",
    ) -> bool:
        """Start MAO inside a Docker Sandbox.

        Args:
            prompt: Optional initial task prompt
            use_custom_template: Use MAO-preinstalled template (recommended)
            model: Model to use for CTO (sonnet, opus, haiku)

        Returns:
            True if sandbox started successfully
        """
        cmd = [
            "docker",
            "sandbox",
            "run",
            "--name",
            self.sandbox_name,
        ]

        # Use custom template with MAO preinstalled
        if use_custom_template and self.template_exists():
            cmd.extend(["--template", self.TEMPLATE_NAME])

        # Add claude and project path
        cmd.extend(["claude", str(self.project_path)])

        # If prompt provided, run mao start inside sandbox
        if prompt:
            mao_cmd = f"mao start --model {model} \"{prompt}\""
            cmd.extend(["--", "bash", "-c", mao_cmd])

        result = subprocess.run(cmd)
        return result.returncode == 0

    def attach(self) -> bool:
        """Attach to an existing MAO sandbox.

        Returns:
            True if attach succeeded
        """
        if not self.is_running():
            return False

        cmd = ["docker", "sandbox", "run", self.sandbox_name]
        result = subprocess.run(cmd)
        return result.returncode == 0

    def remove(self, force: bool = False) -> bool:
        """Remove the MAO sandbox.

        Args:
            force: Force removal even if running

        Returns:
            True if removal succeeded
        """
        cmd = ["docker", "sandbox", "rm"]
        if force:
            cmd.append("--force")
        cmd.append(self.sandbox_name)

        result = subprocess.run(cmd)
        return result.returncode == 0

    def exec(self, command: str) -> subprocess.CompletedProcess:
        """Execute a command inside the running sandbox.

        Args:
            command: Command to execute

        Returns:
            CompletedProcess with results
        """
        cmd = [
            "docker",
            "sandbox",
            "exec",
            self.sandbox_name,
            "bash",
            "-c",
            command,
        ]
        return subprocess.run(cmd, capture_output=True, text=True)

    def get_status(self) -> Optional[str]:
        """Get the status of this sandbox.

        Returns:
            Status string or None if not found
        """
        sandboxes = self.list_sandboxes()
        for sb in sandboxes:
            if sb["name"] == self.sandbox_name:
                return sb["status"]
        return None
