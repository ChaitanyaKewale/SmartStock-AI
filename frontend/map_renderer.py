"""SVG Warehouse Map rendering engine for SmartStock AI.

Renders an authoritative 16x12 vector graphics grid with:
- Walkable aisles
- Physical storage racks with shelf IDs
- Dedicated accessible pickup positions
- Distribution station dock
- Fixed pillars and user-placed obstacles
- Restricted hazard zones
- Robot position and orientation arrow
- Selected shelf inspection highlights
- Comprehensive legend and coordinate markers
- Safe HTML table fallback
"""

from __future__ import annotations

import html
from typing import Optional, Set, Tuple
from simulation.warehouse import WarehouseGrid
from simulation.models import Position, RobotDirection, Robot


def render_warehouse_svg(
    grid: WarehouseGrid,
    robot: Optional[Robot] = None,
    selected_shelf_id: Optional[str] = None,
    hover_cell: Optional[Tuple[int, int]] = None,
    planned_route: Optional[list[Position]] = None,
    traversed_route: Optional[list[Position]] = None
) -> str:
    """Generate clean, scalable, standalone SVG markup for the warehouse grid."""
    active_robot = robot or grid.robot_initial
    cell_size = 46
    margin_left = 32
    margin_top = 28
    svg_width = margin_left + grid.width * cell_size + 16
    svg_height = margin_top + grid.height * cell_size + 16

    # Collect pickup positions for high-visibility indicator
    pickup_coords: Set[Tuple[int, int]] = {
        (s.pickup_position.x, s.pickup_position.y) for s in grid.racks_by_id.values()
    }

    selected_shelf = grid.racks_by_id.get(selected_shelf_id) if selected_shelf_id else None
    selected_coord = (selected_shelf.x, selected_shelf.y) if selected_shelf else None

    # Route sets for rendering paths if present
    planned_set = {(p.x, p.y) for p in (planned_route or [])}
    traversed_set = {(p.x, p.y) for p in (traversed_route or [])}

    svg_parts = []
    svg_parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_width} {svg_height}" '
        f'style="width: 100%; max-width: {svg_width}px; background: #080d1a; border-radius: 6px; '
        f'border: 1px solid #1f2937; display: block; margin: 0 auto; user-select: none;">'
    )

    # Definitions: patterns, markers, and filters
    svg_parts.append("""
    <defs>
      <!-- Hazard stripes for restricted zones -->
      <pattern id="hazard-stripes" width="10" height="10" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">
        <line x1="0" y1="0" x2="0" y2="10" stroke="#7f1d1d" stroke-width="5" />
        <line x1="5" y1="0" x2="5" y2="10" stroke="#450a0a" stroke-width="5" />
      </pattern>
      <!-- Obstacle crosshatch -->
      <pattern id="obstacle-hatch" width="8" height="8" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">
        <line x1="0" y1="0" x2="0" y2="8" stroke="#475569" stroke-width="3" />
        <line x1="4" y1="0" x2="4" y2="8" stroke="#1e293b" stroke-width="5" />
      </pattern>
      <!-- User barrier pattern -->
      <pattern id="user-barrier" width="8" height="8" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">
        <line x1="0" y1="0" x2="0" y2="8" stroke="#d97706" stroke-width="3" />
        <line x1="4" y1="0" x2="4" y2="8" stroke="#78350f" stroke-width="5" />
      </pattern>
    </defs>
    """)

    # 1. Coordinate Column Labels (Top)
    for col in range(grid.width):
        cx = margin_left + col * cell_size + (cell_size / 2)
        cy = margin_top - 10
        svg_parts.append(
            f'<text x="{cx}" y="{cy}" fill="#64748b" font-size="11" font-family="monospace" '
            f'text-anchor="middle" font-weight="600">{col}</text>'
        )

    # 2. Coordinate Row Labels (Left)
    for row in range(grid.height):
        cx = margin_left - 12
        cy = margin_top + row * cell_size + (cell_size / 2) + 4
        svg_parts.append(
            f'<text x="{cx}" y="{cy}" fill="#64748b" font-size="11" font-family="monospace" '
            f'text-anchor="middle" font-weight="600">{row}</text>'
        )

    # 3. Grid Cells
    for row in range(grid.height):
        for col in range(grid.width):
            x = margin_left + col * cell_size
            y = margin_top + row * cell_size
            is_sel = (col, row) == selected_coord

            # Distribution Station
            if grid.is_distribution_station(col, row):
                svg_parts.append(
                    f'<rect x="{x}" y="{y}" width="{cell_size}" height="{cell_size}" '
                    f'fill="#0369a1" stroke="#38bdf8" stroke-width="2" rx="4" />'
                    f'<text x="{x + cell_size/2}" y="{y + 18}" fill="#ffffff" font-size="10" '
                    f'font-family="monospace" font-weight="700" text-anchor="middle">STATION</text>'
                    f'<text x="{x + cell_size/2}" y="{y + 32}" fill="#bae6fd" font-size="9" '
                    f'font-family="monospace" text-anchor="middle">DS-01</text>'
                )

            # Physical Storage Rack
            elif grid.is_rack(col, row):
                shelf = grid.get_shelf_at(col, row)
                shelf_id = shelf.id if shelf else "RACK"
                stroke_color = "#60a5fa" if not is_sel else "#38bdf8"
                stroke_width = "1.5" if not is_sel else "3"
                fill_color = "#1e293b" if not is_sel else "#1e3a8a"
                badge_bg = "#0f172a" if not is_sel else "#1d4ed8"

                svg_parts.append(
                    f'<rect x="{x+2}" y="{y+2}" width="{cell_size-4}" height="{cell_size-4}" '
                    f'fill="{fill_color}" stroke="{stroke_color}" stroke-width="{stroke_width}" rx="4" />'
                    f'<rect x="{x+6}" y="{y+6}" width="{cell_size-12}" height="14" fill="{badge_bg}" rx="2" />'
                    f'<text x="{x + cell_size/2}" y="{y + 17}" fill="#93c5fd" font-size="10" '
                    f'font-family="monospace" font-weight="700" text-anchor="middle">{shelf_id}</text>'
                    f'<text x="{x + cell_size/2}" y="{y + 33}" fill="#cbd5e1" font-size="8" '
                    f'font-family="sans-serif" text-anchor="middle">Items: {shelf.current_stock_count if shelf else 0}</text>'
                )

            # Fixed Pillar Obstacle
            elif (col, row) in grid.fixed_obstacles:
                svg_parts.append(
                    f'<rect x="{x+2}" y="{y+2}" width="{cell_size-4}" height="{cell_size-4}" '
                    f'fill="url(#obstacle-hatch)" stroke="#64748b" stroke-width="1.5" rx="3" />'
                    f'<circle cx="{x + cell_size/2}" cy="{y + cell_size/2}" r="5" fill="#334155" stroke="#94a3b8" />'
                )

            # User-Added Obstacle Barrier
            elif (col, row) in grid.user_added_obstacles:
                svg_parts.append(
                    f'<rect x="{x+2}" y="{y+2}" width="{cell_size-4}" height="{cell_size-4}" '
                    f'fill="url(#user-barrier)" stroke="#f59e0b" stroke-width="2" rx="3" />'
                    f'<text x="{x + cell_size/2}" y="{y + cell_size/2 + 3}" fill="#fef3c7" '
                    f'font-size="9" font-family="monospace" font-weight="700" text-anchor="middle">BARRIER</text>'
                )

            # Restricted Hazard Zone
            elif grid.is_restricted(col, row):
                svg_parts.append(
                    f'<rect x="{x+2}" y="{y+2}" width="{cell_size-4}" height="{cell_size-4}" '
                    f'fill="url(#hazard-stripes)" stroke="#dc2626" stroke-width="1.5" rx="3" />'
                    f'<text x="{x + cell_size/2}" y="{y + cell_size/2 + 3}" fill="#fecaca" '
                    f'font-size="8" font-family="monospace" text-anchor="middle">RESTRICTED</text>'
                )

            # Walkable Aisle Floor (with pickup or route indicators)
            else:
                is_pickup = (col, row) in pickup_coords
                is_planned = (col, row) in planned_set
                is_traversed = (col, row) in traversed_set

                cell_fill = "#0f172a"
                border_color = "#1e293b"
                border_width = "1"

                if is_traversed:
                    cell_fill = "#064e3b"
                elif is_planned:
                    cell_fill = "#172554"

                svg_parts.append(
                    f'<rect x="{x}" y="{y}" width="{cell_size}" height="{cell_size}" '
                    f'fill="{cell_fill}" stroke="{border_color}" stroke-width="{border_width}" />'
                )

                # Pickup Bay Indicator
                if is_pickup:
                    svg_parts.append(
                        f'<rect x="{x+5}" y="{y+5}" width="{cell_size-10}" height="{cell_size-10}" '
                        f'fill="none" stroke="#059669" stroke-width="1.5" stroke-dasharray="3 3" rx="3" />'
                        f'<circle cx="{x + cell_size/2}" cy="{y + cell_size/2}" r="3" fill="#10b981" />'
                    )

    # 4. Highlight Selected Shelf Pickup Connection
    if selected_shelf:
        s_cx = margin_left + selected_shelf.x * cell_size + cell_size / 2
        s_cy = margin_top + selected_shelf.y * cell_size + cell_size / 2
        p_cx = margin_left + selected_shelf.pickup_position.x * cell_size + cell_size / 2
        p_cy = margin_top + selected_shelf.pickup_position.y * cell_size + cell_size / 2

        svg_parts.append(
            f'<line x1="{s_cx}" y1="{s_cy}" x2="{p_cx}" y2="{p_cy}" '
            f'stroke="#38bdf8" stroke-width="2.5" stroke-dasharray="4 2" />'
            f'<circle cx="{p_cx}" cy="{p_cy}" r="7" fill="none" stroke="#38bdf8" stroke-width="2" />'
        )

    # 5. Render Robot Unit
    rx = margin_left + active_robot.position.x * cell_size + cell_size / 2
    ry = margin_top + active_robot.position.y * cell_size + cell_size / 2
    rot = active_robot.facing.rotation_degrees

    svg_parts.append(f"""
    <g transform="translate({rx}, {ry}) rotate({rot})">
      <!-- Robot Outer Halo -->
      <circle cx="0" cy="0" r="17" fill="none" stroke="#10b981" stroke-width="2" opacity="0.8" />
      <!-- Chassis Body -->
      <circle cx="0" cy="0" r="14" fill="#047857" stroke="#34d399" stroke-width="1.5" />
      <!-- Direction Pointer Arrow (points North by default) -->
      <polygon points="0,-12 6,-2 -6,-2" fill="#ffffff" />
      <circle cx="0" cy="3" r="3" fill="#065f46" />
    </g>
    """)

    svg_parts.append('</svg>')
    return "".join(svg_parts)


