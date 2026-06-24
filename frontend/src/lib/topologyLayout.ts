// Deterministic layered layout for the site view: devices are bucketed into
// horizontal tiers (edge -> core -> distribution -> access -> hosts) and spread
// evenly within each tier. Pure function so renders are stable.

import { deviceMeta } from "./deviceMeta";
import type { SiteDevice } from "./types";

export interface PositionedDevice extends SiteDevice {
  x: number;
  y: number;
  tier: number;
}

const TIER_GAP_Y = 170;
const NODE_GAP_X = 210;
const TOP_PAD = 40;

export function layoutSiteDevices(devices: SiteDevice[]): PositionedDevice[] {
  const byTier = new Map<number, SiteDevice[]>();
  for (const d of devices) {
    const tier = deviceMeta(d.device_type).tier;
    const arr = byTier.get(tier) ?? [];
    arr.push(d);
    byTier.set(tier, arr);
  }

  const tiers = [...byTier.keys()].sort((a, b) => a - b);
  const widest = Math.max(
    1,
    ...tiers.map((t) => (byTier.get(t) as SiteDevice[]).length),
  );
  const canvasWidth = widest * NODE_GAP_X;

  const positioned: PositionedDevice[] = [];
  tiers.forEach((tier, tierIdx) => {
    const row = (byTier.get(tier) as SiteDevice[]).sort((a, b) =>
      a.id.localeCompare(b.id),
    );
    const rowWidth = row.length * NODE_GAP_X;
    const offsetX = (canvasWidth - rowWidth) / 2;
    row.forEach((d, i) => {
      positioned.push({
        ...d,
        tier,
        x: offsetX + i * NODE_GAP_X,
        y: TOP_PAD + tierIdx * TIER_GAP_Y,
      });
    });
  });

  return positioned;
}

// Global map: normalised (0-1) site positions scaled into a viewport box.
export function scaleSitePosition(
  pos: { x: number; y: number },
  width = 900,
  height = 560,
): { x: number; y: number } {
  return { x: pos.x * width, y: pos.y * height };
}
