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
# LEFT PANEL (CREEPER + STATUS)
# =========================

def left_panel():
    logo = Text("""
⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⡟⠉⠉⠉⠉⢻⣿⣿⣿⣿⡟⠉⠉⠉⠉⢻⣿⣿⣿
⣿⣿⣿⡇⠀⠀⠀⠀⢸⣿⣿⣿⣿⡇⠀⠀⠀⠀⢸⣿⣿⣿
⣿⣿⣿⣇⣀⣀⣀⣀⡸⠿⠿⠿⠿⢇⣀⣀⣀⣀⣸⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⡇⠀⠀⠀⠀⢸⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⠉⠉⠁⠀⠀⠀⠀⠈⠉⠉⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⠀⠀⣶⣶⣶⣶⣶⣶⠀⠀⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣶⣾⣿⣿⣿⣿⣿⣿⣷⣶⣿⣿⣿⣿⣿⣿
⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿
""", style="bold #22c55e")

    content = Text()
    content.append("\nWelcome back, Bhavesh!\n\n", style="bold white")
    content.append("WhiteNet CLI v1.0\n", style="cyan")
    content.append("\n")
    content.append("✔ Identity Layer Active\n", style="#22c55e")
    content.append("✔ IPv6 Binding Enabled\n", style="#22c55e")
    content.append("✔ Zero Trust Mode ON\n", style="#22c55e")

    return Panel(
        Align.center(logo + content),
        border_style="red",
        padding=(1, 3),
        box=ROUNDED,
        title="WhiteNet",
        title_align="left"
    )

# =========================
# RIGHT PANEL (GUIDE)
# =========================

def right_panel():
    content = Text()

    content.append("Tips for getting started\n\n", style="bold white")

    content.append("issue --user <name>\n", style="cyan")
    content.append("bind --cert cert.json\n", style="cyan")
    content.append("handshake --ipv6 <ip>\n", style="cyan")
    content.append("send --sender <ip1> --receiver <ip2>\n", style="cyan")

    content.append("\nRecent activity\n", style="bold white")
    content.append("No recent activity\n", style="dim")

    return Panel(
        content,
        border_style="red",
        padding=(1, 2),
        box=ROUNDED,
        title="Guide",
        title_align="left"
    )

# =========================
# MAIN
# =========================

def main():
    layout = create_layout()

    layout["left"].update(left_panel())
    layout["right"].update(right_panel())

    console.clear()
    console.print(layout)

# =========================

if __name__ == "__main__":
    main()