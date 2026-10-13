"""Build demo/library/skynode_installation_guide.pdf, a fictional installation guide.

    uv run --no-project --with reportlab python demo/tools/build_installation_guide.py

The content is invented for testing retrieval across documents: it repeats a few facts from
the knowledge base (near-duplicate passages) and adds facts found nowhere else (the SolarKit,
the cellular data plan, mounting heights).
"""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    ListFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUT = Path(__file__).resolve().parents[1] / "library" / "skynode_installation_guide.pdf"
styles = getSampleStyleSheet()
H1, H2, BODY = styles["Title"], styles["Heading2"], styles["BodyText"]


def p(text: str) -> Paragraph:
    return Paragraph(text, BODY)


def bullets(*items: str) -> ListFlowable:
    return ListFlowable([p(i) for i in items], bulletType="bullet", leftIndent=14)


def table(rows: list[list[str]]) -> Table:
    t = Table(rows, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    return t


def footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.drawString(inch, 0.5 * inch, "SkyNode Installation Guide, edition 2 (2026)")
    canvas.drawRightString(LETTER[0] - inch, 0.5 * inch, f"Page {doc.page}")
    canvas.restoreState()


story = [
    Paragraph("SkyNode Installation Guide", H1),
    p(
        "<i>Edition 2 (2026), for SkyNode Lite, Pro and Max. Aurora Instruments is a fictional "
        "company created for demonstration and testing; all names, figures and products are "
        "invented.</i>"
    ),
    Spacer(1, 10),
    Paragraph("1. Choosing a site", H2),
    p(
        "Good readings depend more on where the sensors stand than on the model. Mount the "
        "temperature and humidity sensor 1.5 to 2 m above the ground, over grass or bare soil "
        "rather than paving, and at least 4 m from walls, which store and radiate heat."
    ),
    bullets(
        "<b>Wind sensor:</b> ideally 10 m above the ground. Where that isn't practical, mount it "
        "at least 2 m higher than any obstacle within 10 m, such as a roof ridge or tree.",
        "<b>Rain gauge:</b> level, open to the sky, and at least twice as far from any tree or "
        "building as that object is tall.",
        "<b>Soil sensors (Max only):</b> bury the soil moisture probe at root depth, typically "
        "15 to 30 cm, and keep the leaf wetness sensor at canopy height.",
    ),
    p(
        "Every outdoor module must stay within the wireless range of the hub: 60 m for the "
        "SkyNode Lite, 120 m for the Pro and 300 m for the Max, measured in open air. Walls, "
        "hills and dense vines shorten the range."
    ),
    PageBreak(),
    Paragraph("2. Power", H2),
    p(
        "The central hub is powered by the included USB-C adapter and contains a backup battery "
        "that keeps the station running for up to 8 hours during a power outage. Each outdoor "
        "sensor module runs on two AA lithium batteries; use lithium rather than alkaline cells "
        "in freezing conditions."
    ),
    p(
        "Sensor battery life is up to 12 months on the Lite, 18 months on the Pro and 24 months "
        "on the Max in temperate climates. Below -20°C, expect about half of that."
    ),
    Paragraph("SolarKit: running a hub without mains power", H2),
    p(
        "The <b>SolarKit</b> accessory ($79) keeps a hub running where there is no mains power. "
        "It combines a 10 W solar panel with a 20,000 mAh battery pack, which stores about 4 "
        "days of power for cloudy weather. With at least 3 hours of direct sun a day it runs the "
        "hub indefinitely."
    ),
    p(
        "The SolarKit fits the <b>SkyNode Pro and Max hubs only</b>. The Lite hub takes power "
        "through a different connector and cannot use the SolarKit; it needs mains power."
    ),
    PageBreak(),
    Paragraph("3. Connectivity", H2),
    p(
        "During setup the Lite and Pro join your Wi-Fi network. The Lite needs a 2.4 GHz network "
        "(see the firmware release notes for later hardware revisions); the Pro supports 2.4 and "
        "5 GHz. The Max uses Wi-Fi where available and falls back to its built-in cellular modem."
    ),
    Paragraph("Cellular data for the SkyNode Max", H2),
    p(
        "Every Max ships with an Aurora SIM card already fitted. The first 12 months of cellular "
        "data are included in the purchase price, up to 1 GB a month, which covers normal use at "
        "a 10-second update interval. After the first year, cellular data needs the Aurora "
        "Cellular plan:"
    ),
    table(
        [
            ["Aurora Cellular plan", "Price", "Data"],
            ["Monthly", "$3 a month", "1 GB a month"],
            ["Annual", "$30 a year", "1 GB a month"],
        ]
    ),
    Spacer(1, 6),
    p(
        "Without Wi-Fi or a cellular plan, the Max keeps logging locally (90 days of onboard "
        "storage), and readings sync once a connection returns."
    ),
    PageBreak(),
    Paragraph("4. Setting up", H2),
    bullets(
        "Install the Aurora app, create an account and choose <b>Add station</b>.",
        "Plug in the hub, or connect the SolarKit, and wait for the status light to turn "
        "steady green.",
        "Pair each sensor module by holding its pairing button for 3 seconds.",
        "Calibrate the wind direction: point the arrow on the wind sensor to true north and "
        "confirm in the app.",
        "Register the station in the app within 30 days of purchase to extend the warranty "
        "from 2 to 3 years at no extra cost.",
    ),
    Paragraph("Troubleshooting", H2),
    p(
        "If a sensor stops reporting, first confirm it is within the model's wireless range of "
        "the hub, then check the battery level in the app. If both are fine, remove and reinsert "
        "the batteries to make the sensor re-pair with the hub."
    ),
]

doc = SimpleDocTemplate(
    str(OUT),
    pagesize=LETTER,
    title="SkyNode Installation Guide",
    author="Aurora Instruments (fictional)",
)
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(f"Wrote {OUT}")
