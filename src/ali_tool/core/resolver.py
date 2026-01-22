"""Template Resolver - Clean, simple template substitution engine."""

from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from .plugin import Plugin
from .registry import ServiceRegistry

Node = Union["Literal", "Variable", "Conditional", "ArrayLookup"]


@dataclass
class Literal:
    """Plain text node."""

    text: str


@dataclass
class Variable:
    """Variable substitution node."""

    name: str
    default: Optional[str] = None


@dataclass
class Conditional:
    """Conditional inclusion node."""

    var: str
    then_part: List[Node]  # List of nodes
    else_part: Optional[List[Node]] = None  # Optional else clause


@dataclass
class ArrayLookup:
    """Array lookup node for mapping values."""

    var: str
    mappings: Dict[str, str]  # key:value mappings
    default: Optional[str] = None


class TemplateParser:
    """Parse template strings into AST."""

    def __init__(self, template: str):
        self.template = template
        self.pos = 0
        self.length = len(template)

    def parse(self) -> List[Node]:
        """Parse template into list of nodes."""
        nodes = []
        text = ""

        while self.pos < self.length:
            # Triple braces for literal braces
            if self.peek(3) == "{{{":
                if text:
                    nodes.append(Literal(text))
                    text = ""
                self.pos += 3
                text += "{"
            elif self.peek(3) == "}}}":
                self.pos += 3
                text += "}"
            # Conditional
            elif self.peek(2) == "{?":
                if text:
                    nodes.append(Literal(text))
                    text = ""
                nodes.append(self.parse_conditional())
            # Variable
            elif self.peek(1) == "{":
                if text:
                    nodes.append(Literal(text))
                    text = ""
                nodes.append(self.parse_variable())
            else:
                text += self.template[self.pos]
                self.pos += 1

        if text:
            nodes.append(Literal(text))

        return nodes

    def peek(self, n: int) -> str:
        """Look ahead n characters."""
        return self.template[self.pos : self.pos + n]

    def parse_variable(self) -> Union[Variable, ArrayLookup]:
        """Parse {var}, {var|default}, or {var[k1:v1,k2:v2]}."""
        self.pos += 1

        end = self.template.find("}", self.pos)
        if end == -1:
            raise ValueError(f"Unclosed variable at position {self.pos}")

        content = self.template[self.pos : end]
        self.pos = end + 1

        if "[" in content and "]" in content:
            bracket_start = content.index("[")
            bracket_end = content.index("]")
            var_name = content[:bracket_start].strip()
            lookup_str = content[bracket_start + 1 : bracket_end]

            mappings = {}
            default = None

            for pair in lookup_str.split(","):
                if ":" in pair:
                    key, value = pair.split(":", 1)
                    key = key.strip()
                    value = value.strip()
                    if key == "default" or key == "_":
                        default = value
                    else:
                        mappings[key] = value

            return ArrayLookup(var_name, mappings, default)

        if "|" in content:
            name, default = content.split("|", 1)
            return Variable(name.strip(), default)
        else:
            return Variable(content.strip())

    def parse_conditional(self) -> Conditional:
        """Parse {?var:then} or {?var:then:else}."""
        self.pos += 2

        colon = self.template.find(":", self.pos)
        if colon == -1:
            raise ValueError(f"Invalid conditional at position {self.pos}")

        var = self.template[self.pos : colon].strip()
        self.pos = colon + 1

        then_text, has_else = self.extract_conditional_part()
        then_part = TemplateParser(then_text).parse()

        else_part = None
        if has_else:
            else_text, _ = self.extract_conditional_part()
            else_part = TemplateParser(else_text).parse()

        if self.pos < self.length and self.template[self.pos] == "}":
            self.pos += 1

        return Conditional(var, then_part, else_part)

    def extract_conditional_part(self) -> tuple[str, bool]:
        """Extract text until : or }, handling nested braces."""
        text = ""
        brace_depth = 0

        while self.pos < self.length:
            ch = self.template[self.pos]

            if ch == "{":
                brace_depth += 1
                text += ch
                self.pos += 1
            elif ch == "}":
                if brace_depth > 0:
                    brace_depth -= 1
                    text += ch
                    self.pos += 1
                else:
                    return text, False
            elif ch == ":" and brace_depth == 0:
                self.pos += 1
                return text, True
            else:
                text += ch
                self.pos += 1

        return text, False