def render_map_fallback(grid: WarehouseGrid) -> str:
    """Safe HTML table fallback rendered if SVG generation or component display encounters issues."""
    rows = []
    rows.append('<div style="overflow-x:auto; font-family: monospace; font-size: 11px;">')
    rows.append('<table style="border-collapse: collapse; border: 1px solid #334155; margin: 0 auto;">')

    for y in range(grid.height):
        rows.append('<tr>')
        for x in range(grid.width):
            if (x, y) == (grid.distribution_station.x, grid.distribution_station.y):
                bg, txt = "#0284c7", "DS"
            elif (x, y) == (grid.robot_initial.position.x, grid.robot_initial.position.y):
                bg, txt = "#10b981", "BOT"
            elif grid.is_rack(x, y):
                shelf = grid.get_shelf_at(x, y)
                bg, txt = "#1e3a5f", shelf.id if shelf else "RK"
            elif (x, y) in grid.fixed_obstacles:
                bg, txt = "#475569", "OBS"
            elif (x, y) in grid.user_added_obstacles:
                bg, txt = "#d97706", "BAR"
            elif grid.is_restricted(x, y):
                bg, txt = "#7f1d1d", "RES"
            else:
                bg, txt = "#0f172a", "."
            rows.append(
                f'<td style="background:{bg}; color:#f8fafc; border:1px solid #1e293b; '
                f'width:34px; height:34px; text-align:center;">{html.escape(txt)}</td>'
            )
        rows.append('</tr>')

    rows.append('</table></div>')
    return "".join(rows)
