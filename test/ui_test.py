from rich.console import Console
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich.align import Align
from rich.box import ROUNDED

console = Console()

# =========================
# LAYOUT
# =========================

def create_layout():
    layout = Layout()

    layout.split_column(
        Layout(name="main", ratio=1),
    )

    layout["main"].split_row(
        Layout(name="left"),
        Layout(name="right")
    )

    return layout

# =========================
# LEFT PANEL (LOGO + STATUS)
# =========================

def left_panel():
    logo = Text("""
   ░██░ ░██░
    ░████░
   ░██░ ░██░
""", style="bold magenta")

    content = Text()
    content.append("Welcome back, Bhavesh!\n\n", style="bold white")
    content.append("WhiteNet CLI v1.0\n", style="cyan")
    content.append("\n")
    content.append("✔ Identity Layer Active\n", style="green")
    content.append("✔ IPv6 Binding Enabled\n", style="green")
    content.append("✔ Zero Trust Mode ON\n", style="green")

    return Panel(
        Align.center(logo + content),
        border_style="red",
        box=ROUNDED,
        title="WhiteNet",
        title_align="left"
    )

# =========================
# RIGHT PANEL (TIPS)
# =========================

def right_panel():
    content = Text()

    content.append("Tips for getting started\n\n", style="bold white")

    content.append("Run: issue --user <name>\n", style="cyan")
    content.append("Run: bind --cert cert.json\n", style="cyan")
    content.append("Run: handshake --ipv6 <ip>\n", style="cyan")

    content.append("\nRecent activity\n", style="bold white")
    content.append("No recent activity\n", style="dim")

    return Panel(
        content,
        border_style="red",
        box=ROUNDED,
        title="Guide",
        title_align="left"
    )

# =========================
# MAIN RENDER
# =========================

def main():
    layout = create_layout()

    layout["left"].update(left_panel())
    layout["right"].update(right_panel())

    console.clear()
    console.print(layout)


if __name__ == "__main__":
    main()