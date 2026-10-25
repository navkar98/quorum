import { useState } from "react";
import { CrowdBuilding, IncidentHeatCell, MapBuilding } from "../shared/types";

type Mode = "incident" | "crowd";

interface Landmark { label: string; x: number; y: number; }

// Color scale helpers. Incident mode is keyed on system assessment (NOT raw density),
// crowd mode on device-count intensity. They are intentionally different scales.
function incidentColor(cell?: IncidentHeatCell): string {
  if (!cell) return "#1e293b";
  switch (cell.system_assessment) {
    case "potential_impact": return "#b91c1c";
    case "conflicting_evidence": return "#d97706";
    default: return cell.report_count > 0 ? "#475569" : "#1e293b";
  }
}

function crowdColor(total: number, max: number): string {
  if (total === 0) return "#1e293b";
  const t = Math.min(1, total / Math.max(1, max));
  const r = Math.round(30 + t * 10);
  const g = Math.round(41 + t * 150);
  const b = Math.round(59 + t * 150);
  return `rgb(${r},${g},${b})`;
}

interface HoverState { buildingId: number; left: number; top: number; }

export default function CampusMap({
  mode, buildings, incidentCells, crowd, landmarks = [], onSelect,
}: {
  mode: Mode;
  buildings: MapBuilding[];
  incidentCells: IncidentHeatCell[];
  crowd: CrowdBuilding[];
  landmarks?: Landmark[];
  onSelect?: (buildingId: number) => void;
}) {
  const [hover, setHover] = useState<HoverState | null>(null);

  const maxCrowd = Math.max(1, ...crowd.map((c) => c.total));

  // Most-severe incident cell per building (for the map glyph color).
  const incidentByBuilding = new Map<number, IncidentHeatCell>();
  for (const c of incidentCells) {
    const prev = incidentByBuilding.get(c.building_id);
    const rank = (x: IncidentHeatCell) =>
      x.system_assessment === "potential_impact" ? 3 :
      x.system_assessment === "conflicting_evidence" ? 2 : 1;
    if (!prev || rank(c) > rank(prev)) incidentByBuilding.set(c.building_id, c);
  }
  // All incident cells per building, keyed by floor, for the per-floor tooltip.
  const incidentByBuildingFloor = new Map<number, Map<number | null, IncidentHeatCell>>();
  for (const c of incidentCells) {
    if (!incidentByBuildingFloor.has(c.building_id)) incidentByBuildingFloor.set(c.building_id, new Map());
    incidentByBuildingFloor.get(c.building_id)!.set(c.floor, c);
  }
  const crowdByBuilding = new Map(crowd.map((c) => [c.building_id, c]));

  const hoveredBuilding = hover ? buildings.find((b) => b.id === hover.buildingId) : null;

  function onEnter(e: React.MouseEvent, buildingId: number) {
    const wrap = (e.currentTarget as SVGElement).closest(".map-wrap") as HTMLElement | null;
    if (!wrap) return;
    const rect = wrap.getBoundingClientRect();
    setHover({
      buildingId,
      left: e.clientX - rect.left,
      top: e.clientY - rect.top,
    });
  }

  return (
    <div className="map-wrap" style={{ position: "relative" }} onMouseLeave={() => setHover(null)}>
      <svg viewBox="0 0 100 100" width="100%" height="480" role="img"
        aria-label="Approximate UMass Boston campus map">
        {/* water / land backdrop approximating the waterfront campus */}
        <rect x="0" y="0" width="100" height="100" fill="#0b1b2b" />
        <path d="M0,70 Q30,64 50,72 T100,70 L100,100 L0,100 Z" fill="#0e2435" opacity="0.9" />
        <rect x="8" y="6" width="86" height="60" rx="3" fill="#10261c" opacity="0.5" />
        {/* University Drive loop (approx) */}
        <path d="M22,14 H78 Q84,14 84,22 V52 Q84,60 76,62 H30 Q22,62 22,52 Z"
          fill="none" stroke="#b4541f" strokeWidth="1.1" opacity="0.6" />

        {landmarks.map((l) => (
          <text key={l.label} x={l.x} y={l.y} fontSize="1.9" fill="#5b7490"
            textAnchor="middle" fontStyle="italic">{l.label}</text>
        ))}

        {buildings.map((b) => {
          const fill =
            mode === "incident"
              ? incidentColor(incidentByBuilding.get(b.id))
              : crowdColor(crowdByBuilding.get(b.id)?.total ?? 0, maxCrowd);
          const label =
            mode === "incident"
              ? incidentByBuilding.get(b.id)?.report_count ?? 0
              : crowdByBuilding.get(b.id)?.total ?? 0;
          const isHovered = hover?.buildingId === b.id;
          return (
            <g key={b.id}
              onClick={() => onSelect?.(b.id)}
              onMouseMove={(e) => onEnter(e, b.id)}
              onMouseEnter={(e) => onEnter(e, b.id)}
              style={{ cursor: "pointer" }}>
              <rect
                x={b.x - b.w / 2} y={b.y - b.h / 2} width={b.w} height={b.h}
                rx="1.4" fill={fill}
                stroke={isHovered ? "#38bdf8" : "#475569"}
                strokeWidth={isHovered ? "0.8" : "0.3"}
              />
              <text x={b.x} y={b.y - 0.5} fontSize="2.1" fill="#e2e8f0"
                textAnchor="middle">{shortName(b.label)}</text>
              <text x={b.x} y={b.y + 2.6} fontSize="2.6" fill="#f8fafc"
                textAnchor="middle" fontWeight="700">{label || ""}</text>
            </g>
          );
        })}
      </svg>

      {hover && hoveredBuilding && (
        <FloorTooltip
          building={hoveredBuilding}
          crowd={crowdByBuilding.get(hover.buildingId)}
          incidentFloors={incidentByBuildingFloor.get(hover.buildingId)}
          left={hover.left}
          top={hover.top}
        />
      )}

      {mode === "incident" ? (
        <div className="legend">
          <span><i className="swatch" style={{ background: "#b91c1c" }} /> Potential impact</span>
          <span><i className="swatch" style={{ background: "#d97706" }} /> Conflicting evidence</span>
          <span><i className="swatch" style={{ background: "#475569" }} /> Reports present</span>
          <span className="muted">Hover a building for per-floor detail. Report density does not prove danger.</span>
        </div>
      ) : (
        <div className="legend">
          <span><i className="swatch" style={{ background: "#38bdf8" }} /> Higher device count</span>
          <span><i className="swatch" style={{ background: "#1e293b" }} /> Low / none</span>
          <span className="muted">Hover a building for per-floor detail. Estimated devices; not exact occupancy.</span>
        </div>
      )}
    </div>
  );
}

