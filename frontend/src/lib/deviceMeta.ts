// Visual + hierarchy metadata per device type. `tier` drives the top-down
// layered layout in the site view (0 = network edge, higher = access/hosts).

import {
  Router,
  Network,
  Share2,
  Wifi,
  Shield,
  Layers,
  Boxes,
  Server,
  Cpu,
  type LucideIcon,
} from "lucide-react";

export interface DeviceMeta {
  label: string;
  icon: LucideIcon;
  tier: number;
}

const META: Record<string, DeviceMeta> = {
  router: { label: "Edge Router", icon: Router, tier: 0 },
  edge_router: { label: "Edge Router", icon: Router, tier: 0 },
  firewall: { label: "Firewall", icon: Shield, tier: 0 },
  core_switch: { label: "Core Switch", icon: Network, tier: 1 },
  spine: { label: "Spine", icon: Layers, tier: 1 },
  distribution_switch: { label: "Distribution", icon: Share2, tier: 2 },
  leaf: { label: "Leaf", icon: Boxes, tier: 2 },
  access_switch: { label: "Access Switch", icon: Network, tier: 3 },
  access_point: { label: "Access Point", icon: Wifi, tier: 4 },
  server: { label: "Server", icon: Server, tier: 4 },
};

const FALLBACK: DeviceMeta = { label: "Device", icon: Cpu, tier: 3 };

export function deviceMeta(deviceType: string): DeviceMeta {
  return META[deviceType] ?? FALLBACK;
}

export const MAX_TIER = 4;