class TemplateResolver:
    """Resolve template AST with context."""

    def __init__(self, context: Dict[str, Any]):
        self.context = context

    def resolve(self, nodes: List[Node]) -> str:
        """Resolve list of nodes to string."""
        result = []

        for node in nodes:
            if isinstance(node, Literal):
                result.append(node.text)
            elif isinstance(node, Variable):
                result.append(self.resolve_variable(node))
            elif isinstance(node, Conditional):
                result.append(self.resolve_conditional(node))
            elif isinstance(node, ArrayLookup):
                result.append(self.resolve_array_lookup(node))

        return "".join(result)

    def resolve_variable(self, node: Variable) -> str:
        """Resolve a variable node."""
        value = self.context.get(node.name)

        if value is None or value == "":
            if node.default is not None:
                return node.default
            return ""

        return str(value)

    def resolve_conditional(self, node: Conditional) -> str:
        """Resolve a conditional node."""
        value = self.context.get(node.var)

        if value is not None and value != "":
            return self.resolve(node.then_part)
        elif node.else_part is not None:
            return self.resolve(node.else_part)
        else:
            return ""

    def resolve_array_lookup(self, node: ArrayLookup) -> str:
        """Resolve an array lookup node."""
        value = self.context.get(node.var)

        if value is None or value == "":
            return node.default if node.default is not None else ""

        str_value = str(value)
        if str_value in node.mappings:
            return node.mappings[str_value]

        return node.default if node.default is not None else ""


def resolve_command(
    state: Dict[str, Any],
    plugin: Plugin,
    command: Dict[str, Any],
    registry: ServiceRegistry,
) -> str:
    """Resolve command template with state and services."""
    template = command.get("exec", "")
    if not template:
        return "Error: No exec defined"

    # Collect services and pre-resolve any that contain state variables
    services = collect_service_templates(registry)
    plugin_dir = str(plugin.path.parent)

    # First resolve services that might reference state variables
    resolved_services = {}
    base_context = {**state, "plugin_dir": plugin_dir}

    for name, service_template in services.items():
        # Only resolve if it contains variables from state
        if "{" in service_template:
            # Try to resolve with current state (but not other services to avoid recursion)
            resolved_services[name] = substitute(service_template, base_context)
        else:
            resolved_services[name] = service_template

    # Now resolve the command with both services and state
    context = {**resolved_services, **base_context}
    return substitute(template, context)


def collect_service_templates(registry: ServiceRegistry) -> Dict[str, str]:
    """Collect all service templates from plugins."""
    templates = {}

    for plugin in registry.plugins:
        plugin_services = plugin.config.get("services", {})

        for service_name, service_def in plugin_services.items():
            if isinstance(service_def, str):
                templates[service_name] = service_def
            elif isinstance(service_def, dict):
                template = service_def.get("template", "")
                if template:
                    templates[service_name] = template

    return templates


def collect_selectors(registry: ServiceRegistry) -> Dict[str, Dict[str, str]]:
    """Collect all selectors from plugins."""
    selectors = {}

    for plugin in registry.plugins:
        plugin_selectors = plugin.selectors
        for selector_name, selector_def in plugin_selectors.items():
            selectors[selector_name] = selector_def

    return selectors


def expand_selectors(
    state: Dict[str, Any],
    selectors: Dict[str, Dict[str, str]],
    registry: ServiceRegistry,
) -> Dict[str, Any]:
    """Expand selectors by adding their exec commands to state."""
    # First get service templates for resolving selector exec strings
    services = collect_service_templates(registry)

    for field_name, value in list(state.items()):
        if field_name.startswith("_") or field_name.endswith("_exec"):
            continue

        if not isinstance(value, str):
            continue

        if value in selectors:
            selector_def = selectors[value]
            exec_template = selector_def.get("exec", "")
            # Resolve any service references in the selector's exec
            if exec_template and "{" in exec_template:
                exec_resolved = substitute(exec_template, services)
                state[f"{field_name}_exec"] = exec_resolved
            else:
                state[f"{field_name}_exec"] = exec_template

    return state


def substitute(template: str, context: Dict[str, Any]) -> str:
    """Substitute template with context (single-pass).

    Args:
        template: Template string with {var} placeholders
        context: Variable values for substitution

    Returns:
        Resolved template string
    """
    parser = TemplateParser(template)
    nodes = parser.parse()
    resolver = TemplateResolver(context)
    result = resolver.resolve(nodes)
    return result.strip()
