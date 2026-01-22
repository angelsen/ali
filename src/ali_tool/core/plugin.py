"""Plugin - Loads and holds plugin YAML configuration."""

import sys
import shutil
import subprocess
import yaml
from pathlib import Path


class Plugin:
    """A plugin loaded from YAML. Just data, no logic."""

    def __init__(self, yaml_path: Path):
        self.path = yaml_path
        self.name = yaml_path.parent.name

        with open(yaml_path) as f:
            self.config = yaml.safe_load(f)

        self.version = self.config.get("version", "1.0")
        self.description = self.config.get("description", "")
        self.provides = self.config.get("provides", {})
        self.requires = self.config.get("requires", [])
        self.grammar = self.config.get("grammar", {})

        vocab = self.config.get("vocabulary", {})
        self.verbs = set(vocab.get("verbs", []))

        self.expectations = self.config.get("expectations", {})
        self.inference = self.config.get("inference", [])
        self.commands = self.config.get("commands", [])
        self.selectors = self.config.get("selectors", {})
        self.context = self.config.get("context", {})
        self.integration = self.config.get("integration", {})

    def is_active(self) -> bool:
        """Check if plugin should be active based on context requirements."""
        if not self.context:
            return True

        if "requires_env" in self.context:
            import os

            required = self.context["requires_env"]
            if isinstance(required, str):
                required = [required]
            for env_var in required:
                if env_var not in os.environ:
                    return False

        return True

    def init(self) -> int:
        """Initialize plugin integration files and show instructions.

        Returns:
            Exit code: 0 for success, 1 for error
        """
        if not self.integration:
            print(
                f"Plugin '{self.name}' has no integration configuration",
                file=sys.stderr,
            )
            return 1

        print(f"Initializing {self.name} integration...", file=sys.stderr)

        # Copy config files
        for file_info in self.integration.get("files", []):
            source = self.path.parent / file_info["source"]
            target = Path(file_info["target"]).expanduser()

            if not source.exists():
                print(f"✗ Source file not found: {source}", file=sys.stderr)
                continue

            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy(source, target)
                print(f"✓ Copied {file_info['source']} to {target}", file=sys.stderr)
            except Exception as e:
                print(f"✗ Failed to copy {file_info['source']}: {e}", file=sys.stderr)

        # Check if already integrated
        check_cmd = self.integration.get("check_command")
        already_integrated = False
        if check_cmd:
            result = subprocess.run(check_cmd, shell=True, capture_output=True)
            already_integrated = result.returncode == 0

        if already_integrated:
            print("✓ Already integrated", file=sys.stderr)
        else:
            # Offer to inject config line
            inject = self.integration.get("inject")
            if inject:
                target_file = Path(inject["file"]).expanduser()
                line = inject["line"]

                try:
                    response = input(f"Add to {target_file}? [Y/n] ").strip().lower()
                except EOFError:
                    response = "n"

                if response in ("", "y", "yes"):
                    try:
                        with open(target_file, "a") as f:
                            f.write(f"\n# ALI integration\n{line}\n")
                        print(f"✓ Added to {target_file}", file=sys.stderr)
                    except Exception as e:
                        print(f"✗ Failed to write: {e}", file=sys.stderr)
                        print("\nManual setup:", file=sys.stderr)
                        print(f"  echo '{line}' >> {target_file}", file=sys.stderr)
                else:
                    print("\nManual setup:", file=sys.stderr)
                    print(f"  echo '{line}' >> {target_file}", file=sys.stderr)

        usage = self.integration.get("usage")
        if usage:
            print(f"\nUsage: {usage}", file=sys.stderr)

        return 0

    def __repr__(self):
        """Return string representation of plugin."""
        return f"Plugin({self.name} v{self.version})"