function FloorTooltip({
  building, crowd, incidentFloors, left, top,
}: {
  building: MapBuilding;
  crowd?: CrowdBuilding;
  incidentFloors?: Map<number | null, IncidentHeatCell>;
  left: number;
  top: number;
}) {
  // Union of floor numbers from crowd data and incident cells.
  const floors = new Set<number>();
  crowd?.floors.forEach((f) => floors.add(f.floor));
  incidentFloors?.forEach((_, fl) => { if (fl != null) floors.add(fl); });
  const sorted = [...floors].sort((a, b) => a - b);

  const crowdByFloor = new Map((crowd?.floors ?? []).map((f) => [f.floor, f]));
  const buildingWide = incidentFloors?.get(null); // whole-building reports

  // Keep the tooltip inside the map horizontally.
  const clampedLeft = Math.min(left + 14, 560);

  return (
    <div className="floor-tooltip" style={{ left: clampedLeft, top: top + 12 }} role="tooltip">
      <div className="ft-title">{building.label}</div>
      <table className="ft-table">
        <thead>
          <tr><th>Floor</th><th>Devices</th><th>Reports</th><th>Status</th></tr>
        </thead>
        <tbody>
          {sorted.length === 0 && (
            <tr><td colSpan={4} className="muted">No floor data.</td></tr>
          )}
          {sorted.map((fl) => {
            const c = crowdByFloor.get(fl);
            const inc = incidentFloors?.get(fl);
            return (
              <tr key={fl}>
                <td>F{fl}</td>
                <td>{c ? c.count : 0}{c && !c.fresh ? " ⚠" : ""}</td>
                <td>{inc ? inc.report_count : 0}
                  {inc && inc.distinct_sources > 0 ? ` (${inc.distinct_sources} src)` : ""}</td>
                <td>{inc ? <span className={"ft-badge " + inc.system_assessment}>{shortStatus(inc.system_assessment)}</span> : <span className="muted">—</span>}</td>
              </tr>
            );
          })}
          {buildingWide && (
            <tr>
              <td>All</td>
              <td className="muted">—</td>
              <td>{buildingWide.report_count}
                {buildingWide.distinct_sources > 0 ? ` (${buildingWide.distinct_sources} src)` : ""}</td>
              <td><span className={"ft-badge " + buildingWide.system_assessment}>{shortStatus(buildingWide.system_assessment)}</span></td>
            </tr>
          )}
        </tbody>
      </table>
      <div className="ft-foot">
        Total devices: {crowd?.total ?? 0}
        {crowd && crowd.stale_or_unknown > 0 ? ` · ${crowd.stale_or_unknown} stale/unknown` : ""}
      </div>
    </div>
  );
}

function shortStatus(a: string): string {
  return a === "potential_impact" ? "Potential"
    : a === "conflicting_evidence" ? "Conflicting" : "Insufficient";
}

function shortName(label: string): string {
  const map: Record<string, string> = {
    "Campus Center": "Campus Ctr",
    "Healey Library": "Healey",
    "McCormack Hall": "McCormack",
    "Wheatley Hall": "Wheatley",
    "University Hall": "Univ Hall",
    "Integrated Sciences Complex": "ISC",
    "Quinn Administration": "Quinn",
    "Clark Athletic Center": "Clark",
    "Residence Hall East": "Res East",
    "Residence Hall West": "Res West",
  };
  return map[label] ?? label;
}
